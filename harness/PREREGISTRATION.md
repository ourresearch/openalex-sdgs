# Pre-registrations

Two decisions in this project were made by rules written down before any of the labels they used existed. Both
are copied here as written, with internal file paths replaced by their places in this repo and budget lines removed.
Times are US Central.

## The committee eval (1 October 2026, 07:30, before any committee label existed)

**Why.** The September gold was one Claude Opus 5 pass under a rule copied from Jev's own instructions, and a judge's
rubric must not be written from the model's option texts. Title-only works (about 44% of the corpus) were never
tested, and the head was never scored on a public benchmark. Jason Priem asked for a committee of models.

**Rubric v2 (`harness/rubric.py`).** For each goal: the UN goal statement and a compressed list of its official
targets (from the UN SDG indicator framework, not from Jev's instructions). Question per (work, goal): does the work's
main subject or contribution address one of this goal's targets? Passing mentions, keyword overlap, and generic "this
matters for sustainability" lines are not enough. Title-only works are judged from what is there, with "no" when the
title alone doesn't establish it. Jev's one-line scopes (the SDG 9 negative clause, the 12/16/17 targets) are not
copied in.

**Judges.** One call per work returning 17 × {verdict yes/no, one-line reason}, strict JSON schema:

- Claude Opus 5.5 (`claude-opus-5-5`, effort high, cached system prompt; on refusal, retry once, then record `refused`).
- GPT-6.1 Sol (`openai/gpt-6.1-sol` via OpenRouter Responses, effort medium).
- Pairs where they agree are labelled. Pairs where they disagree go to Claude Fable 5.1 (`claude-fable-5-1`, effort
  high) with the work, that goal's rubric, and both judges' verdicts and reasons as "Judge A" / "Judge B" in random
  order; Fable returns the final verdict and reason. A Fable refusal leaves the pair `unresolved`: reported as a
  bracket (scored both ways), never dropped silently.

**Sets.**

- **S1**, continuity: the 598 September works. Worn (it chose the SDG 9 wording and the 0.4 threshold); reported, not
  used to decide.
- **S2**, decision set: a fresh simple random sample of **2,000 works** from works that have a work vector, excluding
  S1 and the 200,000 training and calibration works. Slices reported: abstract vs title-only, English vs other, core
  vs xpac. No stratification.

**Models scored on both sets.** Aurora (served tags at 0.4), Jev direct (current wording, including SDG 9 variant b;
a fresh Jev run on S2), head v1 (calibrated score, served threshold 0.4, scored from the work vectors).

**Metrics.** Per goal and pooled precision, recall and F1 at each model's served threshold, with Wilson 95% bounds and
a bootstrap over works; AUC for Jev and the head; head calibration vs the committee; labels per work and no-goal share
vs the committee's. Judge diagnostics: Opus–Sol pair agreement and kappa, how often Fable sided with each, each single
judge's own scoring of the three models (does the ranking depend on the judge?), refusal and unresolved counts.

**Pre-registered rules.**

- The head's threshold stays 0.4 on S2; any other threshold is a diagnostic, not a choice.
- **Title-only rule:** if the head's precision on S2 title-only works is below 0.60, propose a separate title-only
  threshold (chosen on one half of the title-only works, confirmed on the other) or no tags for title-only works,
  before the write.
- **Go rule for the write:** head pooled F1 on S2 ≥ Aurora's + 0.20 and the head beats Aurora on ≥ 13 of 17 goals. If
  missed, stop and tell Jason.

**Also:** the head on the Aurora survey set (surveyed pairs: AUC, F1 at 0.4, precision at Aurora's recall).

**Result.** Go rule PASS (head v1 F1 0.680 vs Aurora 0.295, gap +0.386, 17 of 17 goals); title-only rule not
triggered (head v1 precision 0.602). `python3 benchmarks/score_committee.py --head v1` reproduces it;
`benchmarks/data/committee/scores_v1.md` is its output.

## The SDG 15 fix (1 October 2026, 15:35, before any new label)

**Why.** Head v1's SDG 15 precision on S2 was 0.23 (17 right of 74 tags). About 34 of the 57 wrong tags were records
(GBIF occurrence downloads, specimen and observation records, figure excerpts of taxonomic articles) and about 10 were
taxonomy papers. Jev rated them 0.3 to 0.5, the head 0.9 to 1.0, because v1's training drops Jev's 0.3 to 0.7 band.
Jason Priem chose the narrow reading (a work counts when it addresses one of the goal's UN targets), then: "pick the
one that gets the highest score".

**Wordings** (shared positive part; they differ only in the taxonomy clause; full text in
`classifier/jev_request.py`, `TRAINING_SDG15_CANDIDATES`):

- `rec`: the goal's targets, then "a species occurrence download, a specimen or observation record, or a figure or
  excerpt from a taxonomic article is not by itself SDG 15".
- `rec_tax`: the same, plus "nor is a species description, taxonomic revision or phylogeny without a conservation,
  land-use or ecosystem aim".

**Relabel.** SDG 15 only, both wordings, on the 200,000 training works with a first SDG 15 answer of 0.2 or more (a
stricter wording cannot create positives; the rest keep their first label); same state as the SDG 9 relabel;
`jev-1.13.0`.

**Training variants** (goal 15 only; the other 16 goals stay v1 bit for bit): `drop` = v1 recipe (p ≥ 0.7 vs ≤ 0.3,
band dropped); `keep` = all training works, y = p ≥ 0.5. Isotonic calibration on the calibration split as v1. Four
candidates = 2 wordings × 2 recipes.

**Selection.** S2 halves by `int(work_id) % 2` (0 = choose, 1 = confirm). Committee labels, unresolved as no,
threshold 0.4 (unchanged). Choose the candidate with the highest SDG 15 F1 on the choose half (ties: higher
precision). **Confirm rule:** on the confirm half its F1 beats v1's and its precision is at least 0.50. If it fails,
report to Jason and ship nothing new for SDG 15 without his call. Diagnostics, not choices: full S2, S1, SDG 15 AUC on
the Aurora survey set, tag share on S2.

**Result.** `rec_tax/drop` chosen; confirm rule PASS (confirm half P 0.75, F1 0.57 vs v1's 0.32). Head v2 = v1 with
goal 15 replaced. `benchmarks/data/sdg15_fix/result.md`.
