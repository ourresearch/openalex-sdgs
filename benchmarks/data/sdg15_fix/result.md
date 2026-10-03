# SDG 15 fix: the four candidates (2026-10-01 15:36 CT)

Committee labels (unresolved as no), threshold 0.4. S2 halves by work_id % 2: choose n=998 (15 yes), confirm n=1002 (13 yes). Survey: 572 SDG 15 surveyed pairs with a clear majority (408 yes).

| candidate | choose P / R / F1 (tags) | confirm P / R / F1 (tags) | S2 P / R / F1 | S2 AUC | S2 tag share | S1 F1 | survey AUC | survey F1 |
|---|---|---|---|---|---|---|---|---|
| v1 | 0.24 / 0.60 / 0.35 (37) | 0.22 / 0.61 / 0.32 (37) | 0.23 / 0.61 / 0.33 (74) | 0.951 | 0.037 | 0.64 | 0.73 | 0.74 |
| rec/drop | 0.64 / 0.60 / 0.62 (14) | 0.75 / 0.46 / 0.57 (8) | 0.68 / 0.54 / 0.60 (22) | 0.965 | 0.011 | 0.55 | 0.766 | 0.73 |
| rec/keep | 0.56 / 0.60 / 0.58 (16) | 0.73 / 0.61 / 0.67 (11) | 0.63 / 0.61 / 0.62 (27) | 0.949 | 0.013 | 0.57 | 0.768 | 0.77 |
| rec_tax/drop **chosen** | 0.69 / 0.60 / 0.64 (13) | 0.75 / 0.46 / 0.57 (8) | 0.71 / 0.54 / 0.61 (21) | 0.934 | 0.011 | 0.57 | 0.756 | 0.73 |
| rec_tax/keep | 0.64 / 0.60 / 0.62 (14) | 0.88 / 0.54 / 0.67 (8) | 0.73 / 0.57 / 0.64 (22) | 0.948 | 0.011 | 0.57 | 0.767 | 0.75 |

Chosen on the choose half: **rec_tax/drop**. Confirm rule (F1 > v1's 0.32 and P >= 0.50 on the confirm half): **PASS** (0.57, P 0.75).
