# Models

**The whole classifier is one 0.2 MB JSON file.** `sdg_jev_head_v2.json` is what OpenAlex runs on every work; `v1`
is kept because the committee eval's go rule was pre-registered on it. They differ only in goal 15. `MANIFEST.json`
holds their sha256, which match the files OpenAlex's pipeline loads.

| Field | What |
|---|---|
| `model_version` | `sdg-jev-head-v2` (stored with every scored work) |
| `input_dim` | 1024: the work's Qwen3-Embedding-0.6B vector, a unit vector (`classifier/embed.py`) |
| `W`, `b` | 17 rows of 1,024 weights and 17 biases, goal 1 first |
| `goals[j]` | `n`, `id` (the UN's URI, as served), `display_name`, `threshold` (0.4), `iso_x` / `iso_y` (the isotonic calibration's breakpoints) |
| `teacher`, `input`, `score`, `threshold_policy`, `sdg15` | Notes written at training time; internal names in them refer to OpenAlex's pipeline |

To score a vector `x` for goal `j`:

```python
raw = 1 / (1 + exp(-(W[j] @ x + b[j])))
score = clip(interp(raw, goals[j]["iso_x"], goals[j]["iso_y"]), 0, 1)
tagged = score >= goals[j]["threshold"]
```

`classifier/head.py` does this for many works at once and returns the list OpenAlex serves (tagged goals, highest
score first). `goals.json` lists the 17 goals with their served names and thresholds.
