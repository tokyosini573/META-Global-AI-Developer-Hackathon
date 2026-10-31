# Rehearsal

**Rehearse a launch before you spend the budget.** Rehearsal is a launch world model: give it two
launch plans for one app, and it plays both out in a simulated US market for 90 days, says which
plan wins, and lets you ask any simulated person why they did what they did.

**Live demo: https://tokyosini573--rehearsal.modal.run**

Built solo for the Meta Global AI Developer Hackathon (Indie track) with Muse Wonder, Muse Spark,
Muse Glimmer and Muse Voice Transcribe.

| Open | What you see |
|---|---|
| [`/`](https://tokyosini573--rehearsal.modal.run) | The two plans play out on two US maps, one dot per 60 people. The verdict is on top. |
| [`/?day=90&person=a:87`](https://tokyosini573--rehearsal.modal.run/?day=90&person=a:87) | One person's drawer: who they are, the ad and paywall they saw, what they did each day. Ask them a question by voice or text. |
| [`/?new`](https://tokyosini573--rehearsal.modal.run/?new) | "Try it yourself": the input screen, filled with the example plans. |
| [`/?backtest`](https://tokyosini573--rehearsal.modal.run/?backtest) | The backtest: the same world predicting what happened to 9 real two-sided apps. |

## The example

Kindred is a new dating app made up for this demo (its ad, store page and paywall are in
`engine/screens/`). Both plans spend $40,000 over 90 days and charge $9.99 a week for unlimited
swipes; free users get 5 swipes a day.

- **Plan A:** TikTok ads nationwide, paywall from day 1.
- **Plan B:** Austin, then Denver on day 30, then Nashville on day 60, with campus ambassadors and
  local TikTok ads. Each person's first 30 days are free.

**Plan B wins in 25 of 30 runs.** Median paying users after 90 days: 450 for B against 240 for A.
Plan A reaches more people (59,000 against 39,000) and gets more installs (5,400 against 3,300),
but its users are spread over the whole country. In 20 of 30 runs no Plan A user gets a single
match, and 91% of its users quit in the first week, against 41% for Plan B. A dating app is worth nothing until
there is someone nearby to match with, and Plan B packs its users close enough together to find
each other.

## How it works

```
Kindred's screens + both plans
        │
        ▼
Muse Wonder ─── designs the market's people: 8 types with shares, ages and life details
        │
        ▼
Fixed pool of 2,928 fictional people (48 per place, 600 per launch city)
        │
        ▼
Muse Glimmer (distilled from Spark) ─── every person's own decision on every screen:
        │                               3 ads + 18 paywall states each, 61,488 answers
        ▼
World engine ─── day by day: reach, install, match nearby, paywall, quit
        │        calibrated to industry rates, 30 Monte Carlo runs per plan
        ▼
Verdict ─── winner by paying users; Muse Wonder writes why, from what people said
        │
        ▼
Live interview ─── Muse Voice Transcribe + Muse Spark answer as one person, from their record
```

| Step | Model or method | Code |
|---|---|---|
| Design the people | Muse Wonder reads Kindred's ad, store page, paywall and both plans, and returns 8 person types (for example "Serious seeker", "Tired of swiping", "Casual and bored") with shares, age ranges and detail sentences about work, money, dating history, mood and habits. | `engine/world/wonder.py` |
| Build the pool | 2,928 fictional people drawn from that design. Each has a name, an age, a job, a place and a story. | `engine/world/glimmer.py` |
| Decide | Muse Glimmer, fine-tuned to answer like Muse Spark, looks at the actual screen image and the person's story and gives probabilities for each option ("install" or "scroll past"; "pay", "come back tomorrow" or "delete the app"). All answers are computed once on Modal and committed, so a run needs no GPU. | `engine/distill/`, `data/decisions/kindred_glimmer.json` |
| Simulate | Paid reach, word of mouth, matching by distance, paywall, churn. Rules come from a frozen rule set (below). | `engine/world/sim.py` |
| Calibrate | Model probabilities set who acts; industry rates set how many. | `engine/world/calibrate.py` |
| Repeat | 30 runs per plan with different random draws; the verdict counts wins. | `engine/run.py` |
| Explain | Muse Wonder writes the reason under the verdict, from the medians and people's own words, with no numbers. The engine adds the win count. | `engine/world/wonder.py` |
| Interview | Muse Voice Transcribe turns a spoken question into text. Muse Spark answers in character, using only that person's record from the replay. | `engine/interview.py` |

### The math

All of it is in `engine/world/sim.py` and `engine/world/calibrate.py`, with the rules in
`rules/two_sided.md`.

- **Matching needs people nearby.** For person *i*, the number of active people on the other side
  within reach is a distance-weighted count, `n_i = Σ_j exp(−d_ij / λ)`, with λ = 5 km. Each dot
  stands for 60 real people, so the count is taken over where those people live: the whole
  country for a nationwide ad, one city for a city launch.
- **Daily match chance.** `P_i = 1 − (1 − q)^min(swipes, n_i)`, with q = 0.012 per swipe. Free
  users have 5 swipes a day; paying users and users in a free trial have 60.
- **Churn.** The base daily quit risk falls with days since install,
  `h(t) = floor + (first_day − floor) · exp(−t / τ)`, fitted to US dating retention on day 1,
  day 7 and day 30. In logit space, the risk rises by `log(1 + γ)` for anyone with no match after 7
  days, and falls by β = 0.8 for each match in the last 30 days.
- **Word of mouth.** People with a match in the last 30 days invite friends nearby, at a daily
  rate taken from the frozen growth-rate band.
- **Reach.** Daily paid reach is `spend / CPM · 1,000 · CTR` for TikTok and `spend / cost per
  contact` for ambassadors. A city plan splits its spend across the cities open that day. Arrivals
  are drawn from a Poisson distribution.
- **Calibration.** Each decision's probability is shifted in logit space, `p′ = σ(logit(p) + b)`,
  with **one** shift *b* per decision, fitted on Plan A and applied unchanged to Plan B. The levels
  come from benchmarks: store page to install 8.6%, day-7 retention 9.6%, paying within 30 days
  4.6%. The model's differences between people and between plans survive calibration. After
  fitting, Plan A shows 8.7%, 9.0% and 5.0%.
- **Monte Carlo.** 30 independent runs per plan. The verdict is the share of runs a plan wins on
  paying users at day 90.

## Distilling Spark into Glimmer

Muse Spark makes these decisions well, but it takes about 20 seconds a call and is capped at 150
calls a minute, which is too slow for thousands of different people. So Glimmer (open weights, 30B)
was fine-tuned to give Spark's answer for each person.

- **Data:** 4,000 fictional people, each looking at the real Kindred screens. Spark answered each
  once, at a cost of $1.82.
- **Training:** QLoRA on one H100 (LoRA r = 16 on attention, vision tower frozen), 56 minutes.
- **Result on 408 held-out people:** Glimmer gives the same top choice as Spark 85% of the time,
  against 74% before training and 86% for Spark asked a second time. It agrees with Spark about as
  often as Spark agrees with itself.
- **On Wonder's people:** Spark re-answered 300 random decisions from the pool, and Glimmer agreed
  90% of the time.
- **Speed and cost:** served with vLLM from the merged weights, a decision takes 0.064 s against
  about 20 s for Spark, at about a sixth of the cost.

Full method and tables: [`docs/distillation.md`](docs/distillation.md).
The tuned weights will be published on Hugging Face (link to follow).

## Does it predict anything real? The backtest

A world model is only worth trusting if it can predict outcomes it has not seen. The same engine
was run on 9 real two-sided apps (ride-hailing, dating, laundry pickup, shipping, resale marketplaces, freelance skills),
described without their names, and asked yes/no questions about their growth. For example: "More
trips in month 13 than in month 10?"

**The order of commits is the evidence** (all on 2026-10-29, JST):

| Time | Commit | What |
|---|---|---|
| 19:31 | `eef683f` | The launch rules are frozen, from 8 other apps only, before any backtest. |
| 23:07 | `83412f9` | Held-out cases 5–9 are added, inputs only. |
| 23:15 | `49122a3` | The world's predictions are committed. |
| 23:17 | `fd71369` | The real outcomes are added and scored. |

**Results on the held-out cases (20 questions on 5 apps):**

| Model | Direction right | Brier score (lower is better) |
|---|---|---|
| **Rehearsal's world** | **16 of 20** | **0.134** |
| "Always grows" | 11 of 20 | 0.450 |
| Bass diffusion only | 11 of 20 | 0.450 |
| No view (0.5 for everything) | 0 of 20 | 0.250 |

- **Does Spark just remember the companies?** Spark named 8 of the 9 companies from their
  name-removed descriptions. So the whole backtest was run again with generic descriptions (two
  sides, country, one city or nationwide; no era, features or city names). The predictions moved
  by 0.07 on average and 2 of 33 flipped direction. On the cases Spark could not name from the
  generic description, the world still got 17 of 20 right.
- **The method changed once, in the open.** Method v2 was chosen after v1 had been scored on
  cases 1–4. That is why only cases 5–9 count as held out
  ([`backtest/protocol_v2.md`](backtest/protocol_v2.md)).

Full report, every question and every probability: [`backtest/report.md`](backtest/report.md).

## Limits

- **Small validation sample.** 20 held-out questions on 5 apps is a check of the method, not a
  measured accuracy. Questions are directional only.
- **Growth in mid-life.** The world under-predicts growth in the middle of a company's life: 6 of
  its 9 backtest misses are growth it did not see.
- **Missing market forces.** The engine has no competitors and no price changes over time.
- **The people are not census data.** They are Muse Wonder's judgment of the US dating market.
  Metro sizes are rough weights.
- **Biases carry over.** Glimmer reproduces Spark's answers, including Spark's biases. It was
  validated against Spark, not against real users.
- **Noisy calibration.** The 7-day and 30-day measures rest on a few dots per run, so they bounce
  between rounds. The engine averages the second half of 20 rounds.
- **Repeated stories.** Outside the three launch cities, the pool has 48 people per place, so a
  nationwide plan repeats some of them.
- **"Try it yourself" replays an example.** The input screen replays the progress of the example
  plans. A new plan needs a new Glimmer table, which runs offline (about an hour on one GPU).
- **Day wording in interviews.** The paywall prompts in the first week describe the install as a
  few days ago, so a person may say "three days" about day 1.

## Privacy and data

- **Fictional people only.** Every simulated person is fictional. Only fictional data was sent to
  the Spark contributor model, because Meta may use its inputs for training.
- **Visitor questions.** In the live interview, visitor questions go to Spark standard, which is
  not used for training.
- **Rate limits.** The public API allows 30 questions per visitor per hour and 2,000 a day in
  total.
- **Sources.** Benchmarks are cited in `plans/kindred.yaml`, and rule evidence in
  `rules/two_sided.md`. Backtest facts come from public reporting (`backtest/answers.yaml`).
- **No product data.** No code, data or design from any existing company's product is used.
  MiroFish (AGPL-3.0) was design inspiration only, and none of its code is used.
- **Licenses.** The map uses `us-atlas` (ISC, from US Census Bureau boundaries) and the fonts are
  Geist and Geist Mono (SIL OFL).

### Changes to the frozen rules

`rules/two_sided.md` was frozen in Korean in `eef683f` and translated to English in
[#1](https://github.com/tokyosini573/META-Global-AI-Developer-Hackathon/pull/1). Only the
language changed: no rule, number or range was altered. Two non-rule fixes were made at the same
time. A colon that broke YAML parsing became a dash, and a sample count in a note was corrected
from 6 to 5 to match the case table. Method v2 of the backtest added the market-size term that
the frozen Bass rule already contains; `backtest/protocol_v2.md` records when and why.

## Run it yourself

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m engine.run --runs 30      # rehearse both plans -> web/public/replays/engine.json
.venv/bin/python -m pytest -q tests
cd web && npm install && npm run dev         # http://localhost:5173
```

A run needs no API key and no GPU, because Glimmer's decisions are committed. The live interview
and the steps that call the models need a Meta Model API key in `.env` (see `.env.example`):

```bash
.venv/bin/python -m engine.serve              # interview API on :8787; the dev server proxies /api to it
.venv/bin/python -m engine.backtest.run predict v2 && .venv/bin/python -m engine.backtest.run score
.venv/bin/modal deploy engine/site_modal.py   # the public site (key in the Modal secret rehearsal-meta)
```

The distillation steps (data, training, the decision table) are listed in
[`docs/distillation.md`](docs/distillation.md) and [`CLAUDE.md`](CLAUDE.md).

## Repository

```
engine/world/     the world: people (Wonder), decisions (Glimmer, Spark), simulation, calibration, replay
engine/distill/   Spark -> Glimmer: data, QLoRA training, evaluation, vLLM serving on Modal
engine/backtest/  backtest runner and scoring
engine/screens/   Kindred's ad, store page and paywall (HTML rendered to images the models look at)
engine/interview.py, serve.py, site_modal.py   live interview API and the public site
plans/            the two launch plans and the market values, each with its source
rules/            frozen two-sided launch rules and their evidence
backtest/         cases (inputs), predictions, answers, report
data/             Wonder's people, Glimmer's decisions, distillation results
web/              the site (Vite, React, Tailwind); replays in web/public/replays
docs/             distillation, replay format
```

## Cost

Everything was built for about $3 of Meta Model API credit and about $15 of Modal GPU time.
That covers Spark's training data, Glimmer's training and evaluation, the precomputed decision table
and the backtests.
