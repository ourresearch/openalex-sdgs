# Changelog

The classifier uses [semantic versioning](https://semver.org). A **major** version changes what counts as a right
answer (the rubric in `harness/rubric.py`) or replaces the approach. A **minor** version changes the classifier (the
weights, the threshold, Jev's instructions or snapshot, the embedding) and is benchmarked again on the committee's
2,000 works. A **patch** fixes code without changing any tag. Every release reports its benchmark here.

## 1.0.0 (4 October 2026)

First public release: head v2's weights, the 200,000 training labels, every test set (ids, scores, votes), every judge
verdict, and the code that trained, tagged, judged and scored.

Benchmarked on 2,000 random works judged by a committee (Claude Opus 5.5 and GPT-6.1 Sol, Claude Fable 5.1 deciding
their disagreements) under the UN's goal and target text (`python3 benchmarks/score_committee.py`): precision 0.68,
recall 0.72, F1 0.70; the Aurora SDG-BERT tags it replaced, 0.29, 0.31 and 0.29. Higher F1 on 17 of 17 goals. On the
Aurora survey's researcher votes (8,767 questions), F1 75.5 vs 63.6 and AUC 0.748 vs 0.607.

How it got here:

- **21 September 2026.** First test: Jev's 17 answers against one judge (Claude Opus 5) on 598 works, half random and
  half drawn from Aurora's tags. Jev F1 0.78, Aurora 0.42, and Jev ahead on all 17 goals.
- **22 September 2026.** Public benchmarks (OSDG-CD, the Aurora survey set). A search over Jev's instructions (GEPA)
  gave no held-out gain and was dropped. SDG 9 got a negative clause ("a new device, material or method is not by
  itself SDG 9") and was relabelled. Head v1 trained on 200,000 of Jev's answers: F1 0.77 against the September judge,
  with one threshold, 0.4, for every goal.
- **1 October 2026.** Because the September judge's rule came from Jev's own instructions, a committee re-judged 2,598
  works under a rubric written from the UN's text, with every rule pre-registered (`harness/PREREGISTRATION.md`). The
  go rule passed: head v1 F1 0.68 vs Aurora 0.29 on 2,000 fresh random works, 17 of 17 goals. It also showed head v1
  tagging GBIF occurrence downloads and specimen records as SDG 15 (precision 0.23). A pre-registered fix reworded the
  SDG 15 question, relabelled 13,085 works and retrained goal 15: head v2, SDG 15 precision 0.71, overall F1 0.70.
- **2 October 2026.** Head v2 scored every work with a vector (474,877,445). Aurora's last tags were copied, once, into
  a deprecated field, `sustainable_development_goals_aurora`, to be removed in November 2026.
- **3 October 2026.** The nightly build started writing head v2's goals into `sustainable_development_goals` and stopped
  running Aurora; from that night the API served head v2's goals for single works.
- **4 October 2026.** The search index was rebuilt with head v2's goals and swapped in (02:51 UTC), so filters and
  group-bys use them too, and the API dropped the experimental `x_sdgs` field (API properties version 15.0.0).
