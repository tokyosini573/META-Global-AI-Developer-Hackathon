import yaml
import pytest

from engine.run import ROOT
from engine.world.calibrate import fit_shifts, shift_options, sigma
from engine.world.decide import DecisionCache, StubProvider
from engine.world.sim import Simulation, totals


def test_shift_options_keeps_a_distribution():
    probs = {"pay": 0.05, "come_back_tomorrow": 0.15, "delete_app": 0.8}
    out = shift_options(probs, {"pay": 1.0, "delete_app": -1.0}, "come_back_tomorrow")
    assert sum(out.values()) == pytest.approx(1)
    assert out["pay"] > probs["pay"] and out["delete_app"] < probs["delete_app"]


def test_fit_shifts_reaches_target():
    shifts, seen = fit_shifts(lambda s: {"x": sigma(-2 + s["x"])}, {"x": 0.3}, iters=30)
    assert seen["x"] == pytest.approx(0.3, abs=1e-3)


def test_same_seed_same_world():
    cfg = yaml.safe_load((ROOT / "plans" / "kindred.yaml").read_text())
    cache = DecisionCache(StubProvider())
    runs = [totals(Simulation(cfg, "b", cache, {}, seed=7, days=20).run(), 20, cfg["people_per_dot"])
            for _ in range(2)]
    assert runs[0] == runs[1]
