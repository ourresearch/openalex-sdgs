"""Ask Jev, a decision model from TypeSafe AI, the SDG questions for a set of works: JSONL in, JSONL out.

  export JEV_API_KEY=...            # a TypeSafe AI key (https://typesafe.ai)
  python -m classifier.fetch_works --ids ids.txt --out works.jsonl
  python -m classifier.jev --input works.jsonl --out labels.jsonl                    # training request, all 17 goals (v2 wording)
  python -m classifier.jev --input works.jsonl --out jev.jsonl --request eval        # "Jev direct" as benchmarked
  python -m classifier.jev --input works.jsonl --out sdg15.jsonl --goals 15          # one goal, one Noul per request

Input rows: {work_id, title, venue, abstract} (or {id, text} with --request excerpt). Output rows: {work_id, p: {goal:
probability}, model}; a failed request is written as {work_id, error}. Rerunning with the same --out skips rows already
answered. The exact wording of every request is in classifier/jev_request.py.

Jev is not bit-deterministic: asking again moves probabilities by a few hundredths, so a re-run will not reproduce the
shipped labels digit for digit.
"""
import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classifier import jev_request as J  # noqa: E402

JEV_URL = "https://api.typesafe.ai/v1/systemone"
RETRYABLE = {429, 500, 502, 503, 529}


def _backoff(attempt):
    return min(30.0, 0.5 * 2 ** attempt) * (0.5 + random.random())


class Pacer:
    """Requests per second, shared by all threads."""

    def __init__(self, rps):
        self._interval = 1.0 / max(rps, 0.001)
        self._next = time.perf_counter()
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.perf_counter()
            self._next = max(self._next, now)
            delay = self._next - now
            self._next += self._interval
        if delay > 0:
            time.sleep(delay)


class JevClient:
    """TypeSafe's native API. Retries 429 / 5xx / transport errors with jittered backoff."""

    def __init__(self, api_key=None, rps=20.0, timeout=60.0, max_attempts=6, model=J.JEV_MODEL):
        import requests  # only the client needs it

        self._requests = requests
        api_key = api_key or os.environ.get("JEV_API_KEY")
        if not api_key:
            raise RuntimeError("Jev API key missing: set JEV_API_KEY")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._pacer, self._timeout, self._max_attempts, self._model = Pacer(rps), timeout, max_attempts, model
        self._local = threading.local()

    def _session(self):
        s = getattr(self._local, "s", None)
        if s is None:
            s = self._local.s = self._requests.Session()
        return s

    def decide(self, state, qs):
        body = {"model": self._model, "state": state, "questions": qs}
        for attempt in range(1, self._max_attempts + 1):
            self._pacer.wait()
            try:
                resp = self._session().post(JEV_URL, headers=self._headers, json=body, timeout=self._timeout)
            except (self._requests.Timeout, self._requests.ConnectionError) as e:
                if attempt == self._max_attempts:
                    return {"ok": False, "error": repr(e)[:300]}
                time.sleep(_backoff(attempt)); continue
            if resp.status_code == 200:
                data = resp.json()
                return {"ok": True, "answers": data.get("answers", {}), "model": data.get("model")}
            if resp.status_code in RETRYABLE and attempt < self._max_attempts:
                ra = resp.headers.get("retry-after")
                time.sleep(float(ra) if ra else _backoff(attempt)); continue
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        return {"ok": False, "error": "gave up"}


def request_for(kind, goals):
    if kind == "training":
        return J.training_state, {g: J.TRAINING_NOULS[g] for g in goals}
    if kind == "eval":
        return J.eval_state, {g: J.eval_noul(g) for g in goals}
    if kind == "excerpt":
        return (lambda w: J.eval_state(w, excerpt=True)), {g: J.eval_noul(g, sdg9="seed") for g in goals}
    raise ValueError(kind)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--request", choices=("training", "eval", "excerpt"), default="training")
    ap.add_argument("--goals", default="1-17", help="e.g. 15 or 9,15 (one request per work, only these Nouls)")
    ap.add_argument("--rps", type=float, default=20.0, help="requests per second (your Jev account's cap applies)")
    ap.add_argument("--concurrency", type=int, default=16)
    a = ap.parse_args()
    goals = list(range(1, 18)) if a.goals == "1-17" else [int(g) for g in a.goals.split(",")]
    state_of, nouls = request_for(a.request, goals)
    qs = J.questions(nouls)

    key = lambda w: w.get("work_id") or w.get("id")
    works = [json.loads(l) for l in open(a.input) if l.strip()]
    works = [w for w in works if "error" not in w]
    done = set()
    if os.path.exists(a.out):
        done = {key(json.loads(l)) for l in open(a.out) if l.strip() and '"p"' in l}
    todo = [w for w in works if key(w) not in done]
    print(f"{len(works):,} rows, {len(done):,} already answered, {len(todo):,} to ask ({a.request}, goals {a.goals})", file=sys.stderr)

    client = JevClient(rps=a.rps)
    lock = threading.Lock(); n = [0, 0]; t0 = time.time()
    with open(a.out, "a") as out, ThreadPoolExecutor(a.concurrency) as ex:
        futs = {ex.submit(client.decide, state_of(w), qs): w for w in todo}
        for f in as_completed(futs):
            w, r = futs[f], f.result()
            if r["ok"]:
                rec = {"work_id": key(w), "model": r.get("model") or J.JEV_MODEL,
                       "p": {str(g): round(float(r["answers"][f"sdg{g}"]["noul"]), 4) for g in goals}}
            else:
                rec = {"work_id": key(w), "error": r["error"]}
            with lock:
                out.write(json.dumps(rec) + "\n"); n[0 if r["ok"] else 1] += 1
                if sum(n) % 200 == 0:
                    out.flush()
                    print(f"  {sum(n):,}/{len(todo):,} ok={n[0]:,} failed={n[1]:,} {sum(n) / (time.time() - t0):.1f}/s", file=sys.stderr)
    print(f"wrote {a.out}: {n[0]:,} answered, {n[1]:,} failed", file=sys.stderr)


if __name__ == "__main__":
    main()
