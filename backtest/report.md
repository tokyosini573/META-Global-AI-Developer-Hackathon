# Backtest report

Predictions were committed before the answers were added: `predictions.json` (method v1, cases 1-4) and `predictions_v2.json` (method v2, all cases). Method v2 draws the rule values and a reach factor per run from the frozen ranges; it was chosen after the v1 scores were known, so only cases 5 onward are held out for it (`protocol_v2.md`).

| Case | Marker | Question | Real | world v2 | world v2 generic | world v1 | always_success | bass_only | no_view |
|---|---|---|---|---|---|---|---|---|---|
| case_1 | m1 | Are there more transactions in month 3 than in month 0? | yes | 0.88 | 0.97 | 0.95 | 1.00 | 1.00 | 0.50 |
| case_1 | m2 | Are there more active users at month 9 than at month 3? | yes | 0.88 | 0.80 | 0.90 | 1.00 | 1.00 | 0.50 |
| case_1 | m3 | Are there more active users at month 42 than at month 12? | no | 0.30 | 0.30 | 0.40 | 1.00 | 1.00 | 0.50 |
| case_2 | m1 | Is version b ahead of version a on active users at month 12? | yes | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 | 0.50 |
| case_2 | m2 | Have more people had a success (a match that leads to a conversation) in version b than in version a by month 12? | yes | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 | 0.50 |
| case_2 | m3 | Does version b have more active users at month 12 than at month 0? | yes | 0.78 | 0.90 | 1.00 | 1.00 | 1.00 | 0.50 |
| case_2 | m4 | Is version a ahead of version b on active users at the end of the first month (month 0)? | yes | 0.97 | 1.00 | 1.00 | 0.50 | 0.50 | 0.50 |
| case_3 | m1 | Are there more transactions in month 15 than in month 6? | yes | 0.30 | 0.17 | 0.20 | 1.00 | 1.00 | 0.50 |
| case_3 | m2 | Are there more active users at month 10 than at month 6? | yes | 0.45 | 0.45 | 0.40 | 1.00 | 1.00 | 0.50 |
| case_3 | m3 | Are there more active users at month 42 than at month 15? | no | 0.45 | 0.40 | 0.35 | 1.00 | 1.00 | 0.50 |
| case_4 | m1 | Does version b have more active users at month 17 than version a had at month 11? | yes | 1.00 | 0.93 | 1.00 | 0.50 | 0.50 | 0.50 |
| case_4 | m2 | Does version a have more active users at month 16 than at month 10? | yes | 0.00 | 0.15 | 1.00 | 1.00 | 1.00 | 0.50 |
| case_4 | m3 | Is version a ahead of version b on cumulative contribution margin at month 17? | yes | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 0.50 |
| case_5 | m1 | Are there more transactions in month 3 than in month 0? | yes | 0.95 | 0.75 |  | 1.00 | 1.00 | 0.50 |
| case_5 | m2 | Are there more transactions in month 13 than in month 10? | no | 0.50 | 0.47 |  | 1.00 | 1.00 | 0.50 |
| case_5 | m3 | Are there more transactions in month 21 than in month 13? | yes | 0.20 | 0.12 |  | 1.00 | 1.00 | 0.50 |
| case_5 | m4 | Are there more transactions in month 28 than in month 21? | no | 0.23 | 0.33 |  | 1.00 | 1.00 | 0.50 |
| case_5 | m5 | Are there more transactions in month 36 than in month 28? | no | 0.28 | 0.38 |  | 1.00 | 1.00 | 0.50 |
| case_6 | m1 | Are there more transactions in month 8 than in month 2? | yes | 0.88 | 0.80 |  | 1.00 | 1.00 | 0.50 |
| case_6 | m2 | Are there more active users at month 8 than at month 2? | yes | 0.97 | 0.82 |  | 1.00 | 1.00 | 0.50 |
| case_6 | m3 | Are there more transactions in month 12 than in month 10? | no | 0.20 | 0.20 |  | 1.00 | 1.00 | 0.50 |
| case_6 | m4 | Are there more active users at month 12 than at month 10? | no | 0.30 | 0.23 |  | 1.00 | 1.00 | 0.50 |
| case_6 | m5 | Are there more transactions in month 22 than in month 12? | no | 0.10 | 0.23 |  | 1.00 | 1.00 | 0.50 |
| case_7 | m1 | Are there more transactions in month 12 than in month 3? | yes | 0.23 | 0.35 |  | 1.00 | 1.00 | 0.50 |
| case_7 | m2 | Are there more active users at month 12 than at month 6? | yes | 0.38 | 0.55 |  | 1.00 | 1.00 | 0.50 |
| case_7 | m3 | Are there more active users at month 41 than at month 24? | no | 0.38 | 0.45 |  | 1.00 | 1.00 | 0.50 |
| case_7 | m4 | Are there more active users at month 49 than at month 12? | no | 0.42 | 0.35 |  | 1.00 | 1.00 | 0.50 |
| case_8 | m1 | Are there more active users at month 3 than at month 1? | yes | 1.00 | 1.00 |  | 1.00 | 1.00 | 0.50 |
| case_8 | m2 | Are there more transactions in month 3 than in month 1? | yes | 1.00 | 1.00 |  | 1.00 | 1.00 | 0.50 |
| case_8 | m3 | Are there more active users at month 28 than at month 3? | no | 0.00 | 0.03 |  | 1.00 | 1.00 | 0.50 |
| case_9 | m1 | Are there more transactions in month 15 than in month 3? | yes | 0.85 | 0.78 |  | 1.00 | 1.00 | 0.50 |
| case_9 | m2 | Are there more active users at month 17 than at month 5? | yes | 0.93 | 0.80 |  | 1.00 | 1.00 | 0.50 |
| case_9 | m3 | Are there more transactions in month 33 than in month 15? | yes | 0.60 | 0.47 |  | 1.00 | 1.00 | 0.50 |

## Held out for method v2: cases 5 onward

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world v2 | 16 of 20 | 0.134 |
| world v2 generic | 17 of 20 | 0.141 |
| always_success | 11 of 20 | 0.450 |
| bass_only | 11 of 20 | 0.450 |
| no_view | 0 of 20 | 0.250 |

## Cases Spark did not recognize

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world v2 | 3 of 3 | 0.000 |
| world v2 generic | 3 of 3 | 0.000 |
| always_success | 2 of 3 | 0.333 |
| bass_only | 2 of 3 | 0.333 |
| no_view | 0 of 3 | 0.250 |

## Cases 1-4 (method v1 was scored on these first)

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world v2 | 8 of 13 | 0.321 |
| world v2 generic | 8 of 13 | 0.309 |
| world v1 | 9 of 13 | 0.253 |
| always_success | 6 of 13 | 0.250 |
| bass_only | 6 of 13 | 0.250 |
| no_view | 0 of 13 | 0.250 |

## All cases

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world v2 | 24 of 33 | 0.207 |
| world v2 generic | 25 of 33 | 0.207 |
| world v1 | 9 of 13 | 0.253 |
| always_success | 17 of 33 | 0.371 |
| bass_only | 17 of 33 | 0.371 |
| no_view | 0 of 33 | 0.250 |

Direction counts a probability of exactly 0.5 as wrong: the baselines have no view on variant-vs-variant markers.

## Recognition check

Spark was shown each name-removed description and asked which real company it describes.

| Case | Guess | Confidence | Recognized |
|---|---|---|---|
| case_1 | Sidecar | 0.96 | yes |
| case_2 | Hinge | 0.96 | yes |
| case_3 | Washio | 0.9 | yes |
| case_4 | Mercari | 0.98 | yes |
| case_5 | Juno | 0.9 | yes |
| case_6 | RideAustin | 0.85 | yes |
| case_7 | Shyp | 0.98 | yes |
| case_8 | Mercari | 0.89 | no |
| case_9 | Coconala | 0.96 | yes |

## Anonymization test

The v2 run was repeated with every Spark decision made from a generic description built only from the case's structured fields (the two sides, country, one city or nationwide): no era, no product features, no city names, no history. If the predictions hold, they come from the mechanics and the inputs rather than from what Spark remembers about the company. This is a sensitivity check run after the answers were known; the answers play no part in it.

- Markers compared: 33
- Mean change in probability: 0.07
- Direction flipped: 2 (case_7 m2 0.38 -> 0.55, case_9 m3 0.60 -> 0.47)

Recognition with the generic descriptions:

| Case | Guess | Confidence | Recognized |
|---|---|---|---|
| case_1 | Uber | 0.85 | no |
| case_2 | unknown | 0.9 | no |
| case_3 | Washio | 0.6 | yes |
| case_4 | Mercari | 0.95 | yes |
| case_5 | Uber | 0.95 | no |
| case_6 | Uber | 0.95 | no |
| case_7 | Shyp | 0.9 | yes |
| case_8 | Mercari | 0.95 | no |
| case_9 | Coconala | 0.85 | yes |

Generic run, scored only on the cases Spark could not name from the generic description:

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| world v2 generic | 17 of 20 | 0.183 |
| always_success | 9 of 20 | 0.438 |
| bass_only | 9 of 20 | 0.438 |
| no_view | 0 of 20 | 0.250 |

## Limits

- 33 markers on 9 cases, 20 of them on the 5 cases held out for method v2: still a small sample; read the scores as a check of the method, not a measured accuracy.
- Spark named 8 of the 9 companies from their name-removed descriptions, including less-known ones. With generic descriptions it still named 4 (often the best-known app of the category). The anonymization test suggests memory moves the predictions little (mean change 0.07, 2 of 33 directions flipped), but the unrecognized subset is small.
- Method v2 (rule values drawn from the frozen ranges, market-size term) was chosen after the v1 scores of cases 1-4 were known; cases 1-4 under v2 are not evidence for it.
- The world under-predicts growth in the middle of a company's life: 6 of the 9 v2 misses are growth it did not see (case_3 m1-m2, case_4 m2, case_5 m3, case_7 m1-m2). It did well on the held-out cases partly because 9 of their 20 markers were declines, which it tends to expect.
- Markers are directional only, and several rest on company claims or proxies (downloads or sign-ups for active users, drivers for riders); answers.yaml marks the weak ones.
- The engine has no competitors and no price changes over time: case_6 lost its market when two large rivals returned, case_5 competed with them throughout, and case_8 dropped its fee after about 2.5 months.
- Two decline markers (case_1 m3, case_3 m3) were added before any v1 prediction, because every in-window marker was a growth marker and an always-success baseline would have scored perfectly.
- case_4 m3 is fixed by the inputs (one variant charges a fee, the other is free), so it barely tests the world.
- case_2's variant a (the old app kept as is) never happened; the comparison is a counterfactual.
- Backtest worlds are not calibrated to benchmarks; markers compare a world with itself, not absolute levels.
