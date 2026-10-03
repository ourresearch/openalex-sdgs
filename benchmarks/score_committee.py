"""Score the committee eval: Aurora, Jev direct and the head against the committee's labels.

    python3 benchmarks/score_committee.py                # head v2 (served): writes benchmarks/data/committee/scores_v2.{md,json}
    python3 benchmarks/score_committee.py --head v1      # head v1, the head the go rule was pre-registered on

Reads benchmarks/data/committee/: the judges' rows (opus, sol, fable .jsonl.gz; last row per work wins), the works
file (set, slices, Aurora's served tags), Jev direct's and the head's scores; and benchmarks/data/september/ for the
September labels (S1 only). Needs numpy.

Committee label per (work, goal): Opus and Sol agree -> that verdict; they disagree -> Fable's verdict; Fable refused /
errored / not yet run, or either judge failed on the work -> `unresolved`. Every label-dependent number is computed twice,
unresolved counted as "no" and as "yes" (the bracket).

Models, each at its served threshold (label if score >= threshold):
  Aurora     served tags in the works file (`aurora`, scores >= 0.4 only), threshold 0.4
  Jev direct p >= 0.5 (S1: the SDG 9 variant-b run on the 598; S2: a fresh run)
  Head       calibrated score >= 0.4 (head_v1 or head_v2 .jsonl.gz, from models/ and the work vectors)
September labels (S1 only): one Opus 5 pass, 2026-09-21 (benchmarks/data/september/judge_opus5.jsonl.gz).

Pre-registered rules (harness/PREREGISTRATION.md): go rule on S2 = head pooled F1 >= Aurora's + 0.20 AND head F1 > Aurora F1
on >= 13 of 17 goals; title-only rule = head precision on S2 title-only works (no abstract in the text the judges saw)
< 0.60. Both are evaluated under both brackets. The F1-maximising head threshold is printed as a diagnostic, never a choice.
"""
import argparse, collections, gzip, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data", "committee"); SEPT = os.path.join(HERE, "data", "september")
sys.path.insert(0, os.path.join(ROOT, "harness"))
import rubric as R

GOALS = list(range(1, 18))
MODELS = ("aurora", "jev", "head")
HEAD = "v2"   # set by --head
NAME = {"aurora": "Aurora (served, 0.4)", "jev": "Jev direct (0.5)", "head": "Head v2 (0.4)"}
SHORT = {"aurora": "Aurora", "jev": "Jev", "head": "Head"}
THRESH = {"aurora": 0.4, "jev": 0.5, "head": 0.4}
BRACKETS = ("no", "yes")
SET_SIZE = {"s1": 598, "s2": 2000}
GO_GAP, GO_WINS, TITLE_P = 0.20, 13, 0.60


# ---------------------------------------------------------------- loading
def load_jsonl(path):
    """Rows of a jsonl(.gz) file; lines that don't parse (a run still appending) are counted, not fatal."""
    rows, bad = [], 0
    if os.path.exists(path):
        with (gzip.open(path, "rt") if path.endswith(".gz") else open(path)) as f:
            for line in f:
                if not line.strip(): continue
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: bad += 1
    return rows, bad


def vec(d):
    return [float((d or {}).get(str(g)) or 0.0) for g in GOALS]


def load_inputs():
    works = {}
    for w in load_jsonl(f"{DATA}/works.jsonl.gz")[0]:
        w["_set"] = w["set"]; works[w["work_id"]] = w
    head = {r["work_id"]: vec(r["p"]) for r in load_jsonl(f"{DATA}/head_{HEAD}.jsonl.gz")[0] if r.get("p")}
    jev = {r["work_id"]: vec(r["p"]) for r in load_jsonl(f"{DATA}/jev.jsonl.gz")[0]
           if r.get("p") and works.get(r["work_id"], {}).get("_set") == r["set"]}
    sept = {r["work_id"]: [bool(r["yes"][str(g)]) for g in GOALS] for r in load_jsonl(f"{SEPT}/judge_opus5.jsonl.gz")[0] if r.get("yes")}
    return works, head, jev, sept


def load_run(run):
    st, bad = {}, {}
    for k in ("opus", "sol", "fable"):
        path = f"{run}/{k}.jsonl.gz"
        rows, bad[k] = load_jsonl(path if os.path.exists(path) else f"{run}/{k}.jsonl")   # shipped (.gz) or a fresh run
        st[k] = {r["work_id"]: r for r in rows}   # last row per work wins (committee.py rule)
    return st, bad


def committee_label(o, s, f):
    """(labels 1/0/None, sources) for one work; mirrors committee.merge(). Sources: agree | fable | unresolved:<cause>."""
    if o["status"] != "ok" or s["status"] != "ok":
        cause = "unresolved:" + ("opus_" + o["status"] if o["status"] != "ok" else "sol_" + s["status"])
        return [None] * 17, [cause] * 17
    lab, src = [], []
    for g in GOALS:
        vo, vs = o["verdict"][str(g)], s["verdict"][str(g)]
        if vo == vs: lab.append(int(vo == "yes")); src.append("agree")
        elif f and f["status"] == "ok" and str(g) in f.get("verdict", {}): lab.append(int(f["verdict"][str(g)] == "yes")); src.append("fable")
        else: lab.append(None); src.append("unresolved:fable_" + (f["status"] if f else "pending"))
    return lab, src


class SetData:
    """Everything for one set, restricted to works with both an Opus and a Sol row."""
    def __init__(self, name, works, run, head, jev, sept):
        self.name = name
        allw = [w for w in works.values() if w["_set"] == name]
        self.n_set = len(allw)
        op, so, fb = run["opus"], run["sol"], run["fable"]
        ws = [w for w in allw if w["work_id"] in op and w["work_id"] in so]
        self.ws = ws; self.ids = [w["work_id"] for w in ws]; n = len(ws)
        self.n = n
        self.L = np.full((n, 17), np.nan); self.src = []
        self.O = np.full((n, 17), np.nan); self.S = np.full((n, 17), np.nan)
        self.stale_fable = 0
        for i, w in enumerate(ws):
            o, s, f = op[w["work_id"]], so[w["work_id"]], fb.get(w["work_id"])
            lab, src = committee_label(o, s, f)
            self.L[i] = [np.nan if x is None else x for x in lab]; self.src.append(src)
            if o["status"] == "ok": self.O[i] = [o["verdict"][str(g)] == "yes" for g in GOALS]
            if s["status"] == "ok": self.S[i] = [s["verdict"][str(g)] == "yes" for g in GOALS]
            if f and o["status"] == "ok" and s["status"] == "ok":
                dis = [g for g in GOALS if o["verdict"][str(g)] != s["verdict"][str(g)]]
                if sorted(f.get("disputed") or []) != dis: self.stale_fable += 1
        self.status = {k: collections.Counter(run[k][i]["status"] for i in self.ids if i in run[k]) for k in ("opus", "sol", "fable")}
        self.U = np.isnan(self.L)
        self.missing = {"head": sum(i not in head for i in self.ids), "jev": sum(i not in jev for i in self.ids)}
        z = [0.0] * 17
        self.score = {"aurora": np.array([vec(w.get("aurora")) for w in ws]).reshape(n, 17),
                      "jev": np.array([jev.get(i, z) for i in self.ids]).reshape(n, 17),
                      "head": np.array([head.get(i, z) for i in self.ids]).reshape(n, 17)}
        self.pred = {m: self.score[m] >= THRESH[m] for m in MODELS}
        self.sept = np.array([sept[i] if i in sept else [False] * 17 for i in self.ids], bool).reshape(n, 17)
        self.has_sept = np.array([i in sept for i in self.ids], bool)

    def gold(self, b):
        return (self.L == 1) | (self.U if b == "yes" else False)


# ---------------------------------------------------------------- metrics
def rnd(x, k=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), k)


def prf(tp, fp, fn):
    return (tp / (tp + fp) if tp + fp else None, tp / (tp + fn) if tp + fn else None,
            2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None)


def wilson(k, n, z=1.959964):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [rnd(c - h), rnd(c + h)]


def auc(score, gold):
    """Mann-Whitney AUC with average ranks for ties; None if a class is empty."""
    score = np.asarray(score, float).ravel(); gold = np.asarray(gold, bool).ravel()
    pos = int(gold.sum()); neg = gold.size - pos
    if not pos or not neg: return None
    _, inv, cnt = np.unique(score, return_inverse=True, return_counts=True)
    ranks = (np.cumsum(cnt) - (cnt - 1) / 2.0)[inv]
    return (ranks[gold].sum() - pos * (pos + 1) / 2.0) / (pos * neg)


def kappa(a, b):
    a = np.asarray(a, bool).ravel(); b = np.asarray(b, bool).ravel()
    if not a.size: return None, None
    po = float((a == b).mean()); pa, pb = a.mean(), b.mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    return po, (float((po - pe) / (1 - pe)) if pe < 1 else None)


def bootstrap_f1(cw, B, seed):
    """cw: model -> per-work (tp, fp, fn) arrays. Resamples works (same draws for every model, so differences are paired)."""
    n = len(next(iter(cw.values()))[0])
    if n < 2 or B <= 0: return {}
    rng = np.random.default_rng(seed)
    W = rng.multinomial(n, np.full(n, 1.0 / n), size=B).astype(np.float64)
    f1 = {}
    for m, (tp, fp, fn) in cw.items():
        TP, FP, FN = W @ tp, W @ fp, W @ fn; den = 2 * TP + FP + FN
        f1[m] = np.where(den > 0, 2 * TP / np.maximum(den, 1e-12), np.nan)
    def ci(x):
        x = x[np.isfinite(x)]
        return [rnd(np.percentile(x, 2.5)), rnd(np.percentile(x, 97.5))] if x.size else None
    out = {m: ci(v) for m, v in f1.items()}
    for a, b in (("head", "aurora"), ("jev", "aurora"), ("head", "jev")):
        if a in f1 and b in f1: out[f"{a}_minus_{b}"] = ci(f1[a] - f1[b])
    return out


def pooled(preds, G, B, seed):
    res, cw = {}, {}
    for m, P in preds.items():
        tp_w, fp_w, fn_w = (P & G).sum(1), (P & ~G).sum(1), (~P & G).sum(1)
        tp, fp, fn = int(tp_w.sum()), int(fp_w.sum()), int(fn_w.sum())
        p, r, f = prf(tp, fp, fn)
        res[m] = {"P": rnd(p), "P_ci": wilson(tp, tp + fp), "R": rnd(r), "R_ci": wilson(tp, tp + fn), "F1": rnd(f),
                  "tp": tp, "fp": fp, "fn": fn}
        cw[m] = (tp_w.astype(float), fp_w.astype(float), fn_w.astype(float))
    bs = bootstrap_f1(cw, B, seed) if G.shape[0] else {}
    for m in preds: res[m]["F1_ci"] = bs.get(m)
    res["F1_diff_ci"] = {k: v for k, v in bs.items() if "_minus_" in k}
    res["gold_pos"] = int(G.sum()); res["works"] = int(G.shape[0]); res["pairs"] = int(G.size)
    return res


def per_goal(D, G):
    out = {}
    for j, g in enumerate(GOALS):
        row = {"gold_pos": int(G[:, j].sum()), "unresolved": int(D.U[:, j].sum())}
        for m in MODELS:
            P = D.pred[m][:, j]; tp = int((P & G[:, j]).sum()); fp = int((P & ~G[:, j]).sum()); fn = int((~P & G[:, j]).sum())
            p, r, f = prf(tp, fp, fn)
            row[m] = {"P": rnd(p), "R": rnd(r), "F1": rnd(f), "tp": tp, "fp": fp, "fn": fn, "tags": tp + fp}
        for m in ("jev", "head"): row[f"{m}_auc"] = rnd(auc(D.score[m][:, j], G[:, j]))
        out[g] = row
    return out


def wins(pg, a, b):
    """Goals where model a's F1 is strictly above b's (a goal with no F1 for either side is not comparable)."""
    won = [g for g in GOALS if pg[g][a]["F1"] is not None and pg[g][b]["F1"] is not None and pg[g][a]["F1"] > pg[g][b]["F1"]]
    comparable = [g for g in GOALS if pg[g][a]["F1"] is not None and pg[g][b]["F1"] is not None]
    return {"won": len(won), "goals": won, "comparable": len(comparable)}


def label_dist(M):
    c = M.sum(1)
    if not c.size: return None
    return {"no_goal": rnd((c == 0).mean()), "one": rnd((c == 1).mean()), "two_plus": rnd((c >= 2).mean()), "mean_labels": rnd(c.mean(), 3)}


def calibration(p, G):
    p = p.ravel(); y = G.ravel().astype(float); b = np.minimum((p * 10).astype(int), 9)
    bins, ece = [], 0.0
    for k in range(10):
        m = b == k; n = int(m.sum())
        if not n: bins.append({"bin": f"{k / 10:.1f}-{(k + 1) / 10:.1f}", "n": 0}); continue
        mp, yr = float(p[m].mean()), float(y[m].mean()); ece += n / p.size * abs(mp - yr)
        bins.append({"bin": f"{k / 10:.1f}-{(k + 1) / 10:.1f}", "n": n, "mean_p": rnd(mp), "yes_rate": rnd(yr)})
    return {"bins": bins, "ece": rnd(ece) if p.size else None}


def best_threshold(p, G):
    grid = np.round(np.arange(0.05, 0.951, 0.01), 2); best = None; curve = []
    for t in grid:
        P = p >= t; tp = int((P & G).sum()); fp = int((P & ~G).sum()); fn = int((~P & G).sum())
        pr, rc, f = prf(tp, fp, fn); curve.append({"t": float(t), "P": rnd(pr), "R": rnd(rc), "F1": rnd(f)})
        if f is not None and (best is None or f > best["F1"] + 1e-12): best = {"t": float(t), "P": rnd(pr), "R": rnd(rc), "F1": f}
    if best: best["F1"] = rnd(best["F1"])
    return {"best": best, "at_0.4": next((c for c in curve if abs(c["t"] - 0.4) < 1e-9), None), "curve": curve}


def bracket_block(D, b, B, seed):
    G = D.gold(b)
    pg = per_goal(D, G)
    return {"pooled": pooled(D.pred, G, B, seed), "per_goal": pg,
            "wins": {"head_vs_aurora": wins(pg, "head", "aurora"), "jev_vs_aurora": wins(pg, "jev", "aurora"),
                     "head_vs_jev": wins(pg, "head", "jev")},
            "auc_pooled": {m: rnd(auc(D.score[m], G)) for m in ("jev", "head")},
            "head_calibration": calibration(D.score["head"], G),
            "labels_per_work": {"committee": label_dist(G), **{m: label_dist(D.pred[m]) for m in MODELS}},
            "head_best_threshold_diagnostic": best_threshold(D.score["head"], G)}


def slices_s2(D):
    has_abs = np.array([bool(w["has_abstract"]) for w in D.ws], bool)
    en = np.array([w.get("language") == "en" for w in D.ws], bool)
    xp = np.array([bool(w.get("is_xpac")) for w in D.ws], bool)
    vec_abs = np.array([bool(w.get("emb_has_abstract")) for w in D.ws], bool)
    return [("abstract", "With an abstract", has_abs), ("title_only", "Title only (no abstract shown to the judges)", ~has_abs),
            ("english", "English", en), ("other_language", "Other or unknown language", ~en),
            ("core", "Core (not xpac)", ~xp), ("xpac", "xpac", xp),
            ("head_vector_title_only", "Head vector built without an abstract (diagnostic)", ~vec_abs)]


def sub(D, mask):
    """A shallow SetData restricted to works in mask."""
    S = SetData.__new__(SetData)
    S.name = D.name; S.ws = [w for w, k in zip(D.ws, mask) if k]; S.ids = [i for i, k in zip(D.ids, mask) if k]; S.n = int(mask.sum())
    S.L, S.U, S.O, S.S, S.sept, S.has_sept = D.L[mask], D.U[mask], D.O[mask], D.S[mask], D.sept[mask], D.has_sept[mask]
    S.score = {m: v[mask] for m, v in D.score.items()}; S.pred = {m: v[mask] for m, v in D.pred.items()}
    S.src = [s for s, k in zip(D.src, mask) if k]
    return S


def judges_block(D, B, seed):
    both = ~np.isnan(D.O).any(1) & ~np.isnan(D.S).any(1)
    O, S = D.O[both] == 1, D.S[both] == 1
    po, kp = kappa(O, S)
    src = [s for s, k in zip(D.src, both) if k]
    Lb = D.L[both]
    dis = O != S
    fable_mask = np.array([[x == "fable" for x in r] for r in src], bool).reshape(O.shape)
    side = collections.Counter()
    side["opus"] = int((fable_mask & (Lb == O)).sum()); side["sol"] = int((fable_mask & (Lb == S)).sum())
    side["fable_yes"] = int((fable_mask & (Lb == 1)).sum()); side["fable_no"] = int((fable_mask & (Lb == 0)).sum())
    causes = collections.Counter(x for r in D.src for x in r if x.startswith("unresolved"))
    res = {"works": D.n, "works_both_ok": int(both.sum()), "pairs_both_ok": int(O.size),
           "pair_agreement": rnd(po), "kappa": rnd(kp),
           "yes_rate": {"opus": rnd(O.mean()) if O.size else None, "sol": rnd(S.mean()) if S.size else None,
                        "committee_resolved": rnd(float(np.nanmean(D.L))) if (~D.U).any() else None,
                        "fable_on_disputes": rnd(side["fable_yes"] / max(1, side["fable_yes"] + side["fable_no"]))},
           "works_with_dispute": int(dis.any(1).sum()), "disputed_pairs": int(dis.sum()),
           "fable_sided": dict(side), "unresolved_pairs": int(D.U.sum()), "unresolved_works": int(D.U.any(1).sum()),
           "unresolved_by_cause": dict(causes), "status": {k: dict(v) for k, v in D.status.items()}}
    # each single judge's own scoring of the three models, on the works both judges answered
    Db = sub(D, both)
    srcs = {"opus": Db.O == 1, "sol": Db.S == 1, "committee": Db.gold("no")}
    if Db.U.any(): srcs["committee_unresolved_yes"] = Db.gold("yes")
    res["single_judge_scoring"] = {k: {m: {kk: v[m][kk] for kk in ("P", "R", "F1")} for m in MODELS}
                                   for k, G in srcs.items() for v in [pooled(Db.pred, G, 0, seed)]}
    for k, v in res["single_judge_scoring"].items():
        v["ranking"] = " > ".join(SHORT[m] for m in sorted(MODELS, key=lambda m: -(v[m]["F1"] or 0)))
    return res


def september_block(D, B, seed):
    """S1 only: committee vs the September Opus 5 labels, and the models under each."""
    Ds = sub(D, D.has_sept)
    if not Ds.n: return None
    res = {"works": Ds.n}
    res_ = ~Ds.U
    comp = {}
    po, kp = kappa(Ds.L[res_] == 1, Ds.sept[res_]); comp["committee_vs_sept"] = {"pairs": int(res_.sum()), "agreement": rnd(po), "kappa": rnd(kp),
        "yes_rate_a": rnd(float((Ds.L[res_] == 1).mean())) if res_.any() else None, "yes_rate_b": rnd(float(Ds.sept[res_].mean())) if res_.any() else None}
    for j, M in (("opus", Ds.O), ("sol", Ds.S)):
        ok = ~np.isnan(M).any(1)
        po, kp = kappa(M[ok] == 1, Ds.sept[ok])
        comp[f"{j}_vs_sept"] = {"pairs": int(ok.sum() * 17), "agreement": rnd(po), "kappa": rnd(kp),
                                "yes_rate_a": rnd(float((M[ok] == 1).mean())) if ok.any() else None,
                                "yes_rate_b": rnd(float(Ds.sept[ok].mean())) if ok.any() else None}
    res["agreement"] = comp
    res["scoring"] = {"committee": pooled(Ds.pred, Ds.gold("no"), B, seed)}
    if Ds.U.any(): res["scoring"]["committee_unresolved_yes"] = pooled(Ds.pred, Ds.gold("yes"), B, seed)
    res["scoring"]["september_opus5"] = pooled(Ds.pred, Ds.sept, B, seed)
    flips = {"committee_yes_sept_no": int(((Ds.L == 1) & ~Ds.sept).sum()), "committee_no_sept_yes": int(((Ds.L == 0) & Ds.sept).sum())}
    res["flips"] = flips
    per_goal_flip = {g: {"committee_yes": int((Ds.L[:, j] == 1).sum()), "sept_yes": int(Ds.sept[:, j].sum())} for j, g in enumerate(GOALS)}
    res["per_goal_yes"] = per_goal_flip
    return res


def go_rule(s2b):
    out = {}
    for b in BRACKETS:
        p = s2b[b]["pooled"]; w = s2b[b]["wins"]["head_vs_aurora"]
        fh, fa = p["head"]["F1"], p["aurora"]["F1"]
        gap = None if fh is None or fa is None else fh - fa
        ok_gap = gap is not None and gap >= GO_GAP - 1e-9; ok_w = w["won"] >= GO_WINS
        out[b] = {"head_F1": fh, "aurora_F1": fa, "gap": rnd(gap), "gap_ci": p["F1_diff_ci"].get("head_minus_aurora"),
                  "goals_won": w["won"], "comparable_goals": w["comparable"], "gap_ok": ok_gap, "wins_ok": ok_w, "pass": ok_gap and ok_w}
    v = [out[b]["pass"] for b in BRACKETS]
    out["verdict"] = "PASS" if all(v) else "FAIL" if not any(v) else "SPLIT (depends on how unresolved pairs are counted)"
    return out


# ---------------------------------------------------------------- markdown
def f3(x): return "n/a" if x is None else f"{x:.3f}"
def f2(x): return "n/a" if x is None else f"{x:.2f}"
def sg(x): return "n/a" if x is None else f"{x:+.3f}"
def ci(c, fmt="{:.2f}"):
    if not c: return ""
    sep = " to " if "+" in fmt else "–"                      # signed ranges read badly with a dash ("-0.20–+0.40")
    return f" ({fmt.format(c[0])}{sep}{fmt.format(c[1])})"
def pct(x): return "n/a" if x is None else f"{100 * x:.1f}%"
def num(n): return f"{n:,}"
def prf_cell(d): return f"{f2(d['P'])} / {f2(d['R'])} / {f2(d['F1'])}"


def md_pooled(p, title=None):
    L = [] if not title else [f"*{title}*", ""]
    L += ["| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right tags / wrong tags / missed |", "|---|---|---|---|---|"]
    for m in MODELS:
        d = p[m]
        L.append(f"| {NAME[m]} | {f3(d['P'])}{ci(d['P_ci'])} | {f3(d['R'])}{ci(d['R_ci'])} | **{f3(d['F1'])}**{ci(d['F1_ci'])} | {d['tp']} / {d['fp']} / {d['fn']} |")
    dc = p.get("F1_diff_ci") or {}
    if dc: L += ["", "F1 differences (paired bootstrap over works, 95% CI): head − Aurora "
                 f"{sg(p['head']['F1'] - p['aurora']['F1'] if p['head']['F1'] is not None and p['aurora']['F1'] is not None else None)}{ci(dc.get('head_minus_aurora'), '{:+.3f}')}; "
                 f"Jev − Aurora {sg(p['jev']['F1'] - p['aurora']['F1'] if p['jev']['F1'] is not None and p['aurora']['F1'] is not None else None)}{ci(dc.get('jev_minus_aurora'), '{:+.3f}')}; "
                 f"head − Jev {sg(p['head']['F1'] - p['jev']['F1'] if p['head']['F1'] is not None and p['jev']['F1'] is not None else None)}{ci(dc.get('head_minus_jev'), '{:+.3f}')}."]
    return L


def md_set(J, s, unres):
    B = J["sets"][s]["brackets"]; nb = B["no"]; L = []
    L += ["### Pooled over every (work, goal) pair", ""]
    L += md_pooled(nb["pooled"], "Unresolved pairs counted as no" if unres else None)
    if unres: L += [""] + md_pooled(B["yes"]["pooled"], "Unresolved pairs counted as yes")
    L += ["", f"AUC (pooled pairs): Jev {f3(nb['auc_pooled']['jev'])}, head {f3(nb['auc_pooled']['head'])}"
          + (f" (unresolved as yes: Jev {f3(B['yes']['auc_pooled']['jev'])}, head {f3(B['yes']['auc_pooled']['head'])})" if unres else "") + ".", ""]
    w = nb["wins"]
    L += ["### Per goal", "",
          f"Each cell is precision / recall / F1 at the model's served threshold. The head beats Aurora on F1 on **{w['head_vs_aurora']['won']} of 17** goals"
          f" (Jev beats Aurora on {w['jev_vs_aurora']['won']}; the head beats Jev on {w['head_vs_jev']['won']})"
          + (f"; with unresolved pairs counted as yes, the head beats Aurora on {B['yes']['wins']['head_vs_aurora']['won']}" if unres else "")
          + ". Goals with fewer than 15 committee yes pairs have wide intervals.", "",
          f"| SDG | committee yes | unresolved | Aurora | Jev direct | Head {HEAD} | Jev AUC | Head AUC | head vs Aurora |",
          "|---|---|---|---|---|---|---|---|---|"]
    for g in GOALS:
        r = nb["per_goal"][g]; fh, fa = r["head"]["F1"], r["aurora"]["F1"]
        verdict = "n/a" if fh is None or fa is None else "won" if fh > fa else "tie" if fh == fa else "lost"
        L.append(f"| {g} {R.NAMES[g]} | {r['gold_pos']} | {r['unresolved']} | {prf_cell(r['aurora'])} | {prf_cell(r['jev'])} | {prf_cell(r['head'])} |"
                 f" {f3(r['jev_auc'])} | {f3(r['head_auc'])} | {verdict} |")
    L += ["", "### Labels per work", "", "| | no goal | 1 goal | 2+ goals | mean goals per work |", "|---|---|---|---|---|"]
    rows = [("Committee" + (" (unresolved as no)" if unres else ""), nb["labels_per_work"]["committee"])]
    if unres: rows.append(("Committee (unresolved as yes)", B["yes"]["labels_per_work"]["committee"]))
    rows += [(NAME[m], nb["labels_per_work"][m]) for m in MODELS]
    for k, d in rows:
        if d: L.append(f"| {k} | {pct(d['no_goal'])} | {pct(d['one'])} | {pct(d['two_plus'])} | {d['mean_labels']:.2f} |")
    cal = nb["head_calibration"]; caly = B["yes"]["head_calibration"]
    L += ["", "### Is the head's score an honest probability? (calibration)", "",
          "If the head says 0.7, about 70% of such pairs should be committee yes. ECE is the average gap (0 = perfect).", "",
          "| head p | pairs | mean p | committee yes-rate |" + (" yes-rate, unresolved as yes |" if unres else ""),
          "|---|---|---|---|" + ("---|" if unres else "")]
    for b0, b1 in zip(cal["bins"], caly["bins"]):
        if b0["n"]: L.append(f"| {b0['bin']} | {num(b0['n'])} | {f3(b0['mean_p'])} | {f3(b0['yes_rate'])} |" + (f" {f3(b1['yes_rate'])} |" if unres else ""))
    L += ["", f"ECE: {f3(cal['ece'])}" + (f" (unresolved as yes: {f3(caly['ece'])})" if unres else "") + ".", ""]
    bt = nb["head_best_threshold_diagnostic"]
    if bt["best"]:
        L += [f"**Diagnostic only, not a choice** (pre-registered: the threshold stays 0.4): the uniform head threshold that maximises pooled F1 on this set is "
              f"{bt['best']['t']:.2f} (P {f3(bt['best']['P'])} / R {f3(bt['best']['R'])} / F1 {f3(bt['best']['F1'])}) vs F1 {f3(bt['at_0.4']['F1'])} at 0.4.", ""]
    return L


def render_md(J):
    S = J["sets"]; P = J["progress"]; L = []
    L += [f"# SDG committee eval: scores (head {HEAD})", "",
          f"Written by `benchmarks/score_committee.py --head {HEAD}` from `benchmarks/data/committee/`. Rubric {J['rubric'][:12]}. "
          f"Bootstrap {J['boot']} resamples over works, seed {J['seed']}. Head {HEAD}: `models/sdg_jev_head_{HEAD}.json`.", ""]
    partial = [f"{s.upper()} {P[s]['judged']:,} of {P[s]['in_set']:,}" for s in ("s2", "s1") if P[s]["judged"] < P[s]["in_set"]]
    if partial:
        L += [f"> **Provisional.** Not every work has both judges' answers yet ({'; '.join(partial)} works judged). Every number below covers only the judged works.", ""]
    warn = J["integrity"]
    if warn["problems"]:
        L += ["> **Integrity warnings:** " + "; ".join(warn["problems"]), ""]

    # headline
    L += ["## Headline", ""]
    hl = []
    if "s2" in S:
        s2 = S["s2"]; g = s2["go_rule"]; gn = g["no"]; p = s2["brackets"]["no"]["pooled"]; t = s2["title_only_rule"]["no"]
        hl.append(f"**Go rule on S2: {g['verdict']}.** On {s2['works']:,} fresh random works (S2), the head's pooled F1 is **{f2(p['head']['F1'])}**"
                  f"{ci(p['head']['F1_ci'])} against Aurora's **{f2(p['aurora']['F1'])}**{ci(p['aurora']['F1_ci'])}, a gap of {'n/a' if gn['gap'] is None else format(gn['gap'], '+.2f')}"
                  f"{ci(gn['gap_ci'], '{:+.2f}')} where the rule needs +0.20, and the head beats Aurora on {gn['goals_won']} of 17 goals where the rule needs 13."
                  f" Jev direct, the head's teacher, scores {f2(p['jev']['F1'])}{ci(p['jev']['F1_ci'])}.")
        if t["head_P"] is not None:
            hl.append(f"On title-only works ({t['works']:,}), the head's precision is {f2(t['head_P'])}{ci(t['head_P_ci'])}: the pre-registered title-only rule"
                      f" (act if below 0.60) is **{'TRIGGERED' if t['triggered'] else 'not triggered'}**.")
    else:
        hl.append("**Go rule on S2: not computable**: no S2 work in this run has both judges' answers.")
    u = sum(S[s]["judges"]["unresolved_pairs"] for s in S); n_pairs = sum(S[s]["works"] * 17 for s in S)
    if u:
        same = ("the go-rule verdict is the same whichever way they are counted" if "s2" in S and "SPLIT" not in S["s2"]["go_rule"]["verdict"]
                else "see the bracket rows below")
        hl.append(f"{u:,} of {n_pairs:,} (work, goal) pairs are unresolved (a judge refused or failed, or Fable had not ruled); every score is computed twice, "
                  f"with them counted as no and as yes; {same}.")
    else:
        hl.append(f"All {n_pairs:,} (work, goal) pairs have a committee label (none unresolved).")
    if "s1" in S:
        p1 = S["s1"]["brackets"]["no"]["pooled"]
        hl.append(f"On September's {S['s1']['works']:,} works (S1, continuity only: this set already chose the 0.4 threshold and the SDG 9 wording), F1 is "
                  f"Aurora {f2(p1['aurora']['F1'])}, Jev {f2(p1['jev']['F1'])}, head {f2(p1['head']['F1'])}.")
    L += [" ".join(hl), ""]
    L += ["**How to read this.** Each model tags a work with zero or more of the 17 goals. The committee (Opus 5.5 and GPT-6.1 Sol, Fable 5.1 breaking ties) "
          "is the answer key. *Precision*: of the tags a model gives, the share the committee agrees with. *Recall*: of the committee's tags, the share the "
          "model finds. *F1*: one number balancing the two (0 to 1). *AUC*: how well a model's score ranks right tags above wrong ones (0.5 = coin flip, "
          "1 = perfect). Ranges in brackets are 95% confidence intervals: Wilson for precision and recall, bootstrap over works for F1.", ""]

    for s, title in (("s2", "S2: the decision set (2,000 fresh random works)"), ("s1", "S1: September's 598 works (continuity; worn)")):
        if s not in S:
            L += [f"## {title}", "", "No work from this set in the run.", ""]; continue
        d = S[s]; unres = d["judges"]["unresolved_pairs"] > 0
        L += [f"## {title}", "", f"{d['works']:,} works judged, {d['works'] * 17:,} (work, goal) pairs; committee yes on {d['brackets']['no']['pooled']['gold_pos']:,} pairs; "
              f"{d['judges']['unresolved_pairs']:,} unresolved pairs on {d['judges']['unresolved_works']:,} works.", ""]
        if s == "s2":
            g = d["go_rule"]
            L += ["### Pre-registered go rule", "", "Head pooled F1 ≥ Aurora's + 0.20 **and** head beats Aurora on ≥ 13 of 17 goals.", "",
                  "| unresolved counted as | head F1 | Aurora F1 | gap (95% CI) | goals won | result |", "|---|---|---|---|---|---|"]
            for b in BRACKETS:
                x = g[b]
                L.append(f"| {b} | {f3(x['head_F1'])} | {f3(x['aurora_F1'])} | {sg(x['gap'])}{ci(x['gap_ci'], '{:+.3f}')} | {x['goals_won']} of 17 | "
                         f"{'PASS' if x['pass'] else 'FAIL'} |")
            L += ["", f"**Verdict: {g['verdict']}.**", ""]
        L += md_set(J, s, unres)
        if s == "s2":
            t = d["title_only_rule"]
            L += ["### Slices", "", "Pre-registered slices. Same pooled metrics, unresolved counted as no.", "",
                  "| Slice | works | committee yes pairs | Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) |", "|---|---|---|---|---|---|---|"]
            for key, label, sl in d["slices"]:
                p = sl["no"]
                for k, m in enumerate(MODELS):
                    x = p[m]
                    L.append(f"| {label if k == 0 else ''} | {num(p['works']) if k == 0 else ''} | {num(p['gold_pos']) if k == 0 else ''} | {SHORT[m]} |"
                             f" {f3(x['P'])}{ci(x['P_ci'])} | {f3(x['R'])}{ci(x['R_ci'])} | {f3(x['F1'])}{ci(x['F1_ci'])} |")
            L += ["", "**Title-only rule** (pre-registered: if the head's precision on S2 title-only works is below 0.60, propose a separate title-only threshold or no tags for title-only works before the write):", ""]
            for b in BRACKETS:
                x = t[b]
                L.append(f"- unresolved counted as {b}: head precision {f3(x['head_P'])}{ci(x['head_P_ci'])} on {x['works']:,} title-only works → "
                         f"**{'TRIGGERED' if x['triggered'] else 'not triggered'}**")
            L.append("")
        if s == "s1" and d.get("september"):
            sp = d["september"]
            L += ["### Committee vs September's single Opus 5 judge", "",
                  f"On the {sp['works']:,} S1 works in this run. Agreement over (work, goal) pairs; kappa corrects for agreement by chance.", "",
                  "| Comparison | pairs | agreement | kappa | yes-rate (first) | yes-rate (September) |", "|---|---|---|---|---|---|"]
            lab = {"committee_vs_sept": "Committee (resolved pairs) vs September", "opus_vs_sept": "Opus 5.5 alone vs September", "sol_vs_sept": "Sol alone vs September"}
            for k, x in sp["agreement"].items():
                L.append(f"| {lab[k]} | {num(x['pairs'])} | {pct(x['agreement'])} | {f3(x['kappa'])} | {pct(x['yes_rate_a'])} | {pct(x['yes_rate_b'])} |")
            L += ["", f"Committee yes where September said no: {sp['flips']['committee_yes_sept_no']}; committee no where September said yes: "
                  f"{sp['flips']['committee_no_sept_yes']}.", "",
                  "Models scored under each answer key (same works):", "",
                  "| Answer key | Aurora P / R / F1 | Jev P / R / F1 | Head P / R / F1 |", "|---|---|---|---|"]
            klab = {"committee": "Committee", "committee_unresolved_yes": "Committee (unresolved as yes)", "september_opus5": "September Opus 5"}
            for k, x in sp["scoring"].items():
                L.append(f"| {klab[k]} | {prf_cell(x['aurora'])} | {prf_cell(x['jev'])} | {prf_cell(x['head'])} |")
            L += ["", "Per goal, yes counts: " + ", ".join(f"SDG {g} {v['committee_yes']}/{v['sept_yes']}" for g, v in sp["per_goal_yes"].items())
                  + " (committee/September).", ""]

    # judges
    L += ["## Judges", "", "Opus 5.5 and GPT-6.1 Sol each judge every work; Fable 5.1 rules only where they disagree.", "",
          "| | " + " | ".join(s.upper() for s in S) + " |", "|---|" + "---|" * len(S)]
    def row(label, f): L.append(f"| {label} | " + " | ".join(f(S[s]["judges"]) for s in S) + " |")
    row("works judged by both", lambda j: num(j["works_both_ok"]))
    row("Opus–Sol pair agreement", lambda j: pct(j["pair_agreement"]))
    row("Cohen's kappa (Opus vs Sol)", lambda j: f3(j["kappa"]))
    row("Opus yes-rate", lambda j: pct(j["yes_rate"]["opus"]))
    row("Sol yes-rate", lambda j: pct(j["yes_rate"]["sol"]))
    row("committee yes-rate (resolved pairs)", lambda j: pct(j["yes_rate"]["committee_resolved"]))
    row("works with a disagreement", lambda j: num(j["works_with_dispute"]))
    row("disagreeing pairs", lambda j: num(j["disputed_pairs"]))
    row("Fable sided with Opus", lambda j: num(j["fable_sided"].get("opus", 0)))
    row("Fable sided with Sol", lambda j: num(j["fable_sided"].get("sol", 0)))
    row("Fable said yes / no", lambda j: f"{j['fable_sided'].get('fable_yes', 0)} / {j['fable_sided'].get('fable_no', 0)}")
    row("Opus status", lambda j: ", ".join(f"{k} {v}" for k, v in sorted(j["status"]["opus"].items())))
    row("Sol status", lambda j: ", ".join(f"{k} {v}" for k, v in sorted(j["status"]["sol"].items())))
    row("Fable status (works with a disagreement)", lambda j: ", ".join(f"{k} {v}" for k, v in sorted(j["status"]["fable"].items())) or "none")
    row("unresolved pairs (works)", lambda j: f"{j['unresolved_pairs']} ({j['unresolved_works']})")
    row("unresolved by cause", lambda j: ", ".join(f"{k.split(':', 1)[1]} {v}" for k, v in sorted(j["unresolved_by_cause"].items())) or "none")
    L += ["", "**Does the ranking depend on the judge?** Pooled F1 of each model with each judge's labels as the answer key, on the works both judges answered.", "",
          "| Set | Answer key | Aurora F1 | Jev F1 | Head F1 | ranking |", "|---|---|---|---|---|---|"]
    klab = {"opus": "Opus 5.5 alone", "sol": "GPT-6.1 Sol alone", "committee": "Committee", "committee_unresolved_yes": "Committee (unresolved as yes)"}
    for s in S:
        for k, v in S[s]["judges"]["single_judge_scoring"].items():
            L.append(f"| {s.upper()} | {klab[k]} | {f3(v['aurora']['F1'])} | {f3(v['jev']['F1'])} | {f3(v['head']['F1'])} | {v['ranking']} |")
    served = collections.Counter(f"{k}: {r.get('model_served')}" for k in ("opus", "sol", "fable") for r in J["_rows"][k].values() if r.get("model_served"))
    L += ["", "Served models (last row per work): " + ", ".join(f"{k} ×{v}" for k, v in sorted(served.items())) + ".", ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main
def score(run, B=1000, seed=1300):
    works, head, jev, sept = load_inputs()
    st, bad = load_run(run)
    J = {"run": "benchmarks/data/committee", "rubric": R.SHA256, "boot": B, "seed": seed,
         "thresholds": THRESH, "head": HEAD, "inputs": {"works": "benchmarks/data/committee/works.jsonl.gz", "head": f"benchmarks/data/committee/head_{HEAD}.jsonl.gz",
                                          "jev": "benchmarks/data/committee/jev.jsonl.gz", "september_labels": "benchmarks/data/september/judge_opus5.jsonl.gz"},
         "progress": {}, "sets": {}}
    problems = []
    if any(bad.values()): problems.append(f"half-written or unparseable lines skipped (normal while a run is appending): {({k: v for k, v in bad.items() if v})}")
    rub = collections.Counter(r.get("rubric") for k in ("opus", "sol", "fable") for r in st[k].values())
    if set(rub) - {R.SHA256}: problems.append(f"rows with another rubric sha: {sum(v for k, v in rub.items() if k != R.SHA256)}")
    other = [i for i in set(st["opus"]) | set(st["sol"]) if i not in works]
    if other: problems.append(f"{len(other)} works in the run are in neither S1 nor S2 (not scored)")
    judged = {}
    for s in ("s2", "s1"):
        D = SetData(s, works, st, head, jev, sept)
        judged[s] = D.n
        J["progress"][s] = {"in_set": D.n_set, "judged": D.n, "not_yet": D.n_set - D.n}
        if D.missing["head"] or D.missing["jev"]: problems.append(f"{s}: works without model scores {D.missing} (scored as no tags)")
        if D.stale_fable: problems.append(f"{s}: {D.stale_fable} Fable rows whose disputed goals differ from the current Opus/Sol rows")
        if not D.n: continue
        d = {"works": D.n, "brackets": {b: bracket_block(D, b, B, seed) for b in BRACKETS}, "judges": judges_block(D, B, seed)}
        if s == "s2":
            d["go_rule"] = go_rule(d["brackets"])
            d["slices"] = []
            for key, label, mask in slices_s2(D):
                Ds = sub(D, mask)
                d["slices"].append((key, label, {b: pooled(Ds.pred, Ds.gold(b), B, seed) for b in BRACKETS}))
            t = next(x for x in d["slices"] if x[0] == "title_only")[2]
            d["title_only_rule"] = {b: {"works": t[b]["works"], "head_P": t[b]["head"]["P"], "head_P_ci": t[b]["head"]["P_ci"],
                                        "triggered": t[b]["head"]["P"] is not None and t[b]["head"]["P"] < TITLE_P} for b in BRACKETS}
            d["title_only_rule"]["works"] = t["no"]["works"]; d["title_only_rule"]["head_P"] = t["no"]["head"]["P"]
            d["title_only_rule"]["head_P_ci"] = t["no"]["head"]["P_ci"]; d["title_only_rule"]["triggered"] = d["title_only_rule"]["no"]["triggered"]
        if s == "s1": d["september"] = september_block(D, B, seed)
        J["sets"][s] = d
    # cross-check against committee.jsonl when the harness has written one
    cj = load_jsonl(f"{run}/committee.jsonl.gz")[0] or load_jsonl(f"{run}/committee.jsonl")[0]
    if cj:
        mine = {}
        for s in ("s1", "s2"):
            for w in works.values():
                i = w["work_id"]
                if w["_set"] == s and i in st["opus"] and i in st["sol"]:
                    mine[i] = committee_label(st["opus"][i], st["sol"][i], st["fable"].get(i))[0]
        mism = sum(1 for r in cj if r["work_id"] in mine and
                   [None if r["label"].get(str(g)) is None else int(r["label"][str(g)] == "yes") for g in GOALS] != mine[r["work_id"]])
        J["integrity_committee_jsonl"] = {"rows": len(cj), "compared": sum(r["work_id"] in mine for r in cj), "label_mismatches": mism}
        if mism: problems.append(f"{mism} works whose labels differ from committee.jsonl (it may predate the latest stage rows)")
    J["integrity"] = {"problems": problems, "unparseable_lines": bad, "rubric_rows": dict(rub)}
    J["_rows"] = st
    return J


def main():
    global HEAD
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--head", choices=("v1", "v2"), default="v2", help="which head to score (v2 is served; v1 is what the go rule was pre-registered on)")
    ap.add_argument("--run", default=DATA, help="directory with opus/sol/fable .jsonl.gz (default: benchmarks/data/committee)")
    ap.add_argument("--out", default=DATA, help="where scores_<head>.md / .json go (default: benchmarks/data/committee)")
    ap.add_argument("--boot", type=int, default=1000); ap.add_argument("--seed", type=int, default=1300)
    a = ap.parse_args()
    HEAD = a.head; NAME["head"] = f"Head {HEAD} (0.4)"
    run = os.path.abspath(os.path.expanduser(a.run)); out = os.path.abspath(os.path.expanduser(a.out))
    J = score(run, a.boot, a.seed)
    os.makedirs(out, exist_ok=True)
    md = render_md(J); J.pop("_rows")
    with open(f"{out}/scores_{HEAD}.json", "w") as f: json.dump(J, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(f"{out}/scores_{HEAD}.md", "w") as f: f.write(md)
    print(f"wrote {out}/scores_{HEAD}.md and scores_{HEAD}.json")
    for s in ("s2", "s1"):
        if s in J["sets"]:
            p = J["sets"][s]["brackets"]["no"]["pooled"]
            print(f"  {s}: {J['sets'][s]['works']} works | F1 aurora {p['aurora']['F1']} jev {p['jev']['F1']} head {HEAD} {p['head']['F1']}"
                  + (f" | go rule {J['sets'][s]['go_rule']['verdict']}" if s == "s2" else ""))
    if J["integrity"]["problems"]: print("  integrity:", J["integrity"]["problems"])


if __name__ == "__main__":
    main()
