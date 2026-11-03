# Brief format (v2)

A brief is everything a founder tells Rehearsal about one app: what it is (sections 01–07) and what
to try this time (section 08, the experiment setup). The Setup page (`web/src/components/Setup.tsx`)
fills it, the admin's live run posts it (`POST /api/live`), and `engine/live.py build_cfg` turns it
into a plan file the engine runs. The demo apps keep theirs in `plans/<app>.brief.yaml`; there the
experiment setup comes from `plans/<app>.yaml` (`plans.a`, `plans.b`), so section 08 holds only
`people`, `days` and each experiment's `changes`.

Every replay carries its brief in `meta.brief` (docs/replay-format.md), so the Setup page can show
a finished example read-only.

Fields marked `?` are optional. Text fields are short plain English; the engine trims them to the
length given.

```jsonc
{
  "version": 2,
  "app": "Kindred",                       // 24 characters, letters, digits, spaces
  "category": "dating",                   // "dating" | "resale" | "rides" (engine/packs)
  "market": "United States",              // fixed: the only market with map, census and ad-cost data

  // 01 App profile
  "profile": {
    "does": "…",                          // what it does, 300 characters
    "why": "…",                           // why people would pick it over what they use now, 200
    "features?": ["…"]                    // up to 5, 40 characters each
  },

  // 02 Target audience
  "audience": {
    "age": [18, 34],                      // inside the pack's limits (dating 18–34, others 18–64)
    "who": "…",                           // who it is for, 200 characters
    "income?": "under_30k",               // "under_30k" | "30_60k" | "60_100k" | "over_100k" | "mixed"
    "lifestyle?": "…",                    // work and lifestyle, 120
    "interests?": "…",                    // 120
    "new_apps?": "early"                  // "early" | "friends" (waits for friends) | "rarely"
  },

  // 03 Product experience (the images are uploaded separately, see "Images")
  "product": {
    "signup_methods": ["phone", "apple"], // any of "email" "phone" "apple" "google" "facebook"
    "permissions?": ["location"],         // any of "location" "camera" "photos" "contacts" "notifications"
    "free_limits?": "5 swipes a day"      // 80 characters
  },

  // 04 Monetization
  "money": {
    "model": "subscription",              // "subscription" | "service_fee" | "per_ride_fee" | "one_time"
    "price": 9.99,                        // dollars, or a fraction for "percent" (0.10 = 10%)
    "per": "week",                        // "week" | "month" | "transaction" | "percent"
    "trial_days?": 0,
    "paywall": "after_free_limit",        // "after_signup" | "after_free_limit" | "after_trial" | "at_checkout"
    "free?": "…", "paid?": "…"            // what is free, what is paid, 120 each
  },

  // 05 Marketing campaign: the ads (1 to 3). Each person reached by an ad-led channel sees one.
  "ads": [
    { "id": "ad_1", "angle": "feature", "line": "Your perfect match, right away" }
                                          // angle: "feature" | "price" | "trust" | "other"; line: 80
  ],

  // 06 Competition (optional)
  "competition?": { "now": "…", "switch": "…" },   // what people use now; why they would switch. 200 each

  // 07 Retention (optional). Never an expected usage frequency: when people quit comes from public
  // retention curves and their own decisions; this text is only the context they decide in.
  "retention?": { "back": "…", "leave": "…" },     // what brings people back; what could make them leave

  // Fixed extra values per category (engine/packs); absent = the pack's default
  "extra?": {
    "women_share?": 0.3, "free_likes_per_day?": 5,  // dating
    "fee_share?": 0.10, "seller_share?": 0.42,      // resale
    "fare_usd?": 14, "driver_share?": 0.3           // rides
  },

  // 08 Experiment setup
  "setup": {
    "people": 10000,                      // 1000 | 5000 | 10000 simulated people reached in each experiment
    "days": 90,                           // 7 | 14 | 30 | 90
    "campaign": {                         // shared by both experiments (live runs only)
      "budget_usd": 40000,
      "channels": [{ "kind": "feed", "where": "nationwide", "budget_share": 0.8,
                     "start_day": 0, "end_day": 60, "side?": "seller" }],
                                          // kind: feed | search | event | outdoor | referral (engine/world/channels.py)
      "cities?": [{ "name": "Austin, Texas", "open_day": 0 }],   // engine/world/geo.py METROS
      "ads": ["ad_1", "ad_2", "ad_3"]     // which ads run
    },
    "experiments": {
      "a": { "changes": "Nothing: the shared campaign" },
      "b": { "changes": "Austin on day 0, Denver on day 30",
             // only what differs from the shared campaign (live runs only):
             "budget_usd?": 40000, "channels?": [], "cities?": [], "ads?": ["ad_3"],
             "price?": 4.99, "trial_days?": 30 }
    }
  }
}
```

## Images

Uploaded with the brief as multipart files (live runs), or rendered from `engine/screens/<app>.html`
into `web/public/screens/` (demo apps). One image per name:

| Name | What | Packs |
|---|---|---|
| `store` | the store page | all |
| `signup` | the sign-up screen | all |
| `main` | the main screen while using the app | dating |
| `paywall` | the paywall | dating |
| `main_<side>` | the main screen for each side (`main_seller`, `main_buyer`, `main_driver`, `main_rider`) | resale, rides |
| `ad_1` `ad_2` `ad_3` | the ads, one per entry in `ads` | all |

Demo screen files keep the pack's prefix: Kindred `ad` (= ad_1), `ad_2`, `ad_3`, `signup`, `store`,
`paywall_*`; Reloop `reloop_ad` (= ad_1), `reloop_ad_2`, `reloop_ad_3`, `reloop_signup`, …

## Where each field goes

| Field | Used by |
|---|---|
| profile, audience, competition | Muse Wonder's design of the kinds of people; the install question |
| ads, ad images | the install question: each person sees one ad (`meta.ads`, person `ad_id`) |
| product, signup image | the sign-up question (new in v2) |
| money, paywall / main images | the question people face while using the app (paywall, list, buy, drive, ride) |
| retention | the question asked when someone stops using the app: why |
| setup | plans (channels, cities, budget, days) and how many simulated people stand for the audience |
