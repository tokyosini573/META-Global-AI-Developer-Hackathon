# Rehearsal

Launch world model for the Meta Global AI Developer Hackathon (Indie track, due 2026-11-05 11:00 JST).
It rehearses two launch plans (A vs B) for one app in a simulated US market over 90 days and says which wins and why.
Planning docs live one folder up (`../00_대회정보.md` … `../06_영상스토리보드.md`); approved mockups live in `../시안/`.

## v2 (2026-11-03)

The binding scope is `../10_재설계문서_1103.md` (Korean, local): the full funnel (saw an ad → installed →
signed up → first core action → still using → paid) with each person's own reasons per step, app info
separated from the experiment setup (A/B), up to three ads compared per kind of person. Build nothing it
lists under "빼기" (X1–X9): no market outside the US, no one-sided apps, no platform/language/URL inputs,
no user-entered CPI/CPM/CTR, no expected-retention input, no third experiment. Interfaces:
`docs/brief-format.md` (input), `docs/replay-format.md` "Version 2" (output), `web/src/brief.ts`,
`web/src/replay.ts`. Approved screen mockup: `../시안/02_재설계_미리보기.html`.

## Hard constraints

- Build only these screens: the front page, the Setup page (`?new`, read-only example or the admin's live run with `?new&admin`), then on the stage the main screen, the report (`?report`), the ads table (`?ads`), the one-person drawer and the backtest (the 3-minute video, `../06_영상스토리보드.md`). Scope since 2026-11-03: two-sided apps in three market packs (dating, resale, rides), channels grouped by how people meet the app, and admin-only live runs from uploaded screens (they cost money); the public site plays precomputed replays. Since 2026-11-10 the site scales to zero, and the run button shows a contact address to anyone without the admin key. Nothing else (no settings, login, run list, stats tables).
- Never use code, data or design from any existing company's product. The demo apps (Kindred, Reloop, Hopway) are new and must not resemble existing apps.
- Only fictional data goes to the Spark contributor model (Meta may train on it). Uploaded screens and visitor questions go to Spark standard.
- After any engine change, `python -m engine.run` must reproduce the committed `web/public/replays/engine.json` exactly (the Wonder verdict and report caches hit only on identical facts).
- MiroFish (AGPL-3.0) is design inspiration only. Never copy its code.
- Every dataset and asset must have a license that allows this use.
- Everything in this repo is English: screen copy, code comments, docs, commit messages, PR titles/bodies/comments and the README (global competition). The one exception is `docs/handbook.ko.md`, the Korean twin of `docs/handbook.md` (keep the two in step). The planning docs one folder up are Korean.

## Design rules (light theme since 2026-11-03; `../05_디자인원칙.md` has the Korean version)

1. The bare address opens the front page (`web/src/components/Landing.tsx`): what Rehearsal is, how to use it, what you get, why trust it, which Meta models, in that order, each in plain words. It ends with "Start a rehearsal", which offers two options: watch a precomputed example (`?new&replay=<name>`) or the admin's live run (`?new&admin`). A new visitor must never land on a screen they cannot read.
2. The Setup page scrolls like the front page. Every other view is the 1920×1080 stage behind a URL parameter. One stage screen answers one question. Main: "Which experiment wins, and why?" (verdict on top, at most 3 numbers, maps in the middle, the funnel below; a dot opens the drawer). Report: "Where did people leave, and why?". Ads: "Which people answered which ad?". Every number carries the note that it is simulated, calibrated to public benchmarks, not observed.
3. Use only the tokens below. UI parts are plain Tailwind on these tokens; do not invent ad-hoc colors or sizes.
4. Plain words on screen. No internal terms (`archetype`, `agent_state`, `cohort`, …).
5. Check every milestone with screenshots (`scripts/shot.sh` for the stage; a tall headless Chrome window for the front page) against the checklist below, and list what to remove before adding anything.
6. Reference sites may guide structure or color direction only. Never copy another product's design or copy, and never name a reference site in the repo.

### Tokens (`web/src/index.css`)

| Token | Value | Use |
|---|---|---|
| `bg` | `#FFFFFF` | page |
| `surface` | `#F4F7FB` | bands, drawer, cards on the stage |
| `line` | `#E1E7EF` | 1px rules, borders |
| `dot-idle` | `#D5DDE7` | halftone map dots |
| `dim` | `#5B6B7A` | labels, secondary text |
| `text` | `#1C2B39` | body |
| `strong` | `#0B1A2C` | headlines, key numbers |
| `blue-50` / `100` / `200` | `#EEF4FF` / `#DCE7FF` / `#BCD1FF` | tints, chips, hover |
| `blue-600` | `#1B5BF5` | buttons and links (the one action color) |
| `blue-900` | `#0B2A5B` | the closing call-to-action band, drawer overlay |
| `plan-a` | `#E08A00` | everything Plan A |
| `plan-b` | `#1B5BF5` | everything Plan B |

- On the stage, the only accents are plan-a and plan-b, plus blue-600 for a primary button. The numbers take the winner's color. The backtest stays black and white.
- Type: Geist 600 88px headline (-3% tracking) · Geist 600 48px section title · Geist 500 56px numbers (tabular) · Geist 400 22px lead · Geist 400 20px body · Geist Mono 500 15px uppercase labels (+6% tracking), for short labels only. Below 40px, use only these sizes.
- Spacing in multiples of 4 (mostly 8/16/24/48/96). Stage gutter 64px; front page content up to 1200px wide. Radius 12px on drawer, cards, buttons.
- No shadows, no emoji, at most 3 icons per screen, no box inside a box, no gradient on buttons/cards/text. One soft background glow is allowed on the stage.
- Motion: dots fade in over ~0.3 s, 90 days = 30 s on the stage (14 s in the front page preview), numbers count up over 0.4 s, drawer slides in over 0.25 s.

### Screenshot checklist

- Front page: could a first-time visitor say what Rehearsal does after the first screen?
- Setup: are only the required sections open, and is every input a number, choice or range where it can be?
- Stage: does the top line alone say who won and why?
- 3 numbers or fewer on the main screen (axis ticks and dates excluded)?
- Only the tokens above?
- No internal terms on screen?
- No box inside a box?
- Each stage screen visible at 1920×1080 without scrolling?
- Anything that does not serve the visitor or the video? Remove it.

## Layout

```
engine/    Python world engine. interview.py + serve.py = the live interview API; site_modal.py = the public site on Modal.
           world/ = geo, decide (decision cache + providers), wonder (people design, verdict), glimmer (per-person pool + table),
           spark (per-type table), typed (Wonder's kinds of people + Spark per kind, any pack), channels, calibrate,
           sim, output, screens, report (Wonder groups each step's reasons, the engine counts); run.py = CLI.
           live.py = the admin's live run from a brief (Wonder -> Spark standard -> rehearse -> report).
           fake_replay.py writes the old hand-made placeholder replay.
           packs/ = dating, resale, rides: what differs per market (sides, mechanics, gate screen, words).
plans/     Launch plans + market values per demo app (kindred, reloop, hopway), <app>.brief.yaml = the app's brief;
           channels.yaml = channel costs;
           benchmarks_research.md = sources (PRIOR = no public number). Each value cites a rule id or a benchmark.
rules/     Frozen rule cards (commit eef683f). Changing them must be recorded in the README.
backtest/  Held-out backtest cases, predictions, answers and report (protocol_v2.md); rule-set case facts.
engine/distill/  Spark -> Glimmer distillation: data, format, Modal training/eval/serving, score (docs/distillation.md).
runs/      SQLite output per run (ignored by git).
web/       Vite + React + TypeScript + Tailwind v4. main.tsx: bare address -> Landing, ?new -> Setup, any other parameter -> App (stage).
web/public/replays/   Replay JSON files the site plays (committed, so the demo survives without API credit).
docs/replay-format.md The contract between engine and screen. docs/brief-format.md What a founder puts in.
scripts/   shot.sh: 1920×1080 screenshots with headless Chrome.
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m engine.run --runs 30    # Glimmer table; calibrate + Monte Carlo -> web/public/replays/engine.json, runs/engine.sqlite
.venv/bin/python -m engine.run --plans plans/reloop.yaml --name reloop   # resale (hopway.yaml: rides); ?replay=reloop
.venv/bin/python -m engine.world.typed plans/reloop.yaml   # Wonder's kinds + Spark contributor table (incremental, ~$0.4)
.venv/bin/python -m engine.world.screens resale rides      # render a pack's demo screens (needs Google Chrome)
.venv/bin/python -m engine.world.wonder people     # Wonder designs the people -> data/wonder/kindred_people.json
.venv/bin/python -m engine.world.glimmer prepare   # new pool/screens: then glimmer_modal.py::decide_table, then `collect`, `check`
.venv/bin/python -m pytest -q tests
.venv/bin/python -m engine.backtest.run predict v2 && .venv/bin/python -m engine.backtest.run score
.venv/bin/python -m engine.backtest.run export   # -> web/public/backtest.json (plain words in backtest/display.yaml)
.venv/bin/python -m engine.distill.make_data --n 4000 && .venv/bin/python -m engine.distill.format --upload
.venv/bin/modal run --detach engine/distill/glimmer_modal.py::train --run r1   # then ::evaluate, ::merge, ::evaluate_vllm
.venv/bin/python -m engine.distill.publish adapter && .venv/bin/modal run engine/distill/publish_modal.py   # weights -> Hugging Face (HF_TOKEN in .env and Modal secret huggingface)
python3 engine/fake_replay.py          # regenerate web/public/replays/demo.json
.venv/bin/python -m engine.serve        # live interview API on :8787 (Voice Transcribe + Spark); Vite proxies /api
cd web && npm run dev                   # http://localhost:5173
cd web && npm run build                 # type-check + build
.venv/bin/modal deploy engine/site_modal.py   # public site + API (after the build; key in Modal secret rehearsal-meta)
scripts/shot.sh "http://localhost:5173/?day=90&still" out.png   # ?day=N freezes on a day, ?replay=engine plays the engine output (any parameter opens the stage; ?play plays the default)
scripts/shot.sh "http://localhost:5173/?day=90&still&person=a:87" out.png   # ?person=<plan>:<id> opens one person's drawer; &ask asks them live
scripts/shot.sh "http://localhost:5173/?backtest&still&point=case_5:m2" out.png   # ?backtest opens the backtest screen; &point shows one card
scripts/shot.sh "http://localhost:5173/?replay=engine&report&day=90&still" out.png   # the report; &ads the ads table; &plan=a picks the tab
# the Setup page scrolls: shoot it with a tall headless Chrome window (?new&replay=engine, or ?new&admin for the live run)
API_PORT=8788 .venv/bin/python -m engine.serve   # another port; start Vite with the same API_PORT
```

The stage is a fixed 1920×1080 canvas scaled to fit the window, so the site looks exactly like the video at any size.
