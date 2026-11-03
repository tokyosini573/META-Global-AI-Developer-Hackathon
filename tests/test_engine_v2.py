"""The v2 funnel (docs/replay-format.md "Version 2"): ads, sign-up, why people stop, the replay. No API calls:
the stub answers every decision, and Glimmer's committed table answers what it was trained on."""

import copy
import json

import numpy as np
import pytest
import yaml

from engine import packs
from engine.run import ROOT, apply_people, calibrate, load_plan, rehearse
from engine.world import channels, typed
from engine.world.decide import DecisionCache, StubProvider
from engine.world.glimmer import GlimmerProvider, trained_on
from engine.world.sim import Simulation

APPS = {"dating": "kindred", "resale": "reloop", "rides": "hopway"}
NOTE = "Simulated, calibrated to public benchmarks. Not observed."


def brief_for(name):
    """The app's brief: Kindred's committed one, or a fictional one made from it for the other demos."""
    path = ROOT / "plans" / f"{name}.brief.yaml"
    if name == "kindred" or path.exists():
        return yaml.safe_load(path.read_text())
    b = yaml.safe_load((ROOT / "plans" / "kindred.brief.yaml").read_text())
    b["app"] = {"reloop": "Reloop", "hopway": "Hopway"}[name]
    b["category"] = {"reloop": "resale", "hopway": "rides"}[name]
    b["audience"]["age"] = [25, 50]
    b["ads"] = [{"id": "ad_1", "angle": "price", "line": "Sell it this weekend."},
                {"id": "ad_2", "angle": "trust", "line": "Neighbors you can meet."}]
    return b


def cfg_with_brief(name, people=1000, days=None):
    cfg = load_plan(ROOT / "plans" / f"{name}.yaml")
    cfg["brief"] = brief_for(name)
    cfg["brief"]["setup"]["people"] = people
    if days:
        cfg["days"] = days
    cfg["calibration"]["seeds"] = 2          # fast: the level is not what these tests check
    return cfg


def stub_for(cfg):
    if packs.of(cfg)["id"] == "dating":
        return GlimmerProvider(others=StubProvider())
    design = json.loads(typed.paths(cfg)[0].read_text())
    return StubProvider(types=typed.kinds(design))


@pytest.fixture(scope="module", params=list(APPS))
def run(request):
    cfg = cfg_with_brief(APPS[request.param])
    cache = DecisionCache(stub_for(cfg))
    rep, summary, first = rehearse(cfg, cache, n_runs=3, use_wonder=False, log=lambda *a: None)
    return cfg, rep, summary, first


def test_load_plan_reads_the_brief_next_to_the_plan_file():
    assert load_plan(ROOT / "plans" / "kindred.yaml")["brief"]["app"] == "Kindred"
    assert "brief" not in load_plan(ROOT / "plans" / "hopway.yaml") or (ROOT / "plans" / "hopway.brief.yaml").exists()


def test_experiment_ads():
    b = {"ads": [{"id": "ad_1"}, {"id": "ad_2"}, {"id": "ad_3"}],
         "setup": {"campaign": {"ads": ["ad_1", "ad_2"]}, "experiments": {"a": {}, "b": {"ads": ["ad_3"]}}}}
    assert packs.experiment_ads(b, "a") == ["ad_1", "ad_2"]
    assert packs.experiment_ads(b, "b") == ["ad_3"]
    del b["setup"]["campaign"]
    assert packs.experiment_ads(b, "a") == ["ad_1", "ad_2", "ad_3"]
    assert packs.experiment_ads(None, "a") == ["ad_1"]
    pack = packs.load("resale")
    assert [packs.ad_screen(pack, a) for a in ("ad_1", "ad_2")] == ["reloop_ad", "reloop_ad_2"]
    assert packs.signup_screen(pack) == "reloop_signup" and packs.signup_screen(packs.load("dating")) == "signup"


def test_meta_is_v2(run):
    cfg, rep, _, _ = run
    m, pack = rep["meta"], packs.of(cfg)
    assert rep["version"] == 2 and m["note"] == NOTE and m["agents"] == 1000
    assert m["brief"]["app"] == cfg["brief"]["app"] and "images" in m["brief"]
    assert [f["key"] for f in m["funnel"]] == (["saw", "installed", "signed_up", "first", "active", "paid"]
                                               if pack["id"] == "dating" else
                                               ["saw", "installed", "signed_up", "first", "active"])
    assert m["funnel"][4]["label"] == f"Using on day {cfg['days']}"
    assert [a["id"] for a in m["ads"]] == [a["id"] for a in cfg["brief"]["ads"]]
    assert m["ads"][0]["screen"] == pack.get("screen_prefix", "") + "ad"
    assert len(m["kinds"]) >= 6 and all({"id", "name", "share"} <= set(k) for k in m["kinds"])


def test_people_add_up_with_the_funnel(run):
    cfg, rep, summary, _ = run
    days = cfg["days"]
    by = lambda d: d is not None and d <= days      # noqa: E731
    for k, ppl in rep["people"].items():
        n = {"saw": len(ppl), "installed": sum(by(p["installed"]) for p in ppl),
             "signed_up": sum(by(p["signed_up"]) for p in ppl), "first": sum(by(p["matched"]) for p in ppl),
             "active": sum(by(p["signed_up"]) and not by(p["quit"]) for p in ppl),
             "paid": sum(by(p["paid"]) for p in ppl)}
        want = summary["funnels"][0][k]
        assert {key: n[key] for key in want} == want
        steps = list(want.values())
        assert steps[:4] == sorted(steps[:4], reverse=True) and n["active"] <= n["signed_up"]
        lo_hi = rep["plans"][k]["range"]
        assert set(lo_hi) == set(want) and all(lo <= hi for lo, hi in lo_hi.values())


def test_each_person_has_the_v2_fields(run):
    cfg, rep, _, first = run
    pack = packs.of(cfg)
    kinds = {k["id"] for k in rep["meta"]["kinds"]}
    keys = [f["key"] for f in rep["meta"]["funnel"]]
    for k, ppl in rep["people"].items():
        shown = packs.experiment_ads(cfg["brief"], k)
        channel = {p.id: p.channel for p in first[k].people}
        for p in ppl:
            assert p["kind"] in kinds
            ad_led = pack["context_screen"][pack["channel_context"][channel[p["id"]]]] == "ad"
            assert (p["ad_id"] in shown) if ad_led else p["ad_id"] is None
            if p["ad_id"]:
                assert p["story"]["ad"] == packs.ad_screen(pack, p["ad_id"])
            if p["installed"] is None:
                assert p["signed_up"] is None
            elif p["signed_up"] is None:                       # deleted the app at sign-up
                assert p["quit"] == p["installed"] and p["matched"] is None and p["paid"] is None
                assert any("sign-up" in line for _, line, _ in p["story"]["diary"])
            else:
                assert p["signed_up"] >= p["installed"]
            st = p["story"]
            done = {"saw": True, "installed": p["installed"] is not None, "signed_up": p["signed_up"] is not None,
                    "first": p["matched"] is not None, "active": p["signed_up"] is not None and p["quit"] is None,
                    "paid": p["paid"] is not None}
            missed = next((x for x in keys if not done[x]), None)
            assert st.get("stop", {}).get("to") == missed
            if p["quit"] is not None:
                assert st["quit_reason"], p              # the stub always says something
            if missed in ("first", "active") and p["quit"] is not None:
                assert st["stop"]["words"] == st["quit_reason"]


def test_ad_cells(run):
    cfg, rep, _, _ = run
    kinds = {k["id"] for k in rep["meta"]["kinds"]}
    for k, plan in rep["plans"].items():
        cells = plan["ads"]["cells"]
        assert set(cells) == kinds
        shown = packs.experiment_ads(cfg["brief"], k)
        for row in cells.values():
            assert set(row) == set(shown) and all(0 <= i <= s for s, i in row.values())
        assert plan["changes"] == cfg["brief"]["setup"]["experiments"][k]["changes"]


def test_ads_are_shown_evenly():
    cfg = cfg_with_brief("kindred", people=1000)
    apply_people(cfg)
    res = Simulation(cfg, "a", DecisionCache(stub_for(cfg)), {}, seed=1).run()
    seen = [p.ad_id for p in res.people if p.ad_id]
    counts = [seen.count(a) for a in ("ad_1", "ad_2", "ad_3")]
    assert min(counts) > 0.8 * len(seen) / 3


def test_people_sets_people_per_dot():
    for people in (1000, 10000):
        cfg = cfg_with_brief("kindred", people=people)
        apply_people(cfg)
        top = max(channels.expected_reach(cfg, p, cfg["days"]) for p in cfg["plans"].values())
        assert top / cfg["people_per_dot"] == pytest.approx(people, rel=1e-3)
    cfg = load_plan(ROOT / "plans" / "kindred.yaml")
    cfg.pop("brief")
    apply_people(cfg)
    assert cfg["people_per_dot"] == 60          # no brief: the plan file's value


def test_signup_target_only_with_a_brief_and_at_least_60_days():
    cfg = cfg_with_brief("kindred", people=1000, days=7)
    apply_people(cfg)
    cache = DecisionCache(stub_for(cfg))
    shifts, seen = calibrate(cfg, cache, 7)
    assert "signup" in shifts and seen["paid_30d"] is not None
    plain = copy.deepcopy(cfg)
    plain.pop("brief")
    shifts, _ = calibrate(plain, DecisionCache(GlimmerProvider()), 7)
    assert "signup" not in shifts


def test_no_brief_keeps_everyone_who_installs():
    cfg = yaml.safe_load((ROOT / "plans" / "kindred.yaml").read_text())
    res = Simulation(cfg, "a", DecisionCache(GlimmerProvider()), {}, seed=2, days=20).run()
    assert all(p.signed_up == p.installed for p in res.people)
    assert not any(d[2] in ("sign_up", "why_quit") for d in res.decisions)
    assert all(p.ad_id == "ad_1" for p in res.people if p.channel == "feed")


def test_a_short_run_still_works():
    cfg = cfg_with_brief("reloop", people=1000, days=7)
    rep, summary, _ = rehearse(cfg, DecisionCache(stub_for(cfg)), n_runs=2, use_wonder=False, log=lambda *a: None)
    assert rep["meta"]["days"] == 7 and rep["meta"]["funnel"][4]["label"] == "Using on day 7"


def test_glimmer_answers_only_what_it_was_trained_on():
    assert trained_on("paywall", ("no", "few", "w1")) and trained_on("install", "ad_1")
    assert trained_on("install", "store") and trained_on("install", "-")
    assert not any(trained_on(k, b) for k, b in (("install", "ad_2"), ("sign_up", "-"),
                                                 ("why_quit", ("no", "few", "w1"))))
    g = GlimmerProvider(others=StubProvider())
    pid = next(iter(g.pool))
    assert g.decide("install", pid, "tiktok_ad", "ad_1") == g.entries[f"{pid}|install|tiktok_ad"]["probs"]
    assert set(g.decide("sign_up", pid, "signup", "-")) == {"finish", "delete_app"}


@pytest.mark.parametrize("name", list(APPS.values()))
def test_typed_questions_carry_the_brief(name, tmp_path):
    cfg = cfg_with_brief(name)
    b = cfg["brief"]
    p = typed.TypedProvider(cfg, typed.paths(cfg)[0], tmp_path / "t.json")
    keys = list(p.keys())
    kinds = {k[0] for k in keys}
    assert {"install", "sign_up", "why_quit"} <= kinds
    assert not any(k[0] == "install" and k[3] == "-" for k in keys)
    ad_key = next(k for k in keys if k[0] == "install" and k[3] == "ad_2")
    persona, image, question, options, shape = p._prompt(ad_key)
    assert image == packs.ad_screen(p.pack, "ad_2") and shape == "each"
    assert b["ads"][1]["line"] in question and b["profile"]["why"] in question
    assert b["competition"]["now"] in question and question.endswith("What do you do?")
    su = next(k for k in keys if k[0] == "sign_up")
    _, image, question, options, _ = p._prompt(su)
    assert image == packs.signup_screen(p.pack) and options == ("finish", "delete_app") and "Apple" in question
    wq = next(k for k in keys if k[0] == "why_quit")
    _, _, question, options, shape = p._prompt(wq)
    assert b["retention"]["back"] in question and shape == "reason"
    # an answer asked with other words is asked again
    p.entries[typed._key_str(su)] = {"probs": {"finish": 1.0, "delete_app": 0.0}, "q": "old"}
    assert not p._fresh(su)
    p.entries[typed._key_str(su)]["q"] = p._q(su)
    assert p._fresh(su)
    plain = load_plan(ROOT / "plans" / f"{name}.yaml")
    plain.pop("brief", None)
    v1 = list(typed.TypedProvider(plain, typed.paths(plain)[0], tmp_path / "u.json").keys())
    assert {k[0] for k in v1} <= {"install"} | set(packs.of(plain)["gates"].values())


def test_design_prompt_uses_the_audience_ages():
    cfg = cfg_with_brief("reloop")
    assert typed.age_range(cfg) == (25, 50)
    cfg["brief"]["audience"]["age"] = [10, 99]
    assert typed.age_range(cfg) == packs.of(cfg)["age"]
    text = typed.brief_text(cfg["brief"])
    assert cfg["brief"]["profile"]["why"] in text and cfg["brief"]["competition"]["switch"] in text


def test_stop_is_the_first_step_never_reached(run):
    """stop.to == b exactly for the people who reached every step before b but not b."""
    cfg, rep, _, _ = run
    days = cfg["days"]
    by = lambda d: d is not None and d <= days      # noqa: E731
    keys = [f["key"] for f in rep["meta"]["funnel"]]
    for ppl in rep["people"].values():
        for p in ppl:
            done = {"saw": True, "installed": by(p["installed"]), "signed_up": by(p["signed_up"]),
                    "first": by(p["matched"]), "active": by(p["signed_up"]) and not by(p["quit"]),
                    "paid": by(p["paid"])}
            for i, b in enumerate(keys):
                first_miss = all(done[a] for a in keys[:i]) and not done[b]
                assert (p["story"].get("stop", {}).get("to") == b) == first_miss
    assert np.isfinite(rep["meta"]["people_per_dot"])
