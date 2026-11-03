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
