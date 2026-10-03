# OpenAlex SDGs

How [OpenAlex](https://openalex.org) decides which of the UN's 17
[Sustainable Development Goals](https://sdgs.un.org/goals) a work addresses. Since October 2026 (TODO: the date the API
first serves it) every work's [`sustainable_development_goals`](https://help.openalex.org/data/sdgs/) field comes
from a classifier OpenAlex trained and tested itself. It replaced the Aurora SDG-BERT model from the Aurora
Universities Network, which OpenAlex had served for years. This is **version 1.0.0** (see the [changelog](CHANGELOG.md)).

> **Everything is here:** the model weights, the training labels, every test set, every judge verdict and the code,
> so you can check our numbers or build something better.

## Benchmarks

**On 2,000 works drawn at random from OpenAlex, the new SDG tags are right 68% of the time and find 72% of the goals
the works address. The old tags were right 29% of the time and found 31%.**

<img src="docs/img/f1-by-goal.svg" alt="F1 by goal on 2,000 random OpenAlex works, old classifier then new: all 17 goals 29% and 70%; No poverty 24% and 73%; Zero hunger 25% and 71%; Good health 44% and 84%; Quality education 41% and 81%; Gender equality 29% and 50%; Clean water 31% and 78%; Clean energy 9% and 76%; Decent work 27% and 59%; Industry and innovation 14% and 47%; Reduced inequalities 12% and 45%; Sustainable cities 32% and 59%; Responsible consumption 15% and 46%; Climate action 20% and 60%; Life below water 26% and 44%; Life on land 31% and 61%; Peace and justice 28% and 52%; Partnerships 17% and 20%." width="760">

| 2,000 random works, judged by a committee of AI models | New classifier | Old classifier (Aurora SDG-BERT) |
|---|---|---|
| F1 | **0.70** | 0.29 |
| Precision (share of tags that are right) | **0.68** | 0.29 |
| Recall (share of the right goals found) | **0.72** | 0.31 |
| Goals where the new classifier scores higher F1 | **17 of 17** | |

**The answer key is a committee.** Claude Opus 5.5 and GPT-6.1 Sol, from two labs, each read every work and decided
all 17 goals against the UN's own goal and target text ([rubric](harness/rubric.py)). Where they disagreed, Claude
Fable 5.1 decided. The two judges agreed on 98.9% of decisions, and the ranking is the same under either judge alone.
The sample includes works with only a title (37%) and works in other languages (31%). Precision and recall by goal:
[precision](docs/img/precision-by-goal.svg), [recall](docs/img/recall-by-goal.svg). Details, intervals and every
slice: [benchmarks/](benchmarks/README.md).

**It also wins where researchers, not models, wrote the labels.** In the Aurora survey, 244 researchers voted on
whether papers contribute to a goal. On the 8,767 paper-and-goal questions with a clear majority, the new classifier
scores F1 75.5 and the old one 63.6 (AUC 0.748 and 0.607). These papers came from the Aurora project's own search
queries, so this is the old model's home ground.

## How it works

**A large language model labels a sample; a small, fast classifier learns from it and tags every work.**

1. **Label.** [Jev](https://typesafe.ai), a decision model from TypeSafe AI, read the titles and abstracts of 200,000
   works and gave a probability for each of the 17 goals. The exact requests are in
   [classifier/jev_request.py](classifier/jev_request.py); the labels are in [training/data/](training/README.md).
2. **Embed.** OpenAlex already stores a vector for every work with a title:
   [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) over its title, abstract and venue
   ([classifier/embed.py](classifier/embed.py)).
3. **Learn.** For each goal, a logistic regression on the vector learns Jev's confident answers, and an isotonic fit
   turns its output into a score from 0 to 1 ([training/train.py](training/train.py)). The whole model is 17 rows of
   1,024 weights: [models/sdg_jev_head_v2.json](models/README.md).
4. **Tag.** A goal is tagged when its score is 0.4 or above. Every new work is tagged the night its vector is made
   ([production/](production/README.md)).

**What counts.** A work counts for a goal when its main subject addresses one of the goal's UN targets, not when it
only touches the theme. A paper on atomic energy levels is not SDG 7, and a species occurrence record is not SDG 15.
Two goals got a sentence saying so after the tests found the classifier reading them too broadly: SDG 9 ("a new
device, material or method is not by itself SDG 9") and SDG 15 (records and bare species descriptions are not by
themselves SDG 15). The SDG 15 fix was [pre-registered](harness/PREREGISTRATION.md) and lifted its precision from
0.23 to 0.71.

**What `score` means.** It is the classifier's confidence, not a probability. On the 2,000 works, tags scored 0.4 to
0.5 were right 34% of the time, 0.5 to 0.8 between 45% and 57%, 0.8 to 0.9 71%, and above 0.9 86%
([calibration table](benchmarks/README.md#what-score-means)).

## Known issues

- **Some goals are weaker.** F1 is 0.81 or more for health and education, but under 0.50 for SDG 9, 10, 12, 14 and
  17. SDG 17 (partnerships) has 8 committee yeses in 2,000 works, too few to tune on.
- **Titles alone.** About 2 in 3 of the tags on works without an abstract are right (precision 0.65 on 740 such
  works).
- **It learned from Jev, and trails it.** Asking Jev directly scores F1 0.74 on the same works; the classifier keeps
  most of that at a tiny fraction of the compute, and loses it mostly on precision.
- **Counts changed at the switch.** Per-goal totals moved a lot, health up and energy down most: on the September
  sample, Aurora tagged energy three times as often as the judge and health half as often. Say which classifier your
  numbers came from when you compare across October 2026.

## Use it

Filter or group any search by goal in the [API](https://api.openalex.org/works?filter=sustainable_development_goals.id:13)
or on [openalex.org](https://openalex.org/works?filter=sustainable_development_goals.id:13):

```
https://api.openalex.org/works?filter=sustainable_development_goals.id:7,publication_year:2025
https://api.openalex.org/works?filter=publication_year:2025&group_by=sustainable_development_goals.id
```

## Reproduce it

```
python3 benchmarks/score_public.py              # the public benchmarks (standard library, 1 s)
python3 benchmarks/score_committee.py           # the committee eval, every table (numpy, 10 s)
python3 -m classifier.head --check              # the shipped scores, recomputed from the shipped vectors and weights
```

[REPRODUCE.md](REPRODUCE.md) rebuilds the texts from the OpenAlex API, re-runs the judges and Jev, re-embeds, and
retrains the classifier.

## License and credits

Code: [MIT](LICENSE). Data and model weights: CC0, like everything in OpenAlex. Labels by Jev (TypeSafe AI); judging by
Claude Opus 5.5 and Claude Fable 5.1 (Anthropic) and GPT-6.1 Sol (OpenAI); work vectors from Qwen3-Embedding-0.6B
(Alibaba Qwen, Apache 2.0). The Aurora survey data (Vanderfeesten, Spielberg and Gunes, Zenodo 3813230) and OSDG-CD
(OSDG, UNDP IICPSD SDG AI Lab and PPMI, Zenodo 6831287) are used under CC BY 4.0. The old classifier is the Aurora
Universities Network's SDG-BERT ([Zenodo 7304547](https://zenodo.org/records/7304547)).
