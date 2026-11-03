"""v2 live run, report and demo briefs: checks that need no API call (Wonder and Spark are stubbed)."""

import copy
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml

from engine import interview, live, packs, serve
from engine.world import report, screens

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "web" / "public" / "replays" / "fixture_v2.json"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32


def brief_of(app):
    return yaml.safe_load((ROOT / "plans" / f"{app}.brief.yaml").read_text())


def live_brief(category="resale"):
    """A demo brief with a shared campaign, as the Setup page sends it for a live run."""
    b = brief_of(live.EXAMPLES[category])
    b["setup"] = {"people": 1000, "days": 30, "campaign": {
        "budget_usd": 20000, "ads": ["ad_1", "ad_2", "ad_3"],
        "channels": [{"kind": "feed", "where": "nationwide", "budget_share": 0.8, "start_day": 0, "end_day": 30},
                     {"kind": "search", "where": "nationwide", "budget_share": 0.2, "start_day": 0, "end_day": 30}]},
        "experiments": {"a": {"changes": "Nothing: the shared campaign"},
                        "b": {"changes": "Seattle first, only the trust ad",
                              "cities": [{"name": "Seattle, Washington", "open_day": 0}],
                              "channels": [{"kind": "event", "where": "cities", "budget_share": 1, "start_day": 0,
                                            "end_day": 30, "side": "seller"},
                                           {"kind": "feed", "where": "cities", "budget_share": 1, "start_day": 5,
                                            "end_day": 30}],
                              "ads": ["ad_3"], "price": 0.05}}}
    return b


def fixture():
    rep = json.loads(FIXTURE.read_text())
    for p in rep["plans"].values():
        p.pop("report", None)
        p["ads"].pop("line", None)
    return rep


# --- demo briefs ---------------------------------------------------------------------------------

@pytest.mark.parametrize("app", ["kindred", "reloop", "hopway"])
def test_demo_brief_builds_the_example_plans(app):
    b = brief_of(app)
    cfg = live.build_cfg(b)
    plan_file = yaml.safe_load((ROOT / "plans" / f"{app}.yaml").read_text())
    assert cfg["pack"] == plan_file["pack"] and cfg["app"] == plan_file["app"]
    for k in "ab":
        got = {f: v for f, v in cfg["plans"][k].items() if f not in ("changes", "ads")}
        assert got == plan_file["plans"][k]
        assert cfg["plans"][k]["changes"] == b["setup"]["experiments"][k]["changes"]
        assert cfg["plans"][k]["ads"] == ["ad_1", "ad_2", "ad_3"]
    assert [a["angle"] for a in b["ads"]] == ["feature", "price", "trust"]
    for path in cfg["brief"]["images"].values():           # every image the brief names is rendered
        assert (ROOT / "web" / "public" / path.lstrip("/")).exists(), path
    for ad in cfg["ads"]:
        assert screens.path(ad["screen"]).exists()


def test_demo_briefs_name_no_real_company():
    words = " ".join((ROOT / "plans" / f"{a}.brief.yaml").read_text().lower() for a in ("kindred", "reloop", "hopway"))
    for name in ("tinder", "bumble", "hinge", "uber", "lyft", "ebay", "craigslist", "poshmark", "facebook marketplace",
                 "depop", "mercari", "offerup"):
        assert name not in words, name


# --- build_cfg from a live brief ------------------------------------------------------------------

def test_build_cfg_applies_the_shared_campaign_and_each_experiments_changes():
    cfg = live.build_cfg(live_brief(), rid="abcdef123456")
    a, b = cfg["plans"]["a"], cfg["plans"]["b"]
    assert cfg["days"] == 30 and cfg["people"] == 1000 and cfg["budget_usd"] == 20000
    assert [c["kind"] for c in a["channels"]] == ["feed", "search"] and "cities" not in a
    assert a["ads"] == ["ad_1", "ad_2", "ad_3"] and a["changes"] == "Nothing: the shared campaign"
    assert [c["name"] for c in b["cities"]] == ["Seattle, Washington"]
    assert [(c["kind"], c["where"], c.get("side")) for c in b["channels"]] == [("event", "cities", "seller"),
                                                                              ("feed", "cities", None)]
    assert sum(c["budget_share"] for c in b["channels"]) == pytest.approx(1)
    assert b["ads"] == ["ad_3"] and b["fee_share"] == 0.05 and b["budget_usd"] == 20000
    assert cfg["world"]["share_seller"] == 0.42 and cfg["fee_share"] == 0.10
    assert cfg["brief"]["images"]["main_seller"] == "/api/live/abcdef123456/screen/main_seller"
    assert [a["screen"] for a in cfg["ads"]] == ["reloop_ad", "reloop_ad_2", "reloop_ad_3"]


def test_build_cfg_cleans_what_the_form_sends():
    b = live_brief()
    b["app"] = "My <b>App</b>!"
    b["setup"]["days"], b["setup"]["people"] = 999, 7
    b["audience"]["age"] = [3, 300]
    b["profile"]["does"] = "x" * 1000
    b["ads"] = b["ads"] + [{"id": "ad_9", "angle": "shouting", "line": "Four"}]
    b["extra"] = {"fee_share": 5, "fare_usd": 14, "seller_share": "lots"}
    camp = b["setup"]["campaign"]
    camp["cities"] = [{"name": "Atlantis, Nowhere", "open_day": 0}]          # not a listed metro: dropped
    camp["channels"] = [{"kind": "feed", "budget_share": 3, "start_day": 0, "end_day": 500, "side": "nobody"},
                        {"kind": "event", "budget_share": 1, "start_day": 0, "end_day": 90}]
    cfg = live.build_cfg(b)
    br = cfg["brief"]
    assert cfg["app"] == "My bAppb" and cfg["days"] == 90 and cfg["people"] == 1000
    assert br["audience"]["age"] == [18, 64] and len(br["profile"]["does"]) == 300
    assert [a["id"] for a in br["ads"]] == ["ad_1", "ad_2", "ad_3"]     # three ads at most
    assert br["extra"] == {"fee_share": 0.99} and cfg["fee_share"] == 0.99
    chans = cfg["plans"]["a"]["channels"]
    assert [c["kind"] for c in chans] == ["feed"]                           # offline promotion needs a city
    assert chans[0]["budget_share"] == 1 and chans[0]["end_day"] == 90 and "side" not in chans[0]
    assert chans[0]["where"] == "nationwide"
    bad = live_brief()
    bad["setup"]["experiments"]["b"]["channels"] = [{"kind": "tv", "budget_share": 1, "start_day": 0, "end_day": 10}]
    with pytest.raises(AssertionError):
        live.build_cfg(bad)
    for broken in ({**live_brief(), "category": "pets"}, {**live_brief(), "ads": []}, {**live_brief(), "app": "!!"}):
        with pytest.raises(ValueError):
            live.build_cfg(broken)


def test_build_cfg_dating_prices_and_trial():
    b = brief_of("kindred")
    b["money"].update(price=19.99, per="month", trial_days=7)
    b["extra"] = {"women_share": 0.4, "free_likes_per_day": 10}
    b["setup"]["campaign"] = {"budget_usd": 40000, "ads": ["ad_1"], "channels": [
        {"kind": "feed", "where": "nationwide", "budget_share": 1, "start_day": 0, "end_day": 90}]}
    b["setup"]["experiments"]["b"] = {"changes": "A month free", "trial_days": 30, "ads": ["ad_2", "ad_3"]}
    cfg = live.build_cfg(b)
    assert cfg["price_per_week"] == pytest.approx(19.99 * 12 / 52, abs=0.01)
    assert cfg["world"]["share_male"] == 0.6
    a, bb = cfg["plans"]["a"], cfg["plans"]["b"]
    assert (a["trial_days"], bb["trial_days"]) == (7, 30)
    assert a["free_swipes_per_day"] == bb["free_swipes_per_day"] == 10
    assert a["ads"] == ["ad_1"] and bb["ads"] == ["ad_2", "ad_3"]


# --- images -------------------------------------------------------------------------------------

def test_image_slots_match_the_brief_format():
    assert live.image_slots("dating", 3) == ["store", "signup", "main", "paywall", "ad_1", "ad_2", "ad_3"]
    assert live.image_slots("resale", 1) == ["store", "signup", "main_seller", "main_buyer", "ad_1"]
    assert live.image_slots("rides", 2) == ["store", "signup", "main_driver", "main_rider", "ad_1", "ad_2"]


@pytest.mark.parametrize("pack_id", packs.IDS)
def test_image_map_covers_every_decision_screen(pack_id, tmp_path):
    pack = packs.load(pack_id)
    pre = pack.get("screen_prefix", "")
    images = live.image_map(pack, tmp_path, live.image_slots(pack_id, 3))
    assert images[pre + "ad"].name == "ad_1.png" and images[pre + "ad_3"].name == "ad_3.png"
    assert images[pre + "signup"].name == "signup.png" and images[pre + "store"].name == "store.png"
    for side, gate in pack["gates"].items():
        for m in ("no", "yes"):
            for n in screens.NEARBY:
                f = images[screens.gate_screen(gate, (m, n, "w1"), pack)].name
                assert f == ("paywall.png" if pack_id == "dating" else f"main_{side}.png")


# --- the run and the API ------------------------------------------------------------------------

@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "DIR", tmp_path)
    monkeypatch.setattr(live, "_today", {"day": "", "n": 0})
    return tmp_path


def test_start_checks_images_before_counting_a_run(run_dir, monkeypatch):
    monkeypatch.setattr(live, "_run", lambda *a: None)
    b = live_brief()
    files = {s: PNG for s in live.image_slots("resale", 3)}
    with pytest.raises(ValueError, match="missing images: ad_3"):
        live.start(b, {k: v for k, v in files.items() if k != "ad_3"}, {})
    with pytest.raises(ValueError, match="not a PNG"):
        live.start(b, {**files, "store": b"<html>"}, {})
    assert live._today["n"] == 0
    rid = live.start(b, {**files, "extra": PNG}, {})
    saved = sorted(p.name for p in (run_dir / rid).iterdir())
    assert saved == sorted([f"{s}.png" for s in files] + ["plans.yaml"])
    monkeypatch.setattr(live, "DAILY", 1)
    with pytest.raises(PermissionError):
        live.start(b, files, {})


def multipart(fields):
    boundary = "xyzBOUNDARYxyz"
    body = b""
    for name, data in fields.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{name}.png"\r\n'
                 "Content-Type: application/octet-stream\r\n\r\n").encode() + data + b"\r\n"
    return f"multipart/form-data; boundary={boundary}", body + f"--{boundary}--\r\n".encode()


def test_live_api(run_dir, monkeypatch):
    monkeypatch.setattr(live, "_run", lambda *a: None)
    env = {"ADMIN_KEY": "k"}
    ctype, body = multipart({"brief": json.dumps(live_brief()).encode(),
                             **{s: PNG for s in live.image_slots("resale", 3)}})
    status, _, out = serve.handle_live(env, "POST", "/api/live", "nope", ctype, body)
    assert status == 403
    status, _, out = serve.handle_live(env, "POST", "/api/live", "k", ctype, body)
    assert status == 200, out
    rid = json.loads(out)["id"]
    status, _, out = serve.handle_live(env, "GET", f"/api/live/{rid}", "k", "", b"")
    assert status == 200 and json.loads(out)["state"] == "running" and len(json.loads(out)["steps"]) == 5
    assert serve.handle_live(env, "GET", f"/api/live/{rid}/screen/ad_2", "", "", b"") == (200, "image/png", PNG)
    assert serve.handle_live(env, "GET", f"/api/live/{rid}/screen/nothing", "", "", b"")[0] == 404
    assert serve.handle_live(env, "GET", f"/api/live/{rid}/replay", "k", "", b"")[0] == 404    # not done yet
    assert serve.handle_live(env, "GET", "/api/live/example/resale", "k", "", b"")[0] == 404  # gone in v2
    ctype, body = multipart({s: PNG for s in live.image_slots("resale", 3)})
    status, _, out = serve.handle_live(env, "POST", "/api/live", "k", ctype, body)
    assert status == 400 and b"brief" in out
    ctype, body = multipart({"brief": b"{not json"})
    assert serve.handle_live(env, "POST", "/api/live", "k", ctype, body)[0] == 400


def test_live_paths_are_never_files_outside_the_run():
    for rid, name in (("../../etc", "ad"), ("abcdef123456", "../x"), ("abcdef123456", "a/b")):
        with pytest.raises(KeyError):
            live.screen(rid, name)


def test_a_live_run_end_to_end_with_stubbed_models(run_dir, monkeypatch):
    """The whole run on the resale demo's kinds of people and decision table; any model call fails the test."""
    from engine import run
    from engine.world import spark, typed, wonder

    def no_call(*a, **k):
        raise AssertionError("a paid model call")
    monkeypatch.setattr(spark, "ask_body", no_call)
    monkeypatch.setattr(wonder, "ask", no_call)

    def design(cfg, images, out_path):
        assert [Path(p).name for p in images] == [f"{s}.png" for s in live.image_slots("resale", 3)]
        shutil.copy(ROOT / "data" / "wonder" / "reloop_people.json", out_path)
        shutil.copy(ROOT / "data" / "decisions" / "reloop_spark.json", Path(out_path).with_name("decisions.json"))
    monkeypatch.setattr(typed, "design", design)
    monkeypatch.setattr(run, "wonder_reason", no_call)
    monkeypatch.setattr(live, "RUNS", 2)
    monkeypatch.setattr(live.threading, "Thread", Inline)
    b = live_brief()
    b["setup"]["days"] = 90      # until calibration runs apart from the chosen days (W1), a shorter run cannot fit it
    rid = live.start(b, {s: PNG for s in live.image_slots("resale", 3)}, {})
    st = live.status(rid)
    assert st["state"] == "done", st["error"]
    rep = json.loads(live.replay(rid))
    assert rep["meta"]["live"] and rep["meta"]["brief"]["app"] == "Reloop"
    assert rep["meta"]["pack"]["screens"][0] == f"/api/live/{rid}/screen/store"
    shown = {p["story"]["ad"] for ppl in rep["people"].values() for p in ppl if p["story"].get("ad")}
    assert shown and all(s.startswith(f"/api/live/{rid}/screen/") for s in shown)


class Inline:
    """threading.Thread that runs its target at start(), so the test can wait for the run."""

    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


def test_resolve_screens_points_the_replay_at_the_uploads(tmp_path):
    rep = json.loads(FIXTURE.read_text())
    pack = packs.load("dating")
    slots = live.image_slots("dating", 3)
    images = live.image_map(pack, tmp_path, slots)
    rep["people"]["a"][0]["story"]["last"] = "paywall_m1_many"
    live.resolve_screens(rep, "abcdef123456", images, slots)
    s = rep["people"]["a"][0]["story"]
    assert s["ad"] == "/api/live/abcdef123456/screen/ad_1" and s["last"] == "/api/live/abcdef123456/screen/paywall"
    assert s["sex"] == "w" and rep["meta"]["live"]
    assert rep["meta"]["ads"][0]["screen"] == "/api/live/abcdef123456/screen/ad_1"


# --- report -------------------------------------------------------------------------------------

def check_report(rep):
    keys = [f["key"] for f in rep["meta"]["funnel"]]
    for k, plan in rep["plans"].items():
        stops = Counter((p["story"].get("stop") or {}).get("to") for p in rep["people"][k])
        assert [(r["from"], r["to"]) for r in plan["report"]] == list(zip(keys, keys[1:]))
        for r in plan["report"]:
            assert r["left"] == stops[r["to"]]
            assert len(r["themes"]) <= 3 and sum(t["count"] for t in r["themes"]) <= r["left"]
            assert [t["count"] for t in r["themes"]] == sorted((t["count"] for t in r["themes"]), reverse=True)
            people = {p["id"]: p for p in rep["people"][k]}
            seen = set()
            for t in r["themes"]:
                assert t["count"] == len(t["ids"]) and not seen & set(t["ids"])
                seen |= set(t["ids"])
                assert all(people[i]["story"]["stop"]["to"] == r["to"] for i in t["ids"])
                assert t["quote"] in {people[i]["story"]["stop"]["words"] for i in t["ids"]}
                assert not any(c.isdigit() for c in t["name"]) or t["name"] == t["quote"]
        assert plan["ads"]["line"] and not any(c.isdigit() for c in plan["ads"]["line"])


def test_report_without_wonder_groups_identical_sentences():
    rep = report.build(fixture(), {"app": "Kindred"}, use_wonder=False)
    check_report(rep)
    first = rep["plans"]["b"]["report"][0]
    assert first["themes"][0]["name"] == first["themes"][0]["quote"]


def test_report_counts_wonders_themes_itself(tmp_path, monkeypatch):
    def ask(messages, schema=None, name=None):
        text = messages[0]["content"]
        if name == "ads_line":
            return {"a": "The trust ad did best with people new in town.", "b": "The ads did about the same."}
        labels = [line.split(" ")[0] for line in text.splitlines() if line.startswith("r") and "people)" in line]
        # two themes; a made-up label and a label claimed twice must not change the counts
        return {"themes": [{"name": "first half", "reasons": labels[::2] + ["r99"]},
                           {"name": "Second half", "reasons": labels[1::2] + labels[:1]}]}
    monkeypatch.setattr(report.wonder, "ask", ask)
    cfg = {"app": "Kindred", "verdict_cache": str(tmp_path / "verdicts.json")}
    rep = report.build(fixture(), cfg)
    check_report(rep)
    first = rep["plans"]["a"]["report"][0]
    assert [t["name"] for t in first["themes"]] == ["First half", "Second half"]
    assert sum(t["count"] for t in first["themes"]) == first["left"]
    assert rep["plans"]["a"]["ads"]["line"].startswith("The trust ad")
    assert (tmp_path / "report.json").exists()
    monkeypatch.setattr(report.wonder, "ask", lambda *a, **k: pytest.fail("asked again"))
    assert report.build(fixture(), cfg)["plans"]["a"]["report"] == rep["plans"]["a"]["report"]   # from the cache


def test_report_refuses_wonder_output_with_numbers(tmp_path, monkeypatch):
    calls = []

    def ask(messages, schema=None, name=None):
        calls.append(name)
        if name == "ads_line":
            return {"a": "Ad two won 3 times.", "b": "Fine."}
        return {"themes": [{"name": "Top 3 worries", "reasons": ["r0"]}]}
    monkeypatch.setattr(report.wonder, "ask", ask)
    rep = report.build(fixture(), {"app": "Kindred", "verdict_cache": str(tmp_path / "v.json")}, log=lambda *a: None)
    check_report(rep)
    assert all(t["name"] == t["quote"] for r in rep["plans"]["a"]["report"] for t in r["themes"])
    assert "3" not in rep["plans"]["a"]["ads"]["line"]
    assert calls.count("ads_line") == 2                     # refused once, asked once more, then the plain line
    assert not (tmp_path / "report.json").exists()          # refused answers are not kept


def test_report_leaves_a_v1_replay_alone():
    rep = json.loads((ROOT / "web" / "public" / "replays" / "engine.json").read_text())
    before = copy.deepcopy(rep)
    report.build(rep, {"app": "Kindred"})
    assert rep == before


# --- interview ----------------------------------------------------------------------------------

def test_interview_reads_v2_people_and_why_they_stopped(tmp_path, monkeypatch):
    rid = "abcdef123456"
    (tmp_path / rid).mkdir()
    rep = json.loads(FIXTURE.read_text())
    (tmp_path / rid / "replay.json").write_text(json.dumps(rep))
    monkeypatch.setattr(live, "DIR", tmp_path)
    p = next(x for x in rep["people"]["b"] if (x["story"].get("stop") or {}).get("to") == "paid")
    data, got = interview.person(f"live_{rid}", "b", p["id"])
    text = interview.record(data, "b", got)
    assert got["id"] == p["id"] and p["story"]["stop"]["words"] in text
    ad = next(a for a in rep["meta"]["ads"] if a["id"] == p["ad_id"])
    assert ad["line"] in text and rep["meta"]["brief"]["profile"]["does"] in text
    old = json.loads((ROOT / "web" / "public" / "replays" / "engine.json").read_text())
    assert "Why you stopped" not in interview.record(old, "a", old["people"]["a"][0])

