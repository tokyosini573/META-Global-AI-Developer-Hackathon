# Benchmarks research for the launch-simulation engine (US, mobile apps)

Researched 2026-11-03. Every row has a public URL and the period it describes.

**Confidence scale**
- **high**: a primary source (company filing, peer-reviewed paper or platform documentation) that I read directly.
- **medium**: a vendor benchmark report built on large aggregated data, a single vendor's own claim, or a figure I could read only through a search snippet.
- **low**: a blog or vendor estimate with no stated method, a self-reported survey, or old data.

**PRIOR** marks a value where no public number was found. It is my own suggested range with the reasoning given, not a measurement.

Caveats that apply throughout:
- Vendor benchmarks disagree with each other. Use the ranges, and compare numbers only within the same source.
- "Overall" Apple Ads figures from different vendors use different samples.

---

## Part 1: Acquisition channels

### 1. Online feed ads (TikTok, Meta, YouTube, display)

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| $13.26 (TikTok), $14.19 (Meta) | USD CPM | Median CPM across advertisers in the vendor's data, all objectives (not app-install only). TikTok CPM rose 16% in 2025 | https://influee.co/blog/tiktok-ads-benchmarks | 2025 | low-medium |
| $10–15 typical; lead-gen $20–45 | USD CPM | Meta (FB+IG) CPM in the US, all objectives | https://affectgroup.com/blog/meta-ads-cpm-in-the-us-2025-benchmarks-for-facebook-and-instagram/ | 2025 | low |
| 1.71% | CTR | Facebook *traffic* campaigns, cross-industry average (not app installs). Prior year 1.57%. CPC $0.70 | https://www.wordstream.com/blog/facebook-ads-benchmarks-2025 (read via search snippet; page returned 403) | 2025 | medium |
| 0.84% (range 0.5–1.5%) | CTR | TikTok conversion-optimized ads (cites Lebesgue analysis) | https://www.dataslayer.ai/blog/tiktok-ads-reporting-metrics-dashboards-2025 | 2025 | low |
| ~$12 CPM, 1.5% CTR (in-stream); ~$5 CPM, 0.8% CTR (Shorts) | USD CPM / CTR | YouTube estimates from a calculator site | https://ttcalculator.net/data/earnings/tiktok-advertising-rates-benchmarks/ | ~2025 | low |
| 0.1–0.3% banner; 2–6% static interstitial; 3–8% video interstitial | CTR | In-app display formats; mixed secondary sources, mostly gaming | https://blog.playio.co/mobile-game-ad-ctr-benchmarks-2026 | 2023–2025 | low |
| TikTok $1.50–4; Meta $2–6; Google $1.50–5 | USD CPI | Cost per install ranges, "highly vertical-dependent" | https://findclout.com/blog/cost-per-install-by-channel-2026 | 2026 | low |
| $0.99 (e-commerce), $1.01 (shopping), $0.89 (marketplace) | USD CPI | **Global** blended CPI, all channels. The US figure is several times higher | https://www.adjust.com/blog/shopping-app-trends/ | Q1 2025 | medium |
| iOS ≈ 3× Android (~$3.60 vs ~$1.20) | USD CPI | Global platform gap, attributed to AppsFlyer | https://mapendo.co/blog/cost-per-install-2025 | ~2024–25 | low |

**Other parameters**
- **Click to install (PRIOR):** 20–40% of feed-ad clicks become installs. No clean public number exists. As an anchor, the US App Store product-page conversion is 8.56% for all page viewers (Part 2), and an ad-clicker has higher intent.
- **Volume limit:** effectively none at hackathon budgets; supply comes from auction inventory.
- **City targeting:** yes. Meta, TikTok and Google all support city, ZIP or radius targeting (standard platform features).

### 2. Search and app-store ads

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| CPT $1.91; CPI $4.06; TTR 6.6%; CR 55% | USD / % | **US** Apple Ads search-results median, all categories (AppTweak Campaign Manager data) | https://www.apptweak.com/en/aso-blog/apple-ads-benchmarks?currency=us | Jan–Dec 2025 | medium |
| CPT $0.82; CPI $1.33; TTR 12.3%; CR 58.9% | USD / % | **US** Apple Ads, **Shopping** category median (about 2,800 US advertisers) | same | 2025 | medium |
| CPT $1.58; CPI $3.70; TTR 4.7%; CR 50.5% | USD / % | **US** Apple Ads, **Travel** category (Uber and Lyft are listed in Travel) | same | 2025 | medium |
| CPT $1.01; CPI $1.96; TTR 7.3%; CR 57.9% | USD / % | **US** Apple Ads, **Navigation** category | same | 2025 | medium |
| CPT median $1.79; TTR median 8.2% | USD / % | US Apple Ads across 23 categories (SplitMetrics guide) | https://www.splitmetrics.com/blog/apple-search-ads (via search snippet) | Apr–Jun 2026 | medium |
| TTR 9.7%; CR 66.2% | % | Global Apple Ads search-results averages (SplitMetrics 2025 report) | https://splitmetrics.com/apple-ads-search-results-benchmarks-2025/introduction | 2025 | medium |
| 6.3B impressions, 495.6M taps, 315.6M downloads (≈7.9% TTR, ≈64% tap→install) | count | Totals in the SplitMetrics 2026 report, 91 markets. The ratios are my own arithmetic | https://splitmetrics.com/apple-ads-search-results-benchmarks-2026/benchmarks-by-app-categories | 2025 data | medium |
| CR Shopping 69.55%, Travel 70.30%; all categories 65.82% | % tap→install | Global Apple Ads by category (MobileAction) | https://www.mobileaction.co/report/apple-ads-2026-benchmark-report/conversion-rate-search-results-ads/ | 2025 | medium |
| CPT $1.84; CPA $2.76; TTR 9.07%; CR 66.7% | USD / % | Global Apple Ads (MobileAction 2025 report) | https://www.mobileaction.co/report/apple-search-ads-2025-benchmark-report/executive-summary/ | 2024 | medium |
| CPC $5.26; conv. rate 7.52% | USD / % | Google Search ads (web, not app campaigns), all industries, 16k+ campaigns | https://searchengineland.com/google-ads-costs-rising-but-conversion-rates-improved-in-2025-477927 | 2024–25 | medium |
| State, Locality (city/metro), country | targeting | Apple Ads App Store campaigns can target by US state and city/metro ("US\|NY\|New York City") | https://developer.apple.com/documentation/apple-ads-platform-api/geo-targeting-endpoints.md | current docs | high |

**Search demand (how many people search for a category term)**
- **No public number found** for US monthly searches of generic category terms such as "dating app" or "sell clothes app". Apple shows only a 5–100 "popularity" score, not volume.
- The only figures available:
  - About 450k monthly Google searches for online-dating-app terms (Oct 2021–Mar 2022, not US-specific, cited via Business of Apps): https://databoks.katadata.co.id/en/technology-telecommunications/statistics/36a5cdf657ee0da/top-10-most-popular-app-categories-based-on-google-search-volume (low).
  - Bumble 301k and Match 165k US brand searches (Semrush, Feb 2023): https://www.insidermonkey.com/blog/12-most-popular-dating-sites-and-apps-in-the-us-1254025/ (low).
- **PRIOR:** 10k–100k US App Store searches per month for a generic category term, and 1k–10k inside a single metro. Treat this as the hard cap on search-channel impressions. Reasoning:
  - Generic terms sit well below the top brand terms, which run about 100k–1.4M.
  - Metro share scales roughly with population; NYC is about 6% of the US.

### 3. Offline field promotion (campus ambassadors, booths, flyers)

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| $15–25/hr (events); $10–15/hr (street-team distribution) | USD per hour | US campus ambassador wages (vendor guide) | https://www.makaiinc.com/resources/student-brand-ambassador-compensation-and-incentive-models-compared | ~2025 | low |
| $25/hr ambassador, $27/hr lead | USD per hour | One real US campus activation job posting (Ames, IA) | https://www.trustedherd.com/companies/newbridge-marketing-group/currentJobs/brand-ambassador-ames-iowa--1004129850 | 2025–26 | low (single posting) |
| $62.72 | USD per referred lease | One campus ambassador case study: 50 ambassadors, $18.7k over 9 months, performance pay | https://www.makaiinc.com/resources/student-brand-ambassador-compensation-and-incentive-models-compared | n/a | low (single case) |
| 1–4% | scans ÷ estimated viewers | QR scan rate for posters/flyers on pinboards and street posts; 25–60% for table tents. Vendor aggregate; denominator is estimated | https://linkbreakers.com/help/article/qr-code-physical-placement-benchmarks | 2026 | low |
| 2.0–4.4% | response rate | Direct mail to prospect lists (ANA response-rate report, via secondary sources). Analog for printed pieces | https://www.ana.net/miccontent/show/id/sl-2024-03-ana-response-rate-report-2023 ; https://www.4over4.com/statistics/direct-mail-response-rate-benchmarks | 2023–2025 | low-medium |

**PRIORs for the model**
- **Flyers handed out:** 60–120 per ambassador-hour, which at $15–25/hr is about $0.15–0.40 per flyer contact. Of people handed a flyer, 1–3% visit the store page.
- **Booth conversations:** 10–25 per hour. Of people spoken to, 15–35% install on the spot (assisted install).
- **Volume limit:** foot traffic and staff hours.
- **City targeting:** yes, by construction; it can even be targeted to a single campus.

### 4. Out-of-home and mass media

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| $12.43 | USD CPM | NYC billboard CPM claimed by OUTFRONT (media owner) | https://www.outfront.com/markets/new-york-city | current page | low (seller claim) |
| $4–9 car cards; $6–16 station domination; $8–20 train wrap | USD CPM | NYC subway rate ranges (AdQuick marketplace) | https://adquick.com/outdoor-advertising/new-york-ny | 2025–26 | low |
| $7–75+ | USD CPM | NYC digital OOH, street level to Times Square | https://adquick.com/dooh-advertising/new-york-ny | 2026 | low |
| ~$43.35 broadcast; ~$20.60 cable | USD CPM (adults) | National TV upfront CPMs (Media Dynamics estimate, quoted by Adwave) | https://adwave.com/resources/tv-advertising-cost-trends | 2024–25 season | low-medium |
| 76% "took action"; 73% favorable | % of survey respondents | OAAA/Harris survey (n=1,023), self-reported action after seeing DOOH. **Not** a per-exposure response rate | https://oaaa.org/news/new-study-finds-digital-out-of-home-advertising-surpasses-other-media-in-driving-favorability-and-action | 2024 | low |
| 5.3× index | search activity per $ | OOH drives 5.3× expected search share relative to spend (OAAA/Comscore). An index, not a rate | https://mediapost.com/publications/article/373961/oaaacomscore-study-finds-out-of-home-nearly-as-go.html | ~2022 | low |

**Response rate and targeting**
- **No public per-exposure response rate found** for OOH or TV.
- **PRIOR:** 0.02–0.2% of OOH or TV impressions lead to a store-page visit within 2 weeks. Reasoning:
  - An OOH impression is only an "opportunity to see", and acting on it needs recall plus a separate search.
  - So it should sit about 1–2 orders of magnitude below an active digital click (banner CTR 0.1–0.3%, feed CTR about 1%).
- **City targeting:** OOH is city- and even station-specific. TV can be targeted to one DMA through local spot buys.

### 5. Referral / invite programs

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| Credit varies by market; referee must take first ride within 30 days | rules | Lyft official referral rules (no fixed $ stated) | https://www.lyft.com/terms/referrals | updated 2025-09-29 | high (rules), n/a (amount) |
| $10–50 referee credit, depending on city | USD | Lyft rider referral credit, third-party guide | https://www.ridester.com/lyft-promo-codes-existing | ~2025 | low |
| 8–10% "good", 15%+ "outstanding" | invites → sign-ups | Invitation conversion rate (startup-metrics glossary) | https://www.shno.co/startup-metrics/invitation-conversion-rate | n/a | low |
| 10–15% median; 20%+ top quartile | referrals → conversions | Referral conversion rate (vendor guide, SaaS-leaning) | https://fungies.io/saas-referral-program-guide.md | ~2025 | low |
| 19.2% | % of participants | Share of program participants who make at least one successful referral (GrowSurf) | https://growsurf.com/statistics/referral-program-benchmarks.md | ~2025 | low |
| 25.3% (205 of 809) | % of apps | Share of tracked apps with a visible invite/referral surface (lower bound) | https://www.lazyweb.com/research/how-many-apps-have-a-referral-program.md | Jul 2026 | low |

**PRIOR:** $5–20 per side (double-sided reward) for consumer marketplaces and mobility. 5–15% of invites sent lead to an install. Volume is limited by active users × share who refer (about 5–20%).

---

## Part 2: Calibration targets by category

### A. Shopping / resale marketplace

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| 8.56% (App Store); 16.15% (Google Play) | % | **US** store product-page view → install, all categories (category split is behind a paywall) | https://www.apptweak.com/en/aso-blog/average-app-conversion-rate-per-category?format=md | 2025 | medium |
| 10.6% | % | Shopping product-page conversion (Adjust blog, year unclear) | https://www.adjust.com/blog/how-to-improve-mobile-conversion-rates-ecommerce-apps/ | undated | low |
| 58.9% (US) / 69.55% (global) | % tap→install | Apple Ads Shopping CR (high-intent search traffic; upper bound for a page visit) | AppTweak and MobileAction links in Part 1 §2 | 2025 | medium |
| D1 24.8% marketplace; 16% deal discovery; 12.8% general shopping | % | **Global** day-1 retention (Adjust Shopping App Insights). Marketplace sessions on day 0: 1.86 per user | https://www.businesswire.com/news/home/20250805461912/en ; https://www.adjust.com/blog/shopping-app-insights-2025/ | Jan 2023–Jun 2025 | medium |
| D1 12% / D7 6% / D30 2% | % | Shopping apps retention (Adjust data as relayed by Promodo; global) | https://www.promodo.com/blog/mobile-marketing-benchmarks | 2025 | low |
| D30 ≈ 8.1% | % | Shopping D30 (cites AppsFlyer 2026 eCommerce report; secondhand) | https://www.rocketshiphq.com/?p=5319 | 2025–26 | low |
| D1 26% / D7 13% / D30 7% | % | All-vertical global average (Adjust) | https://www.adjust.com/blog/what-makes-a-good-retention-rate/ | ~2024 | medium |
| 4.7% (one edition) and 10.5% (2019) | % installs → purchase | Shopping install-to-purchase rate (Liftoff Mobile Shopping Apps Report; no fixed 30-day window) | https://liftoff.io/?p=15725 ; https://content.liftoff.io/hubfs/2022/Reports/2022%20Shopping%20Apps%20Report/2022%20Mobile%20Shopping%20Apps%20Report%20-%20EN%20(1).pdf | 2019–2022 | low (dated) |
| $12.64 CPA; 18.5% conv. | USD / % | Cost per purchase and purchase conversion (Liftoff 2022 shopping report) | Liftoff 2022 PDF above | 2021–22 | low (dated) |

**PRIORs for a P2P resale marketplace**
- **First purchase:** 5–12% of installers buy within 30 days. Liftoff's 4.7–10.5% install-to-purchase range is the anchor; P2P resale needs a matching listing, so use the lower half in a thin new market.
- **First listing:** 8–15% of installers list within 30 days. This draws on Poshmark's buyer/seller overlap in Part 3.
- **Retention:** D1 20–25%, D7 10–12%, D30 4–7%. This sits between Adjust's marketplace D1 and the all-vertical curve.

### B. Ride-hailing (riders and drivers)

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| CR 50.5%; TTR 4.7% | % | **US** Apple Ads Travel category (Uber and Lyft are in Travel) | https://www.apptweak.com/en/aso-blog/apple-ads-benchmarks?currency=us | 2025 | medium |
| 16.5% | % | Travel product-page conversion (Adjust blog, year unclear) | https://www.adjust.com/blog/how-to-improve-mobile-conversion-rates-ecommerce-apps/ | undated | low |
| D1 18%, D30 2.8% | % | Travel apps retention (Business of Apps Travel App Report; travel, not rideshare-specific) | https://www.businessofapps.com/?p=97743 (via search snippet; page returned 403) | 2025 | low |
| 189M MAPCs; 3.512B trips/quarter (≈6.2 trips per MAPC per month) | count | Uber global platform (mobility + delivery). The per-month ratio is my arithmetic | https://investor.uber.com/news-events/news/press-release-details/2025/Uber-Announces-Results-for-Third-Quarter-2025/default.aspx | Q3 2025 | high |
| 68.1% (men 65.0%, women 76.5%) | % | **Driver** 6-month attrition: share of US UberX/POOL drivers not active 26 weeks after first trip (n≈1.87M drivers) | https://www.nber.org/papers/w24732.pdf (Cook, Diamond, Hall, List, Oyer; Table 1) | first trips Jan 2015–Mar 2016 | high (but dated) |
| ~11% | % | Driver sign-ups completing a first trip (Uber data-science take-home dataset; **synthetic**, Jan 2015 cohort) | https://www.interviewquery.com/takehomes/uber-data-challenge ; https://devpost.com/software/the-missed-ride-why-uber-drivers-skip-their-first-trip | 2015 | low |
| >10% fail | % applicants | Massachusetts state background-check rejection of Uber/Lyft applicants (8,200+ of ~70k) | https://www.cbsnews.com/boston/news/uber-lyft-background-checks-fail-massachusetts | 2017 | medium |

**PRIORs for ride-hailing**
- **Rider first ride:** 25–45% of rider installers take a first ride within 30 days, if supply exists. Installs here are intent-driven (people often install at the moment of need), and Lyft's referral rules use a 30-day first-ride window.
- **Rider retention:** D30 retention ≈ 5–10%.
- **Driver funnel:** 10–30% of driver sign-ups complete a first trip. The ~11% synthetic figure is the floor; the range accounts for background-check loss.
- **Driver churn:** 60–70% of drivers inactive by 6 months (NBER).

### C. Sign-up completion (install -> finished sign-up), all three markets

Added 2026-11-03 for the v2 `signup` calibration target (the `sign_up` decision right after install).
Only runs with a brief use it.

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| ~50% average (iOS over 79%) | % installs | Dating apps install-to-registration, from paid installs (Liftoff 2022 Dating Apps Report) | https://content.liftoff.io/hubfs/aaa_Reports/2022/2022%20Dating%20Apps%20Report%20-%20EN.pdf | 2021–2022 | medium |
| 39.9% (Q1), 39.8% (Q2) | % installs | Dating apps install-to-registration (Liftoff, quoted by a trade site) | https://www.globaldatinginsights.com/news/28072015-what-is-the-cost-of-acquiring-dating-app-users-in-2015/ | 2015 | low |
| 45.8% | % installs | US shopping apps install-to-register (Adjust data, Statista chart) | https://www.statista.com/statistics/1021327/mobile-shopping-app-user-acquisition-rate-usa | 2020 | medium |
| social 88.4%, eCommerce 70.6%, finance 52.1% | % installs | Install-to-registration by category, paid installs (Liftoff Mobile App Engagement Index) | https://liftoff.io/?p=2828 | Q4 2014 | low (old) |
| ~20% within week one | % installs | Fintech apps install-to-sign-up (CleverTap fintech benchmark) | https://financialit.net/news/fintech-startups/clevertaps-fintech-benchmark-report-only-1-5-users-install-fintech-apps-sign | 2022–2023 | medium |

- **Dating (Kindred):** 0.50, Liftoff 2022.
- **Resale (Reloop):** 0.46, the US shopping figure; a resale app asks for the same things (email or phone, location).
- **Rides (Hopway):** PRIOR 40–70%, point 0.55. No public ride-hailing number. A ride app asks for a phone number
  and usually a payment card before the first ride, so it sits between the finance and eCommerce figures above.

---

## Part 3: Mechanics priors

### Ride-hailing

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| ~15 min | ETA (minutes) | "Once the ETA for the nearest car reaches ~15 minutes, people give up trying to get a ride" (SF) | https://www.uber.com/us/en/newsroom/uber-expectations-as-we-grow/ | H1 2014 | medium (company blog, old) |
| Peaks at 2 min, then decays exponentially | completion vs ETA | Completed-trip probability vs shown ETA. In some cities demand drops beyond 2–3 min; in others ≤10 min is acceptable | same | H1 2014 | medium |
| >97% of completed trips under 10 min | % | SF pickup ETA distribution in a mature market | same | 2014 | medium |
| <6 min avg (Uber/Lyft) vs 24 min (taxi) | minutes wait | LA audit, 1,700+ hailed rides; 20% of taxi requests never picked up | https://escholarship.org/uc/item/3k9018wk (Brown, UCLA ITS brief) | Oct–Dec 2017 | high |
| 99.7% | % | Ride-hail riders who reached their destination even after a driver cancel (LA) | same | 2017 | high |
| 2 min | minutes | Uber's free rider-cancel window; Uber said 2 minutes is usually enough for riders to decide | https://techcrunch.com/2016/04/26/no-you-cant-go-to-the-bathroom-first | 2016 | medium |
| 41% (2014) → 18% (2015) | % requests | Ride-hailing requests unfulfilled in New York (quoted in a PLoS ONE paper; the 18% is cited to a trade blog) | https://pmc.ncbi.nlm.nih.gov/articles/PMC5993247 | 2014–2015 | low-medium |
| >40% | % requests | Didi Shanghai requests receiving no driver response on one day | same (cites Economic Information Daily) | Jan 2017 | low |
| ~1 min faster YoY; ETAs >10% faster YoY | qualitative | Lyft management: fastest ETAs in 4 years (no absolute minutes disclosed) | https://www.fool.com/earnings/call-transcripts/2025/02/11/lyft-lyft-q4-2024-earnings-call-transcript/ | Q2 & Q4 2024 | medium (company claim) |

**PRIORs**
- **Rider patience after matching:** cancel probability rises sharply after 5–8 min of waiting; hard abandon at about 15 min (Uber's ETA give-up point).
- **Launch market:** average ETA 8–15 min.
- **Mature market:** 3–6 min (LA <6 min in 2017; SF 97% <10 min in 2014).
- **Unfulfilled requests in a new market:** 20–40%, falling below 5–10% as supply densifies. Anchors are NYC's 41% → 18% and Didi Shanghai's >40% at peak.

### Resale marketplaces

| Value | Unit | What it measures | Source | Period | Conf. |
|---|---|---|---|---|---|
| 34% | % of buyers | Poshmark: buyers activated 2012–2018 who also activated as sellers by YE2019 | https://www.sec.gov/Archives/edgar/data/1825480/000119312520320132/d66583ds1.htm (S-1) | cohorts 2012–2018, as of end 2019 | high |
| 39% | % of sellers | Poshmark: sellers activated 2012–2018 who also activated as buyers by YE2019 | same | same | high |
| 48% | % of sellers | Poshmark sellers who spent part of their earnings on the marketplace in the same year | same | 2019 | high |
| 6.2M buyers / 4.5M sellers / 31.7M active users | count | Poshmark: active buyers per active seller ≈ 1.4 | same | TTM to 2020-09-30 | high |
| 12.2% in 30 days; 5.8% in 7 days | % listings sold | eBay sell-through, 33,638 listings from one tool's sellers (median 7.5 days to sale among sold items) | https://flowlister.com/infographics/ | published Oct 2026 | low (single vendor) |
| eBay 18–30%; Poshmark 15–25%; Mercari 12–22% | % listings sold in 30 days | Cross-listing vendor estimate table | https://closo.co/blogs/inventory-logistics-management/sell-through | Sep 2026 | low |

**PRIORs**
- **Sell-through:** 15–25% of listings sell within 30 days on a healthy P2P marketplace, and 5–12% in a new, thin local market. The thin-market range uses eBay's 12.2% as a broad-reach floor and assumes less buyer reach.
- **Buyers who also list:** 10–20% within the first 30 days, rising toward the 34% lifetime cohort share.
