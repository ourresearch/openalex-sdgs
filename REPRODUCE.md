# Reproduce

Every number here comes from files in the repo: the judges' verdicts, Jev's answers, the work vectors and the models'
scores are all stored, so no step below needs an API key, a GPU or any private resource until you choose to call a
model yourself. The repo holds no titles or abstracts; `classifier/fetch_works.py` rebuilds them from the public
OpenAlex API when a step needs text.

You need Python 3.10 or later.

```bash
git clone https://github.com/ourresearch/openalex-sdgs
cd openalex-sdgs
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## The benchmarks (seconds, a laptop)

```bash
python benchmarks/score_committee.py              # 2,000 random works + the September 598, head v2
python benchmarks/score_committee.py --head v1    # the same with head v1: the pre-registered go rule
python benchmarks/score_public.py                 # the Aurora survey set and OSDG-CD
python docs/charts/make_charts.py                 # redraws docs/img/*.svg from scores_v2.json
```

`score_committee.py` builds the committee's label for every (work, goal) pair from the three judges' rows, scores
Aurora, Jev direct and the head at their served thresholds, and writes `benchmarks/data/committee/scores_v2.md` (and
`.json`). It should print:

```
  s2: 2000 works | F1 aurora 0.2947 jev 0.7391 head v2 0.7015 | go rule PASS
  s1: 598 works | F1 aurora 0.3737 jev 0.7732 head v2 0.7162
```

and with `--head v1`, head 0.6803 and 0.7174. Bootstrap intervals use 1,000 resamples with seed 1300.

## The classifier (seconds)

```bash
python -m classifier.head --check
```

recomputes every shipped head score from the shipped vectors (`benchmarks/data/*/vectors.npz`) and weights
(`models/`), and prints the largest difference: 0 for both heads on both sets. To tag your own vectors:

```bash
python -m classifier.head --vectors my_vectors.npz --out scores.jsonl
```

## New works, end to end

```bash
python -m classifier.fetch_works --ids my_ids.txt --out works.jsonl --mailto you@example.org
pip install torch "sentence-transformers>=3"
python -m classifier.embed --input works.jsonl --out vectors.npz
python -m classifier.head --vectors vectors.npz --out scores.jsonl
```

OpenAlex embeds with a hosted copy of Qwen3-Embedding-0.6B; `embed.py` runs the open weights on the same text. We have
not yet measured how closely the two agree, so for an exact check use the shipped vectors.

## Ask Jev

Needs a key from [TypeSafe AI](https://typesafe.ai) (`export JEV_API_KEY=...`) and `pip install requests`; one request
per work, about 900 input tokens.

```bash
python -m classifier.jev --input works.jsonl --out labels.jsonl                    # the training request, all 17 goals
python -m classifier.jev --input works.jsonl --out jev.jsonl --request eval        # "Jev direct", as benchmarked
```

Jev is not bit-deterministic: asking again moves probabilities by a few hundredths. The answers that were benchmarked
and trained on are the stored ones.

## Retrain

`training/README.md`: rebuild the 200,000 training works' texts and vectors, then
`python training/train.py --vectors train_vectors.npz --version v2 --out my_head.json --compare models/sdg_jev_head_v2.json`
(needs scikit-learn). The SDG 15 candidates and their selection: `benchmarks/data/sdg15_fix/` and
`harness/PREREGISTRATION.md`.

## Judge again

Needs `pip install anthropic httpx`, `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY`. About 2,600 works, three models.

```bash
python -m classifier.fetch_works --ids benchmarks/data/committee/works.jsonl.gz --out works.jsonl
python harness/committee.py --works works.jsonl --out my_run
python benchmarks/score_committee.py --run my_run --out my_run
```

`harness/judge_september.py` re-runs the first test's single judge. The judges are not deterministic and texts change
upstream, so expect a few verdicts to differ from October 2026's.

## What cannot be redrawn from outside

The 2,000-work sample was drawn with SQL over OpenAlex's internal tables on 1 October 2026 (a hash order over works
with a vector, excluding the September set and the training works), and the 200,000 training works the same way in
September. Their ids are all here, which is what every score needs. The public benchmarks come from Zenodo:
[OSDG-CD](https://zenodo.org/records/6831287) (release 2022.07) and the [Aurora survey](https://zenodo.org/records/3813230).
Aurora's own model, to re-run it on OSDG-CD: [Zenodo 7304547](https://zenodo.org/records/7304547) (SDG-BERT v1.1, the
weights OpenAlex served).
