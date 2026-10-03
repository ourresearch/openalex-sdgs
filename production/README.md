# Production

The two Databricks notebooks that put the classifier into OpenAlex, copied from OpenAlex's data pipeline as of the
switch (two edits: a phrase about running costs and a support-ticket number removed from comments). They need OpenAlex's tables and will not run elsewhere; they are here
so you can see exactly what runs.

- `sdg_jev_head_score.py` scores every work's vector with `models/sdg_jev_head_v2.json` and writes the 17 scores and the
  served list per work. `full` mode scored all 474,877,445 works with a vector before the switch; `incremental` mode
  runs every night after new works are embedded, so a new work gets its goals the same night. The nightly build copies
  the list into each work's `sustainable_development_goals`. A work with no vector, or no goal at 0.4 or above, gets
  an empty list.
- `freeze_aurora_sdgs.py` made a one-time copy of Aurora's last tags (192,888,578 works). It fills the deprecated
  `sustainable_development_goals_aurora` field, which will be removed in November 2026 (TODO: exact removal date).

`classifier/head.py` is the same arithmetic without Spark.
