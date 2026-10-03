"""Score work vectors with the SDG head: 17 calibrated scores per work, and the goals OpenAlex serves.

    python -m classifier.head --vectors benchmarks/data/committee/vectors.npz --out scores.jsonl
    python -m classifier.head --check          # recompute the shipped head scores from the shipped vectors

The head is a JSON file in models/ (format: models/README.md). For each goal j:

    raw_j   = sigmoid(W_j . x + b_j)                       x = the work's 1024-d Qwen3 vector
    score_j = interp(raw_j, iso_x_j, iso_y_j), clipped     the per-goal isotonic calibration
    served  = every goal with score_j >= threshold_j (0.4 for all 17), highest score first

This is the arithmetic of production/sdg_jev_head_score.py, the notebook that tags every work in OpenAlex, without
Spark. One difference: the notebook holds the isotonic breakpoints in float32 and this module in float64, as the evals
did, which moves a score by at most about 0.002. Needs numpy.
"""
import argparse
import gzip
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = os.path.join(ROOT, "models", "sdg_jev_head_v2.json")


class Head:
    def __init__(self, path=DEFAULT_MODEL):
        art = json.load(open(path))
        self.version = art["model_version"]
        self.W = np.asarray(art["W"], np.float32)
        self.b = np.asarray(art["b"], np.float32)
        self.goals = art["goals"]
        self.iso = [(np.asarray(g["iso_x"], np.float64), np.asarray(g["iso_y"], np.float64)) for g in self.goals]
        self.thresholds = np.asarray([g["threshold"] for g in self.goals], np.float32)
        assert self.W.shape == (17, art["input_dim"])

    def scores(self, X):
        """X: (n, 1024) float32 -> (n, 17) calibrated scores in [0, 1], goal 1 first."""
        raw = 1.0 / (1.0 + np.exp(-(np.asarray(X, np.float32) @ self.W.T + self.b)))
        return np.stack([np.clip(np.interp(raw[:, j], *self.iso[j]), 0, 1) for j in range(17)], axis=1)

    def served(self, row):
        """One work's 17 scores -> the sustainable_development_goals list OpenAlex serves."""
        keep = [j for j in range(17) if row[j] >= self.thresholds[j]]
        keep.sort(key=lambda j: (-row[j], j))
        return [{"id": self.goals[j]["id"], "display_name": self.goals[j]["display_name"], "score": round(float(row[j]), 4)}
                for j in keep]


def check():
    """The shipped head_v1 / head_v2 scores of the committee eval and the survey set, recomputed from the shipped vectors."""
    ok = True
    for name, vecs, key in (("committee", "benchmarks/data/committee/vectors.npz", "work_id"),
                            ("aurora_survey", "benchmarks/data/aurora_survey/vectors.npz", "work_id")):
        z = np.load(os.path.join(ROOT, vecs)); ids = z["ids"].tolist()
        for v in ("v1", "v2"):
            H = Head(os.path.join(ROOT, "models", f"sdg_jev_head_{v}.json")).scores(z["X"])
            mine = {f"W{i}": row for i, row in zip(ids, H)}
            diff, n = 0.0, 0
            with gzip.open(os.path.join(ROOT, f"benchmarks/data/{name}/head_{v}.jsonl.gz"), "rt") as f:
                for line in f:
                    r = json.loads(line)
                    if r[key] in mine:
                        n += 1
                        diff = max(diff, max(abs(float(r["p"][str(g)]) - round(float(mine[r[key]][g - 1]), 5)) for g in range(1, 18)))
            good = diff <= 1e-5
            ok &= good
            print(f"{name} head {v}: {n:,} works, max |score difference| {diff:.6f} {'ok' if good else 'MISMATCH'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vectors", help=".npz with ids (int64, the numeric part of the work id) and X (n x 1024 float32)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", help="JSONL: {work_id, model_version, scores, sustainable_development_goals}")
    ap.add_argument("--check", action="store_true", help="recompute the shipped scores and compare")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    if not (a.vectors and a.out):
        ap.error("--vectors and --out are required (or --check)")
    head = Head(a.model)
    z = np.load(a.vectors)
    H = head.scores(z["X"])
    with open(a.out, "w") as f:
        for i, row in zip(z["ids"].tolist(), H):
            f.write(json.dumps({"work_id": f"W{i}", "model_version": head.version,
                                "scores": {str(g): round(float(row[g - 1]), 5) for g in range(1, 18)},
                                "sustainable_development_goals": head.served(row)}) + "\n")
    tagged = int((H >= head.thresholds).any(1).sum())
    print(f"wrote {a.out}: {len(H):,} works, {tagged:,} with at least one goal ({head.version})")


if __name__ == "__main__":
    main()
