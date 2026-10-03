# Benchmarks

Every number in the main [README](../README.md), how we got it, and how to check it. Everything here is rebuilt by

```
python3 benchmarks/score_committee.py              # the committee eval with head v2 -> data/committee/scores_v2.md
python3 benchmarks/score_committee.py --head v1    # the same with head v1, the pre-registered go rule -> scores_v1.md
python3 benchmarks/score_public.py                 # OSDG-CD and the Aurora survey set -> data/public_results.json
python3 harness/gepa/score_judged.py harness/gepa/pred_seed_judged.jsonl.gz harness/gepa/pred_best_judged.jsonl.gz
```

from files in `data/`: work ids, each model's scores, every judge's verdict and reason, and the votes of the public
sets. No title or abstract is included, because publishers own them; `classifier/fetch_works.py` rebuilds them from the
OpenAlex API.

## What right means

**A tag is right if a committee of judges, reading the work against the UN's goal and target text, agrees.** Claude
Opus 5.5 and GPT-6.1 Sol each read every work (title, venue, type and abstract when there is one) and answer, for each
of the 17 goals, whether the work's main subject or contribution addresses one of that goal's targets, with a one-line
reason. A passing mention, a keyword overlap or a line saying the work matters for sustainability is not enough. Where
they disagree, Claude Fable 5.1 reads the work, the goal's targets and both judges' reasons, and decides. The rubric is
[harness/rubric.py](../harness/rubric.py) and every word the judges saw is in
[harness/judge_prompts.md](../harness/judge_prompts.md). The rubric, the samples and the decision rules were fixed
before any judge ran ([pre-registration](../harness/PREREGISTRATION.md)).

On the 2,000 random works the two judges agreed on 98.9% of (work, goal) decisions (Cohen's kappa 0.77). Sol says yes
more often (3.0% of pairs vs 2.0%); Fable sided with Opus on 298 of 381 disagreements. Opus refused 10 works (each after a retry) and Fable one, leaving 171 of 34,000 pairs unresolved. Every number is computed twice, with those pairs counted as
no and as yes; the headline counts them as no, and no conclusion changes the other way.

## The sets

| Set | Works | What it is | Used for |
|---|---|---|---|
| [`data/committee`](data/committee/) S2 | 2,000 | Simple random sample of works with a vector, drawn 1 October 2026, none used in training | **The benchmark.** Nothing was tuned on it except SDG 15 (below) |
| [`data/committee`](data/committee/) S1 | 598 | September's test set: 300 random works with an abstract, 300 drawn from Aurora's tags | Continuity; it chose the 0.4 threshold and the SDG 9 wording |
| [`data/aurora_survey`](data/aurora_survey/) | 8,767 questions | Researchers' votes on (paper, goal) pairs, 2019-2020 | A benchmark with no model in the loop |
| [`data/osdg`](data/osdg/) | 23,362 excerpts | OSDG-CD: policy and research excerpts, one volunteer-voted goal each | The community benchmark, for Jev and Aurora |

## The benchmark: 2,000 random works

Pooled over all 34,000 (work, goal) pairs, each classifier at its served threshold:

| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right / wrong / missed tags |
|---|---|---|---|---|
| Aurora SDG-BERT (old, 0.4) | 0.285 (0.25–0.32) | 0.305 (0.27–0.34) | **0.295** (0.27–0.33) | 224 / 562 / 510 |
| Jev direct (0.5) | 0.762 (0.73–0.79) | 0.718 (0.68–0.75) | **0.739** (0.71–0.76) | 527 / 165 / 207 |
| Head v1 (0.4) | 0.640 (0.61–0.67) | 0.726 (0.69–0.76) | **0.680** (0.65–0.71) | 533 / 300 / 201 |
| **Head v2 (0.4, served)** | 0.681 (0.65–0.71) | 0.723 (0.69–0.75) | **0.702** (0.67–0.73) | 531 / 249 / 203 |

Intervals: Wilson for precision and recall, a bootstrap over works for F1. Head v2 minus Aurora is +0.41 F1 (+0.37
to +0.44, paired bootstrap). The head beats Aurora on all 17 goals; per-goal tables are in
[`data/committee/scores_v2.md`](data/committee/scores_v2.md). Goals with fewer than 15 committee yeses (1, 5, 13, 14,
17) have wide intervals.

**The pre-registered go rule passed** on head v1, the head it was written for: F1 0.680 vs 0.295, a gap of +0.386
where the rule needed +0.20, and 17 of 17 goals where it needed 13. Counting unresolved pairs as yes: 0.624 vs 0.272,
16 of 17.

**Slices** (head v2, F1; unresolved as no):

| Slice | Works | Aurora | Jev direct | Head v2 |
|---|---|---|---|---|
| With an abstract | 1,260 | 0.32 | 0.75 | 0.71 |
| Title only | 740 | 0.20 | 0.71 | 0.66 |
| English | 1,386 | 0.30 | 0.75 | 0.72 |
| Other or unknown language | 614 | 0.28 | 0.71 | 0.67 |
| Core sources | 1,395 | 0.31 | 0.76 | 0.71 |
| Other sources (xpac) | 605 | 0.25 | 0.66 | 0.65 |

The pre-registered title-only rule (act if the head's precision on title-only works is below 0.60) was not triggered:
0.602 for head v1, 0.646 for head v2.

**The ranking does not depend on the judge.** With each judge's labels alone as the answer key, F1 on the works both
answered is Aurora 0.30, head v2 0.70, Jev 0.73 under Opus 5.5; Aurora 0.31, head v2 0.67, Jev 0.69 under Sol.

**How many goals per work.** The committee gives no goal to 69.5% of works and two or more to 5.1%; head v2 67.0% and
5.0%; Aurora 60.9% and 0.2%. Aurora almost never gives a second goal.

## What `score` means

The head's score is calibrated to Jev's answers, not to the committee, so read it as confidence, not probability.
Share of head v2's (work, goal) pairs the committee says yes to, by score:

| Score | Pairs | Committee yes |
|---|---|---|
| 0.1-0.2 | 253 | 12% |
| 0.2-0.3 | 205 | 19% |
| 0.3-0.4 | 73 | 27% |
| 0.4-0.5 | 73 | 34% |
| 0.5-0.6 | 98 | 45% |
| 0.6-0.7 | 87 | 56% |
| 0.7-0.8 | 67 | 57% |
| 0.8-0.9 | 115 | 71% |
| 0.9-1.0 | 340 | 86% |

Below 0.1: 32,689 pairs, 0.4% yes. The threshold stayed at 0.4 as pre-registered; the F1-maximising threshold on
this set is 0.50, at the same F1 (0.702).

## Public benchmarks

**Aurora survey set** ([Zenodo 3813230](https://zenodo.org/records/3813230), CC BY 4.0). From October 2019 to January
2020, 244 researchers were each shown 100 papers that the Aurora project's search query for one goal had found, and
asked whether each contributes to that goal. 10,704 (paper, goal) pairs; 8,889 papers resolved in OpenAlex. Scored on
the 8,767 questions with a clear majority (5,473 yes, 3,294 no):

| Model | AUC | F1 at 0.4 (P / R) | Precision at Aurora's recall (0.569) | Goals per paper at 0.4 |
|---|---|---|---|---|
| Aurora, as OpenAlex served it | 0.607 | 63.6 (72.2 / 56.9) | 72.2 | 0.82 |
| Jev direct | 0.754 | 78.3 (75.5 / 81.3) | 81.2 | 2.02 |
| Head v1 | 0.746 | 75.6 (77.8 / 73.5) | 80.3 | 1.53 |
| Head v2 (served) | 0.748 | 75.5 (77.9 / 73.3) | 80.4 | 1.52 |

Under the protocol of Kashnitsky et al. 2024 (QSS, arXiv 2209.07285), which counts every goal never asked about as a
false positive, Aurora scores micro F1 61.4 and the heads 55.5 to 55.7, because they give a second goal that nobody was
asked to vote on. Their top goal is in the gold more often (62% vs 56%). Both protocols: `score_public.py`.

**OSDG-CD** ([Zenodo 6831287](https://zenodo.org/records/6831287), CC BY 4.0, release 2022.07). 23,362 excerpts with
positive minus negative votes of 2 or more, SDGs 1-15. The heads cannot be scored here (they read OpenAlex's work
vectors, and excerpts are not works), so this compares Jev, the head's teacher, with Aurora's model, run locally
from its published weights (99.5% tag agreement with the tags OpenAlex served, on 448 works):

| Model | Micro F1 | Macro F1 | Top-1 accuracy | Single-label micro F1 |
|---|---|---|---|---|
| Aurora SDG-BERT, published by Kashnitsky et al. | 53 | 46 | | |
| Aurora SDG-BERT, run here, 0.4 | 55.3 | 50.1 | 54.3% | 55.1 |
| Aurora SDG-BERT, run here, 0.3 (its best) | 57.8 | 53.3 | 54.3% | 57.1 |
| Jev direct, 0.5 | 60.0 | 60.7 | 70.0% | 70.3 |
| Jev direct, 0.6 | 60.8 | 58.9 | 70.0% | 65.8 |

Each excerpt has one gold goal, so any second goal counts as wrong; single-label mode keeps only each model's top goal.

## How the classifier was built and checked

**Head vs its teacher.** On 20,000 held-out works, head v1 ranks Jev's answers with AUC 0.979 to 0.998 per goal
(mean 0.991), agrees with every one of Jev's confident answers (p ≥ 0.9 or ≤ 0.1), and after isotonic calibration its
expected calibration error against Jev is 0.005 or less on every goal. Head v2 changes only goal 15. Per goal:
`python training/train.py` prints the table.

**One threshold for all goals.** On the September set, per-goal thresholds won in-sample and lost under 2-fold
cross-validation (20 splits): uniform 0.4 scored 0.767, per-goal thresholds 0.733 to 0.750. With a calibrated score
and 6 to 31 positives per goal, one threshold is the honest choice; 0.4 also reproduced the judge's rate of goals per
work (0.78 vs 0.80).

**SDG 9 wording** (September set, 598 works, first judge). Jev read "industry, innovation and infrastructure"
literally and tagged any new material or device. Three wordings for the SDG 9 question:

| SDG 9 instruction | F1 at its best threshold | AUC | Random works tagged at 0.5 (judge: 12) |
|---|---|---|---|
| The goal's name | 0.55 | 0.967 | 38 |
| a: name + "industrialisation, resilient infrastructure, R&D capacity and access to technology in developing contexts" | 0.53 | 0.961 | 7 |
| **b**: name + targets + "a new device, material or method is not by itself SDG 9" | **0.63** | **0.969** | 9 |

The explicit negative clause is what works. Wording b was adopted and SDG 9 relabelled on the 66,548 training works
whose first answer was 0.2 or more.

**SDG 15 fix** ([pre-registered](../harness/PREREGISTRATION.md#the-sdg-15-fix-1-october-2026-1535-before-any-new-label),
[result](data/sdg15_fix/result.md)). Head v1's SDG 15 tags on the 2,000 works were right 23% of the time: most wrong ones
were GBIF occurrence downloads, specimen records and species descriptions (about 1 in 120 random works is a GBIF
download). Jev rated them 0.3 to 0.5, inside the band that training drops, so the head never saw them as negatives. A
negative clause in the SDG 15 question, a relabel of 13,085 works and a retrained goal 15 took SDG 15 from 74 tags
(P 0.23, F1 0.33) to 21 (P 0.71, F1 0.61), with no record or taxonomy tag left. The candidate was chosen on half the
works and confirmed on the other half. On the Aurora survey's 572 clear SDG 15 questions, AUC rose from 0.73 to 0.76.
Researchers in that survey split 7 to 6 on pure taxonomy papers; we took the narrower reading.

**GEPA: no gain.** An automated search over Jev's instructions (63 candidates) raised its training objective but not
held-out ranking (AUC 0.993 → 0.991 on 198 judged works; OSDG-CD micro F1 60.8 → 59.1). The seed instructions stayed.
[harness/gepa/](../harness/gepa/README.md).

## The first test, September 2026

Before the committee, one judge (Claude Opus 5, the rule Jev was given) labelled the 598 works of S1
([`data/september`](data/september/)). Pooled F1: Aurora 0.42, Jev direct 0.78, head v1 0.77. Claude Fable 5.1
re-judged 58 of them: 99.0% agreement, kappa 0.89. That answer key shared Jev's own wording, so the committee replaced
it; under the committee the same works score Aurora 0.37, Jev 0.77, head v1 0.72, head v2 0.72. The committee agreed
with the September judge on 98.5% of pairs and is a little stricter.

## Files

| Path | What |
|---|---|
| `data/committee/works.jsonl.gz` | S1 and S2: work id, set, slice fields, Aurora's served tags |
| `data/committee/{opus,sol,fable}.jsonl.gz` | Every judge row: verdict and reason per goal, status, served model |
| `data/committee/committee.jsonl.gz` | The committee label per (work, goal) and where it came from |
| `data/committee/{jev,head_v1,head_v2}.jsonl.gz` | Each model's 17 scores per work |
| `data/committee/vectors.npz` | The 2,598 works' Qwen3 vectors as served, so the heads can be re-scored |
| `data/committee/scores_v{1,2}.{md,json}` | Every table, written by `score_committee.py` |
| `data/committee/judges_summary.json` | The harness's own judge counts |
| `data/september/` | The 600 September works, the Opus 5 judge, the Fable second opinion, Jev under three SDG 9 wordings |
| `data/aurora_survey/` | Votes (`pairs`), DOI to work id, each model's scores, the papers' vectors |
| `data/osdg/` | Gold (no text), Jev's and Aurora's scores |
| `data/sdg15_fix/` | The SDG 15 candidates on both halves |
