# GEPA over Jev's instructions: no gain, rejected

**An automated prompt search made Jev's probabilities higher, not its ranking better, so we kept the hand-written
instructions.**

In September 2026 we ran [GEPA](https://github.com/gepa-ai/gepa) over the 18 texts Jev reads for this task: the rule
and the 17 goal instructions. Claude Opus 5 proposed rewrites from Jev's mistakes; each candidate was scored on judged
works (half the mean probability on gold goals, half the mean of one minus it on the rest) and on Aurora survey votes
(one minus the error). Train: 250 judged works and 2,500 survey pairs; validation: 150 and 1,200; held out: 198
judged works, 5,067 survey pairs and all of OSDG-CD. 63 candidates.

The best candidate rewrote the rule and goals 2, 4, 9 and 15 (`run1_result.json`), and raised the validation score
from 0.6571 to 0.6754. On held-out data:

| Held-out set | Metric | Seed instructions | GEPA best |
|---|---|---|---|
| 198 judged works (163 gold pairs of 3,366) | pooled AUC | 0.993 | 0.991 |
| | pooled F1 at its own best threshold | 77.4 (0.5) | 79.8 (0.6) |
| | precision / recall at 0.5 | 77.0 / 77.9 | 62.1 / 89.6 |
| 5,067 survey pairs | AUC | 0.757 | 0.751 |
| | F1 at its own best threshold | 78.6 (0.4) | 79.4 (0.4) |
| OSDG-CD, 23,362 excerpts | micro / macro F1 at its own best threshold | 60.8 / 60.7 (0.6) | 59.1 / 59.3 (0.7) |
| | top-1 accuracy | 70.0 | 70.2 |

The objective rewarded pushing gold probabilities up, and that is what the search found: at any fixed threshold
recall rose and precision fell, and AUC, which ignores calibration, was flat or slightly down everywhere. The rewrites
read sensibly but trade one set of scope calls for another. Optimizing a ranking metric with the rule held fixed
would be the better test, if anyone tries again.

`python3 score_judged.py pred_seed_judged.jsonl.gz pred_best_judged.jsonl.gz` reproduces the judged rows. The
other predictions (`pred_best_aurora`, `pred_best_osdg`) score with the functions in `benchmarks/score_public.py`.
`splits.json` lists the ids; the scripts are a record of what ran (they used OpenAlex's internal asynchronous Jev
client; `classifier/jev.py` is the public one).
