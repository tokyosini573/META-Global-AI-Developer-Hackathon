"""Decisions people make in front of a screen, and the cache that keeps them cheap.

A decision is asked once per (who, screen, state bucket) and reused by every person and
every Monte Carlo run that lands in the same key. `who` is a person type for the Spark and
stub providers, and one person from the pool for Glimmer (engine/world/glimmer.py). Providers return a
probability for each option; the simulation rolls the dice.

StubProvider is a stand-in with hand-set probabilities anchored on the Spark spike
(engine/spike): far away + no match + paywall -> ~0.8 delete; nearby match -> ~0.2.
The Spark provider replaces it without changing this interface.

v2 adds two decisions and the brief's words (docs/brief-format.md): `sign_up` right after install
(finish or delete the app), and `why_quit`, a reason only, asked when someone stops opening the app.
The question texts here are shared by every provider that asks a model (engine/world/typed.py).
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
    "sign_up": ("finish", "delete_app"),
    "why_quit": ("quit",),           # no choice: the answer is the reason
}
ANGLE = {"feature": "what the app does", "price": "the price", "trust": "why you can trust it", "other": "the app"}
METHODS = {"email": "your email", "phone": "your phone number", "apple": "Apple", "google": "Google",
           "facebook": "Facebook"}
PERMISSIONS = {"location": "use your location", "camera": "use your camera", "photos": "see your photos",
               "contacts": "see your contacts", "notifications": "send you notifications"}


def _cut(text, n):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _either(words, last="or"):
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + f" {last} " + words[-1]


def install_question(pack, context, brief=None, ad=None):
    """What a person reached in `context` is asked. With a brief: the ad they saw (its angle and line),
    why the makers say people would pick the app, and what people use now (R3, R4)."""
    q = pack["contexts"][context]
    if not brief:
        return q
    parts = [q.removesuffix("What do you do?").strip()]
    if ad:
        parts.append(f'The ad is about {ANGLE.get(ad.get("angle"), "the app")}: "{_cut(ad.get("line"), 80)}"')
    parts.append(f"The makers say people would pick it because: {_cut(brief['profile']['why'], 200)}")
    comp = brief.get("competition") or {}
    if comp.get("now"):
        parts.append(f"What people mostly use for this today: {_cut(comp['now'], 200)}")
    if comp.get("switch"):
        parts.append(f"Why the makers say you would switch: {_cut(comp['switch'], 200)}")
    return " ".join(parts) + " What do you do?"


def signup_question(app, brief):
    """Right after install (R5): the sign-up screen, how one can sign up and what the app asks to use."""
    prod = brief.get("product", {})
    methods = [METHODS[m] for m in prod.get("signup_methods", []) if m in METHODS] or ["your email"]
    parts = [f"You just installed {app} and opened it. This is its sign-up screen.",
             f"You can sign up with {_either(methods)}."]
    perms = [PERMISSIONS[x] for x in prod.get("permissions", []) or [] if x in PERMISSIONS]
    if perms:
        parts.append(f"It asks to {_either(perms, 'and')}.")
    if prod.get("free_limits"):
        parts.append(f"Free users get {_cut(prod['free_limits'], 80)}.")
    return " ".join(parts) + " What do you do?"


PAYWALL = {"after_signup": "right after sign-up", "after_free_limit": "once you use up what is free",
           "after_trial": "when the free trial ends", "at_checkout": "when you buy or book something"}
PER = {"week": "a week", "month": "a month", "transaction": "each time", "percent": "of each purchase"}
PRICE_KEY = {"dating": "price_per_week", "resale": "fee_share", "rides": "fare_usd"}


def price_override(screen):
    """A gate screen key with an experiment's own price ("paywall@4.99") -> (gate, price or None)."""
    gate, _, price = screen.partition("@")
    return gate, float(price) if price else None


def gate_key(pack, plan, gate):
    """The screen part of a gate decision's key: the gate, plus the experiment's own price when it has one,
    so an experiment that changes the price is asked with that price."""
    key = PRICE_KEY.get(pack["id"])
    return f"{gate}@{plan[key]}" if key and key in plan else gate


def gate_question(question, brief, price=None):
    """The question while using the app, with how the app makes money and when it asks (P5).
    `price` is an experiment's own price, which replaces the brief's."""
    if not brief or not brief.get("money"):
        return question
    m = brief["money"]
    amount = m["price"] if price is None else price
    cost = f"{amount:.0%}" if m.get("per") == "percent" else f"${amount:,.2f}"
    parts = [question.removesuffix("What do you do?").strip(),
             f"It costs {cost} {PER.get(m.get('per'), '')}".strip() + ","
             f" and it asks you to pay {PAYWALL.get(m.get('paywall'), 'at some point')}."]
    if m.get("trial_days"):
        parts.append(f"New users get {int(m['trial_days'])} days free first.")
    if m.get("free"):
        parts.append(f"Free: {_cut(m['free'], 120)}.")
    if m.get("paid"):
        parts.append(f"Paid: {_cut(m['paid'], 120)}.")
    if (brief.get("product") or {}).get("free_limits"):
        parts.append(f"Free users get {_cut(brief['product']['free_limits'], 80)}.")
    return " ".join(parts) + " What do you do?"


def why_quit_question(app, brief):
    """When someone stops opening the app (R7). The retention text is only the context they answer in."""
    ret = brief.get("retention") or {}
    parts = [f"You have stopped opening {app}."]
    if ret.get("back"):
        parts.append(f"It tries to bring people back with: {_cut(ret['back'], 200)}")
    if ret.get("leave"):
        parts.append(f"Its makers worry people leave because: {_cut(ret['leave'], 200)}")
    return " ".join(parts) + (" Say in one short sentence, in your own voice, what really made you stop. "
                              "It may be something else.")


def nearby_bucket(n_nearby):
    """How many active people of the other side are within reach, in plain buckets."""
    return "none" if n_nearby < 5 else "few" if n_nearby < 50 else "many"


def week_bucket(days_since_install):
    return "w1" if days_since_install < 7 else "w2-4" if days_since_install < 28 else "w5+"


class StubProvider:
    """Hand-set answers for any pack, for tests and dry runs. `types` replaces the placeholder kinds
    (e.g. Wonder's kinds of a transaction pack, each with a side)."""
    name = "stub"
    ACTS = {"list": "list_item", "buy": "buy_item", "drive": "go_online", "ride": "request_ride"}

    def __init__(self, types=None):
        if types is not None:
            self.types = types

    def decide(self, kind, type_id, screen, bucket):
        t = TYPE_BY_ID.get(type_id, {"price": 1.0, "novelty": 1.0})
        if kind == "install":
            base = {"tiktok_ad": 0.10, "ambassador": 0.35, "friend": 0.30}.get(screen, 0.15)
            p = sigma(logit(base) + 0.6 * (t["novelty"] - 1) + {"ad_2": 0.3, "ad_3": -0.3}.get(bucket, 0.0))
            return {"install": p, "scroll_past": 1 - p}
        if kind == "sign_up":
            p = sigma(logit(0.7) + 0.5 * (t["novelty"] - 1))
            return {"finish": p, "delete_app": 1 - p}
        if kind == "why_quit":
            return {"quit": 1.0}
        matched, nearby, _week = bucket
        d = logit(0.2) + 2.2 * (matched == "no") + {"none": 0.6, "few": 0.3, "many": 0.0}[nearby]
        delete = sigma(d)
        if kind == "paywall":
            pay = min(0.04 * (1.3 if matched == "yes" else 0.5) / t["price"], 0.5 * (1 - delete))
            return {"pay": pay, "come_back_tomorrow": 1 - delete - pay, "delete_app": delete}
        if kind in self.ACTS:
            act = 0.3 * (1 - delete)
            return {self.ACTS[kind]: act, "come_back_tomorrow": 1 - delete - act, "delete_app": delete}
        raise ValueError(kind)

    def answer(self, kind, type_id, screen, bucket):
        probs = self.decide(kind, type_id, screen, bucket)
        reasons = {o: f"Placeholder reason to {o.replace('_', ' ')}." for o in probs}
        if kind == "why_quit":
            reasons = {"quit": "Placeholder reason for stopping."}
        return {"probs": probs, "reason": reasons[max(probs, key=probs.get)], "reasons": reasons}


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
