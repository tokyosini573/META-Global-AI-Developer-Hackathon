# Backtest report

Predictions were written to `predictions.json` before `answers.yaml` was read.

| Case | Marker | Question | Real | World | Always success | Bass only |
|---|---|---|---|---|---|---|
| case_1 | m1 | Are there more transactions in month 3 than in month 0? | yes | 0.95 | 1.00 | 1.00 |
| case_1 | m2 | Are there more active users at month 9 than at month 3? | yes | 0.90 | 1.00 | 1.00 |
| case_1 | m3 | Are there more active users at month 42 than at month 12? | no | 0.40 | 1.00 | 1.00 |
| case_2 | m1 | Is version b ahead of version a on active users at month 12? | yes | 0.00 | 0.50 | 0.50 |
| case_2 | m2 | Have more people had a success (a match that leads to a conversation) in version b than in version a by month 12? | yes | 0.00 | 0.50 | 0.50 |
| case_2 | m3 | Does version b have more active users at month 12 than at month 0? | yes | 1.00 | 1.00 | 1.00 |
| case_2 | m4 | Is version a ahead of version b on active users at the end of the first month (month 0)? | yes | 1.00 | 0.50 | 0.50 |
| case_3 | m1 | Are there more transactions in month 15 than in month 6? | yes | 0.20 | 1.00 | 1.00 |
| case_3 | m2 | Are there more active users at month 10 than at month 6? | yes | 0.40 | 1.00 | 1.00 |
| case_3 | m3 | Are there more active users at month 42 than at month 15? | no | 0.35 | 1.00 | 1.00 |
| case_4 | m1 | Does version b have more active users at month 17 than version a had at month 11? | yes | 1.00 | 0.50 | 0.50 |
| case_4 | m2 | Does version a have more active users at month 16 than at month 10? | yes | 1.00 | 1.00 | 1.00 |
| case_4 | m3 | Is version a ahead of version b on cumulative contribution margin at month 17? | yes | 1.00 | 0.50 | 0.50 |

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world | 9 of 13 | 0.253 |
| always_success | 6 of 13 | 0.250 |
| bass_only | 6 of 13 | 0.250 |

Direction counts a probability of exactly 0.5 as wrong: the baselines have no view on variant-vs-variant markers.

## Recognition check

Spark was shown each name-removed description and asked which real company it describes.

| Case | Guess | Confidence | Recognized |
|---|---|---|---|
| case_1 | Sidecar | 0.96 | yes |
| case_2 | Hinge | 0.96 | yes |
| case_3 | Washio | 0.9 | yes |
| case_4 | Mercari | 0.98 | yes |

## Limits

- 13 markers on 4 cases: far too few to claim accuracy; read this as a smoke test of the method.
- Spark recognized every case from its description, so its decisions may lean on what it remembers.
- Markers are directional only, and several rest on company claims or proxies (downloads for active users).
- Two decline markers (case_1 m3, case_3 m3) were added before any prediction, because every in-window marker was a growth marker and an always-success baseline would have scored perfectly.
- case_4 m3 is fixed by the inputs (one variant charges a fee, the other is free), so it barely tests the world.
- case_2's variant a (the old app kept as is) never happened; the comparison is a counterfactual.
- Backtest worlds are not calibrated to benchmarks; markers compare a world with itself, not absolute levels.
