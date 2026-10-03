"""Held-out judged works (multi-label, all 17 goals): pooled P/R/F1 at thresholds, per-goal F1, pooled AUC. usage: score_judged.py PRED [PRED2]   e.g. score_judged.py pred_seed_judged.jsonl.gz pred_best_judged.jsonl.gz"""
import gzip, json, os, sys, bisect
HERE = os.path.dirname(os.path.abspath(__file__))
gold = {r['id']: {int(k): v for k, v in r['gold'].items()} for r in json.load(open(os.path.join(HERE, 'test_judged_gold.json')))}
G = list(range(1, 18))
def load(fn):
    d = {}
    for l in (gzip.open(fn, 'rt') if fn.endswith('.gz') else open(fn)):
        r = json.loads(l)
        if 'p' in r: d[r['id']] = {int(k): float(v) for k, v in r['p'].items()}
    return d
def auc(sc, lab):
    pos = [s for s, y in zip(sc, lab) if y]; neg = sorted(s for s, y in zip(sc, lab) if not y); n = 0.0
    for p in pos: n += bisect.bisect_left(neg, p) + 0.5 * (bisect.bisect_right(neg, p) - bisect.bisect_left(neg, p))
    return n / max(1, len(pos) * len(neg))
res = {}
for fn in sys.argv[1:]:
    P = load(fn); ids = [i for i in gold if i in P]
    sc = [P[i][g] for i in ids for g in G]; lab = [gold[i][g] for i in ids for g in G]
    print(f"\n{fn}: {len(ids)} works, {sum(lab)} gold pairs of {len(lab)}; pooled AUC {auc(sc, lab):.3f}")
    print(f"  {'T':>4} {'P':>6} {'R':>6} {'F1':>6}")
    per = {}
    for T in [0.4, 0.5, 0.6, 0.7]:
        tp = sum(s >= T and y for s, y in zip(sc, lab)); fp = sum(s >= T and not y for s, y in zip(sc, lab)); fn_ = sum(s < T and y for s, y in zip(sc, lab))
        p = tp / max(1, tp + fp); r = tp / max(1, tp + fn_); print(f"  {T:4.1f} {p*100:6.1f} {r*100:6.1f} {2*p*r/max(1e-9,p+r)*100:6.1f}")
    for g in G:
        tp = sum(P[i][g] >= 0.5 and gold[i][g] for i in ids); fp = sum(P[i][g] >= 0.5 and not gold[i][g] for i in ids); fn_ = sum(P[i][g] < 0.5 and gold[i][g] for i in ids)
        per[g] = (2 * tp / max(1, 2 * tp + fp + fn_), tp + fn_)
    res[fn] = per
if len(res) == 2:
    a, b = sys.argv[1:3]; print(f"\nper-goal F1 at 0.5 ({a} vs {b}): goal n | F1a F1b")
    wins = 0
    for g in G:
        fa, n = res[a][g]; fb, _ = res[b][g]; wins += fb > fa; print(f"  {g:2d} {n:3d} | {fa*100:5.1f} {fb*100:5.1f} {'+' if fb > fa else '-' if fb < fa else '='}")
    print(f"  {b} wins {wins}/17")
