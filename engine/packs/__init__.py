"""Market packs: what differs between kinds of two-sided apps.

Every two-sided app shares the engine (engine/world/sim.py): people reached by the launch, the other
side nearby, a first success, word of mouth, quitting. A pack holds what differs:

- the two sides, and the sentence that tells a simulated person which side they are on
- how a success happens (`mechanics`): "swipe" for dating (both sides browse and match), or
  "transaction" (one side offers, the other asks, and a success needs both nearby on the same day)
- the decision each side makes once they use the app (the gate), its options and its screen
- the situation sentence for each way of meeting the app (channels.py)
- the plain words the screens and the drawer use

A plan file names its pack (`pack: dating`); plans without one are dating.
"""

import importlib

IDS = ("dating", "resale", "rides")


def load(pack_id):
    return importlib.import_module(f"engine.packs.{pack_id}").PACK


def of(cfg):
    return load(cfg.get("pack", "dating"))


def side_shares(pack, cfg):
    """[(side, share)] for the two sides of this market."""
    (a, _), (b, _) = pack["sides"]
    share = cfg["world"][pack["share_key"]]
    return [(a, share), (b, 1 - share)]


def ad_screen(pack, ad_id):
    """The image of one of the brief's ads: ad_1 is the pack's own ad screen, ad_2 and ad_3 add a suffix."""
    return pack.get("screen_prefix", "") + ("ad" if ad_id == "ad_1" else ad_id)


def signup_screen(pack):
    return pack.get("screen_prefix", "") + "signup"


def experiment_ads(brief, plan_key):
    """The ads one experiment shows (docs/brief-format.md setup): its own list, else the shared campaign's,
    else every ad in the brief. No brief: the pack's one ad."""
    if not brief:
        return ["ad_1"]
    setup = brief.get("setup", {})
    ids = [a["id"] for a in brief.get("ads", [])] or ["ad_1"]
    chosen = (setup.get("experiments", {}).get(plan_key, {}).get("ads")
              or setup.get("campaign", {}).get("ads") or ids)
    return [a for a in chosen if a in ids] or ids
