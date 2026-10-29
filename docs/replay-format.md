# Replay format (v1)

One JSON file = one finished rehearsal of two plans. The engine writes it; the site only reads it.
Everything on the main screen is computed from this file at a given day `t` (a float, 0–`meta.days`).

```jsonc
{
  "version": 1,
  "meta": {
    "app": "Kindred",            // demo app name (working name)
    "market": "United States",
    "days": 90,
    "budget_usd": 40000,         // same for both plans
    "placeholder": true          // true = not produced by the real engine
  },
  "plans": {
    "a": {
      "name": "Plan A",
      "summary": "Nationwide ads · paywall from day 1",
      "events": [{ "day": 0, "label": "Ads + paywall" }]   // shown on the timeline
    },
    "b": { "...": "same shape" }
  },
  "verdict": {                   // written after the run (Muse Wonder); shown when t reaches the end
    "winner": "b",
    "headline": "Plan B wins.",
    "reason": "In Austin, new users find a match before they give up. ..."
  },
  "people": {
    "a": [
      // one simulated person. Every day field is the day it happened, or null if it never did.
      { "id": 0, "name": "Maya", "age": 24, "place": "Columbus, Ohio",
        "lon": -83.0, "lat": 40.0,
        "reached": 3.2, "installed": 3.4, "matched": null, "quit": 6.1, "paid": null }
    ],
    "b": []
  },
  "matches": {
    "a": [[12, 87, 15.5]],       // [person id, person id, day] — drawn as a line once day <= t
    "b": []
  }
}
```

## State of a person at day `t`

| Condition | State | Drawn as |
|---|---|---|
| `reached` is null or `reached > t` | not reached | not drawn |
| reached, `installed` null or `> t` | never installed | gray dot |
| `paid <= t` | paying | bright dot + ring |
| `quit <= t` | quit | plan color, 25% |
| otherwise | using | plan color, 85% |

A payer never quits in v1.

## Numbers on the main screen (computed, never stored)

- **Paying users**: `paid <= t` count, B vs A as a percent difference.
- **Got a match**: share of installers with `matched <= t`, B minus A in percentage points (reads even when A has none).
- **Quit in week one**: share of installers who quit within 7 days of installing, B vs A as a percent difference.

Funnel stages at `t`: installed → got a match → still using (installed and not quit) → paying, on one scale for both plans. "Reached" is left out: only ~9% of people reached by an ad install, which would squeeze the rest into a hairline.
