"""Score the two public benchmarks: OSDG-CD and the Aurora survey set (standard library only, a few seconds).

    python3 benchmarks/score_public.py          # prints every table; writes benchmarks/data/public_results.json

OSDG-CD (benchmarks/data/osdg/): 23,362 text excerpts, one volunteer-voted goal each (SDGs 1-15), the rows with
positive minus negative votes >= 2 in the 2022.07 release. Scored with the protocol of Kashnitsky et al. 2024 (QSS,
arXiv 2209.07285): a predicted (excerpt, goal) pair is right if it is the gold goal; micro F1 over pairs, macro F1 =
mean of per-goal F1. Because the gold has one goal per excerpt, every second goal a model emits counts as wrong, so we
also report top-1 accuracy (the model's highest-scoring goal of all 17 is the gold one) and single-label mode (emit only the
highest-scoring goal, if it clears the threshold).

Aurora survey set (benchmarks/data/aurora_survey/): researchers' accept/reject votes on (paper, goal) pairs, 2019-2020.
Two views:
  - Kashnitsky protocol: gold = pairs with more yes than no votes; any goal a model emits that was never asked about
    counts as a false positive.
  - Surveyed pairs: only the (paper, goal) questions the researchers answered with a clear majority (yes != no);
    AUC, precision / recall / F1 at a threshold, and precision at Aurora's recall.

Models: Aurora SDG-BERT (OSDG: run locally, the model OpenAlex served; survey: the tags OpenAlex served), Jev direct
(zero-shot, the 17-goal request in classifier/jev_request.py, SEPTEMBER_LABELS), and on the survey set the heads v1 and v2.
The heads cannot be scored on OSDG-CD: they read OpenAlex's work vectors, and the excerpts are not works.
"""
import bisect
import collections
import gzip
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def rows(path):
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def preds_of(path):
    return {r["id"]: {int(k): float(v) for k, v in r["p"].items()} for r in rows(path) if r.get("p")}


def kashnitsky(preds, gold, goals, T, single=False):
    """Micro / macro F1, P, R over (doc, goal) pairs on the docs that have predictions."""
    tp, fp, fn = collections.Counter(), collections.Counter(), collections.Counter()
    for d, G in gold.items():
        if d not in preds:
            continue
        p = preds[d]
        if single:
            top = max(goals, key=lambda g: p.get(g, 0.0))
            P = {top} if p.get(top, 0.0) >= T else set()
        else:
            P = {g for g in goals if p.get(g, 0.0) >= T}
        G = G & set(goals)
        for g in P & G: tp[g] += 1
        for g in P - G: fp[g] += 1
        for g in G - P: fn[g] += 1
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    f1s = [2 * tp[g] / max(1, 2 * tp[g] + fp[g] + fn[g]) for g in goals if tp[g] + fn[g]]
    return {"T": T, "micro_f1": 100 * 2 * TP / max(1, 2 * TP + FP + FN), "macro_f1": 100 * sum(f1s) / max(1, len(f1s)),
            "P": 100 * TP / max(1, TP + FP), "R": 100 * TP / max(1, TP + FN)}


def top1(preds, gold):
    """Share of docs whose highest-scoring goal (over all 17) is a gold goal."""
    docs = [d for d in gold if d in preds]
    return 100 * sum(max(preds[d], key=preds[d].get) in gold[d] for d in docs) / max(1, len(docs))


def labels_per_doc(preds, docs, T, goals=range(1, 18)):
    return sum(sum(preds[d].get(g, 0.0) >= T for g in goals) for d in docs) / max(1, len(docs))


def auc(scores, labels):
    neg = sorted(s for s, y in zip(scores, labels) if not y)
    pos = [s for s, y in zip(scores, labels) if y]
    n = sum(bisect.bisect_left(neg, p) + 0.5 * (bisect.bisect_right(neg, p) - bisect.bisect_left(neg, p)) for p in pos)
    return n / max(1, len(pos) * len(neg))


def prf_at(sc, lab, T):
    tp = sum(s >= T and y for s, y in zip(sc, lab)); fp = sum(s >= T and not y for s, y in zip(sc, lab))
    fn = sum(s < T and y for s, y in zip(sc, lab))
    p, r = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return 100 * p, 100 * r, 100 * 2 * p * r / max(1e-9, p + r)


def p_at_recall(sc, lab, rec):
    """Precision at the threshold where recall first reaches `rec` (ties at that score all count as tagged)."""
    k = math.ceil(rec * sum(lab)); t = sorted((s for s, y in zip(sc, lab) if y), reverse=True)[k - 1]
    tp = sum(s >= t and y for s, y in zip(sc, lab)); tags = sum(s >= t for s in sc)
    return 100 * tp / tags, t


def table(head, lines):
    print("| " + " | ".join(head) + " |"); print("|" + "---|" * len(head))
    for l in lines: print("| " + " | ".join(l) + " |")
    print()


def f1(x): return f"{x:.1f}"


def main():
    out = {}
    # ---------------------------------------------------------------- OSDG-CD
    gold = {r["text_id"]: {r["sdg"]} for r in rows(f"{DATA}/osdg/gold.jsonl.gz")}
    goals = list(range(1, 16))
    models = {"aurora": ("Aurora SDG-BERT, run here", preds_of(f"{DATA}/osdg/aurora.jsonl.gz"), (0.4, 0.3)),
              "jev": ("Jev direct", preds_of(f"{DATA}/osdg/jev.jsonl.gz"), (0.5, 0.6))}
    print(f"## OSDG-CD: {len(gold):,} excerpts, one gold goal each\n")
    lines, res = [], {}
    for m, (name, P, ts) in models.items():
        acc = top1(P, gold); res[m] = {"top1": acc, "at": {}}
        for T in ts:
            k = kashnitsky(P, gold, goals, T); s = kashnitsky(P, gold, goals, T, single=True)
            res[m]["at"][str(T)] = {**k, "single_label_micro_f1": s["micro_f1"],
                                    "labels_per_excerpt": labels_per_doc(P, [d for d in gold if d in P], T, goals)}
            lines.append([f"{name}, T = {T}", f1(k["micro_f1"]), f1(k["macro_f1"]), f1(k["P"]), f1(k["R"]), f1(acc),
                          f1(s["micro_f1"]), f"{res[m]['at'][str(T)]['labels_per_excerpt']:.2f}"])
    table(["Model", "micro F1", "macro F1", "P", "R", "top-1 acc", "single-label micro F1", "goals per excerpt"], lines)
    out["osdg"] = {"excerpts": len(gold), **res}

    # ---------------------------------------------------------------- Aurora survey set
    pairs = [r for r in rows(f"{DATA}/aurora_survey/pairs.jsonl.gz") if r["doi"]]
    gold, neg = collections.defaultdict(set), collections.defaultdict(set)
    for r in pairs:
        if r["yes"] > r["no"]: gold[r["doi"]].add(r["sdg"])
        elif r["no"] > r["yes"]: neg[r["doi"]].add(r["sdg"])
    goals = list(range(1, 18))
    asked_docs = {r["doi"] for r in pairs if r["yes"] != r["no"]}
    models = {"aurora_served": "Aurora, as served by OpenAlex", "jev": "Jev direct",
              "head_v1": "Head v1", "head_v2": "Head v2 (served)"}
    P = {m: preds_of(f"{DATA}/aurora_survey/{m}.jsonl.gz") for m in models}
    print(f"## Aurora survey set, Kashnitsky protocol: {len(gold):,} papers with an accepted goal\n")
    lines, res = [], {}
    for m, name in models.items():
        ts = (0.5, 0.6) if m == "jev" else (0.4,)
        acc = top1(P[m], gold); res[m] = {"top1": acc, "at": {}}
        for T in ts:
            k = kashnitsky(P[m], gold, goals, T)
            k["labels_per_doc"] = labels_per_doc(P[m], [d for d in asked_docs if d in P[m]], T)
            res[m]["at"][str(T)] = k
            lines.append([f"{name}, T = {T}", f1(k["micro_f1"]), f1(k["macro_f1"]), f1(k["P"]), f1(k["R"]), f1(acc), f"{k['labels_per_doc']:.2f}"])
    table(["Model", "micro F1", "macro F1", "P", "R", "top-1 acc", "goals per surveyed paper"], lines)
    out["survey_kashnitsky"] = res

    asked = [(r["doi"], r["sdg"], r["yes"] > r["no"]) for r in pairs if r["yes"] != r["no"]]
    common = [(d, g, y) for d, g, y in asked if all(d in P[m] for m in models)]
    lab = [y for _, _, y in common]
    sc = {m: [P[m][d].get(g, 0.0) for d, g, _ in common] for m in models}
    rec_aurora = prf_at(sc["aurora_served"], lab, 0.4)[1] / 100
    print(f"## Aurora survey set, surveyed pairs: {len(common):,} (paper, goal) questions with a clear majority "
          f"({sum(lab):,} yes, {len(lab) - sum(lab):,} no) on {len({d for d, _, _ in common}):,} papers\n")
    lines, res = [], {"pairs": len(common), "yes": sum(lab), "papers": len({d for d, _, _ in common}), "aurora_recall_at_0.4": rec_aurora}
    for m, name in models.items():
        p, r, f = prf_at(sc[m], lab, 0.4); pr, t = p_at_recall(sc[m], lab, rec_aurora)
        docs = {d for d, _, _ in common}
        res[m] = {"auc": auc(sc[m], lab), "P_at_0.4": p, "R_at_0.4": r, "F1_at_0.4": f, "P_at_aurora_recall": pr,
                  "threshold_at_aurora_recall": t, "labels_per_paper_at_0.4": labels_per_doc(P[m], docs, 0.4)}
        lines.append([name, f"{res[m]['auc']:.3f}", f"{f1(f)} ({f1(p)} / {f1(r)})", f1(pr), f"{res[m]['labels_per_paper_at_0.4']:.2f}"])
    table(["Model", "AUC", "F1 at 0.4 (P / R)", f"precision at Aurora's recall ({rec_aurora:.3f})", "goals per paper at 0.4"], lines)
    out["survey_pairs"] = res

    with open(f"{DATA}/public_results.json", "w") as f:
        json.dump(out, f, indent=1, default=lambda x: round(x, 4))
    print("wrote benchmarks/data/public_results.json")


if __name__ == "__main__":
    main()
