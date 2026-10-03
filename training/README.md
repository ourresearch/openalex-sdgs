# Training

**The head learned from 200,000 of Jev's answers.** `data/labels.jsonl.gz` holds them, one row per work:

| Field | What |
|---|---|
| `work_id` | The OpenAlex work id |
| `stratum` | Which part of the sample the work came from (`data/sample_strata.json`) |
| `sdg` | Jev's probability for each goal, first pass, September 2026 (`TRAINING_NOULS_FIRST_PASS` in `classifier/jev_request.py`) |
| `sdg9_v2` | SDG 9 relabelled under the reworded instruction (66,548 works whose first answer was 0.2 or more) |
| `sdg15_v2` | SDG 15 relabelled under the instruction head v2 was trained on (`rec_tax`; 13,085 works) |
| `sdg15_rec` | SDG 15 under the other candidate wording (`rec`), for the pre-registered comparison |

**The sample is not random, on purpose.** It was drawn in September 2026 for two classifiers at once (this one and
OpenAlex's study-design tagger): 121,000 works in strata by abstract, year, script or language and work type, 25,000
biomedical works without a PubMed id, and 54,000 PubMed works, most drawn by publication type. Every stratum and its size is in
`data/sample_strata.json`. The SDG questions were asked in the same Jev request as the study-design questions, with
their own rule in the state.

`data/splits.json.gz` names the 20,000 works held out for calibration (`cal`) and the 20,000 held out to check the head
against Jev (`eval`); the other 160,000 train.

**Retrain.** `train.py` needs the works' vectors, which are not shipped (200,000 × 1,024 floats). Rebuild them from
the API and the open embedding model, then train:

```bash
python -m classifier.fetch_works --ids training/data/labels.jsonl.gz --out train_works.jsonl
python -m classifier.embed --input train_works.jsonl --out train_vectors.npz
python training/train.py --vectors train_vectors.npz --version v2 --out my_head.json --compare models/sdg_jev_head_v2.json
```

Texts change upstream and the local embedding may differ slightly from OpenAlex's hosted one, so a retrained head will
be close to the shipped one, not identical. TODO: run this end to end once and record how close.

**Relabel.** `python -m classifier.jev --input train_works.jsonl --out sdg15.jsonl --goals 15` asks Jev the SDG 15
question alone, in the training request shape, with the current wording.
