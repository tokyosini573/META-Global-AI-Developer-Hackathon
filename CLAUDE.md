# Rehearsal

Launch world model for the Meta Global AI Developer Hackathon (Indie track, due 2026-11-05 11:00 JST).
It rehearses two launch plans (A vs B) for one app in a simulated US market over 90 days and says which wins and why.
Planning docs live one folder up (`../00_대회정보.md` … `../06_영상스토리보드.md`); approved mockups live in `../시안/`.

## Hard constraints

- Build only what the 3-minute video needs (`../06_영상스토리보드.md`): main screen, one-person drawer, input screen, backtest screen. Nothing else (no settings, login, run list, stats tables).
- Never use code, data or design from any existing company's product. The demo dating app is new and must not resemble an existing app.
- MiroFish (AGPL-3.0) is design inspiration only. Never copy its code.
- Every dataset and asset must have a license that allows this use.
- Everything in this repo is English: screen copy, code comments, docs, commit messages, PR titles/bodies/comments and the README (global competition). Only the planning docs one folder up are Korean.

## Design rules (from `../05_디자인원칙.md`; the mockups in `../시안/` are the source of truth)

1. One screen answers one question. Main screen: "Which plan wins, and why?" One headline, one big visual, at most 3 numbers. Everything else goes behind "details".
2. One screen, no tabs. Maps in the middle, funnel below, verdict on top. Clicking a dot opens a drawer from the right.
3. Opening the site plays the precomputed replay immediately. No form first. "Try it yourself" starts filled with the example.
4. Use only the tokens below. UI parts come from shadcn/ui + Tailwind; do not invent ad-hoc components.
5. Plain words on screen. No internal terms (`archetype`, `agent_state`, `cohort`, …).
6. Check every milestone with a 1920×1080 screenshot (`scripts/shot.sh`) against the checklist below, and list what to remove before adding anything.

### Tokens

| Token | Value | Use |
|---|---|---|
| `bg` | `#0A0B0D` | page |
| `surface` | `#121418` | drawer, cards |
| `line` | `#23262D` | 1px rules, grid |
| `dot-idle` | `#2E323A` | halftone map dots |
| `text-dim` | `#6B7280` | labels |
| `text` | `#E8EAED` | body |
| `text-strong` | `#FFFFFF` | headlines, key numbers |
| `plan-a` | `#F2A93B` | everything Plan A |
| `plan-b` | `#4F7CFF` | everything Plan B |

- Only two accents, and they always mean Plan A / Plan B. Screens without plans (backtest) stay black and white.
- Type: Geist 600 88px headline (-3% tracking) · Geist 500 56px numbers (tabular) · Geist 400 18px body · Geist Mono 500 13px uppercase labels (+8% tracking). No sizes between 24 and 40px, except inside depicted app/ad screenshots.
- Spacing in multiples of 4 (mostly 8/16/24/48/96). Page gutter 64px. Radius 12px only on drawer, cards, buttons.
- No shadows, no emoji, at most 3 icons per screen, no box inside a box, no gradient on buttons/cards/text. One soft background glow is allowed.
- Motion: dots fade in over ~0.3 s, 90 days = 30 s, numbers count up over 0.4 s, drawer slides in over 0.25 s.

### Screenshot checklist

- Does the top line alone say who won and why?
- 3 numbers or fewer (axis ticks and dates excluded)?
- Only plan-a and plan-b as accents?
- No text sized 24–40px?
- No internal terms on screen?
- No box inside a box?
- Everything visible at 1920×1080 without scrolling?
- Anything not in the storyboard? Remove it.

## Layout

```
engine/    Python world engine. world/ = geo, decide (decision cache + providers), glimmer (per-person pool + table),
           spark (per-type table), calibrate, sim, output; run.py = CLI.
           fake_replay.py writes the old hand-made placeholder replay.
plans/     Launch plans + market values (each value cites a rule id in rules/two_sided.md or a benchmark).
rules/     Frozen rule cards (commit eef683f). Changing them must be recorded in the README.
backtest/  Held-out backtest cases, predictions, answers and report (protocol_v2.md); rule-set case facts.
engine/distill/  Spark -> Glimmer distillation: data, format, Modal training/eval/serving, score (docs/distillation.md).
runs/      SQLite output per run (ignored by git).
web/       Vite + React + TypeScript + Tailwind v4. Renders a replay.
web/public/replays/   Replay JSON files the site plays (committed, so the demo survives without API credit).
docs/replay-format.md The contract between engine and screen.
scripts/   shot.sh: 1920×1080 screenshots with headless Chrome.
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m engine.run --runs 30    # Glimmer table; calibrate + Monte Carlo -> web/public/replays/engine.json, runs/engine.sqlite
.venv/bin/python -m engine.world.glimmer prepare   # new pool/screens: then glimmer_modal.py::decide_table, then `collect`
.venv/bin/python -m pytest -q tests
.venv/bin/python -m engine.backtest.run predict v2 && .venv/bin/python -m engine.backtest.run score
.venv/bin/python -m engine.distill.make_data --n 4000 && .venv/bin/python -m engine.distill.format --upload
.venv/bin/modal run --detach engine/distill/glimmer_modal.py::train --run r1   # then ::evaluate, ::merge, ::evaluate_vllm
python3 engine/fake_replay.py          # regenerate web/public/replays/demo.json
cd web && npm run dev                   # http://localhost:5173
cd web && npm run build                 # type-check + build
scripts/shot.sh "http://localhost:5173/?day=90&still" out.png   # ?day=N freezes on a day, ?replay=engine plays the engine output
scripts/shot.sh "http://localhost:5173/?day=90&still&person=b:46" out.png   # ?person=<plan>:<id> opens one person's drawer
```

The stage is a fixed 1920×1080 canvas scaled to fit the window, so the site looks exactly like the video at any size.
