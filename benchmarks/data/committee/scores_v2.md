# SDG committee eval: scores (head v2)

Written by `benchmarks/score_committee.py --head v2` from `benchmarks/data/committee/`. Rubric 59d19e472eb8. Bootstrap 1000 resamples over works, seed 1300. Head v2: `models/sdg_jev_head_v2.json`.

## Headline

**Go rule on S2: PASS.** On 2,000 fresh random works (S2), the head's pooled F1 is **0.70** (0.67–0.73) against Aurora's **0.29** (0.27–0.33), a gap of +0.41 (+0.37 to +0.44) where the rule needs +0.20, and the head beats Aurora on 17 of 17 goals where the rule needs 13. Jev direct, the head's teacher, scores 0.74 (0.71–0.76). On title-only works (740), the head's precision is 0.65 (0.57–0.72): the pre-registered title-only rule (act if below 0.60) is **not triggered**. 273 of 44,166 (work, goal) pairs are unresolved (a judge refused or failed, or Fable had not ruled); every score is computed twice, with them counted as no and as yes; the go-rule verdict is the same whichever way they are counted. On September's 598 works (S1, continuity only: this set already chose the 0.4 threshold and the SDG 9 wording), F1 is Aurora 0.37, Jev 0.77, head 0.72.

**How to read this.** Each model tags a work with zero or more of the 17 goals. The committee (Opus 5.5 and GPT-6.1 Sol, Fable 5.1 breaking ties) is the answer key. *Precision*: of the tags a model gives, the share the committee agrees with. *Recall*: of the committee's tags, the share the model finds. *F1*: one number balancing the two (0 to 1). *AUC*: how well a model's score ranks right tags above wrong ones (0.5 = coin flip, 1 = perfect). Ranges in brackets are 95% confidence intervals: Wilson for precision and recall, bootstrap over works for F1.

## S2: the decision set (2,000 fresh random works)

2,000 works judged, 34,000 (work, goal) pairs; committee yes on 734 pairs; 171 unresolved pairs on 11 works.

### Pre-registered go rule

Head pooled F1 ≥ Aurora's + 0.20 **and** head beats Aurora on ≥ 13 of 17 goals.

| unresolved counted as | head F1 | Aurora F1 | gap (95% CI) | goals won | result |
|---|---|---|---|---|---|
| no | 0.702 | 0.295 | +0.407 (+0.373 to +0.439) | 17 of 17 | PASS |
| yes | 0.641 | 0.272 | +0.369 (+0.329 to +0.408) | 16 of 17 | PASS |

**Verdict: PASS.**

### Pooled over every (work, goal) pair

*Unresolved pairs counted as no*

| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right tags / wrong tags / missed |
|---|---|---|---|---|
| Aurora (served, 0.4) | 0.285 (0.25–0.32) | 0.305 (0.27–0.34) | **0.295** (0.27–0.33) | 224 / 562 / 510 |
| Jev direct (0.5) | 0.762 (0.73–0.79) | 0.718 (0.68–0.75) | **0.739** (0.71–0.76) | 527 / 165 / 207 |
| Head v2 (0.4) | 0.681 (0.65–0.71) | 0.723 (0.69–0.75) | **0.702** (0.67–0.73) | 531 / 249 / 203 |

F1 differences (paired bootstrap over works, 95% CI): head − Aurora +0.407 (+0.373 to +0.439); Jev − Aurora +0.444 (+0.408 to +0.477); head − Jev -0.038 (-0.064 to -0.011).

*Unresolved pairs counted as yes*

| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right tags / wrong tags / missed |
|---|---|---|---|---|
| Aurora (served, 0.4) | 0.293 (0.26–0.33) | 0.254 (0.23–0.28) | **0.272** (0.24–0.30) | 230 / 556 / 675 |
| Jev direct (0.5) | 0.772 (0.74–0.80) | 0.590 (0.56–0.62) | **0.669** (0.62–0.72) | 534 / 158 / 371 |
| Head v2 (0.4) | 0.692 (0.66–0.72) | 0.597 (0.56–0.63) | **0.641** (0.60–0.68) | 540 / 240 / 365 |

F1 differences (paired bootstrap over works, 95% CI): head − Aurora +0.369 (+0.329 to +0.408); Jev − Aurora +0.397 (+0.355 to +0.441); head − Jev -0.028 (-0.052 to -0.004).

AUC (pooled pairs): Jev 0.992, head 0.977 (unresolved as yes: Jev 0.887, head 0.883).

### Per goal

Each cell is precision / recall / F1 at the model's served threshold. The head beats Aurora on F1 on **17 of 17** goals (Jev beats Aurora on 17; the head beats Jev on 4); with unresolved pairs counted as yes, the head beats Aurora on 16. Goals with fewer than 15 committee yes pairs have wide intervals.

| SDG | committee yes | unresolved | Aurora | Jev direct | Head v2 | Jev AUC | Head AUC | head vs Aurora |
|---|---|---|---|---|---|---|---|---|
| 1 No poverty | 6 | 10 | 0.18 / 0.33 / 0.24 | 0.67 / 1.00 / 0.80 | 0.80 / 0.67 / 0.73 | 1.000 | 0.886 | won |
| 2 Zero hunger | 54 | 10 | 0.21 / 0.31 / 0.25 | 0.88 / 0.39 / 0.54 | 0.62 / 0.83 / 0.71 | 0.995 | 0.991 | won |
| 3 Good health and well-being | 283 | 11 | 0.85 / 0.30 / 0.44 | 0.83 / 0.88 / 0.85 | 0.81 / 0.88 / 0.84 | 0.988 | 0.982 | won |
| 4 Quality education | 68 | 10 | 0.41 / 0.41 / 0.41 | 0.95 / 0.81 / 0.87 | 0.82 / 0.79 / 0.81 | 0.998 | 0.996 | won |
| 5 Gender equality | 14 | 10 | 0.19 / 0.64 / 0.29 | 0.82 / 0.64 / 0.72 | 0.60 / 0.43 / 0.50 | 0.997 | 0.960 | won |
| 6 Clean water and sanitation | 22 | 10 | 0.24 / 0.41 / 0.31 | 0.95 / 0.82 / 0.88 | 0.84 / 0.73 / 0.78 | 0.999 | 0.972 | won |
| 7 Affordable and clean energy | 19 | 10 | 0.05 / 0.32 / 0.09 | 0.88 / 0.74 / 0.80 | 0.78 / 0.74 / 0.76 | 0.995 | 0.968 | won |
| 8 Decent work and economic growth | 35 | 10 | 0.23 / 0.31 / 0.27 | 0.66 / 0.60 / 0.63 | 0.55 / 0.63 / 0.59 | 0.988 | 0.962 | won |
| 9 Industry, innovation and infrastructure | 44 | 10 | 0.17 / 0.11 / 0.14 | 0.55 / 0.61 / 0.58 | 0.44 / 0.50 / 0.47 | 0.981 | 0.927 | won |
| 10 Reduced inequalities | 24 | 10 | 0.09 / 0.17 / 0.12 | 0.48 / 0.58 / 0.53 | 0.50 / 0.42 / 0.45 | 0.980 | 0.970 | won |
| 11 Sustainable cities and communities | 28 | 10 | 0.29 / 0.36 / 0.32 | 0.75 / 0.43 / 0.55 | 0.65 / 0.54 / 0.59 | 0.986 | 0.927 | won |
| 12 Responsible consumption and production | 35 | 10 | 0.75 / 0.09 / 0.15 | 0.69 / 0.63 / 0.66 | 0.59 / 0.37 / 0.46 | 0.985 | 0.973 | won |
| 13 Climate action | 13 | 10 | 0.14 / 0.31 / 0.20 | 0.53 / 0.62 / 0.57 | 0.53 / 0.69 / 0.60 | 0.990 | 0.990 | won |
| 14 Life below water | 10 | 10 | 0.16 / 0.70 / 0.26 | 0.46 / 0.60 / 0.52 | 0.50 / 0.40 / 0.44 | 0.997 | 0.978 | won |
| 15 Life on land | 28 | 10 | 0.28 / 0.36 / 0.31 | 0.58 / 0.54 / 0.56 | 0.71 / 0.54 / 0.61 | 0.986 | 0.934 | won |
| 16 Peace, justice and strong institutions | 43 | 10 | 0.27 / 0.30 / 0.28 | 0.76 / 0.65 / 0.70 | 0.41 / 0.74 / 0.52 | 0.992 | 0.983 | won |
| 17 Partnerships for the goals | 8 | 10 | 0.13 / 0.25 / 0.17 | 0.33 / 0.25 / 0.29 | 0.50 / 0.12 / 0.20 | 0.913 | 0.858 | won |

### Labels per work

| | no goal | 1 goal | 2+ goals | mean goals per work |
|---|---|---|---|---|
| Committee (unresolved as no) | 69.5% | 25.4% | 5.1% | 0.37 |
| Committee (unresolved as yes) | 69.0% | 25.4% | 5.7% | 0.45 |
| Aurora (served, 0.4) | 60.9% | 38.9% | 0.2% | 0.39 |
| Jev direct (0.5) | 72.8% | 21.6% | 5.6% | 0.35 |
| Head v2 (0.4) | 67.0% | 28.1% | 5.0% | 0.39 |

### Is the head's score an honest probability? (calibration)

If the head says 0.7, about 70% of such pairs should be committee yes. ECE is the average gap (0 = perfect).

| head p | pairs | mean p | committee yes-rate | yes-rate, unresolved as yes |
|---|---|---|---|---|
| 0.0-0.1 | 32,689 | 0.002 | 0.004 | 0.008 |
| 0.1-0.2 | 253 | 0.140 | 0.115 | 0.122 |
| 0.2-0.3 | 205 | 0.243 | 0.190 | 0.195 |
| 0.3-0.4 | 73 | 0.348 | 0.274 | 0.274 |
| 0.4-0.5 | 73 | 0.442 | 0.343 | 0.370 |
| 0.5-0.6 | 98 | 0.548 | 0.449 | 0.459 |
| 0.6-0.7 | 87 | 0.645 | 0.563 | 0.563 |
| 0.7-0.8 | 67 | 0.742 | 0.567 | 0.567 |
| 0.8-0.9 | 115 | 0.838 | 0.713 | 0.722 |
| 0.9-1.0 | 340 | 0.967 | 0.862 | 0.876 |

ECE: 0.005 (unresolved as yes: 0.009).

**Diagnostic only, not a choice** (pre-registered: the threshold stays 0.4): the uniform head threshold that maximises pooled F1 on this set is 0.50 (P 0.716 / R 0.689 / F1 0.702) vs F1 0.702 at 0.4.

### Slices

Pre-registered slices. Same pooled metrics, unresolved counted as no.

| Slice | works | committee yes pairs | Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) |
|---|---|---|---|---|---|---|
| With an abstract | 1,260 | 579 | Aurora | 0.317 (0.28–0.36) | 0.326 (0.29–0.37) | 0.322 (0.29–0.36) |
|  |  |  | Jev | 0.759 (0.72–0.79) | 0.736 (0.70–0.77) | 0.747 (0.72–0.78) |
|  |  |  | Head | 0.690 (0.65–0.72) | 0.738 (0.70–0.77) | 0.713 (0.68–0.74) |
| Title only (no abstract shown to the judges) | 740 | 155 | Aurora | 0.184 (0.14–0.25) | 0.226 (0.17–0.30) | 0.203 (0.15–0.26) |
|  |  |  | Jev | 0.771 (0.69–0.83) | 0.652 (0.57–0.72) | 0.706 (0.65–0.76) |
|  |  |  | Head | 0.646 (0.57–0.72) | 0.671 (0.59–0.74) | 0.658 (0.60–0.72) |
| English | 1,386 | 501 | Aurora | 0.279 (0.24–0.32) | 0.323 (0.28–0.37) | 0.299 (0.26–0.34) |
|  |  |  | Jev | 0.759 (0.72–0.79) | 0.747 (0.71–0.78) | 0.752 (0.72–0.78) |
|  |  |  | Head | 0.685 (0.64–0.72) | 0.750 (0.71–0.79) | 0.716 (0.69–0.75) |
| Other or unknown language | 614 | 233 | Aurora | 0.302 (0.24–0.37) | 0.266 (0.21–0.33) | 0.283 (0.23–0.34) |
|  |  |  | Jev | 0.769 (0.71–0.82) | 0.657 (0.59–0.71) | 0.708 (0.66–0.76) |
|  |  |  | Head | 0.671 (0.61–0.73) | 0.665 (0.60–0.72) | 0.668 (0.61–0.72) |
| Core (not xpac) | 1,395 | 587 | Aurora | 0.309 (0.27–0.35) | 0.308 (0.27–0.35) | 0.309 (0.27–0.34) |
|  |  |  | Jev | 0.769 (0.73–0.80) | 0.748 (0.71–0.78) | 0.758 (0.73–0.78) |
|  |  |  | Head | 0.680 (0.64–0.71) | 0.750 (0.71–0.78) | 0.713 (0.68–0.74) |
| xpac | 605 | 147 | Aurora | 0.215 (0.16–0.28) | 0.292 (0.23–0.37) | 0.248 (0.19–0.30) |
|  |  |  | Jev | 0.727 (0.64–0.80) | 0.599 (0.52–0.67) | 0.657 (0.58–0.72) |
|  |  |  | Head | 0.684 (0.60–0.76) | 0.619 (0.54–0.69) | 0.650 (0.57–0.72) |
| Head vector built without an abstract (diagnostic) | 875 | 238 | Aurora | 0.224 (0.18–0.28) | 0.252 (0.20–0.31) | 0.237 (0.19–0.28) |
|  |  |  | Jev | 0.772 (0.71–0.82) | 0.698 (0.64–0.75) | 0.733 (0.69–0.78) |
|  |  |  | Head | 0.668 (0.61–0.72) | 0.702 (0.64–0.76) | 0.684 (0.64–0.73) |

**Title-only rule** (pre-registered: if the head's precision on S2 title-only works is below 0.60, propose a separate title-only threshold or no tags for title-only works before the write):

- unresolved counted as no: head precision 0.646 (0.57–0.72) on 740 title-only works → **not triggered**
- unresolved counted as yes: head precision 0.652 (0.58–0.72) on 740 title-only works → **not triggered**

## S1: September's 598 works (continuity; worn)

598 works judged, 10,166 (work, goal) pairs; committee yes on 416 pairs; 102 unresolved pairs on 6 works.

### Pooled over every (work, goal) pair

*Unresolved pairs counted as no*

| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right tags / wrong tags / missed |
|---|---|---|---|---|
| Aurora (served, 0.4) | 0.353 (0.31–0.40) | 0.397 (0.35–0.44) | **0.374** (0.33–0.41) | 165 / 302 / 251 |
| Jev direct (0.5) | 0.756 (0.71–0.79) | 0.791 (0.75–0.83) | **0.773** (0.74–0.81) | 329 / 106 / 87 |
| Head v2 (0.4) | 0.683 (0.64–0.72) | 0.752 (0.71–0.79) | **0.716** (0.68–0.75) | 313 / 145 / 103 |

F1 differences (paired bootstrap over works, 95% CI): head − Aurora +0.342 (+0.297 to +0.389); Jev − Aurora +0.400 (+0.351 to +0.449); head − Jev -0.057 (-0.087 to -0.024).

*Unresolved pairs counted as yes*

| Model | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | right tags / wrong tags / missed |
|---|---|---|---|---|
| Aurora (served, 0.4) | 0.364 (0.32–0.41) | 0.328 (0.29–0.37) | **0.345** (0.30–0.39) | 170 / 297 / 348 |
| Jev direct (0.5) | 0.770 (0.73–0.81) | 0.647 (0.60–0.69) | **0.703** (0.64–0.76) | 335 / 100 / 183 |
| Head v2 (0.4) | 0.694 (0.65–0.73) | 0.614 (0.57–0.65) | **0.652** (0.60–0.71) | 318 / 140 / 200 |

F1 differences (paired bootstrap over works, 95% CI): head − Aurora +0.306 (+0.258 to +0.358); Jev − Aurora +0.358 (+0.305 to +0.415); head − Jev -0.051 (-0.078 to -0.021).

AUC (pooled pairs): Jev 0.989, head 0.975 (unresolved as yes: Jev 0.877, head 0.873).

### Per goal

Each cell is precision / recall / F1 at the model's served threshold. The head beats Aurora on F1 on **17 of 17** goals (Jev beats Aurora on 17; the head beats Jev on 4); with unresolved pairs counted as yes, the head beats Aurora on 17. Goals with fewer than 15 committee yes pairs have wide intervals.

| SDG | committee yes | unresolved | Aurora | Jev direct | Head v2 | Jev AUC | Head AUC | head vs Aurora |
|---|---|---|---|---|---|---|---|---|
| 1 No poverty | 8 | 6 | 0.12 / 0.25 / 0.16 | 0.64 / 0.88 / 0.74 | 0.62 / 0.62 / 0.62 | 0.996 | 0.969 | won |
| 2 Zero hunger | 26 | 6 | 0.35 / 0.46 / 0.40 | 0.92 / 0.46 / 0.62 | 0.57 / 0.81 / 0.67 | 0.990 | 0.971 | won |
| 3 Good health and well-being | 129 | 6 | 0.84 / 0.40 / 0.54 | 0.81 / 0.95 / 0.87 | 0.77 / 0.93 / 0.85 | 0.981 | 0.974 | won |
| 4 Quality education | 35 | 6 | 0.60 / 0.51 / 0.55 | 0.94 / 0.89 / 0.91 | 0.81 / 0.83 / 0.82 | 0.997 | 0.994 | won |
| 5 Gender equality | 13 | 6 | 0.35 / 0.54 / 0.42 | 0.79 / 0.85 / 0.81 | 0.85 / 0.85 / 0.85 | 0.999 | 0.997 | won |
| 6 Clean water and sanitation | 12 | 6 | 0.31 / 0.67 / 0.42 | 0.75 / 0.75 / 0.75 | 0.69 / 0.75 / 0.72 | 0.998 | 0.995 | won |
| 7 Affordable and clean energy | 14 | 6 | 0.13 / 0.43 / 0.20 | 0.69 / 0.79 / 0.73 | 0.62 / 0.71 / 0.67 | 0.998 | 0.990 | won |
| 8 Decent work and economic growth | 27 | 6 | 0.39 / 0.33 / 0.36 | 0.79 / 0.70 / 0.75 | 0.67 / 0.52 / 0.58 | 0.984 | 0.928 | won |
| 9 Industry, innovation and infrastructure | 23 | 6 | 0.30 / 0.26 / 0.28 | 0.63 / 0.83 / 0.72 | 0.48 / 0.48 / 0.48 | 0.981 | 0.931 | won |
| 10 Reduced inequalities | 24 | 6 | 0.09 / 0.12 / 0.11 | 0.58 / 0.75 / 0.65 | 0.70 / 0.67 / 0.68 | 0.984 | 0.952 | won |
| 11 Sustainable cities and communities | 22 | 6 | 0.29 / 0.27 / 0.28 | 0.88 / 0.68 / 0.77 | 0.72 / 0.59 / 0.65 | 0.981 | 0.927 | won |
| 12 Responsible consumption and production | 23 | 6 | 0.32 / 0.26 / 0.29 | 0.59 / 0.74 / 0.65 | 0.62 / 0.70 / 0.65 | 0.982 | 0.981 | won |
| 13 Climate action | 10 | 6 | 0.31 / 0.50 / 0.38 | 0.50 / 0.70 / 0.58 | 0.45 / 0.50 / 0.48 | 0.973 | 0.958 | won |
| 14 Life below water | 6 | 6 | 0.22 / 0.83 / 0.34 | 0.83 / 0.83 / 0.83 | 0.67 / 0.67 / 0.67 | 1.000 | 0.997 | won |
| 15 Life on land | 13 | 6 | 0.30 / 0.54 / 0.39 | 0.71 / 0.77 / 0.74 | 0.75 / 0.46 / 0.57 | 0.997 | 0.982 | won |
| 16 Peace, justice and strong institutions | 23 | 6 | 0.28 / 0.48 / 0.35 | 0.85 / 0.48 / 0.61 | 0.53 / 0.91 / 0.67 | 0.985 | 0.990 | won |
| 17 Partnerships for the goals | 8 | 6 | 0.12 / 0.25 / 0.17 | 0.62 / 0.62 / 0.62 | 0.50 / 0.25 / 0.33 | 0.928 | 0.941 | won |

### Labels per work

| | no goal | 1 goal | 2+ goals | mean goals per work |
|---|---|---|---|---|
| Committee (unresolved as no) | 49.0% | 37.5% | 13.6% | 0.70 |
| Committee (unresolved as yes) | 48.0% | 37.5% | 14.5% | 0.87 |
| Aurora (served, 0.4) | 22.7% | 76.4% | 0.8% | 0.78 |
| Jev direct (0.5) | 47.3% | 40.1% | 12.5% | 0.73 |
| Head v2 (0.4) | 42.8% | 43.5% | 13.7% | 0.77 |

### Is the head's score an honest probability? (calibration)

If the head says 0.7, about 70% of such pairs should be committee yes. ECE is the average gap (0 = perfect).

| head p | pairs | mean p | committee yes-rate | yes-rate, unresolved as yes |
|---|---|---|---|---|
| 0.0-0.1 | 9,425 | 0.003 | 0.006 | 0.016 |
| 0.1-0.2 | 132 | 0.138 | 0.167 | 0.174 |
| 0.2-0.3 | 114 | 0.240 | 0.123 | 0.123 |
| 0.3-0.4 | 37 | 0.343 | 0.243 | 0.243 |
| 0.4-0.5 | 42 | 0.440 | 0.405 | 0.429 |
| 0.5-0.6 | 51 | 0.546 | 0.372 | 0.372 |
| 0.6-0.7 | 53 | 0.644 | 0.396 | 0.396 |
| 0.7-0.8 | 47 | 0.745 | 0.575 | 0.575 |
| 0.8-0.9 | 63 | 0.839 | 0.698 | 0.714 |
| 0.9-1.0 | 202 | 0.975 | 0.916 | 0.931 |

ECE: 0.011 (unresolved as yes: 0.020).

**Diagnostic only, not a choice** (pre-registered: the threshold stays 0.4): the uniform head threshold that maximises pooled F1 on this set is 0.41 (P 0.697 / R 0.740 / F1 0.718) vs F1 0.716 at 0.4.

### Committee vs September's single Opus 5 judge

On the 598 S1 works in this run. Agreement over (work, goal) pairs; kappa corrects for agreement by chance.

| Comparison | pairs | agreement | kappa | yes-rate (first) | yes-rate (September) |
|---|---|---|---|---|---|
| Committee (resolved pairs) vs September | 10,064 | 98.5% | 0.818 | 4.1% | 4.7% |
| Opus 5.5 alone vs September | 10,064 | 98.5% | 0.811 | 3.8% | 4.7% |
| Sol alone vs September | 10,166 | 97.7% | 0.769 | 5.8% | 4.7% |

Committee yes where September said no: 50; committee no where September said yes: 104.

Models scored under each answer key (same works):

| Answer key | Aurora P / R / F1 | Jev P / R / F1 | Head P / R / F1 |
|---|---|---|---|
| Committee | 0.35 / 0.40 / 0.37 | 0.76 / 0.79 / 0.77 | 0.68 / 0.75 / 0.72 |
| Committee (unresolved as yes) | 0.36 / 0.33 / 0.35 | 0.77 / 0.65 / 0.70 | 0.69 / 0.61 / 0.65 |
| September Opus 5 | 0.42 / 0.41 / 0.42 | 0.85 / 0.77 / 0.81 | 0.78 / 0.75 / 0.77 |

Per goal, yes counts: SDG 1 8/9, SDG 2 26/31, SDG 3 129/154, SDG 4 35/40, SDG 5 13/15, SDG 6 12/11, SDG 7 14/18, SDG 8 27/22, SDG 9 23/30, SDG 10 24/30, SDG 11 22/24, SDG 12 23/25, SDG 13 10/9, SDG 14 6/6, SDG 15 13/15, SDG 16 23/31, SDG 17 8/6 (committee/September).

## Judges

Opus 5.5 and GPT-6.1 Sol each judge every work; Fable 5.1 rules only where they disagree.

| | S2 | S1 |
|---|---|---|
| works judged by both | 1,990 | 592 |
| Opus–Sol pair agreement | 98.9% | 97.8% |
| Cohen's kappa (Opus vs Sol) | 0.767 | 0.756 |
| Opus yes-rate | 2.0% | 3.8% |
| Sol yes-rate | 3.0% | 5.8% |
| committee yes-rate (resolved pairs) | 2.2% | 4.1% |
| works with a disagreement | 322 | 182 |
| disagreeing pairs | 381 | 226 |
| Fable sided with Opus | 298 | 176 |
| Fable sided with Sol | 82 | 50 |
| Fable said yes / no | 85 / 295 | 44 / 182 |
| Opus status | ok 1990, refused 10 | ok 592, refused 6 |
| Sol status | ok 2000 | ok 598 |
| Fable status (works with a disagreement) | ok 321, refused 1 | ok 182 |
| unresolved pairs (works) | 171 (11) | 102 (6) |
| unresolved by cause | fable_refused 1, opus_refused 170 | opus_refused 102 |

**Does the ranking depend on the judge?** Pooled F1 of each model with each judge's labels as the answer key, on the works both judges answered.

| Set | Answer key | Aurora F1 | Jev F1 | Head F1 | ranking |
|---|---|---|---|---|---|
| S2 | Opus 5.5 alone | 0.301 | 0.729 | 0.695 | Jev > Head > Aurora |
| S2 | GPT-6.1 Sol alone | 0.305 | 0.693 | 0.674 | Jev > Head > Aurora |
| S2 | Committee | 0.296 | 0.742 | 0.706 | Jev > Head > Aurora |
| S2 | Committee (unresolved as yes) | 0.296 | 0.743 | 0.705 | Jev > Head > Aurora |
| S1 | Opus 5.5 alone | 0.386 | 0.769 | 0.714 | Jev > Head > Aurora |
| S1 | GPT-6.1 Sol alone | 0.383 | 0.728 | 0.692 | Jev > Head > Aurora |
| S1 | Committee | 0.376 | 0.779 | 0.720 | Jev > Head > Aurora |

Served models (last row per work): fable: claude-fable-5-1 ×504, opus: claude-opus-5-5 ×2598, sol: openai/gpt-6.1-sol ×2598.

