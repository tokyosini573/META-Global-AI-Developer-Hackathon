"""Ways people first meet an app, and what each costs.

A channel is grouped by how a person meets the app, not by brand: TikTok, Instagram and YouTube
are all an online feed, and differ only in their cost numbers. Each kind fixes three things:

- what a dollar buys: people reached a day (costs in plans/channels.yaml, each with its source)
- where it can reach: nationwide or only the cities a plan has opened
- what the person sees and in what situation: the context sentence of the market pack, and the
  screen it shows (the ad itself, or the store page someone showed them)

Referral is different: it pays existing users to invite friends, so it rides on word of mouth and
its spend is paid per friend who installs.
"""

from pathlib import Path

import yaml

from . import geo

KINDS = ("feed", "search", "event", "outdoor", "referral")
LABELS = {"feed": "Online feed ads", "search": "Search and app store ads", "event": "Offline promotion",
          "outdoor": "Outdoor and mass media", "referral": "Friend referrals"}
# The screen a person reached by each kind decides on
SCREEN = {"feed": "ad", "outdoor": "ad", "search": "store", "event": "store", "referral": "store", "friend": "store"}
COSTS = Path(__file__).resolve().parent.parent.parent / "plans" / "channels.yaml"


def costs():
    return yaml.safe_load(COSTS.read_text())


def area_share(cities):
    """Share of the national audience living in the given metros (rough metro weights, geo.METROS)."""
    if not cities:
        return 1.0
    weight = {m[0]: m[3] for m in geo.METROS}
    total = sum(weight.values())
    return (1 - geo.SMALL_TOWN_SHARE) * sum(weight.get(c["name"], 1) for c in cities) / total


def real_reached(kind, spend, cost, open_cities):
    """Real people reached in one day by `spend` dollars of a paid channel (not referral)."""
    if kind == "feed":
        return spend / cost["cpm_usd"] * 1000 * cost["ctr"]
    if kind == "search":
        cap = cost["monthly_searches"] / 30 * area_share(open_cities)
        return min(spend / cost["cpt_usd"], cap)
    if kind == "event":
        return spend / cost["usd_per_contact"]
    if kind == "outdoor":
        return spend / cost["cpm_usd"] * 1000 * cost["response"]
    raise ValueError(kind)


def expected_reach(cfg, plan, days):
    """Real people a plan's paid channels reach in `days` days, on average (referrals and word of mouth
    excluded: they depend on how the launch goes)."""
    cost = costs()
    budget = plan.get("budget_usd", cfg["budget_usd"])
    total = 0.0
    for t in range(days):
        open_cities = [c for c in plan.get("cities", []) if c["open_day"] <= t]
        for ch in plan["channels"]:
            if ch["kind"] == "referral" or not ch["start_day"] <= t < ch["end_day"]:
                continue
            if ch["where"] != "nationwide" and not open_cities:
                continue
            spend = budget * ch["budget_share"] / (ch["end_day"] - ch["start_day"])
            total += real_reached(ch["kind"], spend, cost[ch["kind"]], [] if ch["where"] == "nationwide" else open_cities)
    return total
