"""The September 2026 judge: one call per work, yes/no and a one-line reason for each of the 17 goals.

  export ANTHROPIC_API_KEY=...
  python harness/judge_september.py --input works.jsonl --out judge.jsonl                       # Claude Opus 5, as judged
  python harness/judge_september.py --input works.jsonl --out fable.jsonl --model claude-fable-5-1   # the second opinion

This was the first evaluation (598 works, 21 September 2026; benchmarks/data/september/). Its rule is the one Jev was
given (classifier/jev_request.py, EVAL_RULE), plus two sentences on what does not count. Because that gold was written
from the classifier's own instructions, it was replaced as the answer key by the committee (harness/committee.py,
rubric.py), which works from the UN's goal and target text. Input rows need work_id, title and abstract
(classifier/fetch_works.py). A refusal is retried once with the other model (Opus 5 <-> Fable 5.1).
"""
import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classifier import jev_request as J  # noqa: E402

LABELS = "\n".join("- " + J.eval_noul(g, sdg9="seed") for g in range(1, 18))
SYSTEM = ("You are judging works from OpenAlex, a scholarly index, to build a gold standard for tagging works with the UN Sustainable "
          "Development Goals (SDGs).\n\nRule: " + J.EVAL_RULE + "\n\nThe goals:\n" + LABELS +
          "\n\nFor every one of the 17 goals answer yes or no with a one-line reason (under 25 words). 'Yes' means the work's subject matter "
          "substantively contributes to or studies that goal; a keyword overlap, a background sentence, or a generic 'implications for policy' "
          "line does not count. A basic-science work whose topic merely belongs to a broad area (energy physics, a disease mechanism, an "
          "education setting) is 'yes' only if its stated contribution bears on the goal. Non-English works: read them in their language.")
SCHEMA = {"type": "object", "properties": {f"sdg{g}": {"type": "object", "properties": {"yes": {"type": "boolean"}, "reason": {"type": "string"}},
                                                       "required": ["yes", "reason"], "additionalProperties": False} for g in range(1, 18)},
          "required": [f"sdg{g}" for g in range(1, 18)], "additionalProperties": False}


def work_text(w):
    return f"Title: {w.get('title') or ''}\nAbstract: {(w.get('abstract') or '')[:6000]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high")
    ap.add_argument("--concurrency", type=int, default=8); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    done = {json.loads(l)["work_id"] for l in open(a.out) if "error" not in json.loads(l)} if os.path.exists(a.out) else set()
    works = [w for w in (json.loads(l) for l in open(a.input)) if w["work_id"] not in done and "error" not in w]
    if a.limit:
        works = works[:a.limit]
    print(f"judge {a.model} effort={a.effort}: {len(works)} works to do ({len(done)} done)", file=sys.stderr)
    client = anthropic.Anthropic(max_retries=4, timeout=600)
    out = open(a.out, "a"); lock = threading.Lock()

    def call(model, txt):
        return client.messages.create(model=model, max_tokens=16000, system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                                      messages=[{"role": "user", "content": txt}],
                                      output_config={"effort": a.effort, "format": {"type": "json_schema", "schema": SCHEMA}})

    def one(w):
        txt = "Judge this work against all 17 goals.\n\n" + work_text(w)
        rec = {"work_id": w["work_id"], "model": a.model}
        try:
            r = call(a.model, txt)
        except Exception as e:
            rec["error"] = repr(e)[:400]; return rec
        rec["stop_reason"] = r.stop_reason
        if r.stop_reason == "refusal":
            rec["refusal"] = str(getattr(r, "stop_details", None))[:300]
            fb = "claude-fable-5-1" if a.model == "claude-opus-5" else "claude-opus-5"
            try:
                r = call(fb, txt); rec["model"] = fb; rec["fallback"] = True; rec["stop_reason"] = r.stop_reason
            except Exception as e:
                rec["error"] = "fallback failed: " + repr(e)[:300]; return rec
            if r.stop_reason == "refusal":
                rec["error"] = "refused twice"; return rec
        text = "".join(b.text for b in r.content if b.type == "text")
        try:
            ans = json.loads(text)
        except Exception:
            rec["error"] = "bad_json"; rec["raw"] = text[:500]; return rec
        rec["yes"] = {g: bool(ans[f"sdg{g}"]["yes"]) for g in range(1, 18)}
        rec["reason"] = {g: ans[f"sdg{g}"]["reason"] for g in range(1, 18)}
        return rec

    n = 0
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for f in as_completed({ex.submit(one, w): w for w in works}):
            rec = f.result()
            with lock:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush(); n += 1
                if "error" in rec:
                    print(f"ERR {rec['work_id']} {rec['error'][:120]}", file=sys.stderr)
    print(f"done: {n} works", file=sys.stderr)


if __name__ == "__main__":
    main()
