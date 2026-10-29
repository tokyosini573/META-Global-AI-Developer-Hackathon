# Two-sided market launch rules (two_sided v1)

This file is the set of mechanical rules the world engine uses when it simulates the launch of a two-sided-market app (an app that only creates value when two groups find each other, such as dating, ride-hailing, lodging, delivery or home services). Its only evidence is the 8 rule cases in `backtest/rule_set_cases.md` (Tinder, Coffee Meets Bagel, Lulu, Uber, Lyft, Airbnb, DoorDash, Homejoy). No other app cases or web searches were used; only general textbook knowledge (network effects, Bass diffusion, cold start, pricing) was borrowed as a frame. Numeric ranges were either computed directly from the cases or, where the cases say nothing, marked `note: prior, not from cases`. This file is frozen with a git commit before any backtest is run. Any change after freezing must be recorded in the README: what changed, why, and after seeing which backtest result.

> Translation note: this file was frozen in Korean in commit eef683f before any backtest and translated to English afterwards. Only the language changed; no rule, number or range was altered. Two non-rule fixes were made at the same time: a colon in card 9's `applies_when` that broke YAML parsing became a dash, and the sample count in "Sample bias" was corrected from 6 to 5 successes to match the case table.

Common notation
- `active_j`: whether person j is active on day t (1 or 0). `d_ij`: distance between two people (km).
- `n_i = Σ_j K(d_ij)·active_j·[j is on the opposite side from i]`, `K(d) = exp(−d/λ)`.
- Daily success probability `P_i = 1 − (1 − q)^{n_i}` (matches, rides, bookings and orders are all called a "success").
- `σ`, `logit`: calibration hook `p′ = σ(logit(p) + b)`.
- Growth-rate conversion: multiple g over period T → daily relative growth rate `r = ln(g)/T`.

---

### 1. Packing one area densely brings the first success sooner (local density threshold)

```yaml
id: local_density_threshold
mechanism: The daily success probability only rises meaningfully once n_i, the number of nearby active users on the opposite side, crosses a threshold, so with the same headcount a launch packed into a small area produces first successes and return visits sooner.
applies_when:
  - Apps where a success is tied to physical distance (meetups, rides, delivery, in-person services, lodging host-guest at city level)
  - The first 90 days after launch, the cold-start stretch while users still number a few thousand or fewer
formula: |
  n_i(t) = Σ_j exp(−d_ij/λ) · active_j(t)   # sum over the opposite side only
  P_i(t) = 1 − (1 − q)^{n_i(t)}
  # Cold-start churn: the daily churn risk before the first success grows as n_i gets smaller
  h_i(t) = h_base · (1 + γ · 1[no first success yet ∧ t − install_i > T_wait])
  # Calibration: when fitting the per-area average success rate to the benchmark, use one single b shared by all areas
  #       (fitting each area separately erases the density effect)
parameters:
  lambda_km:
    range: [1, 10]
    unit: km
    note: "Taken from the size of the seed areas in the cases. Campuses (USC, the two Florida universities) have a radius of 1~3 km; DoorDash's Palo Alto, Stanford, Menlo Park, Los Altos and Mountain View cluster is about 10~15 km across. An estimate of area size, not a measured value."
  seed_side_size:
    range: [50, 300]
    unit: people or suppliers (the seed at launch time in the first area)
    note: "Tinder texted about 300 acquaintances, DoorDash 50 restaurants, Lyft about 200 drivers at +4 months, DoorDash drivers 4→30. The units are mixed, so this gives only a sense of scale."
  seed_area_penetration_15mo:
    range: [0.10, 0.25]
    unit: share of households/people in the seed area who have used it at least once (+15 mo)
    note: "Only one point, DoorDash's '1 in 6 local households' (≈0.17, company claim), so widened on both sides."
  T_wait:
    range: [3, 14]
    unit: days
    note: "prior, not from cases. The cases have no data on how long people wait for a first success."
  gamma:
    range: [0.5, 3.0]
    unit: multiplier (extra on top of the base churn risk)
    note: "prior, not from cases."
predicts:
  - "At the same install count, the plan with the smaller seed-area radius (higher density) has a shorter median number of days to first success."
  - "At the same install count, the denser plan has a higher active share at day 30."
  - "A plan scattered over many places has a higher share of people who churn without a first success, even at the same install count."
evidence:
  - {case: Tinder, fact: "Started by texting about 300 USC acquaintances; 2012-09-29 party where you needed the app to get in", date: "2012-08~09", source_url: "https://techcrunch.com/2014/07/09/whitney-wolfe-vs-tinder/", strength: strong}
  - {case: DoorDash, fact: "Started in one area around Palo Alto, stayed in the South Bay only for 18 months; at +15 months 1 in 6 local households had ordered", date: "2013-02 ~ 2014-05-22", source_url: "https://techcrunch.com/2014/05/22/doordash-17-3m-sequoia", strength: strong}
  - {case: Uber, fact: "Through +8 months, all of the tens of thousands of paid rides were in SF", date: "2011-02-14", source_url: "https://techcrunch.com/?p=275062", strength: strong}
  - {case: Lyft, fact: "SF only for about 8 months; about 200 drivers at +4 months", date: "2012-09-17", source_url: "https://techcrunch.com/2012/09/17/lyfts-focus-on-community-and-the-story-behind-the-pink-mustache/", strength: strong}
  - {case: Airbnb, fact: "Focused on one city, New York, during YC", date: "2009-01~02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
counter_evidence:
  - {case: Lulu, fact: "Started densely, invite-only at two campuses, but failed. Density is only a necessary condition, not a sufficient one", date: "2013-01 ~ 2016-02", source_url: "https://techcrunch.com/?p=751260", strength: strong}
  - {case: Coffee Meets Bagel, fact: "Started in New York but added Boston within a month (city order via Wikipedia) and still stayed independent", date: "2012-05", source_url: "https://techcrunch.com/2012/04/17/coffee-meets-bagel-turns-online-dating-into-a-daily-deal/", strength: weak}
confidence: high
```

All five successful cases started somewhere narrow: a campus, one city, one neighborhood. The engine uses a distance kernel to count "how many people on the opposite side are alive near me", and when that number is small the first success comes late and people leave in the meantime. Lulu, however, started the same way and still failed. So this rule only goes as far as "it does not work without density" and does not say "density is enough".

### 2. Adding cities before the first city settles thins density in every city (expansion pace)

```yaml
id: expansion_pace_dilution
mechanism: Every new city goes through cold start again, so splitting budget, operations staff and seed users across several cities drops n_i per city below the threshold, and total installs grow while successes and return visits fall.
applies_when:
  - The plan has two or more 'open city X on day d' events
  - Cities are much farther apart than λ, so they cannot share n_i with each other
formula: |
  # The seed and ad budget of city c are divided by the number of open cities C(t)
  seed_c = S_total / C(t),  budget_c = B_total / C(t)
  reach_c = 1 − exp(−k · F_c),  F_c ∝ budget_c          # ad saturation hook
  # Per-city liquidity L_c(t) = successes in the last 7 days / actives in the last 7 days
  # Gate (the shape of a good plan): open the next city only when L_{c-1}(t) ≥ L*
  # Operations load: service quality q is cut by C_new, the number of freshly opened cities (open under 90 days) at the same time
  q_c' = σ(logit(q_c) − δ · max(0, C_new − 1))
parameters:
  months_to_second_city_success:
    range: [1, 18]
    unit: months (launch → second city)
    note: "Coffee Meets Bagel about 1 (⚠️ Wikipedia), Airbnb about 5 (Denver event → New York), Lyft about 8, Uber about 11, DoorDash 18 or more. The actual range of the successful and ambiguous cases, as is."
  cities_at_12mo_success:
    range: [1, 4]
    unit: number of cities (+12 mo)
    note: "Uber 2 (SF, New York), Lyft 4 (+12), DoorDash 1 area, Coffee Meets Bagel about 3~4 (⚠️). For comparison: Homejoy 26 at +10 months."
  cities_at_12mo_failure_reference:
    range: [20, 30]
    unit: number of cities
    note: "Homejoy 26 at +10 months, 30 markets at +14 months. A single failure point, so it is used only as a 'this much is risky' marker."
  L_star:
    range: [0.05, 0.30]
    unit: weekly successes per weekly active user
    note: "prior, not from cases. The cases have no per-city liquidity numbers."
  delta:
    range: [0.0, 0.5]
    unit: logit penalty / each additional new city
    note: "prior, not from cases. 0 turns the operations-load effect off."
predicts:
  - "On the same budget, a plan that opens more cities within 90 days has fewer successes per active user per city and lower 30-day retention, even with the same or more cumulative installs."
  - "A plan that opens the second city after the first city's liquidity passes L* has more 90-day active users than a plan that opens them at the same time based only on dates."
evidence:
  - {case: Uber, fact: "New York about 11 months after SF (2011-05), then Seattle, Chicago, Boston, Paris; 6 cities at +18 months", date: "2010-06 ~ 2011-12", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: strong}
  - {case: Lyft, fact: "LA about 8 months after SF (2013-01-31); 4 cities at +12 months, 6 cities at +14 months", date: "2013-01 ~ 2013-07", source_url: "https://techcrunch.com/2013/05/23/lyft-a16z", strength: strong}
  - {case: DoorDash, fact: "Only after 18 months in the South Bay did it go to LA, Boston and Chicago; SF in 2015-01", date: "2015-01-27", source_url: "https://techcrunch.com/2015/01/27/doordash-sf/", strength: strong}
  - {case: Homejoy, fact: "1 → 26 cities in a little over 6 months, 30 markets at +14 months, shut down 2015-07-31", date: "2013-08-18 ~ 2015-07-31", source_url: "https://techcrunch.com/2013/08/18/homejoy-behind-the-scenes/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "Dropped the promo first-date gift outside New York because of the expansion pace (a direct example of expansion reducing per-city input)", date: "2012~2013", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
counter_evidence:
  - {case: Coffee Meets Bagel, fact: "Opened a second city within a month and did not fail (outcome ambiguous)", date: "2012-05", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: weak}
  - {case: Lyft, fact: "Grew quickly to 24 cities at +22 months and still succeeded. This fits the reading that the problem is expanding 'before settling' rather than fast expansion itself, but the cases alone cannot separate the two readings", date: "2014-03", source_url: "https://www.nbcnews.com/news/amp/wbna54636501", strength: weak}
  - {case: Homejoy, fact: "The case file does not say whether the expansion pace caused Homejoy's failure. Bookings and revenue were never disclosed, so per-city density cannot be checked", date: "2015-07", source_url: "https://techcrunch.com/2015/07/17/homejoy-is-shutting-down-at-the-end-of-the-month/", strength: weak}
confidence: medium
```

The successful cases mostly waited 8~18 months before opening a second city, while the failed Homejoy opened 26 cities in ten months. The engine hands out seed and budget per city and makes each city go through cold start again, so expanding too fast produces thin cities on its own. Homejoy is the only evidence on the failure side, so confidence is medium.

### 3. Seed cohorts and events bring both sides to the same place at the same time (seed and event pulse)

```yaml
id: seed_cohort_event_pulse
mechanism: Triggers that gather both sides in the same place on the same day, such as the founders' network or a big event, raise active_j all at once and push n_i above the threshold, but if density does not hold after the event, the pulse simply dies out.
applies_when:
  - The plan has a one-off event such as a launch-day event, a campus party, or a big local event (a day with a supply shortage)
  - Or it sends concentrated invites on launch day to a specific group (acquaintances, a club, one building)
formula: |
  # Event day d_e, attendee set E (within radius r_e, both sides)
  install_prob_j(d_e) = σ(logit(p_install_j) + b_event)        # j ∈ E
  # After the event, briefly raise the Bass innovation coefficient p
  p(t) = p_0 + Δp · exp(−(t − d_e)/τ_event) · 1[t ≥ d_e]
  # A supply-shortage event (a day short of rooms or cars) raises the demand side's q for that day only
  q(d_e) = q · m_shortage
parameters:
  seed_invites:
    range: [100, 300]
    unit: people
    note: "Tinder texted about 300 acquaintances; Lulu's prize condition was 'rate 300 men first'. The scale of the cases, as is."
  event_supply_adds_per_day:
    range: [50, 100]
    unit: new supply listings per day during the event
    note: "Airbnb 50~100 new listings per day during the Denver convention (✅). One event, one point."
  event_demand_served:
    range: [600, 600]
    unit: demand-side people served in one event (lower bound)
    note: "Airbnb 'more than 600 people found a place'. A lower bound that gives only a sense of scale. When used on a simulated population of 1,000~2,000, scale it down proportionally."
  tau_event:
    range: [3, 21]
    unit: days
    note: "prior, not from cases. The cases do not say how long an event's effect lasts."
  m_shortage:
    range: [1.0, 3.0]
    unit: multiplier
    note: "prior, not from cases. Only on supply-shortage days such as sold-out hotels."
predicts:
  - "A plan with a launch event shows a step jump in installs and first successes around the event day."
  - "Actives at 30 days after the event hold only when density within the event radius crossed the threshold (local_density_threshold); otherwise they fall back to the level of a plan without the event."
evidence:
  - {case: Tinder, fact: "Texted about 300 acquaintances → 2012-09-29 party where you needed the app to get in", date: "2012-09-29", source_url: "https://techcrunch.com/2014/07/09/whitney-wolfe-vs-tinder/", strength: strong}
  - {case: Airbnb, fact: "Relaunched for the Democratic National Convention in Denver when hotels were sold out; more than 600 people found a place, 50~100 new listings per day", date: "2008-08-11", source_url: "https://techcrunch.com/2008/08/11/airbed-and-breakfast-takes-pad-crashing-to-a-whole-new-level/", strength: strong}
  - {case: Lulu, fact: "A prize contest and campus agents brought more than 60,000 downloads and 140,000 reviews in the first month (company claim)", date: "2013-02-05", source_url: "https://techcrunch.com/?p=751260", strength: weak}
counter_evidence:
  - {case: Airbnb, fact: "Did not settle right after the event either and only reached 'ramen profitable' after focusing on New York about 6 months later. The event pulse alone did not hold", date: "2009-02-22", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
  - {case: Lulu, fact: "Created a strong early pulse and still failed", date: "2016-02-09", source_url: "https://techcrunch.com/?p=1274326", strength: strong}
confidence: medium
```

The Tinder party and the Airbnb convention brought both sides to one place at one time and created first successes all at once. In the engine, an event briefly raises that day's installs and the word-of-mouth coefficient. But as the two counter-cases show, an event's effect fades, so density has to remain after the event for it to turn into growth.

### 4. Raising supply quality by hand early on raises the success rate (manual supply quality)

```yaml
id: manual_supply_quality
mechanism: When founders personally look after supply-side quality (photos, delivery, service) early in the launch, the success probability per exposure q rises and successes come even with few people, but this effect exists only in the areas and the period that operators can touch directly.
applies_when:
  - Supply-side quality varies a lot from user to user and the demand side chooses by that quality (listing photos, delivery reliability, profile quality)
  - The plan has a manual item such as 'founder/ops team direct intervention', and its target is limited to one or two areas
formula: |
  # Suppliers targeted by the intervention s ∈ M (at most M_cap, the number operators can touch directly)
  q_s' = σ(logit(q_s) + b_quality)          # s ∈ M
  # Intervention capacity is inversely proportional to the number of areas (linked to expansion_pace_dilution)
  M_cap_c = M_total / C(t)
parameters:
  weekly_revenue_multiplier_during_intervention:
    range: [1.6, 2.0]
    unit: weekly multiple
    note: "Airbnb weekly fee revenue during the New York host visits and professional photos $460 → $897 (×1.95) → $1,428 (×1.59). Two weeks, two points, mixed with other causes, so it does not give b_quality directly."
  founder_handled_transactions:
    range: [100, 200]
    unit: transactions
    note: "DoorDash's 4 founders delivered the first 200 orders themselves. A sense of the scale operators can handle directly."
  b_quality:
    range: [0.0, 1.0]
    unit: logit addition
    note: "prior, not from cases. A wide range that does not contradict the multiples above. 0 turns the effect off."
predicts:
  - "A plan with direct supply-side intervention has more successes in the first 30 days at the same number of suppliers."
  - "The wider the intervention's target area, the smaller the intervention effect per supplier."
evidence:
  - {case: Airbnb, fact: "During YC, visited New York hosts in person for professional photos; weekly fee revenue $460 → $897 → $1,428; 'ramen profitable' on 2009-02-22", date: "2009-01 ~ 2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
  - {case: DoorDash, fact: "Built the site in one day, the founders delivered the first 200 orders themselves, orders up 10x over the summer", date: "2013-02 ~ 2013-09", source_url: "https://stanforddaily.com/2013/09/23/alumni-founded-startup-caters-to-palo-alto-mountain-view-food-deliveries/", strength: strong}
counter_evidence:
  - {case: Airbnb, fact: "The case cannot tell whether the revenue increase came from the photos or from the New York focus, the season or YC itself", date: "2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: weak}
confidence: low
```

Airbnb visited New York hosts in person and took photos, and over those few weeks revenue grew 1.6~2x every week. DoorDash's founders delivered the first 200 orders themselves. The engine slightly raises the success probability of suppliers that operators have touched. Because the causes are mixed, the effect size is left as a prior only.

### 5. Word-of-mouth growth speed is set within the range measured in the cases (Bass q calibration)

```yaml
id: wom_growth_rate_band
mechanism: In the early stretch (N ≪ M) the relative growth rate of Bass diffusion is roughly q, so the range obtained by converting the monthly and weekly growth rates the cases disclosed into a daily q is used as the upper band for the word-of-mouth coefficient, and a high growth rate alone is not used to predict success.
applies_when:
  - Every two-sided-market run (always, as long as the Bass hook is used)
  - In particular, when the word-of-mouth coefficients of two plans are picked separately, both must be inside this band
formula: |
  dN/dt = (p + q · N/M) · (M − N)
  # Early approximation: (dN/dt)/N ≈ q · (1 − N/M) + p · M/N  →  if N ≪ M and the p term is small, ≈ q
  # Case growth rate g (over period T) → set r = ln(g)/T as q_eff
  # Only people who have experienced a success spread word of mouth (linked to the density rule)
  q_i = q_eff · 1[i had at least 1 success in the last 30 days]
parameters:
  q_eff_daily:
    range: [0.008, 0.026]
    unit: 1/day
    note: "Case growth rates converted with r = ln(g)/T. Tinder daily matches 3.5M (+14) → 10M (+18), about 120 days: 0.0087. Uber 34% per month: 0.0098. Lyft weekly rides 14,000 → 30,000, about 2 months: 0.0125. Coffee Meets Bagel +50% per month (+5): 0.0135. DoorDash 20% per week (+7): 0.026; orders 10x over the summer (about 90 days): 0.026. The metrics are mixed across users, rides, orders and matches, and paid marketing and the p term are mixed in as well. Those who disclosed are successful or funded companies, so the range is taken to be skewed toward the high end."
  growth_multiple_90d_implied:
    range: [2.0, 10.4]
    unit: 90-day multiple (= exp(q_eff·90))
    note: "Computed from the q_eff range above. If the engine's result falls far outside this band, suspect the calibration."
  failure_growth_reference:
    range: [0.003, 0.03]
    unit: 1/day
    note: "Homejoy 'double-digit monthly growth' (10% or more per month → 0.003 or more). The upper bound is unknown, so the success band's upper bound is used as is. It means the failure case's growth rate was also inside the band."
  p_innovation_daily:
    range: [0.0001, 0.003]
    unit: 1/day
    note: "prior, not from cases. The cases have no numbers that separate ad and press effects."
predicts:
  - "The 90-day growth multiple produced by the engine falls within the band of about 2~10x for both plans. Going outside it counts as a calibration failure."
  - "With the same word-of-mouth coefficient, the plan with more people who have experienced a success (the denser plan) has more installs at 90 days."
evidence:
  - {case: Tinder, fact: "Daily matches 3.5M (2013-10-31) → 5M (2013-12) → 10M (2014-02-28)", date: "2013-10-31 ~ 2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
  - {case: Uber, fact: "Growth of 34% or more per month at +18 months (company claim)", date: "2011-12-06", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: weak}
  - {case: Lyft, fact: "Weekly rides 14,000 → 30,000 (2 months)", date: "2013-05-23", source_url: "https://techcrunch.com/2013/05/23/lyft-a16z", strength: strong}
  - {case: Coffee Meets Bagel, fact: "+50% per month at +5 months, mostly word of mouth", date: "2012-09-26", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: strong}
  - {case: DoorDash, fact: "Growth of 20% or more per week, orders 10x over the summer", date: "2013-09-30", source_url: "https://www.ycombinator.com/blog/doordasy-yc-s13-raises-2-dollars-dot-4m-to-improve-food-delivery-growing-over-20-percent-weekly/", strength: strong}
counter_evidence:
  - {case: Homejoy, fact: "'Double-digit monthly growth' at +14 months, but shut down about 2 years later. The growth rate does not separate survival", date: "2013-12-05", source_url: "https://techcrunch.com/2013/12/05/homejoy-38-m/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "+50% per month at +5 months, but about 80,000 users at +16 months, an ambiguous outcome. Early high growth may not last", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
confidence: medium
```

Converting the growth rates the cases disclosed to a daily basis gives 0.8%~2.6% per day, that is, about 2~10x over 90 days. The engine picks the word-of-mouth coefficient only inside this band and lets only people who have experienced a success spread word of mouth, which ties it to the density rule. Homejoy also grew fast, so the growth rate itself is not used to judge who wins.

### 6. Daily exposures × success rate per exposure sets success volume (exposure throughput)

```yaml
id: exposure_throughput
mechanism: Daily successes are the product of how many opposite-side candidates each person sees per day (exposures) and the success probability per exposure, so a curated design that gives few exposures has a high return rate but less total success and less word-of-mouth material, while a design that gives many exposures has a large total despite a low success rate per exposure (as long as the nearby candidate pool does not run dry).
applies_when:
  - Matching apps where users see candidates one at a time and choose (dating, supplier-choice marketplaces)
  - When two plans differ in their daily exposure cap or recommendation method
formula: |
  pool_i(t) = n_i(t)                                # the nearby opposite-side count from the density rule
  E_i(t) = min(E_cap, pool_i(t) − seen_i(t))       # candidates already seen are removed, so the pool runs dry
  P_i(t) = 1 − (1 − q_e)^{E_i(t)}                   # 1 exposure = 1 attempt
  # Opening (whether the app is opened) is set by calibrating the LLM's choice
  open_i(t) ~ Bernoulli(σ(logit(p_open_i) + b_open)),  mean = open_rate
parameters:
  q_e_swipe:
    range: [0.010, 0.014]
    unit: matches / 1 exposure (swipe)
    note: "Tinder 3.5M matches on 350M daily swipes = 1.0% (+14), 10M on 750M = 1.33% (+18). CEO statements, so weak. Used for high-exposure designs."
  q_e_curated:
    range: [0.03, 0.06]
    unit: direct connections / 1 introduction
    note: "Coffee Meets Bagel about 6,000 direct connections from more than 100,000 introductions → 6% or less. The denominator is a lower bound, so widened downward. Used for one-a-day curation designs."
  E_cap_curated:
    range: [1, 1]
    unit: exposures / day
    note: "Coffee Meets Bagel one person a day (at noon)."
  E_cap_swipe:
    range: [20, 200]
    unit: exposures / day
    note: "prior, not from cases. Tinder's numbers are totals only and the user count was not disclosed, so swipes per person cannot be computed."
  open_rate_curated:
    range: [0.60, 0.75]
    unit: daily open share
    note: "Coffee Meets Bagel '70% check daily' (+5). One point, so widened slightly on both sides."
predicts:
  - "If the nearby candidate pool is large enough (n_i ≫ E_cap), the plan with the higher exposure cap has more cumulative successes at 90 days."
  - "The plan with the lower exposure cap has a higher daily open rate."
  - "If the nearby candidate pool is small (low density), raising the exposure cap does not add successes; seen_i uses up the pool and churn rises."
evidence:
  - {case: Tinder, fact: "350M daily swipes, 3.5M matches", date: "2013-10-31", source_url: "https://www.globaldatinginsights.com/mobile/31102013-tinder-sees-350m-swipes-day-ceo-sean-rad-hints-future-plans/", strength: weak}
  - {case: Tinder, fact: "750M daily swipes, 10M matches, about 1B cumulative matches (company claim)", date: "2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
  - {case: Coffee Meets Bagel, fact: "One person a day, more than 100,000 introductions, about 6,000 direct connections, 70% check daily", date: "2012-09-26", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "About 80,000 users and more than 1.5M matches at +16 months (the definition of a match may differ from a 'direct connection')", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
counter_evidence:
  - {case: Coffee Meets Bagel, fact: "Besides exposure design, the two apps also differ in launch approach, pricing and platform (web → app), so the difference in success volume cannot be attributed to exposure design alone", date: "2012~2014", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: weak}
confidence: medium
```

Swipe designs get a little over 1% matches per exposure, and one-a-day curation designs get about 6% connections per introduction. In exchange, curation designs show only one person a day, so their total is small. The engine produces successes as "how many people are shown per day × success probability per person", and once nearby candidates run out, adding exposures does not help.

### 7. Charging for participation itself must wait until density exists (pricing timing)

```yaml
id: monetization_timing
mechanism: A per-transaction fee is collected only when a success happens, so adding it from day one does not hurt density, but a paywall on participation itself (subscription, viewing limits) cuts actives before the threshold and erodes both n_i and word of mouth, and those who pay to get past the paywall are only a few % of actives.
applies_when:
  - The plan has a pricing event (paywall, end of free trial, start of fees)
  - The pricing can be split into 'participation pricing (access)' and 'transaction pricing (transaction)'
formula: |
  # After the access-pricing event day d_pw, lower the activity probability of those who did not stay free
  active_prob_i' = σ(logit(active_prob_i) − b_paywall)    # non-payers, t ≥ d_pw
  pay_i ~ Bernoulli(σ(logit(p_pay_i) + b_pay)),  solve b_pay so that its mean equals payer_share
  # Transaction pricing: take_rate · price of revenue per success; the activity probability is left untouched
  # (the effect of price on the demand side's success probability q is reflected only through LLM choice + calibration)
parameters:
  payer_share_freemium:
    range: [0.03, 0.05]
    unit: share of active users who pay
    note: "Coffee Meets Bagel beans purchases 3~5% (+16). The one case that was freemium from the start."
  free_months_before_access_paywall_success:
    range: [0, 31]
    unit: months
    note: "Tinder free for about 2.5 years (2012-08 → 2015-03-02 Tinder Plus), Coffee Meets Bagel 0 months (freemium from the start, ambiguous outcome). The wide range is the honest answer."
  b_paywall:
    range: [0.0, 1.5]
    unit: logit penalty
    note: "prior, not from cases. The cases have no numbers that isolate the paywall's effect on actives."
predicts:
  - "A plan that turns on access pricing within 90 days has fewer 90-day actives and cumulative successes than a plan that does not, and more revenue."
  - "For a plan that uses only transaction pricing, at the same fee rate the pricing start date barely changes the active-user curve."
  - "Payers in an access-pricing plan are calibrated to around 3~5% of active users."
evidence:
  - {case: Tinder, fact: "Free for about 2.5 years, first paid product 2015-03-02 ($9.99, $19.99 for age 30 and over)", date: "2015-03-02", source_url: "https://fortune.com/2015/03/02/tinder-plus-cost", strength: strong}
  - {case: Coffee Meets Bagel, fact: "Freemium from the start (earning and buying beans), 3~5% buy beans, about 80,000 users at +16 months", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
  - {case: DoorDash, fact: "$6 delivery fee from day one, no minimum order, restaurant commission — added transaction pricing from the start and grew", date: "2013-02", source_url: "https://techcrunch.com/2013/07/26/y-combinator-backed-doordash-delivers-food-quickly-in-south-bay-hopes-to-expand-beyond-food/", strength: strong}
  - {case: Uber, fact: "Paid rides from the start (premium black cars), more than $100 per rider per month at +18 months (company claim)", date: "2011-12-06", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: weak}
  - {case: Airbnb, fact: "Had transaction fee revenue from early on (weekly $460 → $1,428). The fee rate is not in the case", date: "2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
counter_evidence:
  - {case: Lulu, fact: "Had no revenue model at all at launch and failed. The direction 'just stay free for a long time' alone does not explain survival", date: "2013-01 ~ 2016-02", source_url: "https://techcrunch.com/?p=751260", strength: strong}
  - {case: Coffee Meets Bagel, fact: "Freemium from the start, yet did not fail and stayed independent. There is no evidence that the access-pricing effect is decisive", date: "2018-05", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: weak}
confidence: low
```

Apps that charge only when a transaction happens (DoorDash, Uber, Airbnb) charged from day one and still grew. Among apps that put a price on participation itself, Tinder stayed free for 2.5 years, and Coffee Meets Bagel, which sold paid items from the start, had 3~5% payers. The cases do not give effect sizes, so only the direction and the payer share are fixed and the rest is left as a prior.

### 8. Demand bought with discounts does not come back at full price (subsidy-dependent demand) — failure explanation

```yaml
id: subsidy_dependent_demand
mechanism: Deep discounts on the first transaction make first-transaction counts grow quickly, but people who came in through a discount have a low probability of repurchasing at full price, and after supply-side pay and the discount the share left per transaction can be negative, giving a structure that grows on the surface while leaking money underneath.
applies_when:
  - The plan has a subsidy event such as a first-transaction discount, a free trial transaction or credits
  - Services where the platform's share per transaction (take rate) is small and supply-side pay is a large part of the price
formula: |
  # Whether the first transaction came via a discount: promo_i
  p_repeat_i' = σ(logit(p_repeat_i) − b_promo · promo_i)      # full-price repurchase
  margin_tx = take_rate · price − discount_tx                  # platform share per transaction
  contribution(t) = Σ_tx margin_tx                             # cumulative contribution margin
  # Reported metrics: alongside the first-transaction count, always output the 'full-price second-transaction share' and contribution
parameters:
  take_rate:
    range: [0.20, 0.40]
    unit: platform share of the price
    note: "Homejoy $20 per hour, cleaner pay $12~15 → (20−15)/20 = 0.25 ~ (20−12)/20 = 0.40. Lyft 20% of donations (⚠️ 2014 data)."
  first_tx_discount:
    range: [0.5, 0.8]
    unit: discount rate off the full price
    note: "Homejoy first cleaning $19, full price about $85 → about 0.78 (⚠️ secondary sources only). The lower end is a prior."
  promo_share_of_bookings:
    range: [0.5, 0.75]
    unit: share of all bookings that came via a discount (failure reference point)
    note: "Homejoy '75% of bookings came via discounts' (⚠️ secondary sources only). The lower end is a prior."
  b_promo:
    range: [0.0, 1.5]
    unit: logit penalty
    note: "prior, not from cases. The cases have no repurchase-rate numbers for customers who came via discounts."
predicts:
  - "A plan with a deeper first-transaction discount has more first transactions at 30 days."
  - "The same plan has a lower 'full-price second-transaction share' at 90 days."
  - "If take_rate is smaller than the discount rate, the plan with the deeper discount has a lower 90-day contribution (possibly negative)."
evidence:
  - {case: Homejoy, fact: "$20 per hour, cleaner pay $12~15 per hour", date: "2012~2013", source_url: "https://techcrunch.com/2013/08/18/homejoy-behind-the-scenes/", strength: strong}
  - {case: Homejoy, fact: "$19 first-cleaning promo (full price about $85), 75% of bookings came via discounts — secondary sources only", date: "2018 (retrospective)", source_url: "https://d3.harvard.edu/platform-digit/submission/homejoys-not-so-joyous-demise/", strength: weak}
  - {case: Homejoy, fact: "$40M raised in total and 30 markets, but no bookings or revenue disclosed; shut down 2015-07-31", date: "2013-12-05 ~ 2015-07-31", source_url: "https://techcrunch.com/2015/07/17/homejoy-is-shutting-down-at-the-end-of-the-month/", strength: strong}
  - {case: Lyft, fact: "The platform's share is 20% of donations (2014 data)", date: "2014", source_url: "none (case file gives no URL for this fact)", strength: weak}
counter_evidence:
  - {case: Uber, fact: "Free rides and referral credits appear only in marketing blogs, so they cannot be verified. There is no data to confirm or refute a subsidy effect in the success cases", date: "2010~2011", source_url: "https://techcrunch.com/2010/07/05/ubercab-takes-the-hassle-out-of-booking-a-car-service/", strength: weak}
  - {case: Homejoy, fact: "The case file has no direct evidence that the discount structure caused the shutdown (the cited Forbes article could not be opened)", date: "2015-07-23", source_url: "https://d3.harvard.edu/platform-digit/submission/homejoys-not-so-joyous-demise/", strength: weak}
confidence: low
```

Homejoy paid 60~75% of the price to the person doing the cleaning, so if, as the secondary sources say, it cut the first cleaning by nearly 80%, it would have lost money on every transaction. The engine separately counts full-price repurchases by customers who came via discounts and sums the share left per transaction, so a "sold a lot but nothing was left" outcome shows up in the numbers. The key numbers come only from secondary sources, so confidence is low.

### 9. Novelty installs do not stay active without repeat transactions (separating installs from actives) — failure explanation

```yaml
id: novelty_installs_without_repeat_loop
mechanism: Installs driven by press and buzz pile up fast like a Bass p pulse, but if the core action does not lead to repeat transactions between the two sides (meeting again, riding again, ordering again), churn risk stays high and cumulative installs and active users drift far apart.
applies_when:
  - Apps whose core action is a one-way action by one side (rating, viewing, browsing) and whose repeat successes with the opposite side are weak
  - The plan relies on press, virality or contests to create large first-month installs
  - When choosing the metric for comparing outcomes (always — judge by actives and repeat transactions, not by cumulative installs)
formula: |
  # Separate cumulative installs N and actives A
  dA/dt = installs(t) − Σ_i h_i(t) · active_i
  # Repeat value v_i = number of successes with the opposite side in the last 30 days
  h_i(t) = h_novelty · exp(−t_since_install/τ_nov) + h_floor · exp(−β · v_i)
  # Judging metrics: A(90), number of users with repeat transactions, and A(90)/N(90)
parameters:
  downloads_month1:
    range: [60000, 60000]
    unit: downloads (lower bound, real market)
    note: "Lulu more than 60,000 in the first month (company claim). When used on a simulated population, convert it proportionally. A reference point for how fast novelty installs can pile up."
  active_to_cumulative_ratio:
    range: [0.05, 0.5]
    unit: actives / cumulative installs
    note: "prior, not from cases. Lulu only says its 6M downloads and sign-ups are 'not active' and gives no active count. Left wide."
  tau_nov:
    range: [7, 45]
    unit: days
    note: "prior, not from cases."
  beta:
    range: [0.2, 2.0]
    unit: 1 / 1 success
    note: "prior, not from cases. How much churn falls with each success experienced."
predicts:
  - "A plan that grew first-month installs through buzz can lead in cumulative installs at 30 days yet trail in 90-day actives if repeat successes are few."
  - "At the same install count, the plan with more repeat successes with the opposite side per user has a higher 90-day active/cumulative ratio."
evidence:
  - {case: Lulu, fact: "More than 60,000 downloads and 140,000 reviews in the first month (company claim)", date: "2013-02-05", source_url: "https://techcrunch.com/?p=751260", strength: weak}
  - {case: Lulu, fact: "1M users and 500,000 men requesting reviews at +7 months (founder claim)", date: "2013-08-22", source_url: "https://www.thedailybeast.com/meet-lulu-an-app-that-lets-girls-rate-guys-anonymously/", strength: weak}
  - {case: Lulu, fact: "6M downloads and sign-ups at acquisition ('not active'), the original app discontinued, no revenue model at launch", date: "2016-02-09", source_url: "https://techcrunch.com/?p=1274326", strength: strong}
  - {case: Tinder, fact: "The success case disclosed daily matches (repeat successes) rather than user counts — matches 3.5M → 10M", date: "2013-10-31 ~ 2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
counter_evidence:
  - {case: Lulu, fact: "500,000 men requesting reviews themselves means the rated side also partly took part. The case file gives no basis for asserting that a repeat loop was 'absent'", date: "2013-08-22", source_url: "https://www.thedailybeast.com/meet-lulu-an-app-that-lets-girls-rate-guys-anonymously/", strength: weak}
confidence: low
```

Lulu gathered 60,000 people in the first month and 1 million in seven months, but three years later the app was shut down with the remark that its 6 million downloads were "not active". The engine counts cumulative installs and active users separately and lowers churn risk only for people who get repeat successes with the opposite side. Winners, too, are judged by 90-day actives and repeat transactions, not by installs.

---

## Weak evidence or not extracted

- **There is almost no acquisition-channel data.** None of the 8 cases has ad spend, customer acquisition cost (CAC) or installs by channel. So the `k` of the ad saturation hook `reach = 1 − e^(−kF)` cannot be set from the cases and is entirely prior. When two plans differ only in ad budget, the engine's verdict is outside this file's evidence.
- **There is not a single retention or churn curve number.** Survival curves and churn-risk parameters (`h_base`, `gamma`, `h_novelty`, `beta`, etc.) are all prior. All the cases give is one point, "70% check daily" (Coffee Meets Bagel), and Lulu's remark "not active".
- **Referral rewards such as referral credits and free rides were not extracted.** Uber has only marketing blogs, and Lyft is noted as unverified.
- **Regulatory shocks were not extracted.** Uber's 2010-10 cease-and-desist and renaming are ⚠️, and the cases do not show their effect on later growth.
- **The direction of the price level (premium vs. low-cost) was not set.** Premium black cars (Uber) and donation pricing (Lyft) both succeeded, so no direction can be chosen. The price multiple versus taxis also differs by source: 1.5~2x, about 20%, about 50%.
- **Branding (the pink mustache, etc.) and cross-posting (Craigslist, timing unknown ⚠️) were not extracted.** There are no numbers to measure their effect.
- **Fundraising was not used as a cause.** In most cases funding is reported alongside growth as its result, and the failed Homejoy also raised $40M.
- **The effect of invite-only and limited release (Lulu's invite-only access, US store only) was not extracted separately.** The only case that used this approach is the failed Lulu, so no direction can be set.
- **Sample bias.** 5 successes, 1 ambiguous and 2 failures, and most numbers are company or CEO statements. The growth band (`wom_growth_rate_band`) is likely skewed toward the high end. The failure-side rules (8 and 9) each rest on a single case, so the cases alone cannot confirm whether this file identified the failure causes correctly.
- **Date conflicts.** Tinder's launch (2012-08 vs. 2012-09), Lyft's launch (2012-05 vs. 2012-06), DoorDash (2013-02 vs. 2013-01) and Homejoy's launch month differ by source. Ranges built from month counts (`months_to_second_city_success`, etc.) carry an error of ±1 month.
- **Metric definitions are mixed.** "Match", "direct connection", "ride", "order" and "user" differ from case to case, and even within Coffee Meets Bagel "6,000 direct connections" and "1.5M matches" may be defined differently. The per-exposure success rates (`q_e_*`) are uncertain by as much as the definitions differ.
- **Some cases have no numbers for the 12~18 month window.** Lulu (nothing after +7 until +37), Homejoy (no bookings or revenue disclosed), Airbnb (nothing after +6 until +27). In backtests of this window, rules that lean on these three cases have weak verification power.
