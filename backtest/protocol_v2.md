# Backtest protocol v2

Written 2026-10-29, after the v1 scores of cases 1-4 were known and before any case 5+ answer
entered the repo.

## What v1 showed

- Direction right on 9 of 13 markers against 6 of 13 for both baselines, but the Brier score
  (0.253) was no better than the baselines (0.250).
- Most of the Brier loss came from probabilities of exactly 0.00 or 1.00 that were wrong
  (case_2 m1, m2). With fixed rule values, 20 Monte Carlo runs only vary random arrivals, so the
  world is far more certain than its rules are.
- Spark named all four companies from their name-removed descriptions.
- 13 markers are too few to say anything about accuracy.

## What changes in v2

1. **Rule uncertainty.** Each Monte Carlo run draws its own values from the frozen ranges in
   `rules/two_sided.md` instead of the single points used in v1:

   | Value | Rule card | Range | Draw |
   |---|---|---|---|
   | `lambda_km` | local_density_threshold | 1-10 | log-uniform |
   | `q` | exposure_throughput (curated) | 0.03-0.06 | uniform |
   | `q_dating` | exposure_throughput (swipe) | 0.010-0.014 | uniform |
   | `cap` | exposure_throughput (E_cap_swipe) | 20-200 | log-uniform |
   | `wom_q_daily` | wom_growth_rate_band | 0.008-0.026 | uniform |

   Both variants of a case share the same draw in a run, so variant comparisons stay paired.
2. **Input uncertainty.** `reach_per_month` is a guess in every case. Each run multiplies it by
   one shared factor drawn log-uniform from 0.5-2.
3. **40 runs** per case instead of 20.
4. **More, less-known cases.** Cases 5 onward were researched by a separate agent with the brief
   to prefer companies a well-read model should not name, to pick markers from available public
   data before any prediction, and to include decline markers. Their answers stayed outside the
   repo until `predictions_v2.json` was committed.

Nothing else changes: the rule cards, the decision prompts, the person types and the world
mechanics are the same as in v1.

## How it is scored

- The v1 predictions of cases 1-4 are kept as recorded (`predictions.json`).
- Method v2 is run on all cases (`predictions_v2.json`). Because v2 was chosen after seeing
  the v1 scores, **only cases 5 onward count as held out for v2**. Cases 1-4 under v2 are shown
  but not used as evidence for v2.
- Reported separately: cases 5+, cases Spark did not recognize, cases 1-4, and all cases.
- Recognition is checked after predictions with `engine.backtest.recognize`. No case is dropped
  because Spark recognized it; recognized cases are only reported apart.
- Baselines are unchanged: "always success" and "Bass only".
