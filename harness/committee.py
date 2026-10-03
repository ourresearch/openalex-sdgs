"""Committee of judges for the SDG eval (harness/PREREGISTRATION.md, pre-registered 2026-10-01; rubric.py frozen).

Per work: Opus 5.5 (claude-opus-5-5, effort high, adaptive thinking, cached system prompt) and GPT-6.1 Sol
(openai/gpt-6.1-sol via OpenRouter Responses, effort medium, same prompt and schema) each judge all 17 goals
independently. If they disagree on any goal, ONE Fable 5.1 call (claude-fable-5-1, effort high) gets the work, the
rubric for just the disputed goals, and both judges' verdicts + reasons as "Judge A" / "Judge B" in a random order
(seeded by work id; recorded) and returns the final verdict per disputed goal.

Failure classes are never verdicts:
  Opus refusal -> retried once, then status `refused` (the work's pairs are `unresolved`).
  Sol refusal / served-model mismatch / error -> recorded as a Sol failure; never replaced by another model.
  Fable refusal -> the disputed pairs are `unresolved` (never dropped, never defaulted).
  API errors -> status `error`; a re-run retries them (rows are appended; the last row per work wins).

Stage files in --out (append-only jsonl, resumable: works whose stage row is ok/refused are skipped):
  opus.jsonl, sol.jsonl, fable.jsonl, ledger.jsonl (one row per API call, with token counts), run.log (progress lines);
  committee.jsonl (rewritten at the end of every run from the stage files: label + source per goal).
Every row carries the rubric sha256 and the served model.

Run: export ANTHROPIC_API_KEY=... OPENROUTER_API_KEY=...
     python harness/committee.py --works <works.jsonl from classifier/fetch_works.py> --out <dir> [--limit N]
     [--ids W1,W2] [--conc 12] [--every 10]
Input rows need work_id, set, title, venue, type and abstract. On macOS the run pauses while system free memory is
below 50% and stops if this process passes 1 GB (it was run beside other work on a shared machine).
"""
import argparse, asyncio, collections, hashlib, json, os, random, resource, subprocess, sys, time
import anthropic, httpx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubric as R

OPUS, SOL, FABLE = "claude-opus-5-5", "openai/gpt-6.1-sol", "claude-fable-5-1"
EFFORT = {OPUS: "high", SOL: "medium", FABLE: "high"}
MAX_TOKENS = 32000
GOALS = range(1, 18)


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def last_rows(path):
    d = {}
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l); d[r["work_id"]] = r
    return d


def order_for(work_id):
    """Judge A / Judge B order, random but reproducible per work."""
    h = int(hashlib.sha256(f"{R.SHA256}:{work_id}".encode()).hexdigest()[:8], 16)
    return ("opus", "sol") if h % 2 == 0 else ("sol", "opus")


def mem_ok(max_gb=1.0, min_free=50):
    if sys.platform != "darwin":   # off desk (Modal container): desk's memory rule doesn't apply
        return True, 0.0, 100
    rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9   # macOS reports bytes
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
    free = int(out.rsplit(" ", 1)[-1].rstrip("%"))
    return rss_gb < max_gb and free >= min_free, rss_gb, free


class Committee:
    def __init__(self, out, conc):
        self.out = out; os.makedirs(out, exist_ok=True)
        self.f = {k: open(f"{out}/{k}.jsonl", "a") for k in ("opus", "sol", "fable", "ledger")}
        self.log = open(f"{out}/run.log", "a")
        self.ac = anthropic.AsyncAnthropic(max_retries=4, timeout=900)   # reads ANTHROPIC_API_KEY
        self.hc = httpx.AsyncClient(timeout=900)
        self.sem_a = asyncio.Semaphore(conc); self.sem_o = asyncio.Semaphore(conc)
        self.stat = collections.Counter()

    def write(self, k, rec):
        self.f[k].write(json.dumps(rec, ensure_ascii=False) + "\n"); self.f[k].flush()

    def say(self, s):
        print(s, flush=True); self.log.write(f"{now()} {s}\n"); self.log.flush()

    # ---------- Anthropic (Opus judge, Fable arbiter) ----------
    async def _anthropic(self, stage, wid, model, system, user, schema):
        """One call. Returns (status, parsed_json_or_None, info). Credit-balance 400s wait and retry (transient on this org)."""
        waits = 0
        while True:
            t0 = time.time()
            try:
                async with self.sem_a:
                    async with self.ac.messages.stream(model=model, max_tokens=MAX_TOKENS, thinking={"type": "adaptive"},
                                                       system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                                                       messages=[{"role": "user", "content": user}],
                                                       output_config={"effort": EFFORT[model], "format": {"type": "json_schema", "schema": schema}}) as st:
                        m = await st.get_final_message()
                break
            except anthropic.BadRequestError as e:
                if "credit balance" in str(e) and waits < 10:
                    waits += 1; self.say(f"credit balance 400 on {stage} {wid}; waiting 120 s ({waits}/10)"); await asyncio.sleep(120); continue
                return self._fail(stage, wid, model, e, t0)
            except Exception as e:
                return self._fail(stage, wid, model, e, t0)
        u = m.usage; cr = u.cache_read_input_tokens or 0; cw = u.cache_creation_input_tokens or 0
        info = {"model_req": model, "model_served": m.model, "stop": m.stop_reason, "in": u.input_tokens, "out": u.output_tokens,
                "cache_r": cr, "cache_w": cw, "secs": round(time.time() - t0, 1), "msg_id": m.id}
        if m.stop_reason == "refusal":
            sd = getattr(m, "stop_details", None)
            info["refusal"] = {"category": getattr(sd, "category", None), "explanation": (getattr(sd, "explanation", None) or "")[:300]}
            status, parsed = "refused", None
        elif m.stop_reason == "max_tokens":
            status, parsed = "max_tokens", None
        else:
            text = "".join(b.text for b in m.content if b.type == "text")
            try: parsed, status = json.loads(text), "ok"
            except Exception: parsed, status = None, "bad_json"; info["raw"] = text[:500]
        self._ledger(stage, wid, status, info)
        return status, parsed, info

    def _fail(self, stage, wid, model, e, t0):
        info = {"model_req": model, "model_served": None, "err": repr(e)[:400], "secs": round(time.time() - t0, 1)}
        self._ledger(stage, wid, "error", info); return "error", None, info

    def _ledger(self, stage, wid, status, info):
        self.write("ledger", {"ts": now(), "stage": stage, "work_id": wid, "status": status, "rubric": R.SHA256, **info})

    # ---------- OpenRouter (Sol judge) ----------
    async def _sol(self, wid, user):
        body = {"model": SOL, "instructions": R.JUDGE_SYSTEM, "input": user, "reasoning": {"effort": EFFORT[SOL]},
                "max_output_tokens": MAX_TOKENS, "text": {"format": {"type": "json_schema", "name": "sdg_judgment", "schema": R.JUDGE_SCHEMA, "strict": True}}}
        err = None
        for att in range(4):
            t0 = time.time()
            try:
                async with self.sem_o:
                    r = await self.hc.post("https://openrouter.ai/api/v1/responses", json=body,
                                           headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
                d = r.json()
                if r.status_code != 200 or d.get("error"):
                    raise RuntimeError(f"HTTP {r.status_code}: {str(d.get('error'))[:300]}")
            except Exception as e:
                err = repr(e)[:400]; self._ledger("sol", wid, "error", {"model_req": SOL, "model_served": None, "err": err, "attempt": att,
                                                                         "secs": round(time.time() - t0, 1)})
                await asyncio.sleep(15 * (att + 1)); continue
            u = d.get("usage") or {}
            info = {"model_req": SOL, "model_served": d.get("model"), "stop": d.get("status"), "in": u.get("input_tokens"),
                    "out": u.get("output_tokens"), "reasoning": (u.get("output_tokens_details") or {}).get("reasoning_tokens"),
                    "cache_r": (u.get("input_tokens_details") or {}).get("cached_tokens"),
                    "secs": round(time.time() - t0, 1), "gen_id": d.get("id")}
            if not str(d.get("model", "")).startswith(SOL):
                status, parsed = "served_mismatch", None          # a Sol failure, never a verdict from another model
            elif d.get("status") == "incomplete":
                status, parsed = "incomplete", None; info["incomplete"] = d.get("incomplete_details")
            else:
                msgs = [o for o in d.get("output", []) if o.get("type") == "message"]
                content = (msgs[0].get("content") or [{}])[0] if msgs else {}
                if content.get("type") == "refusal":
                    status, parsed = "refused", None; info["refusal"] = str(content.get("refusal"))[:300]
                else:
                    try: parsed, status = json.loads(content.get("text") or ""), "ok"
                    except Exception: parsed, status = None, "bad_json"; info["raw"] = str(content)[:500]
            self._ledger("sol", wid, status, info)
            return status, parsed, info
        return "error", None, {"model_req": SOL, "model_served": None, "err": err}

    # ---------- stages ----------
    @staticmethod
    def _verdicts(parsed):
        return ({str(g): parsed[f"sdg{g}"]["verdict"] for g in GOALS}, {str(g): parsed[f"sdg{g}"]["reason"] for g in GOALS})

    async def judge_opus(self, w):
        tries = []; status = parsed = info = None
        for att in range(2):                                  # refusal: retry once, then `refused`
            status, parsed, info = await self._anthropic("opus", w["work_id"], OPUS, R.JUDGE_SYSTEM, R.judge_user(w), R.JUDGE_SCHEMA)
            tries.append({"status": status, **({"refusal": info["refusal"]} if "refusal" in info else {})})
            if status != "refused": break
        rec = {"work_id": w["work_id"], "set": w.get("set"), "stage": "opus", "rubric": R.SHA256, "status": status, "attempts": tries,
               "model_req": OPUS, "model_served": info.get("model_served"), "effort": EFFORT[OPUS],
               "ts": now(), **({"err": info["err"]} if "err" in info else {})}
        if status == "ok": rec["verdict"], rec["reason"] = self._verdicts(parsed)
        self.write("opus", rec); return rec

    async def judge_sol(self, w):
        status, parsed, info = await self._sol(w["work_id"], R.judge_user(w))
        rec = {"work_id": w["work_id"], "set": w.get("set"), "stage": "sol", "rubric": R.SHA256, "status": status, "model_req": SOL,
               "model_served": info.get("model_served"), "effort": EFFORT[SOL], "ts": now(),
               **({k: info[k] for k in ("err", "refusal") if k in info})}
        if status == "ok": rec["verdict"], rec["reason"] = self._verdicts(parsed)
        self.write("sol", rec); return rec

    async def arbitrate(self, w, op, so):
        goals = [g for g in GOALS if op["verdict"][str(g)] != so["verdict"][str(g)]]
        V = lambda rec, g: (rec["verdict"][str(g)], rec["reason"][str(g)])
        a, b = order_for(w["work_id"]); side = {"opus": op, "sol": so}
        ja = {g: V(side[a], g) for g in goals}; jb = {g: V(side[b], g) for g in goals}
        status, parsed, info = await self._anthropic("fable", w["work_id"], FABLE, R.ARBITER_SYSTEM, R.arbiter_user(w, goals, ja, jb), R.ARBITER_SCHEMA)
        rec = {"work_id": w["work_id"], "set": w.get("set"), "stage": "fable", "rubric": R.SHA256, "status": status, "disputed": goals,
               "judge_a": a, "judge_b": b, "model_req": FABLE, "model_served": info.get("model_served"), "effort": EFFORT[FABLE],
               "ts": now(), **({k: info[k] for k in ("err", "refusal") if k in info})}
        if status == "ok":
            dec = collections.defaultdict(list)
            for d in parsed["decisions"]: dec[int(d["sdg"])].append(d)
            if sorted(dec) != goals or any(len(v) != 1 for v in dec.values()):
                rec["status"] = "bad_output"; rec["raw_decisions"] = parsed["decisions"]
            else:
                rec["verdict"] = {str(g): dec[g][0]["verdict"] for g in goals}; rec["reason"] = {str(g): dec[g][0]["reason"] for g in goals}
        self.write("fable", rec); return rec

    async def run_work(self, w, done):
        wid = w["work_id"]
        op, so = done["opus"].get(wid), done["sol"].get(wid)
        jobs = {}
        if not op or op["status"] not in ("ok", "refused"): jobs["opus"] = self.judge_opus(w)
        if not so or so["status"] not in ("ok", "refused"): jobs["sol"] = self.judge_sol(w)
        if jobs:
            res = dict(zip(jobs, await asyncio.gather(*jobs.values())))
            op, so = res.get("opus", op), res.get("sol", so)
        self.stat[f"opus_{op['status']}"] += 1; self.stat[f"sol_{so['status']}"] += 1
        if op["status"] == "ok" and so["status"] == "ok":
            if _needs_fable({"opus": {wid: op}, "sol": {wid: so}}, wid):
                fb = done["fable"].get(wid)
                if not fb or fb["status"] not in ("ok", "refused"): fb = await self.arbitrate(w, op, so)
                self.stat[f"fable_{fb['status']}"] += 1
            else:
                self.stat["no_dispute"] += 1
        self.stat["works"] += 1


def merge(out, works):
    """committee.jsonl: one row per work, label + source per goal. Sources: agree | fable | unresolved:<cause>."""
    op, so, fb = (last_rows(f"{out}/{k}.jsonl") for k in ("opus", "sol", "fable"))
    rows = []
    for w in works:
        wid = w["work_id"]; o, s, f = op.get(wid), so.get(wid), fb.get(wid)
        rec = {"work_id": wid, "set": w.get("set"), "rubric": R.SHA256, "opus": o and o["status"], "sol": s and s["status"],
               "fable": f and f["status"], "label": {}, "source": {}}
        if not o or not s:
            continue
        for g in GOALS:
            k = str(g)
            if o["status"] != "ok" or s["status"] != "ok":
                cause = "opus_" + o["status"] if o["status"] != "ok" else "sol_" + s["status"]
                rec["label"][k], rec["source"][k] = None, f"unresolved:{cause}"; continue
            vo, vs = o["verdict"][k], s["verdict"][k]
            if vo == vs:
                rec["label"][k], rec["source"][k] = vo, "agree"
            elif f and f["status"] == "ok" and k in f["verdict"]:
                rec["label"][k], rec["source"][k] = f["verdict"][k], "fable"
            else:
                rec["label"][k], rec["source"][k] = None, f"unresolved:fable_{f['status'] if f else 'pending'}"
        rows.append(rec)
    with open(f"{out}/committee.jsonl", "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")
    return rows


def summarize(out, works):
    """Judge diagnostics for the report: pair agreement and kappa, Fable's sides, failures, served models."""
    op, so, fb = (last_rows(f"{out}/{k}.jsonl") for k in ("opus", "sol", "fable"))
    ids = [w["work_id"] for w in works if w["work_id"] in op and w["work_id"] in so]
    both = [i for i in ids if op[i]["status"] == "ok" and so[i]["status"] == "ok"]
    n = a = oy = sy = 0
    for i in both:
        for g in GOALS:
            vo, vs = op[i]["verdict"][str(g)] == "yes", so[i]["verdict"][str(g)] == "yes"
            n += 1; a += vo == vs; oy += vo; sy += vs
    po = a / n if n else 0; pe = ((oy / n) * (sy / n) + (1 - oy / n) * (1 - sy / n)) if n else 0
    sided = collections.Counter(); unresolved = 0
    for i in both:
        f = fb.get(i)
        dis = [g for g in GOALS if op[i]["verdict"][str(g)] != so[i]["verdict"][str(g)]]
        for g in dis:
            if f and f["status"] == "ok" and str(g) in f["verdict"]:
                v = f["verdict"][str(g)]; sided["opus" if v == op[i]["verdict"][str(g)] else "sol"] += 1
                sided[f"fable_{v}"] += 1
            else: unresolved += 1
    led = [json.loads(l) for l in open(f"{out}/ledger.jsonl")] if os.path.exists(f"{out}/ledger.jsonl") else []
    served = collections.Counter()
    for r in led:
        if r.get("model_served"): served[f"{r['stage']}:{r['model_served']}"] += 1
    return {"works": len(works), "judged_by_both": len(both), "pairs": n, "pair_agreement": round(po, 4),
            "kappa": round((po - pe) / (1 - pe), 4) if n and pe < 1 else None,
            "opus_yes_rate": round(oy / n, 4) if n else None, "sol_yes_rate": round(sy / n, 4) if n else None,
            "works_with_dispute": sum(1 for i in both if any(op[i]["verdict"][str(g)] != so[i]["verdict"][str(g)] for g in GOALS)),
            "disputed_pairs": n - a, "fable_sided": dict(sided), "unresolved_pairs": unresolved,
            "status": {"opus": dict(collections.Counter(op[i]["status"] for i in ids)), "sol": dict(collections.Counter(so[i]["status"] for i in ids)),
                       "fable": dict(collections.Counter(fb[i]["status"] for i in fb if i in set(ids)))},
            "opus_refusal_attempts": sum(1 for r in led if r["stage"] == "opus" and r["status"] == "refused"),
            "served_models": dict(served), "rubric": R.SHA256}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True, nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--ids"); ap.add_argument("--conc", type=int, default=12)
    ap.add_argument("--every", type=int, default=10)
    a = ap.parse_args()
    works = [json.loads(l) for p in a.works for l in open(p)]
    if a.ids: keep = set(a.ids.split(",")); works = [w for w in works if w["work_id"] in keep]
    if a.limit: works = works[:a.limit]
    C = Committee(a.out, a.conc)
    done = {k: last_rows(f"{a.out}/{k}.jsonl") for k in ("opus", "sol", "fable")}
    todo = [w for w in works if not (done["opus"].get(w["work_id"], {}).get("status") in ("ok", "refused")
                                     and done["sol"].get(w["work_id"], {}).get("status") in ("ok", "refused")
                                     and (done["fable"].get(w["work_id"], {}).get("status") in ("ok", "refused")
                                          or not _needs_fable(done, w["work_id"])))]
    C.say(f"committee rubric {R.SHA256[:12]} out={a.out}: {len(works)} works, {len(todo)} to do, conc {a.conc}")
    t0 = time.time(); q = asyncio.Queue(); stop = False

    async def mem_gate():
        """Shared-machine guard: >= 50% free. Pause (don't start new work) while below; exit only if this process passes 1 GB."""
        nonlocal stop
        waited = 0
        while True:
            ok, rss, free = mem_ok()
            if rss >= 1.0: stop = True; C.say(f"STOP: rss {rss:.2f} GB >= 1 GB; re-run to resume"); return False
            if ok: return True
            if waited % 300 == 0: C.say(f"PAUSE: system memory free {free}% < 50%; waiting (rss {rss:.2f} GB)")
            await asyncio.sleep(30); waited += 30
    for w in todo: q.put_nowait(w)

    def progress():
        el = time.time() - t0; n = C.stat["works"]
        bad = lambda pre, good: sum(v for k, v in C.stat.items() if k.startswith(pre) and k[len(pre):] not in good)
        C.say(f"  {n}/{len(todo)} works | opus ok {C.stat['opus_ok']} ref {C.stat['opus_refused']} err {bad('opus_', ('ok', 'refused'))}"
              f" | sol ok {C.stat['sol_ok']} fail {bad('sol_', ('ok',))} | fable calls {sum(v for k, v in C.stat.items() if k.startswith('fable_'))}"
              f" ok {C.stat['fable_ok']} unresolved {C.stat['fable_refused'] + C.stat['fable_error'] + C.stat['fable_bad_output']}"
              f" | {n / el * 60:.1f} works/min | mem free {mem_ok()[2]}%")

    async def worker():
        nonlocal stop
        while not stop:
            if not await mem_gate(): return
            try: w = q.get_nowait()
            except asyncio.QueueEmpty: return
            try: await C.run_work(w, done)
            except Exception as e: C.say(f"ERR {w['work_id']} {repr(e)[:300]}")
            if C.stat["works"] % a.every == 0: progress()
    if todo:                                    # warm both prompt caches with one work before fanning out
        w0 = q.get_nowait()
        if not await mem_gate(): return
        try: await C.run_work(w0, done)
        except Exception as e: C.say(f"ERR {w0['work_id']} {repr(e)[:300]}")
        await asyncio.gather(*(worker() for _ in range(a.conc)))
        progress()
    rows = merge(a.out, works); s = summarize(a.out, works)
    json.dump(s, open(f"{a.out}/summary.json", "w"), indent=1)
    C.say("summary " + json.dumps(s))
    await C.hc.aclose()


def _needs_fable(done, wid):
    o, s = done["opus"].get(wid), done["sol"].get(wid)
    if not (o and s and o["status"] == "ok" and s["status"] == "ok"): return False
    return any(o["verdict"][str(g)] != s["verdict"][str(g)] for g in GOALS)


if __name__ == "__main__":
    asyncio.run(main())
