"""Where people left and why: the v2 report (docs/replay-format.md "Version 2", plans[k].report).

For each step of the funnel, the people who reached the step before it but never this one
(`story.stop.to`), and the reasons they gave (`story.stop.words`). Muse Wonder names up to three
themes per step and sorts each distinct reason into one of them, or none; the engine counts the
people, picks each theme's most common sentence as its quote and keeps the people's ids, so no
number on the Report screen comes from the model. Also the one line under the ads table
(plans[k].ads.line).

    build(rep, cfg, use_wonder=True, log=print)   # fills rep in place; called by engine/run.py rehearse

One Wonder call per funnel step covers both plans, so A and B are sorted into the same themes and
read side by side. Answers are saved by input (like the verdict), so a rerun with the same facts
costs nothing. Wonder output with a digit in it, or one that does not fit, is refused; then (or
with use_wonder=False) identical sentences are grouped and the most common three are the themes.
A v1 replay (no meta.funnel) is left as it is.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from . import wonder

ROOT = Path(__file__).resolve().parent.parent.parent
MAX_THEMES = 3
MAX_SENTENCES = 300          # distinct reasons sent to Wonder per step, most common first
SHORT_LIST = 60              # the second try when Wonder cannot answer for the long list
MAX_NAME = 48                # characters in a theme name



THEMES_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["themes"],
    "properties": {"themes": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["name", "reasons"],
        "properties": {"name": {"type": "string", "description": "Two to six plain words, no numbers."},
                       "reasons": {"type": "array", "items": {"type": "string",
                                                              "description": "A reason's label, like r0."}}}}}},
}
LINE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["a", "b"],
    "properties": {k: {"type": "string", "description": "One plain sentence, under 20 words, no numbers."}
                   for k in ("a", "b")},
}

# What leaving at each step means, for Wonder's question
LEFT_AT = {
    "installed": "saw the app's ad or store page and did not install it",
    "signed_up": "installed the app and did not finish signing up",
    "first": "signed up and never got to the app's first success",
    "active": "got a first success and then stopped using the app",
    "paid": "kept using the app and never paid",
}


def build(rep, cfg, use_wonder=True, log=print):
    """Add plans[k].report and plans[k].ads["line"] to the replay, in place."""
    funnel = rep.get("meta", {}).get("funnel")
    if not funnel or not rep.get("people"):
        return rep
    keys = [f["key"] for f in funnel]
    labels = {f["key"]: f["label"] for f in funnel}
    cache = Cache(cfg)
    reports = {k: [] for k in rep["plans"]}
    for frm, to in zip(keys, keys[1:]):
        left = {k: [p for p in rep["people"].get(k, []) if (p.get("story", {}).get("stop") or {}).get("to") == to]
                for k in rep["plans"]}
        said = {k: {p["id"]: _clean(p["story"]["stop"].get("words")) for p in ppl} for k, ppl in left.items()}
        counts = Counter(w for k in said for w in said[k].values() if w)
        sentences = [w for w, _ in counts.most_common(MAX_SENTENCES)]
        groups = None
        if use_wonder and sentences:
            for few in (sentences, sentences[:SHORT_LIST]):     # a shorter list when the long one fails
                try:
                    groups = _wonder_themes(cfg, rep, labels[frm], labels[to], to, few, counts, cache)
                    break
                except (SystemExit, Exception) as e:     # Wonder down, or an answer that does not fit
                    log(f"report: Wonder themes for {to} with {len(few)} reasons refused ({str(e)[:120]})")
                if len(sentences) <= SHORT_LIST:
                    break
            if groups is None:
                log(f"report: grouping identical sentences for {to}")
        if groups is None:
            groups = [(s, {s}) for s in sentences[:MAX_THEMES]]
        for k in rep["plans"]:
            reports[k].append({"from": frm, "to": to, "left": len(left[k]), "themes": _count(groups, said[k])})
    for k, plan in rep["plans"].items():
        plan["report"] = reports[k]
    _ads_line(rep, cfg, use_wonder, cache, log)
    return rep


def _clean(words):
    return " ".join(words.split()) if isinstance(words, str) and words.strip() else None


def _count(groups, said):
    """[(name, set of sentences)] and {person id: sentence} -> themes with the people counted, biggest first."""
    themes = []
    for name, members in groups:
        ids = [pid for pid, w in said.items() if w in members]
        if not ids:
            continue
        quote = Counter(said[pid] for pid in ids).most_common(1)[0][0]
        themes.append({"name": name, "count": len(ids), "quote": quote, "ids": sorted(ids)})
    themes.sort(key=lambda t: -t["count"])
    return themes[:MAX_THEMES]


def _app_words(cfg, rep):
    brief = cfg.get("brief") or rep["meta"].get("brief") or {}
    what = (brief.get("profile") or {}).get("does") or rep["meta"].get("pack", {}).get("category", "a new app")
    return f"{rep['meta']['app']} ({what})"


def _wonder_themes(cfg, rep, frm_label, to_label, to, sentences, counts, cache):
    listed = "\n".join(f"r{i} ({counts[s]} people): {s}" for i, s in enumerate(sentences))
    text = (f"A launch rehearsal of {_app_words(cfg, rep)} asked simulated people why they did what they did. "
            f"These are the reasons of the people who {LEFT_AT.get(to, f'reached {frm_label} but not {to_label}')} "
            f"(funnel step: {frm_label} -> {to_label}), each with how many people said it:\n{listed}\n\n"
            f"Group the reasons into at most {MAX_THEMES} themes that a founder can act on, biggest first. Name each "
            "theme in two to six plain words a non-expert understands (for example 'Not sure the people are real'), "
            "with no numbers and no jargon. For each theme, list the labels (r0, r1, ...) of the reasons above that "
            "belong to it. A reason belongs to one theme at most; leave out a reason that fits none.")
    return cache.ask(text, THEMES_SCHEMA, "themes", lambda out: _themes_from(out, sentences))


def _themes_from(out, sentences):
    """Wonder's themes -> [(name, set of sentences)], or ValueError when the answer does not fit.

    A label that names no listed reason is dropped, and a reason listed twice stays in its first theme.
    """
    label = {f"r{i}": s for i, s in enumerate(sentences)}
    groups, used = [], set()
    for t in out["themes"][:MAX_THEMES]:
        name = " ".join(str(t["name"]).split()).strip(" .")
        if not name or len(name) > MAX_NAME or any(c.isdigit() for c in name):
            raise ValueError(f"theme name {name[:60]!r}")
        members = {label[r] for r in map(str, t["reasons"]) if r in label and r not in used}
        used |= set(map(str, t["reasons"]))
        if members:
            groups.append((name[0].upper() + name[1:], members))
    if not groups:
        raise ValueError("no reason sorted into a theme")
    return groups


def _ads_line(rep, cfg, use_wonder, cache, log):
    tables = {k: p["ads"]["cells"] for k, p in rep["plans"].items() if (p.get("ads") or {}).get("cells")}
    if not tables:
        return
    kinds = {c["id"]: c["name"] for c in rep["meta"].get("kinds", [])}
    ads = {a["id"]: a for a in rep["meta"].get("ads", [])}
    lines = {k: _template_line(cells, kinds, ads) for k, cells in tables.items()}
    if use_wonder and set(tables) == {"a", "b"}:
        try:
            lines = _wonder_lines(cfg, rep, tables, kinds, ads, cache)
        except (SystemExit, Exception) as e:
            log(f"report: Wonder ads line refused ({str(e)[:120]}); using the plain line")
    for k in tables:
        rep["plans"][k]["ads"]["line"] = lines[k]


def _ad_words(ads, ad_id):
    a = ads.get(ad_id) or {}
    return f"the {a['angle']} ad" if a.get("angle") and a["angle"] != "other" else f"the ad \"{a.get('line', ad_id)}\""


def _best(cells):
    """(kind id, ad id) with the highest install rate among the cells most people saw."""
    seen = [(n, kind, ad) for kind, row in cells.items() for ad, (n, _i) in row.items() if n]
    if not seen:
        return None
    floor = max(n for n, _k, _a in seen) / 4          # a cell only a handful saw is noise
    return max(((row[ad][1] / row[ad][0], kind, ad) for kind, row in cells.items() for ad in row
                if row[ad][0] and row[ad][0] >= floor), default=(0, None, None))[1:]


def _template_line(cells, kinds, ads):
    best = _best(cells)
    if not best or best[0] is None:
        return "Too few people saw the ads to tell them apart."
    kind, ad = best
    words = _ad_words(ads, ad)
    return f"{words[0].upper()}{words[1:]} worked best with \"{kinds.get(kind, kind)}\"."


def _wonder_lines(cfg, rep, tables, kinds, ads, cache):
    table = {rep["plans"][k]["name"]: {kinds.get(kind, kind): {_ad_words(ads, ad): f"{i} of {n} installed"
                                                               for ad, (n, i) in row.items()}
                                       for kind, row in cells.items()} for k, cells in tables.items()}
    text = (f"A launch rehearsal of {_app_words(cfg, rep)} showed each simulated person one of these ads:\n"
            + "\n".join(f"- {_ad_words(ads, a)}: \"{ads[a].get('line', '')}\"" for a in ads)
            + f"\n\nWho saw which ad and how many of them installed, per kind of person and plan:\n"
            f"{json.dumps(table, indent=1)}\n\nFor each plan (a = {rep['plans']['a']['name']}, b = "
            f"{rep['plans']['b']['name']}), write the one line a founder reads under this table: which ad worked "
            "with which kind of people, in plain words: the single clearest difference, one short sentence under 12 "
            "words (for example 'The trust ad won over the people who distrust dating apps.'). Use no numbers. Say "
            "only what the table supports; if the ads did about the same, say so.")
    return cache.ask(text, LINE_SCHEMA, "ads_line", _lines_from)


def _lines_from(out):
    lines = {}
    for k in ("a", "b"):
        line = " ".join(str(out[k]).split())
        if not line or len(line) > 90 or any(c.isdigit() for c in line):
            raise ValueError(f"ads line {line!r}")
        lines[k] = line
    return lines


class Cache:
    """Wonder's answers by input, next to the verdicts (live runs: in the run folder)."""

    def __init__(self, cfg):
        if "verdict_cache" in cfg:
            self.path = Path(cfg["verdict_cache"]).with_name("report.json")
        else:
            self.path = ROOT / "data" / "wonder" / f"{cfg.get('app', 'app').lower()}_report.json"
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def ask(self, text, schema, name, check):
        """check(answer) -> what the caller uses, or an error; only an answer that passes is kept."""
        key = hashlib.sha256((name + text).encode()).hexdigest()[:16]
        if key in self.data:
            return check(self.data[key])
        for attempt in (1, 2):           # Wonder sometimes answers off the point; one more try
            out = wonder.ask([{"role": "user", "content": text}], schema, name)
            try:
                result = check(out)
                break
            except ValueError:
                if attempt == 2:
                    raise
        self.data[key] = out
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1))
        return result
