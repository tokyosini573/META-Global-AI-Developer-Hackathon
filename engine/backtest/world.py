"""A general two-sided launch world for backtest cases.

Same mechanics as the demo engine, from the frozen rule cards, without dating-specific
screens: people are reached by the launch, join or not, find the other side nearby
(local_density_threshold, exposure_throughput), pay per use or by subscription
(monetization_timing, subsidy_dependent_demand), stay or leave each week, and invite
friends after a success (wom_growth_rate_band). Daily for 90 days, weekly after that.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from engine.world import geo

from .decide import TYPES

RULES = {                 # points inside the frozen ranges (rules/two_sided.md)
    "lambda_km": 5,       # local_density_threshold [1, 10]
    "q": 0.045,           # exposure_throughput q_e_curated [0.03, 0.06] (dating: q_e_swipe below)
    "q_dating": 0.012,    # exposure_throughput q_e_swipe [0.01, 0.014]
    "cap": 20,            # exposure_throughput E_cap_swipe [20, 200], low end
    "wom_q_daily": 0.015,  # wom_growth_rate_band [0.008, 0.026]
}
# Method v2 (backtest/protocol_v2.md): each Monte Carlo run draws its own rule values from the
# frozen ranges instead of using the points above, so the spread of outcomes includes how
# unsure the rules are, not only random arrivals. (low, high, log scale?)
RANGES = {
    "lambda_km": (1, 10, True),
    "q": (0.03, 0.06, False),
    "q_dating": (0.01, 0.014, False),
    "cap": (20, 200, True),
    "wom_q_daily": (0.008, 0.026, False),
}
REACH_FACTOR = (0.5, 2.0)  # reach_per_month is a guess in every case: one shared factor per run
NEED_PER_WEEK = 1.0       # prior: how often a demand-side person needs the service
SAMPLE_TARGET = 1500      # simulated people per variant over the whole run
CITY_SPREAD_KM = 8
JP_METROS = [("Tokyo", 139.69, 35.69, 37), ("Osaka", 135.50, 34.69, 19), ("Nagoya", 136.91, 35.18, 9),
             ("Fukuoka", 130.40, 33.59, 5), ("Sapporo", 141.35, 43.06, 4), ("Sendai", 140.87, 38.27, 2),
             ("Hiroshima", 132.46, 34.39, 2)]
JP_SMALL_TOWN_SHARE = 0.3
JP_AREA_KM2 = 3.78e5
# Market size M in wom_growth_rate_band, dN/dt = (p + q N/M)(M - N). v1 left the (M - N) term out,
# so word of mouth could grow without bound. M is the adult population the launch can reach:
# the whole country when nationwide, else the metros of the open cities (rough metro weights).
ADULTS = {"us": 258e6, "jp": 105e6}


def sample_params(seed):
    """Rule values for one v2 run. Seeded apart from the world so both variants of a case share them."""
    r = np.random.default_rng([seed, 7])
    out = {}
    for k, (lo, hi, log) in RANGES.items():
        out[k] = float(math.exp(r.uniform(math.log(lo), math.log(hi)))) if log else float(r.uniform(lo, hi))
    lo, hi = REACH_FACTOR
    out["reach_factor"] = float(math.exp(r.uniform(math.log(lo), math.log(hi))))
    return out


def market_size(v, t):
    if v.get("nationwide") or not v.get("cities"):
        return ADULTS[v["market"]]
    metros = geo.METROS if v["market"] == "us" else JP_METROS
    towns = geo.SMALL_TOWN_SHARE if v["market"] == "us" else JP_SMALL_TOWN_SHARE
    total = sum(m[3] for m in metros)
    size = 0.0
    for c in v["cities"]:
        if c["open_month"] * 30 <= max(t, 0):
            near = min(metros, key=lambda m: (m[1] - c["lon"]) ** 2 + (m[2] - c["lat"]) ** 2)
            size += near[3] / total * (1 - towns) * ADULTS[v["market"]]
    return size or ADULTS[v["market"]]


def nearby_bucket(n):
    return "none" if n < 5 else "few" if n < 50 else "many"


@dataclass
class P:
    side: str
    type: str
    lon: float
    lat: float
    source: tuple
    joined: float
    quit: float | None = None
    successes: list = field(default_factory=list)
    buys: int = 0
    paid_weeks: int = 0


def _nation(rng, market):
    if market == "us":
        _, lon, lat, _ = geo.nationwide(rng)
        return lon, lat
    if rng.random() < JP_SMALL_TOWN_SHARE:
        m = JP_METROS[rng.integers(len(JP_METROS))]
        return m[1] + rng.normal(0, 0.7), m[2] + rng.normal(0, 0.6)
    w = np.array([m[3] for m in JP_METROS], float)
    m = JP_METROS[rng.choice(len(JP_METROS), p=w / w.sum())]
    return m[1] + rng.normal(0, 0.23), m[2] + rng.normal(0, 0.18)


def _nation_density(lon, lat, lam, market):
    if market == "us":
        return geo.nationwide_density(lon, lat, lam)
    w = np.array([m[3] for m in JP_METROS], float)
    w /= w.sum()
    d = geo.distance_km(lon, lat, np.array([m[1] for m in JP_METROS]), np.array([m[2] for m in JP_METROS]))
    metro = (geo._blob(d, geo.METRO_SPREAD_KM, lam) * w[None, :]).sum(axis=1)
    return (1 - JP_SMALL_TOWN_SHARE) * metro + JP_SMALL_TOWN_SHARE * 2 * np.pi * lam ** 2 / JP_AREA_KM2


def people_per_dot(case):
    reach = max(v["reach_per_month"] for v in case["variants"].values())
    return max(1.0, reach * case["months"] / SAMPLE_TARGET)


class World:
    def __init__(self, case, variant, decisions, seed, params=None):
        self.case = case
        self.rules = {**RULES, "reach_factor": 1.0, **(params or {})}
        self.vkey = variant
        self.v = case["variants"][variant]
        self.dec = decisions
        self.rng = np.random.default_rng(seed)
        self.w = people_per_dot(case)
        self.days = case["months"] * 30
        self.sym = bool(case["sides"].get("symmetric"))
        self.people = []
        self.reached = 0.0         # real people the launch or a friend has reached so far
        self.monthly = {}          # month -> {"transactions": n, "revenue": usd, "promo": usd}

    def key(self, p, decision, situation):
        return (self.case["id"], self.vkey, p.type, p.side, decision, situation)

    def roll(self, p, decision, situation):
        probs = self.dec.get(self.key(p, decision, situation))
        return probs[next(iter(probs))]   # probability of the first (active) option

    def _arrive(self, t, dt, invites):
        v, r = self.v, self.rng
        room = max(0.0, 1 - self.reached / market_size(v, t))     # (M - N) / M
        invites = [x for x in invites if r.random() < room]
        n = r.poisson(room * v["reach_per_month"] * self.rules["reach_factor"] * dt / 30 / self.w)
        spots = []
        open_cities = [c for c in v.get("cities") or [] if c["open_month"] * 30 <= t]
        for _ in range(n):
            if v.get("nationwide") or not open_cities:
                spots.append((*_nation(r, v["market"]), ("nation", v["market"])))
            else:
                c = open_cities[r.integers(len(open_cities))]   # expansion_pace_dilution
                spots.append((*geo.near(r, c["lon"], c["lat"], CITY_SPREAD_KM),
                              ("city", c["lon"], c["lat"], CITY_SPREAD_KM)))
        spots += invites
        self.reached += self.w * len(spots)
        share = self.case["sides"]["demand"]["share"]
        types = list(TYPES)
        for lon, lat, source in spots:
            p = P(side="demand" if r.random() < share else "supply", type=types[r.integers(len(types))],
                  lon=float(lon), lat=float(lat), source=source, joined=-1)
            if r.random() < self.roll(p, "join", "-"):
                p.joined = t + float(r.random()) * dt
                self.people.append(p)

    def _nearby(self, active, lon, lat, side):
        lam = self.rules["lambda_km"]
        out = np.zeros(len(active))
        for s in ("demand", "supply"):
            mine = side == s
            others = [p for p in active if p.side != s]
            if not mine.any() or not others:
                continue
            groups = {}
            for p in others:
                groups[p.source] = groups.get(p.source, 0) + 1
            for src, n in groups.items():
                if src[0] == "nation":
                    out[mine] += n * _nation_density(lon[mine], lat[mine], lam, src[1])
                else:
                    out[mine] += n * geo.city_density(lon[mine], lat[mine], src[1], src[2], src[3], lam)
        return self.w * out

    def step(self, t, dt):
        r, v = self.rng, self.v
        month = int(t // 30)
        m = self.monthly.setdefault(month, {"transactions": 0.0, "revenue": 0.0, "promo": 0.0})
        active = [p for p in self.people if p.joined <= t and p.quit is None]

        invites = []
        rate = self.rules["wom_q_daily"] / 0.3 * dt
        for p in active:
            if any(t - d < 30 for d in p.successes):
                for _ in range(r.poisson(rate)):
                    invites.append((*geo.near(r, p.lon, p.lat, 3), p.source))
        self._arrive(t, dt, invites)
        active = [p for p in self.people if p.joined < t + dt and p.quit is None]
        if not active:
            return
        lon = np.array([p.lon for p in active])
        lat = np.array([p.lat for p in active])
        side = np.array([p.side for p in active])
        nearby = self._nearby(active, lon, lat, side)
        q = self.rules["q_dating"] if self.sym else self.rules["q"]
        price = v.get("transaction_price_usd", 0)
        take = v["price"].get("take_rate", 0) if v["price"]["model"] == "take_rate" else 0
        disc = v.get("first_transaction_discount", 0)
        per_day = 1.0 if self.sym else NEED_PER_WEEK / 7

        for i, p in enumerate(active):
            buyer = self.sym or p.side == "demand"
            p_found = 1 - (1 - q) ** min(self.rules["cap"], nearby[i])
            if r.random() < 1 - (1 - per_day * p_found) ** dt:
                if not buyer:
                    p.successes.append(t + float(r.random()) * dt)   # supply side: got work or a match
                else:
                    go = True
                    if take or price:
                        first = "first" if p.buys == 0 else "again"
                        worked = "yes" if p.successes else "no"
                        go = r.random() < self.roll(p, "buy", (first, worked if first == "again" else "-"))
                    if go:
                        p.successes.append(t + float(r.random()) * dt)
                        p.buys += 1
                        m["transactions"] += self.w
                        if take:
                            m["revenue"] += self.w * take * price
                            if p.buys == 1 and disc:
                                m["promo"] += self.w * disc * price

            worked = "yes" if p.successes else "no"
            b = nearby_bucket(nearby[i])
            if v["price"]["model"] == "subscription" and v["price"].get("free_tier", True) and \
                    (self.sym or p.side == "demand"):
                if r.random() < 1 - (1 - self.roll(p, "pay", (worked, b))) ** (dt / 7):
                    p.paid_weeks += dt / 7
                    m["revenue"] += self.w * v["price"].get("subscription_usd_week", 0) * dt / 7
            elif v["price"]["model"] == "subscription" and not v["price"].get("free_tier", True) and \
                    (self.sym or p.side == "demand"):
                m["revenue"] += self.w * v["price"].get("subscription_usd_week", 0) * dt / 7
            stop_week = 1 - self.roll(p, "stay", (worked, b))
            if r.random() < 1 - (1 - stop_week) ** (dt / 7):
                p.quit = t + float(r.random()) * dt

    def run(self):
        t = 0.0
        while t < self.days:
            dt = 1.0 if t < 90 else 7.0
            self.step(t, dt)
            t += dt
        return self

    # ---- metrics ------------------------------------------------------------

    def metric(self, name, month):
        end = (month + 1) * 30
        if name == "active_users":
            return self.w * sum(p.joined <= end and (p.quit is None or p.quit > end) for p in self.people)
        if name == "transactions":
            return self.monthly.get(month, {}).get("transactions", 0.0)
        if name == "users_with_success":
            return self.w * sum(any(d <= end for d in p.successes) for p in self.people)
        if name == "repeat_share":
            buyers = [p for p in self.people if p.side == "demand" and any(d <= end for d in p.successes)]
            return sum(sum(d <= end for d in p.successes) >= 2 for p in buyers) / len(buyers) if buyers else 0.0
        if name == "contribution":
            return sum(m["revenue"] - m["promo"] for k, m in self.monthly.items() if k <= month)
        raise ValueError(name)


def decision_keys(case):
    """Every decision key a run of this case can ask, for prefilling the table."""
    sym = bool(case["sides"].get("symmetric"))
    for vk, v in case["variants"].items():
        for t in TYPES:
            for side in ("demand", "supply"):
                yield (case["id"], vk, t, side, "join", "-")
                for worked in ("yes", "no"):
                    for b in ("none", "few", "many"):
                        yield (case["id"], vk, t, side, "stay", (worked, b))
                        if v["price"]["model"] == "subscription" and v["price"].get("free_tier", True) and \
                                (sym or side == "demand"):
                            yield (case["id"], vk, t, side, "pay", (worked, b))
                if (v["price"]["model"] == "take_rate" or v.get("transaction_price_usd")) and (sym or side == "demand"):
                    yield (case["id"], vk, t, side, "buy", ("first", "-"))
                    for worked in ("yes", "no"):
                        yield (case["id"], vk, t, side, "buy", ("again", worked))
