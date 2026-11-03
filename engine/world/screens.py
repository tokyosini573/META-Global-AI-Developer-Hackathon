"""The app screens a simulated person can be looking at, rendered once as PNGs.

    .venv/bin/python -m engine.world.screens            # every pack's demo app; needs Google Chrome
    .venv/bin/python -m engine.world.screens resale     # one pack
    .venv/bin/python -m engine.world.screens dating --only signup,ad_2   # only these screens (names without prefix)

Each decision key maps to one image: the gate screen (dating's paywall, the resale feed, the ride
request) changes with the person's state (a success or not, how much of the other side is nearby),
so the model sees what they would see. Each pack's demo app is one HTML file in engine/screens/;
its images carry the pack's prefix (dating has none: ad.png, store.png, paywall_m0_none.png).
Besides the first ad (`ad`) each demo app has two more ads (`ad_2` price, `ad_3` trust) and its
sign-up screen (`signup`), as named in its brief (plans/<app>.brief.yaml, docs/brief-format.md
"Images"); dating also has `main`, the swiping screen.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from engine import packs

HERE = Path(__file__).resolve().parent.parent / "screens"
OUT = HERE / "out"
WEB = HERE.parent.parent / "web" / "public" / "screens"   # the one-person drawer shows the same images
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
NEARBY = ("none", "few", "many")

# nearby bucket -> distance shown for the nearest person (dating's paywall)
MILES = {"none": 41, "few": 9, "many": 2}


def _pack(pack):
    return pack or packs.load("dating")


def install_screen(context, pack=None):
    """The image a person reached in this situation looks at: the ad itself or the store page."""
    pack = _pack(pack)
    return pack.get("screen_prefix", "") + pack["context_screen"][context]


def gate_screen(gate, bucket, pack=None):
    pack = _pack(pack)
    success, nearby, _week = bucket
    return f"{pack.get('screen_prefix', '')}{gate}_m{int(success == 'yes')}_{nearby}"


def paywall_screen(bucket):
    return gate_screen("paywall", bucket)


def variants(pack):
    """(image name, query string for the pack's HTML) for every screen the pack can show."""
    pre = pack.get("screen_prefix", "")
    for name in ("ad", "ad_2", "ad_3", "store", "signup") + (("main",) if pack["id"] == "dating" else ()):
        yield pre + name, f"s={name}"
    for gate in sorted(set(pack["gates"].values())):
        for m in (0, 1):
            for nearby in NEARBY:
                query = (f"s=paywall&match={m}&miles={MILES[nearby]}" if gate == "paywall"
                         else f"s={gate}&match={m}&near={nearby}")
                yield f"{pre}{gate}_m{m}_{nearby}", query


def path(name):
    return OUT / f"{name}.png"


def render(pack, only=None):
    """Every screen of the pack's demo app, or only those whose names (without the prefix) are in `only`."""
    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    pre = pack.get("screen_prefix", "")
    for name, query in variants(pack):
        if only and name[len(pre):] not in only:
            continue
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=390,844",
                        "--virtual-time-budget=3000", f"--screenshot={path(name)}",
                        f"file://{HERE / pack['html']}?{query}"], check=True, capture_output=True)
        shutil.copy(path(name), WEB / path(name).name)
        print(path(name).relative_to(HERE.parent.parent))


if __name__ == "__main__":
    args = sys.argv[1:]
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set(args[i + 1].split(","))
        del args[i:i + 2]
    for pid in args or packs.IDS:
        render(packs.load(pid), only)
