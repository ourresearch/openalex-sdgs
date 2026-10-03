# Harness

The code that produced the answer keys. Every file here ran as committed, except that cost accounting and internal
paths were removed.

| File | What |
|---|---|
| `PREREGISTRATION.md` | The committee eval and the SDG 15 fix, as written before any of their labels existed |
| `rubric.py` | Rubric v2: the UN goal statements and compressed targets, the judges' and arbiter's prompts and schemas. Frozen: it checks its own sha256 on import |
| `judge_prompts.md` | Every word the judges saw, generated from `rubric.py` and `judge_september.py` |
| `committee.py` | Opus 5.5 and GPT-6.1 Sol per work, Fable 5.1 on their disagreements; resumable, one row per call |
| `judge_september.py` | The first test's single judge (Claude Opus 5), and its Fable 5.1 second opinion |
| `runs/kgkb/` | The check before the pilot: 10 works that obviously address a goal and 10 that obviously don't, through the full pipeline, plus planted disagreements for Fable (20 of 20 right for every judge) |
| `runs/pilot/` | The 20-work pilot of the committee, read once for harness bugs, not to tune the rubric |
| `gepa/` | The rejected search over Jev's instructions |

Running the committee needs `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY` (Sol was called through OpenRouter's
Responses API). Rebuild the texts first:

```bash
python -m classifier.fetch_works --ids benchmarks/data/committee/works.jsonl.gz --out works.jsonl
python harness/committee.py --works works.jsonl --out my_run
python benchmarks/score_committee.py --run my_run --out my_run
```

The judges are not deterministic, and some abstracts will have changed since October 2026, so a re-run will differ in
a few verdicts.
