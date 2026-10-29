"""자리 표시 리플레이 생성기.

진짜 엔진이 나오기 전까지 화면을 만들고 점검하기 위한 가짜 데이터.
형식은 docs/replay-format.md. 표준 라이브러리만 쓴다.

    python3 engine/fake_replay.py
"""

import json
import random
from pathlib import Path

DAYS = 90
OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "replays" / "demo.json"

# 미국 본토 대략 외곽선 (경도, 위도). 시골 사람 위치를 뽑을 때만 쓴다.
US = [(-124.7, 48.4), (-122.8, 49), (-95.2, 49), (-94.8, 49.3), (-89.6, 48), (-84.9, 46.9), (-83.5, 46),
      (-82.5, 45.3), (-82.1, 43), (-79, 42.9), (-76.5, 44.2), (-74.9, 45), (-71.5, 45), (-70, 46.7), (-69.2, 47.4),
      (-67.8, 47.1), (-67, 44.8), (-70.6, 43.1), (-70.2, 41.7), (-73.7, 40.6), (-74, 39.6), (-75.5, 38.5), (-76, 37),
      (-75.5, 35.3), (-77.9, 33.9), (-80.9, 32.1), (-81.4, 30.7), (-80, 26.9), (-80.4, 25.2), (-81.8, 25.9),
      (-82.8, 27.9), (-84.3, 30), (-86.5, 30.4), (-89.6, 30.2), (-90.2, 29.1), (-93.8, 29.7), (-97.2, 27.7),
      (-97.4, 25.9), (-99.1, 26.4), (-101.4, 29.8), (-103.3, 29), (-104.7, 29.9), (-106.5, 31.8), (-108.2, 31.3),
      (-111, 31.3), (-114.8, 32.5), (-117.1, 32.5), (-118.5, 34), (-120.6, 34.6), (-122.5, 37.5), (-123.8, 39.8),
      (-124.2, 41.9), (-124.1, 43.7), (-124, 46.2)]

# (이름, 경도, 위도, 가중치)
METROS = [("New York, New York", -74, 40.7, 8), ("Los Angeles, California", -118.2, 34, 6),
          ("Chicago, Illinois", -87.6, 41.9, 4), ("Houston, Texas", -95.4, 29.8, 3),
          ("Phoenix, Arizona", -112, 33.4, 2.5), ("Philadelphia, Pennsylvania", -75.2, 40, 2),
          ("San Antonio, Texas", -98.5, 29.4, 2), ("San Diego, California", -117.2, 32.7, 2),
          ("Dallas, Texas", -96.8, 32.8, 3), ("Columbus, Ohio", -83, 40, 1.5), ("Seattle, Washington", -122.3, 47.6, 2),
          ("Atlanta, Georgia", -84.4, 33.7, 3), ("Miami, Florida", -80.2, 25.8, 3),
          ("Boston, Massachusetts", -71.1, 42.4, 2.5), ("San Francisco, California", -122.4, 37.8, 3),
          ("Detroit, Michigan", -83, 42.3, 2), ("Minneapolis, Minnesota", -93.3, 45, 1.5),
          ("Portland, Oregon", -122.7, 45.5, 1.5), ("Las Vegas, Nevada", -115.1, 36.2, 1.2),
          ("Charlotte, North Carolina", -80.8, 35.2, 1.5), ("St. Louis, Missouri", -90.2, 38.6, 1.2),
          ("Kansas City, Missouri", -94.6, 39.1, 1), ("Salt Lake City, Utah", -111.9, 40.8, 1),
          ("Nashville, Tennessee", -86.8, 36.2, 1.5), ("Denver, Colorado", -105, 39.7, 2),
          ("Austin, Texas", -97.7, 30.3, 2)]

# 계획 B의 도시: (이름, 경도, 위도, 시작일, 인원, 퍼짐)
B_CITIES = [("Austin, Texas", -97.7, 30.3, 0, 450, 1.1), ("Denver, Colorado", -105, 39.7, 30, 330, 1.0),
            ("Nashville, Tennessee", -86.8, 36.2, 60, 220, 0.9)]

NAMES = ["Maya", "Jordan", "Sam", "Alex", "Riley", "Taylor", "Chris", "Jamie", "Morgan", "Casey", "Avery", "Drew",
         "Priya", "Luis", "Ana", "Marcus", "Jasmine", "Tyler", "Nina", "Omar", "Grace", "Ethan", "Leah", "Kevin"]

MAYA_ID = 482  # 데모 영상 장면 5에서 누르는 사람


def inside(lon, lat):
    c = False
    j = len(US) - 1
    for i in range(len(US)):
        xi, yi = US[i]
        xj, yj = US[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def place_near(r, lon, lat, spread):
    for _ in range(30):
        p = (lon + r.gauss(0, spread), lat + r.gauss(0, spread * 0.8))
        if inside(*p):
            return p
    return lon, lat


def day_or_none(d):
    return round(d, 2) if d is not None and d <= DAYS else None


def person(r, pid, place, lon, lat, reached):
    return {"id": pid, "name": r.choice(NAMES), "age": r.randint(18, 34), "place": place,
            "lon": round(lon, 3), "lat": round(lat, 3), "reached": round(reached, 2),
            "installed": None, "matched": None, "quit": None, "paid": None}


def live(r, p, p_install, p_match, match_delay, p_quit_matched, p_quit_alone, pay):
    """한 사람의 90일. pay(installed, quit) -> 결제일 또는 None."""
    if r.random() >= p_install:
        return
    installed = p["reached"] + r.expovariate(2)
    matched = installed + r.uniform(*match_delay) if r.random() < p_match else None
    if matched is not None:
        quit_day = matched + r.uniform(5, 50) if r.random() < p_quit_matched else None
    else:
        quit_day = installed + r.uniform(0.5, 7) if r.random() < p_quit_alone else None
    paid = pay(installed, quit_day)
    if paid is not None and paid <= DAYS:
        quit_day = None  # v1: 결제자는 떠나지 않는다
    p["installed"] = day_or_none(installed)
    p["matched"] = day_or_none(matched) if p["installed"] is not None else None
    p["quit"] = day_or_none(quit_day) if p["installed"] is not None else None
    p["paid"] = day_or_none(paid) if p["installed"] is not None else None


def plan_a(r):
    total = sum(m[3] for m in METROS)
    people = []
    for pid in range(1000):
        reached = r.uniform(0, 60)  # 전국 광고는 60일 동안 고르게 집행
        if r.random() < 0.18:
            while True:
                lon, lat = r.uniform(-125, -66.5), r.uniform(24.5, 49.5)
                if inside(lon, lat):
                    break
            p = person(r, pid, "Small town", lon, lat, reached)
            live(r, p, 0.55, 0.05, (2, 12), 0.6, 0.95, lambda i, q: None)
        else:
            pick, k = r.uniform(0, total), 0
            while pick > METROS[k][3]:
                pick -= METROS[k][3]
                k += 1
            name, lon, lat, _ = METROS[k]
            p = person(r, pid, name, *place_near(r, lon, lat, 0.7), reached)
            # 첫날부터 유료: 설치 직후 결제하거나, 아니면 하루 5번 스와이프로 버틴다
            live(r, p, 0.62, 0.36, (1, 10), 0.8, 0.95,
                 lambda i, q: i + r.uniform(0, 2) if r.random() < 0.045 else None)
        people.append(p)
    maya = people[MAYA_ID]
    maya.update({"name": "Maya", "age": 24, "place": "Columbus, Ohio", "lon": -83.0, "lat": 40.0,
                 "reached": 0.8, "installed": 1.0, "matched": None, "quit": 3.2, "paid": None})
    return people


def plan_b(r):
    people, pid = [], 0
    for name, lon, lat, start, n, spread in B_CITIES:
        for _ in range(n):
            p = person(r, pid, name, *place_near(r, lon, lat, spread), start + r.uniform(0, 20))

            def pay(installed, quit_day):
                trial_end = installed + 30  # 30일 무료
                if quit_day is not None and quit_day < trial_end:
                    return None
                return trial_end + r.uniform(0, 3) if r.random() < 0.09 else None

            live(r, p, 0.64, 0.66, (0.5, 5), 0.4, 0.85, pay)
            people.append(p)
            pid += 1
    return people


def pair_matches(r, people):
    """같은 동네에서 매칭된 사람끼리 짝을 지어 선으로 그린다."""
    by_place = {}
    for p in people:
        if p["matched"] is not None and p["place"] != "Small town":
            by_place.setdefault(p["place"], []).append(p)
    pairs = []
    for group in by_place.values():
        group.sort(key=lambda p: p["matched"])
        for i in range(0, len(group) - 1, 2):
            a, b = group[i], group[i + 1]
            pairs.append([a["id"], b["id"], max(a["matched"], b["matched"])])
        if len(group) % 2 and len(group) > 1:
            a, b = group[-1], r.choice(group[:-1])
            pairs.append([a["id"], b["id"], a["matched"]])
    return pairs


def funnel(people):
    inst = [p for p in people if p["installed"] is not None]
    return [len(people), len(inst), sum(p["matched"] is not None for p in inst),
            sum(p["quit"] is None for p in inst), sum(p["paid"] is not None for p in inst)]


def main():
    r = random.Random(20261028)
    people = {"a": plan_a(r), "b": plan_b(r)}
    replay = {
        "version": 1,
        "meta": {"app": "Kindred", "market": "United States", "days": DAYS, "budget_usd": 40000,
                 "placeholder": True},
        "plans": {
            "a": {"name": "Plan A", "summary": "Nationwide ads · paywall from day 1",
                  "events": [{"day": 0, "label": "Ads + paywall"}]},
            "b": {"name": "Plan B", "summary": "Austin → Denver → Nashville · free for 30 days",
                  "events": [{"day": 0, "label": "Austin"}, {"day": 30, "label": "Denver · paywall"},
                             {"day": 60, "label": "Nashville"}]},
        },
        "verdict": {
            "winner": "b",
            "headline": "Plan B wins.",
            "reason": "In Austin, new users find a match before they give up. "
                      "Spread across the country, most of Plan A's users never do.",
        },
        "people": people,
        "matches": {k: pair_matches(r, v) for k, v in people.items()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(replay, ensure_ascii=False, separators=(",", ":")))
    for k in "ab":
        print(k, "reached/installed/matched/still using/paying:", funnel(people[k]))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
