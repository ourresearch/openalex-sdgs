"""Train the SDG head from Jev's labels and the work vectors: 17 logistic regressions plus isotonic calibration.

    python -m classifier.fetch_works --ids training/data/labels.jsonl.gz --out train_works.jsonl      # 200,000 works
    python -m classifier.embed --input train_works.jsonl --out train_vectors.npz                    # GPU recommended
    python training/train.py --vectors train_vectors.npz --version v2 --out my_head_v2.json
    python training/train.py --vectors train_vectors.npz --version v2 --out my_head_v2.json --compare models/sdg_jev_head_v2.json

Needs numpy and scikit-learn (the shipped heads were fit with scikit-learn 1.9.1). The recipe, per goal g:

  1. Labels: Jev's probability for g (training/data/labels.jsonl.gz). Goal 9 uses `sdg9_v2` where present (both heads);
     goal 15 uses `sdg15_v2` where present (v2 only). Works never relabelled keep their first answer.
  2. Split: the 20,000 `cal` and 20,000 `eval` ids in training/data/splits.json.gz are held out; the rest train.
  3. Fit: class-balanced logistic regression (C = 1, lbfgs, 500 iterations) on training works with p >= 0.7 (positive)
     or p <= 0.3 (negative); the uncertain band is dropped.
  4. Calibrate: isotonic regression of the raw score on the `cal` works against Jev's decision (p >= 0.5).
  5. Serve: score = the calibrated score, goal tagged at 0.4 (one threshold for all 17; benchmarks/README.md says why).

Prints fidelity against Jev on the `eval` works (AUC, ECE before and after calibration). The vectors are not shipped
(200,000 x 1024 floats); they come from classifier/embed.py, so a retrained head will be close to the shipped one but
not bit for bit (--compare reports how close).
"""
import argparse
import datetime
import gzip
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "training", "data")
NAMES = {1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education", 5: "Gender equality",
         6: "Clean water and sanitation", 7: "Affordable and clean energy", 8: "Decent work and economic growth",
         9: "Industry, innovation and infrastructure", 10: "Reduced inequalities", 11: "Sustainable cities and communities",
         12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water", 15: "Life on land",
         16: "Peace, justice, and strong institutions", 17: "Partnerships for the goals"}
POS, NEG, THRESHOLD = 0.7, 0.3, 0.4


def ece(p, y, bins=10):
    p, y, e = np.asarray(p), np.asarray(y, float), 0.0
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def load_labels(version):
    lab = {}
    with gzip.open(f"{DATA}/labels.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            y = [r["sdg"][str(g)] for g in range(1, 18)]
            if "sdg9_v2" in r:
                y[8] = r["sdg9_v2"]
            if version == "v2" and "sdg15_v2" in r:
                y[14] = r["sdg15_v2"]
            lab[int(r["work_id"].lstrip("W"))] = np.asarray(y, np.float32)
    return lab


def main():
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vectors", required=True, help=".npz with ids and X, one row per training work (classifier/embed.py)")
    ap.add_argument("--version", choices=("v1", "v2"), default="v2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare", help="a shipped head JSON to compare against")
    a = ap.parse_args()

    z = np.load(a.vectors); ids, X = z["ids"], z["X"].astype(np.float32)
    lab = load_labels(a.version)
    keep = np.array([int(i) in lab for i in ids]); ids, X = ids[keep], X[keep]
    Y = np.stack([lab[int(i)] for i in ids])
    with gzip.open(f"{DATA}/splits.json.gz", "rt") as f:
        sp = json.load(f)
    cal, ev = set(sp["cal"]), set(sp["eval"])
    split = np.array(["cal" if int(i) in cal else "eval" if int(i) in ev else "train" for i in ids])
    tr, ca, evm = split == "train", split == "cal", split == "eval"
    print(f"{len(ids):,} works with a vector and labels: train {tr.sum():,}, cal {ca.sum():,}, eval {evm.sum():,}")

    W = np.zeros((17, X.shape[1]), np.float32); b = np.zeros(17, np.float32); goals = []
    print("| SDG | n train | AUC vs Jev (eval) | ECE raw | ECE calibrated |\n|---|---|---|---|---|")
    for j, g in enumerate(range(1, 18)):
        y = Y[:, j]; m = tr & ((y >= POS) | (y <= NEG))
        clf = LogisticRegression(max_iter=500, C=1.0, class_weight="balanced").fit(X[m], (y[m] >= POS).astype(int))
        W[j], b[j] = clf.coef_[0], clf.intercept_[0]
        raw_ca, raw_ev = clf.predict_proba(X[ca])[:, 1], clf.predict_proba(X[evm])[:, 1]
        ir = IsotonicRegression(out_of_bounds="clip").fit(raw_ca, (y[ca] >= 0.5).astype(int))
        yev = (y[evm] >= 0.5).astype(int)
        auc = roc_auc_score(yev, raw_ev) if 0 < yev.sum() < len(yev) else float("nan")
        print(f"| {g} {NAMES[g]} | {m.sum():,} | {auc:.3f} | {ece(raw_ev, yev):.3f} | {ece(ir.predict(raw_ev), yev):.3f} |")
        goals.append({"n": g, "id": f"https://metadata.un.org/sdg/{g}", "display_name": NAMES[g], "threshold": THRESHOLD,
                      "iso_x": [round(float(v), 6) for v in ir.X_thresholds_], "iso_y": [round(float(v), 6) for v in ir.y_thresholds_]})
    art = {"model_version": f"sdg-jev-head-{a.version}-retrained", "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "teacher": "jev-1.13.0 (training/data/labels.jsonl.gz)", "input": "Qwen3-Embedding-0.6B work vector (classifier/embed.py)",
           "input_dim": int(X.shape[1]), "score": "sigmoid(W·x + b) -> per-goal isotonic (np.interp on iso_x/iso_y, clipped) = p; label if p >= threshold",
           "goals": goals, "W": [[round(float(v), 6) for v in W[j]] for j in range(17)], "b": [round(float(v), 6) for v in b]}
    json.dump(art, open(a.out, "w"))
    print(f"wrote {a.out}")

    if a.compare:
        import sys
        sys.path.insert(0, ROOT)
        from classifier.head import Head
        zc = np.load(os.path.join(ROOT, "benchmarks/data/committee/vectors.npz"))
        mine, ref = Head(a.out).scores(zc["X"]), Head(a.compare).scores(zc["X"])
        agree = ((mine >= THRESHOLD) == (ref >= THRESHOLD)).mean()
        print(f"vs {a.compare} on the 2,598 committee works: max |score difference| {np.abs(mine - ref).max():.4f}, "
              f"tag agreement over (work, goal) pairs {100 * agree:.2f}%")


if __name__ == "__main__":
    main()
