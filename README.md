<img src="web/public/landing/dolphin/smile.webp" alt="" width="72">

# Rehearsal

### Rehearse your app's launch before you spend the budget.

**[Open the live demo →](https://tokyosini573--rehearsal.modal.run)** · Built solo for the Meta Global AI Developer Hackathon with
**Muse Wonder, Muse Spark, Muse Glimmer and Muse Voice Transcribe**

| | |
|---|---|
| **Live demo** | [tokyosini573--rehearsal.modal.run](https://tokyosini573--rehearsal.modal.run): three worked examples. The site starts when you arrive, so the first load can take a few seconds. |
| **Handbook** | [A plain-words guide](docs/handbook.md) to what it does and how, with diagrams · [한국어](docs/handbook.ko.md) |
| **Fine-tuned model** | [Rehearsal-Glimmer-30B-r1](https://huggingface.co/Yesini/Rehearsal-Glimmer-30B-r1) on Hugging Face: Muse Glimmer 30B taught to decide like Muse Spark (Apache 2.0) |

![Rehearsal playing two launch plans for a dating app over 90 days: Plan A nationwide, Plan B in three cities. Plan B wins.](docs/images/replay.gif)

## The problem: you only launch once

A new app spends its launch budget first and learns whether the plan worked months later.
For apps that need two kinds of people near each other (daters, buyers and sellers, riders and
drivers) it is worse: the app is empty until both sides meet, so **where and how you launch decides
whether it lives**.

| Same app, same $40,000 | Plan A | Plan B |
|---|---|---|
| **Reloop**, a resale app | Nationwide ads, everyone at once: **0 sales** | Seattle then Portland, sellers first: **1,837 sales** |
| **Kindred**, a dating app | Nationwide ads, paywall on day one: **6 matches** | City by city, 30 days free: **166 matches** |

<sub>Rehearsal's own examples (Reloop: median of 30 runs; Kindred: the replay on the site). Simulated, calibrated to public benchmarks, not observed.</sub>

Get it wrong and you lose the budget, the months, and your first impression in the market. And
nothing tells you beforehand: a real test costs the launch itself, and surveys miss the map,
because people can like an app and still leave when nobody is nearby.

## What Rehearsal does

**It runs your launch in a simulated US market first.** Describe your app and two launch plans.
Thousands of simulated Americans live through 90 days of each: they see your ad, install, sign up,
use the app, pay or leave, and **each one says why, in their own words**. You see which plan wins,
where people left, which ad worked on whom, and you can ask any one person why.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#EEF4FF', 'primaryBorderColor': '#1B5BF5', 'primaryTextColor': '#0B1A2C', 'lineColor': '#1B5BF5'}}}%%
flowchart LR
    A["<b>1 · Describe</b><br/>your app, its ads<br/>and two plans"] --> B["<b>2 · Simulate</b><br/>thousands of people<br/>decide and say why"] --> C["<b>3 · Read</b><br/>who wins, where<br/>people left, and why"]
```

- **Muse Wonder** looks at your screens and designs the market's kinds of people: age, job, town, mood.
- **Muse Spark** decides for each of them at every step, looking at your real screens, and says why.
  **Muse Glimmer**, an open-weight model distilled from Spark, does it for every single person in the dating example.
- **A world engine** moves them day by day on a US map, calibrated to public industry benchmarks.
  Each plan runs 30 times.

## Why you can trust it

- **It was tested on real launches before it saw the answers.** The rules were frozen and the
  predictions committed to git before the real outcomes were added; the commit order is the
  evidence. On 5 real launches it had never seen, it called **16 of 20 turning points**, against 11
  for a model that always says "it grows".
- **No number comes from a language model.** The models decide and explain; the engine counts.
- **Every reason has a person behind it.** Open any dot on the map and read that person's whole
  story.
- **The limits are written down.** It is a simulation, US only, for two-sided apps. See
  [Honest limits](#honest-limits).

<details>
<summary><b>The full funnel each person goes through</b></summary>

<br>

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#EEF4FF', 'primaryBorderColor': '#1B5BF5', 'primaryTextColor': '#0B1A2C', 'lineColor': '#5B6B7A'}}}%%
flowchart LR
    s1[Saw an ad] --> s2[Installed] --> s3[Signed up] --> s4["First match<br/>(sale, ride)"] --> s5[Still using<br/>on day 90] --> s6[Paid]
    s1 -.->|"Too few swipes, costs too much"| x1((left))
    s3 -.->|"Everyone shown is 40 miles away"| x3((left))
```

At every arrow, the people who stop say why in one sentence. Muse Wonder groups the sentences
into themes; the engine counts the people.

</details>

## What you get

### 1. Which experiment wins, and why

![Main screen: "Plan B wins." Two US maps, Plan A nationwide in amber and Plan B in three cities in blue, with the funnel below](docs/images/main.png)

The verdict comes first, in one plain sentence. Below it, both experiments play out on two US maps
over 90 days, with the funnel under each. In the Kindred example, nationwide ads (A) reach more
people, but they are too spread out to match anyone. Launching city by city with a free month (B)
wins 25 of 30 runs.

### 2. Where people left, and why

![Report screen: for each funnel step, how many people left and up to three reasons in their own words](docs/images/report.png)

For each step of the funnel: how many people stopped there, and the top reasons in their own
words. *"Ten bucks a week is way too much for me."* *"Five free swipes isn't worth all my
location and photos."*

### 3. Which ad worked on whom

![Ads screen: three ads (feature, price, trust) against eight kinds of people, showing the share of each who installed](docs/images/ads.png)

Up to three ads, compared across every kind of person. In the Kindred example the price ad worked
best on curious and busy people, the trust ad on careful ones, and the feature ad on casual ones.

### 4. Any one person, and ask them

<table>
<tr>
<td width="42%"><img src="docs/images/person.png" alt="One person's drawer: Avery, 24, Austin. The ad she saw, the paywall where she paid, and what she did each day"></td>
<td>

Click any dot on the map to open that person: who they are, the ad they saw, the screen where
they paid or left, and what they did each day.

Then **ask them a question, by voice or by text.** Muse Voice Transcribe turns your question into
text, and Muse Spark answers as that person, using only their own record from the simulation.

> **Avery, 24, Austin.** Saw the trust ad on day 1: *"I have no time to scroll forever for far
> matches."* Got a first match on day 15, hit the paywall when the free month ended, and started
> paying on day 66.

</td>
</tr>
</table>

### And the input: the Setup page

![Setup page: "Let's rehearse your app." with the app profile filled in for the Kindred example](docs/images/setup.png)

Seven short sections about the app (profile, audience, product, money, ads, competition,
retention) and an eighth for the two experiments. Most inputs are choices or numbers. The public
site shows each example read-only. A live run with your own screens calls the models and costs money,
so it is open on request: the run button shows how to reach me.

## Three markets, three answers

Each example is a made-up app with its own screens, people and two launch plans. The winner is
not always the same kind of plan.

| Market | Demo app | Experiment A | Experiment B | Result |
|---|---|---|---|---|
| Dating | **Kindred** | Nationwide TikTok ads, paywall from day 1 | Austin, then Denver and Nashville, campus ambassadors, 30 days free | **B** wins 25 of 30 runs |
| Resale | **Reloop** | Nationwide feed ads, everyone at once | Seattle then Portland, sellers first | **B** wins 30 of 30 runs: 1,837 sales against 0 |
| Rides | **Hopway** | Three cities at once, riders and drivers together | Austin then Denver, drivers first | **B** wins 22 of 30 runs: 387 rides against 321 |

Try each one: [Kindred](https://tokyosini573--rehearsal.modal.run/?replay=engine) ·
[Reloop](https://tokyosini573--rehearsal.modal.run/?replay=reloop) ·
[Hopway](https://tokyosini573--rehearsal.modal.run/?replay=hopway)

## Built on Meta's models

| Model | What it does in Rehearsal |
|---|---|
| **Muse Wonder** | Looks at the app's screens and both plans and designs the market's kinds of people. Names the themes in people's reasons, and writes the one-sentence verdict. |
| **Muse Spark** | Decides for each kind of person at every step, looking at the actual screen image, and says why. Answers live interview questions in character. |
| **Muse Glimmer** | Fine-tuned (QLoRA) to answer like Spark for each individual person in the dating demo: same top choice as Spark 85% of the time (Spark agrees with itself 86%), at 0.064 s instead of about 20 s per decision. [Weights are public](https://huggingface.co/Yesini/Rehearsal-Glimmer-30B-r1) (Apache 2.0). |
| **Muse Voice Transcribe** | Turns a spoken question to a simulated person into text. |

## Does it predict anything real?

![Backtest screen: "Would it have called it?" Nine real launches on a timeline, with called and missed turning points](docs/images/backtest.png)

A world model is only worth trusting if it can predict outcomes it has not seen. The same engine
was run on **9 real launches of two-sided apps**, with their names hidden, and asked yes/no
questions about their growth ("More trips in month 13 than in month 10?").

- **The order of the commits is the evidence.** On 2026-10-29 the rules were frozen first
  (`eef683f`), then the held-out cases were added as inputs only (`83412f9`), then the predictions
  were committed (`49122a3`), and only then the real outcomes (`fd71369`).
- **On the held-out cases it called 16 of 20 turning points**, against 11 of 20 for a model that
  always says "it grows" (Brier score 0.134 against 0.450).
- **It is not just memory.** Spark recognized most companies, so the backtest was rerun with
  plain descriptions. The predictions moved by 0.07 on average and 2 of 33 flipped.

Full report: [`backtest/report.md`](backtest/report.md).

## Honest limits

Every number on screen is a simulation, calibrated to public benchmarks; none is observed data.

- **Small check.** 20 held-out questions on 5 apps is a check of the method, not a measured accuracy.
- **Simulated people.** The people are Muse Wonder's judgment of each US market, not census data,
  and they carry the models' biases.
- **Missing forces.** The engine has no competitors and no price changes over time.
- **US and two-sided only.** The map, ad costs and backtest rules are for two-sided apps in the US.

The full list is in [`docs/method.md`](docs/method.md#limits).

## What I built

- **A world engine** in Python that moves thousands of simulated people over a US map day by day,
  with three market packs and five kinds of ad channels, each cost tied to a cited benchmark.
- **A fine-tuned open-weight model.** I downloaded Muse Glimmer 30B, built 4,000 training examples
  from Muse Spark's answers, trained a QLoRA adapter on one Modal H100 in 56 minutes, and published
  the result on [Hugging Face](https://huggingface.co/Yesini/Rehearsal-Glimmer-30B-r1). It matches
  Spark's top choice 85% of the time at about 300 times the speed. It learned one fictional dating
  app, so its value is the method: take an open model and tune it for one narrow job.
- **A backtest with evidence of order:** rules, cases, predictions and answers committed in that order.
- **A deployed site:** React on the front, one FastAPI container on Modal that starts on demand,
  no database, every example precomputed so visiting costs nothing.

## Under the hood

The whole method (the pipeline, the matching and churn math, calibration, the market packs, the
Spark-to-Glimmer distillation, the backtest and privacy) is in **[`docs/method.md`](docs/method.md)**.
Other docs:

- [`docs/brief-format.md`](docs/brief-format.md): what a founder puts in.
- [`docs/replay-format.md`](docs/replay-format.md): what the engine puts out and the site plays.
- [`docs/distillation.md`](docs/distillation.md): distilling Spark into Glimmer, with all tables.

**Privacy.** Every simulated person is fictional, and only fictional data was sent to the Spark
contributor model. Uploaded screens and visitor questions go to Spark standard, which is not used
for training. No code, data or design from any existing company's product is used.

## Run it yourself

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m engine.run --runs 30      # rehearse both plans -> web/public/replays/engine.json
.venv/bin/python -m pytest -q tests
cd web && npm install && npm run dev         # http://localhost:5173
```

A run needs no API key and no GPU, because the models' decisions are committed.

```bash
.venv/bin/python -m engine.run --plans plans/reloop.yaml --name reloop   # resale -> ?replay=reloop
.venv/bin/python -m engine.run --plans plans/hopway.yaml --name hopway   # rides  -> ?replay=hopway
```

The live interview, live runs and the steps that call the models need a Meta Model API key in
`.env` (see `.env.example`):

```bash
.venv/bin/python -m engine.serve              # interview and live-run API on :8787; the dev server proxies /api to it
.venv/bin/modal deploy engine/site_modal.py   # the public site (key in the Modal secret rehearsal-meta)
```

<details>
<summary><b>Every page of the site</b></summary>

<br>

| Open | What you see |
|---|---|
| [`/`](https://tokyosini573--rehearsal.modal.run) | The front page, ending with "Start a rehearsal". |
| [`/?new&replay=engine`](https://tokyosini573--rehearsal.modal.run/?new&replay=engine) | The Setup page, read-only for an example. Switch markets at the top. |
| [`/?new&admin`](https://tokyosini573--rehearsal.modal.run/?new&admin) | The admin's live run: upload your own screens and ads, run with Muse Wonder and Muse Spark. |
| [`/?play`](https://tokyosini573--rehearsal.modal.run/?play) | The main screen: both experiments on two US maps. |
| [`/?replay=engine&report`](https://tokyosini573--rehearsal.modal.run/?replay=engine&report) | Where people left, and why. |
| [`/?replay=engine&ads`](https://tokyosini573--rehearsal.modal.run/?replay=engine&ads) | Which kinds of people answered which ad. |
| [`/?day=90&person=b:42`](https://tokyosini573--rehearsal.modal.run/?day=90&person=b:42) | One person's drawer; ask them a question. |
| [`/?backtest`](https://tokyosini573--rehearsal.modal.run/?backtest) | The backtest on 9 real launches. |

</details>

<details>
<summary><b>Repository layout</b></summary>

<br>

```
engine/world/     the world: people (Wonder), decisions (Glimmer, Spark), channels, simulation, calibration, report, replay
engine/packs/     market packs: dating, resale, rides
engine/live.py    the admin's live run from a brief and its images
engine/distill/   Spark -> Glimmer: data, QLoRA training, evaluation, vLLM serving on Modal
engine/backtest/  backtest runner and scoring
engine/screens/   the demo apps' screens (HTML rendered to images the models look at)
engine/interview.py, serve.py, site_modal.py   live interview API and the public site
plans/            each market's two launch plans, its brief (<app>.brief.yaml), channel costs, benchmark research
rules/            frozen two-sided launch rules and their evidence
backtest/         cases (inputs), predictions, answers, report
data/             Wonder's people, the models' decisions, distillation results
web/              the site (Vite, React, Tailwind); replays in web/public/replays
docs/             method, brief format, replay format, distillation
```

</details>

## Credits and licenses

- **Map:** `us-atlas` (ISC), from US Census Bureau boundaries. **Fonts:** Geist and Geist Mono (SIL OFL).
- **The dolphin** was made by the author with an AI image tool for this project.
- **Demo apps:** Kindred, Reloop and Hopway are made up for this demo; their screens are in
  `engine/screens/`.
- **MiroFish** (AGPL-3.0) was design inspiration only, and none of its code is used.
