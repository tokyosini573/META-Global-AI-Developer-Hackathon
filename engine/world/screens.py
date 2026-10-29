"""The app screens a simulated person can be looking at, rendered once as PNGs.

    .venv/bin/python -m engine.world.screens     # needs Google Chrome

Each decision key maps to one image: the paywall changes with the person's state
(match or not, how far the nearest person is), so the model sees what they would see.
"""

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "screens"
OUT = HERE / "out"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# nearby bucket -> distance shown for the nearest person
MILES = {"none": 41, "few": 9, "many": 2}


def install_screen(screen):
    """tiktok_ad -> the ad; ambassador and friend -> the store page they were shown."""
    return "ad" if screen == "tiktok_ad" else "store"


def paywall_screen(bucket):
    matched, nearby, _week = bucket
    return f"paywall_m{int(matched == 'yes')}_{nearby}"


def variants():
    yield "ad", "s=ad"
    yield "store", "s=store"
    for m in (0, 1):
        for nearby, miles in MILES.items():
            yield f"paywall_m{m}_{nearby}", f"s=paywall&match={m}&miles={miles}"


def path(name):
    return OUT / f"{name}.png"


def render():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, query in variants():
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=390,844",
                        "--virtual-time-budget=3000", f"--screenshot={path(name)}",
                        f"file://{HERE / 'kindred.html'}?{query}"], check=True, capture_output=True)
        print(path(name).relative_to(HERE.parent.parent))


if __name__ == "__main__":
    render()
