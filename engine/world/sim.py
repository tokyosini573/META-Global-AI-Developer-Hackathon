"""One plan, one market, day by day.

Each day: new people are reached (paid channels, referrals and word of mouth), they decide
whether to install, active users meet the other side nearby (spatial kernel), they make the
decision their market pack gives them (a paywall for dating; offer or ask for the others), and
some quit. Mechanics follow rules/two_sided.md; choices come from a DecisionCache; benchmark
levels come from calibration shifts.

Two ways a success happens (engine/packs): "swipe", where both sides browse each other and match;
and "transaction", where one side offers (lists an item, goes online to drive) and the other asks
(buys, requests a ride), and a success needs an offer nearby on the day someone asks.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from engine import packs

from . import channels, geo
from .calibrate import logit, shift, shift_options, sigma
from .decide import TYPES, week_bucket, nearby_bucket

FIRST_NAMES = ["Maya", "Jordan", "Sam", "Alex", "Riley", "Taylor", "Chris", "Jamie", "Morgan", "Casey", "Avery",
               "Drew", "Priya", "Luis", "Ana", "Marcus", "Jasmine", "Tyler", "Nina", "Omar", "Grace", "Ethan",
               "Leah", "Kevin"]
P_FRIEND_INSTALL = 0.3   # prior used to turn the word-of-mouth growth rate into invites per day
MATCH_MEMORY_DAYS = 30   # wom_growth_rate_band: only recent matches spread the word


@dataclass
class Person:
    id: int
    type: str
    side: str            # one of the pack's two sides; each side looks for the other
    channel: str
    place: str
    lon: float
    lat: float
    spread_km: float     # how far the real people this person stands for are spread
    source: tuple        # where the real people behind this person live: ("nation",) or ("city", lon, lat, km)
    reached: float
    name: str
    age: int
    persona: str | None = None   # pool person id when decisions are per person (Glimmer)
    installed: float | None = None
    matched: float | None = None
    quit: float | None = None
    paid: float | None = None
    match_days: list = field(default_factory=list)
    offer_until: float = -1.0    # transaction packs: the offer (listing, driving shift) stays up until this day


@dataclass
class Result:
    plan: str
    people: list
    matches: list        # [person id, person id, day] for drawing lines
    decisions: list      # (day, person id, kind, screen, bucket, probs, chosen)


class Simulation:
    def __init__(self, cfg, plan_key, cache, shifts, seed, days=None):
        self.cfg = cfg
        self.m = cfg["world"]
        self.plan_key = plan_key
        self.plan = cfg["plans"][plan_key]
        self.cache = cache
        self.shifts = shifts
        self.rng = np.random.default_rng(seed)
        self.days = days or cfg["days"]
        self.w = cfg["people_per_dot"]
        self.pack = packs.of(cfg)
        self.sides = packs.side_shares(self.pack, cfg)
        self.costs = channels.costs()
        self.budget = self.plan.get("budget_usd", cfg["budget_usd"])
        self.referral_left = 0.0  # today's referral budget not yet paid out
        self.per_person = getattr(cache.provider, "per_person", False)
        self.taken = set()        # pool people already in this run
        self.types = getattr(cache.provider, "types", TYPES)   # Wonder's types for Glimmer, else the placeholders
        self.people = []
        self.matches = []
        self.decisions = []

    # ---- reach -------------------------------------------------------------

    def _new_person(self, t, channel, place, lon, lat, spread_km, source, side=None):
        r = self.rng
        (a, share), (b, _) = self.sides
        if any("side" in x for x in self.types):      # each side has its own kinds of people
            side = side or (a if r.random() < share else b)
            types = [x for x in self.types if x["side"] == side]
            tp = types[r.choice(len(types), p=np.array([x["weight"] for x in types]) / sum(x["weight"] for x in types))]
        else:
            tp = self.types[r.choice(len(self.types), p=np.array([x["weight"] for x in self.types]))]
            side = side or (a if r.random() < share else b)
        p = Person(id=len(self.people), type=tp["id"], side=side,
                   channel=channel, place=place, lon=float(lon), lat=float(lat), spread_km=float(spread_km), source=source,
                   reached=t + float(r.random()),
                   name=str(r.choice(FIRST_NAMES)), age=int(r.integers(tp["age"][0], tp["age"][1] + 1)))
        if self.per_person:
            # one of the people who live in this place, of this type and side, makes every decision
            p.persona = self.cache.provider.persona(r, place, p.type, p.side, self.taken)
            self.taken.add(p.persona)
            who = self.cache.provider.pool[p.persona]
            p.name, p.age = who["name"], who["age"]
        self.people.append(p)
        return p

    def _paid_arrivals(self, t):
        """Expected simulated people reached today by each paid channel, rolled with Poisson."""
        out = []
        self.referral_left = 0.0
        for ch in self.plan["channels"]:
            if not ch["start_day"] <= t < ch["end_day"]:
                continue
            spend = self.budget * ch["budget_share"] / (ch["end_day"] - ch["start_day"])
            if ch["kind"] == "referral":       # paid per friend who installs, in _word_of_mouth
                self.referral_left += spend
                continue
            open_cities = [c for c in self.plan.get("cities", []) if c["open_day"] <= t]
            if ch["where"] == "nationwide":
                open_cities = []
            elif ch["kind"] == "event" and not open_cities:
                raise ValueError("offline promotion needs cities")
            real = channels.real_reached(ch["kind"], spend, self.costs[ch["kind"]], open_cities)
            n = self.rng.poisson(real / self.w)
            side = ch.get("side")
            if ch["where"] == "nationwide":
                spots = [(*geo.nationwide(self.rng), ("nation",)) for _ in range(n)]
            else:
                # expansion_pace_dilution: the spend is split across the cities open today
                open_cities = [c for c in self.plan["cities"] if c["open_day"] <= t]
                spots = []
                for _ in range(n):
                    c = open_cities[self.rng.integers(len(open_cities))]
                    spots.append((c["name"], *geo.near(self.rng, c["lon"], c["lat"], geo.CITY_SPREAD_KM),
                                  geo.CITY_SPREAD_KM, ("city", c["lon"], c["lat"], geo.CITY_SPREAD_KM)))
            out += [(ch["kind"], *s, side) for s in spots]
        return out

    def _word_of_mouth(self, t, active):
        """wom_growth_rate_band: people with a recent match invite friends nearby. A referral program
        adds paid invites from everyone using the app, while today's referral budget lasts."""
        rate = self.m["wom_q_daily"] / P_FRIEND_INSTALL
        out = []
        for p in active:
            if self.m["wom_only_after_match"] and not any(t - d < MATCH_MEMORY_DAYS for d in p.match_days):
                continue
            for _ in range(self.rng.poisson(rate)):
                # friends live near the people who invite them, spread like them
                out.append(("friend", p.place, *geo.near(self.rng, p.lon, p.lat, 3), p.spread_km, p.source, None))
        if self.referral_left > 0:
            ref = self.costs["referral"]["invites_per_user_day"]
            for p in active:
                for _ in range(self.rng.poisson(ref)):
                    out.append(("referral", p.place, *geo.near(self.rng, p.lon, p.lat, 3), p.spread_km, p.source, None))
        return out

    # ---- decisions ---------------------------------------------------------

    def _decide(self, t, p, kind, screen, bucket, option_shifts, residual):
        probs = shift_options(self.cache.get(kind, p.persona or p.type, screen, bucket), option_shifts, residual)
        options = list(probs)
        chosen = options[self.rng.choice(len(options), p=np.array([probs[o] for o in options]) / sum(probs.values()))]
        self.decisions.append((t, p.id, kind, screen, bucket, probs, chosen))
        return chosen

    def _quit_risk(self, t, p):
        """Daily risk that an active free user stops using the app."""
        c = self.m["churn_curve"]
        since = t - math.floor(p.installed)
        h = c["floor"] + (c["first_day"] - c["floor"]) * math.exp(-since / c["tau_days"])
        x = logit(h) - self.shifts.get("d7_retention", 0.0)
        if not p.match_days and since > self.m["t_wait_days"]:
            x += math.log(1 + self.m["gamma_no_match"])          # local_density_threshold
        recent = sum(t - d < MATCH_MEMORY_DAYS for d in p.match_days)
        x -= self.m["beta_per_match"] * recent                     # novelty_installs_without_repeat_loop
        return sigma(x)

    def _nearby(self, active, lon, lat, side):
        """local_density_threshold: real active people of the other side within reach of each person.

        Each simulated person stands for `people_per_dot` real people drawn from the same
        place distribution as them (all metros for a nationwide ad, one city for a city
        launch), so the count is taken against those distributions, not the few sample points.
        """
        out = np.zeros(len(active))
        for s, _ in self.sides:
            others = [p for p in active if p.side != s]
            mine = side == s
            if not others or not mine.any():
                continue
            out[mine] += self._density(others, lon[mine], lat[mine])
        return self.w * out

    def _density(self, others, lon, lat):
        """Expected kernel weight at (lon, lat) from the real people behind `others`."""
        lam = self.m["lambda_km"]
        out = np.zeros(len(lon))
        n_nation = sum(p.source[0] == "nation" for p in others)
        if n_nation:
            out += n_nation * geo.nationwide_density(lon, lat, lam)
        cities = {}
        for p in others:
            if p.source[0] == "city":
                cities[p.source] = cities.get(p.source, 0) + 1
        for (_, clon, clat, km), n in cities.items():
            out += n * geo.city_density(lon, lat, clon, clat, km, lam)
        return out

    # ---- one day -----------------------------------------------------------

    def step(self, t):
        r = self.rng
        active = [p for p in self.people if p.installed is not None and p.installed < t + 1 and p.quit is None]

        for kind, place, lon, lat, spread, source, side in self._paid_arrivals(t) + self._word_of_mouth(t, active):
            if kind == "referral" and self.referral_left <= 0:
                continue
            p = self._new_person(t, kind, place, lon, lat, spread, source, side)
            screen = self.pack["channel_context"][kind]
            if self._decide(t, p, "install", screen, "-", {"install": self.shifts.get("install", 0.0)}, "scroll_past") == "install":
                p.installed = p.reached + float(r.uniform(0, min(0.3, t + 1 - p.reached)))
                active.append(p)
                if kind == "referral":
                    self.referral_left -= self.w * self.costs["referral"]["usd_per_install"]
        if not active:
            return
        if self.pack["mechanics"] == "transaction":
            return self._transactions(t, active)

        # local_density_threshold + exposure_throughput
        lon = np.array([p.lon for p in active])
        lat = np.array([p.lat for p in active])
        side = np.array([p.side for p in active])
        spread = np.array([p.spread_km for p in active])
        kern = geo.density_kernel(geo.distance_km(lon, lat, lon, lat), spread, spread, self.m["lambda_km"])
        np.fill_diagonal(kern, 0)
        other = side[:, None] != side[None, :]
        nearby = self._nearby(active, lon, lat, side)

        trial_days = self.plan["trial_days"]
        for i, p in enumerate(active):
            in_trial = trial_days > 0 and t - p.installed < trial_days
            unlimited = p.paid is not None or in_trial
            cap = self.plan["unlimited_swipes_per_day"] if unlimited else self.plan["free_swipes_per_day"]
            exposures = min(cap, nearby[i])
            if r.random() < 1 - (1 - self.m["match_per_exposure"]) ** exposures:
                day = t + float(r.random())
                p.match_days.append(day)
                p.matched = p.matched if p.matched is not None else day
                weights = kern[i] * other[i]
                if weights.sum() > 1e-3:
                    j = active[r.choice(len(active), p=weights / weights.sum())]
                    self.matches.append([p.id, j.id, round(day, 2)])

            if unlimited:
                continue
            bucket = ("yes" if p.match_days else "no", nearby_bucket(nearby[i]), week_bucket(t - p.installed))
            # The retention shift also moves "delete": quitting at the paywall is quitting too.
            chosen = self._decide(t, p, "paywall", "paywall", bucket, {"pay": self.shifts.get("paid_30d", 0.0),
                                                                       "delete_app": -self.shifts.get("d7_retention", 0.0)},
                                  "come_back_tomorrow")
            if chosen == "pay":
                p.paid = t + float(r.random())
            elif chosen == "delete_app":
                p.quit = t + float(r.random())
            elif r.random() < self._quit_risk(t, p):
                p.quit = t + float(r.random())

        for p in active:
            in_trial = trial_days > 0 and t - p.installed < trial_days
            if p.paid is None and p.quit is None and in_trial and r.random() < self._quit_risk(t, p):
                p.quit = t + float(r.random())

    def _gate(self, t, p, nearby):
        """The pack's daily decision for someone using the app (transaction packs)."""
        kind = self.pack["gates"][p.side]
        g = self.pack["gate"][kind]
        bucket = ("yes" if p.match_days else "no", nearby_bucket(nearby), week_bucket(t - p.installed))
        return self._decide(t, p, kind, kind, bucket,
                            {g["act"]: self.shifts.get(self.pack["convert_target"], 0.0),
                             "delete_app": -self.shifts.get("d7_retention", 0.0)}, "come_back_tomorrow"), g

    def _transactions(self, t, active):
        """One side offers, the other asks; a success needs an offer nearby on the day someone asks.

        Offers are decided first (seeing how many people nearby are asking), then asks (seeing how many
        offers are up nearby). Each ask succeeds with 1 - (1 - q)^n for n offers within reach
        (local_density_threshold, exposure_throughput); an item sold is gone, a driver can drive again.
        """
        r = self.rng
        pk = self.pack
        supply = [p for p in active if p.side == pk["supply"]]
        demand = [p for p in active if p.side == pk["demand"]]

        def place(ps):
            return np.array([p.lon for p in ps]), np.array([p.lat for p in ps])

        if supply:
            near = self.w * self._density(demand, *place(supply)) if demand else np.zeros(len(supply))
            for i, p in enumerate(supply):
                chosen, g = self._gate(t, p, near[i])
                if chosen == g["act"]:
                    p.offer_until = t + pk["offer_days"]
                elif chosen == "delete_app":
                    p.quit = t + float(r.random())
                elif r.random() < self._quit_risk(t, p):
                    p.quit = t + float(r.random())
        offers = [p for p in supply if p.quit is None and p.offer_until >= t]
        if not demand:
            return
        lon, lat = place(demand)
        near = self.w * self._density(offers, lon, lat) if offers else np.zeros(len(demand))
        q = self.m["success_per_offer"]
        for i, p in enumerate(demand):
            chosen, g = self._gate(t, p, near[i])
            if chosen == g["act"]:
                if offers and r.random() < 1 - (1 - q) ** near[i]:
                    olon, olat = place(offers)
                    sk = np.array([p.spread_km] * len(offers))
                    weights = geo.density_kernel(geo.distance_km(np.array([p.lon]), np.array([p.lat]), olon, olat),
                                                 sk[:1], np.array([o.spread_km for o in offers]), self.m["lambda_km"])[0]
                    j = offers[r.choice(len(offers), p=weights / weights.sum())] if weights.sum() > 1e-9 else \
                        offers[r.integers(len(offers))]
                    day = t + float(r.random())
                    for x in (p, j):
                        x.match_days.append(day)
                        x.matched = x.matched if x.matched is not None else day
                        x.paid = x.paid if x.paid is not None else day
                    self.matches.append([p.id, j.id, round(day, 2)])
                    if pk["offer_used_up"]:
                        j.offer_until = -1.0
                        offers.remove(j)
            elif chosen == "delete_app":
                p.quit = t + float(r.random())
            elif r.random() < self._quit_risk(t, p):
                p.quit = t + float(r.random())

    def run(self):
        for t in range(self.days):
            self.step(t)
        return Result(self.plan_key, self.people, self.matches, self.decisions)


# ---- measures used by calibration and the verdict ---------------------------

def measures(result, days, pack=None):
    """Calibration measures. Dating counts paying users; transaction packs count people on the asking
    side who complete a first transaction (convert_30d)."""
    pack = pack or packs.load("dating")
    ppl = result.people
    if pack["mechanics"] == "transaction":
        ppl = [p for p in ppl if p.side == pack["demand"]]
    reached = [p for p in ppl if p.reached <= days]
    inst = [p for p in reached if p.installed is not None]

    def share(pool, ok):
        return sum(ok(p) for p in pool) / len(pool) if pool else None

    d7_pool = [p for p in inst if p.installed <= days - 7]
    paid_pool = [p for p in inst if p.installed <= days - 30]
    return {
        "install": share(reached, lambda p: p.installed is not None),
        "d7_retention": share(d7_pool, lambda p: p.quit is None or p.quit > p.installed + 7),
        pack["convert_target"]: share(paid_pool, lambda p: p.paid is not None and p.paid <= p.installed + 30),
    }


def totals(result, days, w, pack=None):
    pack = pack or packs.load("dating")
    inst = [p for p in result.people if p.installed is not None and p.installed <= days]
    week1 = [p for p in inst if p.installed <= days - 7]
    out = {
        "reached": w * sum(p.reached <= days for p in result.people),
        "installed": w * len(inst),
        "matched": w * sum(p.matched is not None and p.matched <= days for p in inst),
        "paying": w * sum(p.paid is not None and p.paid <= days for p in inst),
        "quit_week1": (sum(p.quit is not None and p.quit <= p.installed + 7 for p in week1) / len(week1)) if week1 else None,
    }
    if pack["mechanics"] == "transaction":
        out["transactions"] = w * sum(m[2] <= days for m in result.matches)
    return out
