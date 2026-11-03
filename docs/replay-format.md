# Replay format (v2)

One JSON file = one finished rehearsal of two plans. The engine writes it; the site only reads it.
Everything on the main screen is computed from this file at a given day `t` (a float, 0–`meta.days`).
Version 2 (2026-11-03 redesign) adds the full funnel (sign-up and quitting with reasons), up to three
ads, the per-step report and the ads table; the v2 fields are listed in "Version 2" below the v1 shape.

```jsonc
{
  "version": 1,
  "meta": {
    "app": "Kindred",            // demo app name (working name)
    "market": "United States",
    "days": 90,
    "budget_usd": 40000,         // same for both plans
    "placeholder": true,         // true = not produced by the real engine
    "people_types": ["Serious seeker", "..."], // optional: the kinds of people Muse Wonder designed
    "runs": 30,                  // optional: Monte Carlo runs behind the verdict
    "people_per_dot": 60,        // real people one simulated person stands for
    // optional: the market pack's own words (engine/packs/<id>.py "labels"). Absent = dating.
    "pack": {
      "id": "resale", "header": "Local resale app", "category": "a new app for buying and selling ...",
      "screens": ["reloop_ad", "reloop_store", "reloop_buy_m0_few", "reloop_list_m0_few"], // input screen
      "stages": ["Installed", "Sold or bought", "Still using", "Repeat"],   // funnel
      "numbers": ["Completed sales", "Sold or bought", "Quit in week one"], // the three numbers
      "legend": ["Traded", "Using", "Quit"], "goal": "completed sales",
      "ask": { "converted": "...", "quit": "...", "using": "..." },        // drawer question suggestions
      "last_screen": "What {they} saw last", "since": "First sale or purchase on day {day}."
    },
    "live": true                 // optional: an admin's live run from uploaded screens (engine/live.py)
  },
  "plans": {
    "a": {
      "name": "Plan A",
      "summary": "Nationwide ads · paywall from day 1",
      "events": [{ "day": 0, "label": "Ads + paywall" }],  // shown on the timeline
      // optional: the plan in plain words for the input screen (engine/world/output.py plan_card)
      "card": { "title": "Nationwide", "where": "Nationwide from day 1", "ads": "TikTok, nationwide",
                "price": "$9.99 a week. Free users get 5 swipes a day." }
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
        "reached": 3.2, "installed": 3.4, "matched": null, "quit": 6.1, "paid": null,
        // optional: what the one-person drawer shows (engine/world/output.py `story`)
        "story": {
          "sex": "w",                    // the person's side: "m" / "w" for dating (he / she), else e.g. "seller"
          "persona": "You are 24 and ...", // the pool person's own description (Glimmer runs), else null
          "ad": "ad",                    // screen seen when reached: web/public/screens/<name>.png,
                                         // or a path starting with "/" (live runs: /api/live/<id>/screen/ad)
          "last": "paywall_m0_none",     // last paywall screen seen, or null
          "diary": [[4, "Saw the ad on TikTok. Installed it.", "Free to try, why not?"],
                    [6, "Nearest person: 41 miles. Deleted the app.", null]]
          // [day shown, what happened, their own words or null]. Words appear only when the
          // person did what the model thought most likely, so the reason always fits the action.
        } }
    ],
    "b": []
  },
  "matches": {
    "a": [[12, 87, 15.5]],       // [person id, person id, day] — drawn as a line once day <= t
    "b": []
  }
}
```

## Version 2

```jsonc
{
  "version": 2,
  "meta": {
    // ...every v1 field, plus:
    "brief": { },                // the brief this run used (docs/brief-format.md); image names resolved
                                 // like story.ad (web/public/screens/<name>.png or /api/live/... paths)
    "note": "Simulated, calibrated to public benchmarks. Not observed.",
    "agents": 10000,             // simulated people reached in each experiment (brief.setup.people)
    "funnel": [                  // the pack's steps, in order; the web counts each one from people at day t
      { "key": "saw", "label": "Saw an ad" },          // reached
      { "key": "installed", "label": "Installed" },
      { "key": "signed_up", "label": "Signed up" },
      { "key": "first", "label": "Got a match" },      // matched (resale: "Sold or bought", rides: "Took or gave a ride")
      { "key": "active", "label": "Using on day 90" }, // signed up and not quit at t
      { "key": "paid", "label": "Paid" }               // dating only; transaction packs have 5 steps
    ],
    "ads": [                     // brief.ads with their screens
      { "id": "ad_1", "angle": "feature", "line": "...", "screen": "ad" }
    ],
    "kinds": [                   // Muse Wonder's kinds of people (people_types stays for older code)
      { "id": "weekend_declutterer", "name": "Weekend declutterer", "share": 0.15, "side": "seller" }
    ]
  },
  "plans": {
    "a": {
      // ...every v1 field, plus:
      "changes": "Nothing: the shared campaign",      // what this experiment changes (brief.setup.experiments)
      "range": { "paid": [31, 47] },                  // optional: 10th-90th percentile across runs, same scale
                                                      // as the counts in this file, for each funnel key
      "report": [                                     // where people left and why (engine/world/report.py)
        { "from": "saw", "to": "installed", "left": 8970,   // reached `from` by the end, never `to`
          "themes": [                                  // up to 3, biggest first; Muse Wonder names them and
            { "name": "Not sure the people are real",  // sorts each reason into one, the engine counts
              "count": 2780, "quote": "Sounds nice but I need proof they're real first.",
              "ids": [12, 87] } ] }                    // the people in this theme (this file's ids)
      ],
      "ads": {                                         // which kinds of people answered which ad
        "line": "The trust ad won over the people who distrust dating apps.",  // one line, Muse Wonder
        "cells": { "<kind id>": { "ad_1": [410, 16], "ad_2": [398, 28] } }    // [saw it, installed]
      }
    }
  },
  "people": {
    "a": [{
      // ...every v1 field, plus:
      "kind": "weekend_declutterer",   // id in meta.kinds
      "ad_id": "ad_2",                 // the ad they saw, or null (reached by a friend, search, ...)
      "signed_up": 3.5,                // day they finished sign-up, or null (quit at sign-up: quit = installed)
      "story": {
        // ...v1 fields; the diary now also has the sign-up step and, when they stop, why:
        "quit_reason": "He never wrote back, and nobody else is close.",  // or null
        "stop": { "to": "first", "words": "Nearest person is 41 miles away." }
          // the first funnel step this person never reached, and the words of the decision that stopped
          // them there (null when they gave none); absent when they reached every step. engine/world/report.py
          // groups these per step: saw→installed = the install answer, installed→signed_up = the sign-up
          // answer, signed_up→first / first→active = why they quit, active→paid = the last paywall answer
      } }]
  }
}
```

A person counts toward a step at day `t` when: `saw` reached ≤ t · `installed` installed ≤ t ·
`signed_up` signed_up ≤ t · `first` matched ≤ t · `active` signed_up ≤ t and not quit by t ·
`paid` paid ≤ t. Report counts (`left`, theme `count`) are people in this file, so they add up with the
funnel at the last day. When a person quits is still set by the calibrated retention curve (or a
"delete" decision); `quit_reason` is that person's own words for it.

`web/public/replays/fixture_v2.json` is a placeholder v2 file made from `engine.json` by
`scripts/fixture_v2.py` (every v2 number in it is made up) so the screens can be built before the
engine writes v2.

## State of a person at day `t`

| Condition | State | Drawn as |
|---|---|---|
| `reached` is null or `reached > t` | not reached | not drawn |
| reached, `installed` null or `> t` | never installed | gray dot |
| `paid <= t` | paying | bright dot + ring |
| `quit <= t` | quit | plan color, 25% |
| otherwise | using | plan color, 85% |

A payer never quits in dating. In the other markets `paid` is the day of the first completed
transaction (`matched` is the same day), and the person can still quit after it.

## Numbers on the main screen (computed, never stored)

Each number is the winner against the other plan, in the winner's color.

- **Paying users** (dating) or **completed sales / rides** (`matches` with day `<= t`): percent difference, or "only B" when the other plan has none.
- **Got a match** (or the pack's word): share of installers with `matched <= t`, difference in percentage points (reads even when one plan has none).
- **Quit in week one**: share of installers who quit within 7 days of installing, percent difference.

Funnel stages at `t`: installed → got a match → still using (installed and not quit) → paying (dating) or traded and still using (other markets), on one scale for both plans. "Reached" is left out: only ~9% of people reached by an ad install, which would squeeze the rest into a hairline.

## Live replays

`GET /api/live/<id>/replay` (with the `X-Admin-Key` header) returns a replay in this same format, with
`meta.live: true`, screens as `/api/live/<id>/screen/<name>` paths, and `meta.pack.screens` pointing at
the uploads. The site opens it with `?replay=live_<id>`; the interview finds its people with the replay
name `live_<id>`.
