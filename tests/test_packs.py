"""Market packs, channels and the admin's live run: checks that need no API call."""

import copy
import json

import pytest
import yaml

from engine import live, packs
from engine.run import ROOT
from engine.world import channels, typed
from engine.world.decide import DecisionCache
from engine.world.sim import Simulation, measures, totals

MARKETS = {"resale": "reloop", "rides": "hopway"}


def cfg_of(name):
    return yaml.safe_load((ROOT / "plans" / f"{name}.yaml").read_text())


def cache_of(cfg):
    return DecisionCache(typed.TypedProvider(cfg, *typed.paths(cfg)))


@pytest.mark.parametrize("name", MARKETS.values())
def test_pack_table_covers_every_decision(name):
    """The committed kinds-of-people table answers every key, so the example runs never call the API."""
    p = typed.TypedProvider(cfg_of(name), *typed.paths(cfg_of(name)))
    missing = [k for k in p.keys() if typed._key_str(k) not in p.entries]
    assert not missing
    for e in p.entries.values():
        assert sum(e["probs"].values()) == pytest.approx(1)
    sides = {t["side"] for t in p.types}
    assert sides == {s for s, _ in p.pack["sides"]}
    for s in sides:
        assert sum(t["weight"] for t in p.types if t["side"] == s) == pytest.approx(1)


@pytest.mark.parametrize("name", MARKETS.values())
def test_transactions_happen_between_the_two_sides(name):
    cfg = cfg_of(name)
    pack = packs.of(cfg)
    res = Simulation(cfg, "b", cache_of(cfg), {}, seed=3, days=60).run()
    side = {p.id: p.side for p in res.people}
    assert res.matches, "a city launch should complete some transactions"
    for a, b, _ in res.matches:      # [asker, offerer, day]
        assert (side[a], side[b]) == (pack["demand"], pack["supply"])
    t = totals(res, 60, cfg["people_per_dot"], pack)
    assert t["transactions"] == cfg["people_per_dot"] * len(res.matches)
    assert set(measures(res, 60, pack)) == {"install", "d7_retention", pack["convert_target"]}


def test_a_sold_item_is_gone():
    """Resale: one listing sells once, so no seller completes two sales on the same day."""
    cfg = cfg_of("reloop")
    res = Simulation(cfg, "b", cache_of(cfg), {}, seed=3, days=60).run()
    sold = [(b, int(d)) for _, b, d in res.matches]
    assert len(sold) == len(set(sold))


def test_channel_aimed_at_one_side_reaches_only_that_side():
    cfg = cfg_of("reloop")     # Plan B's offline promotion is aimed at sellers
    res = Simulation(cfg, "b", cache_of(cfg), {}, seed=1, days=14).run()
    reached = [p for p in res.people if p.channel == "event"]
    assert reached and all(p.side == "seller" for p in reached)


def test_channel_reach_grows_with_spend():
    cost = channels.costs()
    for kind in ("feed", "event", "outdoor"):
        assert channels.real_reached(kind, 200, cost[kind], []) > channels.real_reached(kind, 100, cost[kind], [])
    city = [{"name": "Austin, Texas"}]
    # search is capped by how many people search, and a city has fewer searchers than the country
    huge = 10 ** 9
    assert channels.real_reached("search", huge, cost["search"], city) < channels.real_reached("search", huge, cost["search"], [])
    with pytest.raises(ValueError):
        channels.real_reached("referral", 100, cost["referral"], [])


@pytest.mark.parametrize("pack_id", live.EXAMPLES)
def test_example_spec_rebuilds_the_example_plans(pack_id):
    spec = live.example_spec(pack_id)
    cfg = live.build_cfg(spec)
    plan_file = cfg_of(live.EXAMPLES[pack_id])
    for k in "ab":
        got, want = cfg["plans"][k], plan_file["plans"][k]
        assert [c["kind"] for c in got["channels"]] == [c["kind"] for c in want["channels"]]
        assert sum(c["budget_share"] for c in got["channels"]) == pytest.approx(1)
        assert [c["name"] for c in got.get("cities", [])] == [c["name"] for c in want.get("cities", [])]
    assert [s["name"] for s in spec["slots"]] == live.screen_slots(pack_id)
    for s in spec["slots"]:
        assert (ROOT / "web" / "public" / s["example"].lstrip("/")).exists()


def test_build_cfg_cleans_what_the_form_sends():
    spec = live.example_spec("resale")
    spec = copy.deepcopy(spec)
    spec["app"] = "My <b>App</b>!"
    spec["days"] = 999
    a = spec["plans"]["a"]
    a["cities"] = [{"name": "Atlantis, Nowhere", "open_day": 0}]          # not a listed metro: dropped
    a["channels"] = [{"kind": "feed", "budget_share": 3, "start_day": 0, "end_day": 500, "side": "nobody"},
                     {"kind": "event", "budget_share": 1, "start_day": 0, "end_day": 90}]
    cfg = live.build_cfg(spec)
    assert cfg["app"] == "My bAppb" and cfg["days"] == 180
    chans = cfg["plans"]["a"]["channels"]
    assert [c["kind"] for c in chans] == ["feed"]          # offline promotion needs a city
    assert chans[0]["budget_share"] == 1 and chans[0]["end_day"] == 180 and "side" not in chans[0]
    assert chans[0]["where"] == "nationwide"
    with pytest.raises(AssertionError):
        live.build_cfg({**spec, "plans": {**spec["plans"], "b": {**spec["plans"]["b"], "channels": [
            {"kind": "tv", "budget_share": 1, "start_day": 0, "end_day": 10}]}}})


def test_live_paths_are_never_files_outside_the_run():
    with pytest.raises(KeyError):
        live.screen("../../etc", "ad")
    with pytest.raises(KeyError):
        live.replay("../x")


def test_interview_reads_a_live_replay(tmp_path, monkeypatch):
    from engine import interview
    rid = "abcdef123456"
    (tmp_path / rid).mkdir()
    rep = json.loads((ROOT / "web" / "public" / "replays" / "reloop.json").read_text())
    (tmp_path / rid / "replay.json").write_text(json.dumps(rep))
    monkeypatch.setattr(live, "DIR", tmp_path)
    pid = rep["people"]["b"][0]["id"]
    data, p = interview.person(f"live_{rid}", "b", pid)
    assert p["id"] == pid and "Reloop" in interview.record(data, "b", p)
