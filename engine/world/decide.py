"""Decisions people make in front of a screen, and the cache that keeps them cheap.

A decision is asked once per (who, screen, state bucket) and reused by every person and
every Monte Carlo run that lands in the same key. `who` is a person type for the Spark and
stub providers, and one person from the pool for Glimmer (engine/world/glimmer.py). Providers return a
probability for each option; the simulation rolls the dice.

StubProvider is a stand-in with hand-set probabilities anchored on the Spark spike
(engine/spike): far away + no match + paywall -> ~0.8 delete; nearby match -> ~0.2.
The Spark provider replaces it without changing this interface.
"""

from dataclasses import dataclass, field

from .calibrate import logit, sigma

# Person types. To be designed by Muse Wonder per market; this is a fixed placeholder set.
# price: how much a price pushes them away (1 = average). novelty: pull of a new app.
TYPES = [
    {"id": "student", "weight": 0.22, "age": (18, 22), "price": 1.4, "novelty": 1.3},
    {"id": "new_in_town", "weight": 0.16, "age": (23, 30), "price": 1.0, "novelty": 1.1},
    {"id": "busy_professional", "weight": 0.18, "age": (26, 34), "price": 0.7, "novelty": 0.8},
    {"id": "casual_browser", "weight": 0.22, "age": (19, 30), "price": 1.2, "novelty": 1.0},
    {"id": "serious_dater", "weight": 0.12, "age": (25, 34), "price": 0.8, "novelty": 0.7},
    {"id": "app_skeptic", "weight": 0.10, "age": (22, 34), "price": 1.3, "novelty": 0.5},
]
TYPE_BY_ID = {t["id"]: t for t in TYPES}

OPTIONS = {
    "install": ("install", "scroll_past"),
    "paywall": ("pay", "come_back_tomorrow", "delete_app"),
}


def nearby_bucket(n_nearby):
    """How many active people of the other side are within reach, in plain buckets."""
    return "none" if n_nearby < 5 else "few" if n_nearby < 50 else "many"


def week_bucket(days_since_install):
    return "w1" if days_since_install < 7 else "w2-4" if days_since_install < 28 else "w5+"


class StubProvider:
    name = "stub"

    def decide(self, kind, type_id, screen, bucket):
        t = TYPE_BY_ID[type_id]
        if kind == "install":
            base = {"tiktok_ad": 0.10, "ambassador": 0.35, "friend": 0.30}[screen]
            p = sigma(logit(base) + 0.6 * (t["novelty"] - 1))
            return {"install": p, "scroll_past": 1 - p}
        if kind == "paywall":
            matched, nearby, _week = bucket
            d = logit(0.2) + 2.2 * (matched == "no") + {"none": 0.6, "few": 0.3, "many": 0.0}[nearby]
            delete = sigma(d)
            pay = min(0.04 * (1.3 if matched == "yes" else 0.5) / t["price"], 0.5 * (1 - delete))
            return {"pay": pay, "come_back_tomorrow": 1 - delete - pay, "delete_app": delete}
        raise ValueError(kind)


@dataclass
class DecisionCache:
    provider: object
    table: dict = field(default_factory=dict)
    calls: int = 0
    hits: int = 0

    def get(self, kind, who, screen, bucket):
        key = (kind, who, screen, bucket)
        if key in self.table:
            self.hits += 1
        else:
            self.calls += 1
            self.table[key] = self.provider.decide(kind, who, screen, bucket)
        return self.table[key]
