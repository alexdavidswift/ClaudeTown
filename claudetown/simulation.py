"""The simulation engine: advance the town one month and narrate it.

Every tick is driven by a *derived* RNG seeded from the master seed and the
tick number (``f"{seed}:{tick}"``). This makes the whole history reproducible:
given the same seed and the same starting state, the town unfolds identically.
That property is what lets the world live in version control and be trusted
across sessions.

``advance_month`` mutates the world dict in place and returns a Chronicle for
that month -- a structured list of the things that happened, which
``chronicle.py`` renders into prose.
"""

from __future__ import annotations

import random
from typing import Any

from . import data, world as worldmod

ADULT = 18 * 12       # months at which a citizen is considered an adult
ELDER = 60 * 12
MAX_FERTILE = 45 * 12
MIN_FERTILE = 19 * 12


def _rng(world: dict[str, Any]) -> random.Random:
    return random.Random(f"{world['seed']}:{world['tick']}")


def _age_years(c: dict[str, Any]) -> int:
    return c["age_months"] // 12


def living(world: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in world["citizens"].values() if c["alive"]]


def _has(c: dict[str, Any], *traits: str) -> bool:
    return any(t in c["traits"] for t in traits)


def _trait_score(c: dict[str, Any], pool: set[str]) -> int:
    return sum(1 for t in c["traits"] if t in pool)


def full_name(c: dict[str, Any]) -> str:
    """A citizen's name including any earned title, e.g. 'Ada the Elder'.

    Titles that are honorific prefixes (like 'Master') read better before the
    given name; epithets ('the Kind') read better after the full name.
    """
    title = c.get("title")
    if not title:
        return c["name"]
    if title == data.TITLE_THE_MASTER:
        return f"{data.TITLE_THE_MASTER} {c['name']}"
    return f"{c['name']} {title}"


# --- Mortality -------------------------------------------------------------

def _monthly_death_chance(c: dict[str, Any]) -> float:
    """A gentle Gompertz-style curve plus health penalties."""
    years = _age_years(c)
    annual = 0.004 + 0.00004 * (max(0, years - 20) ** 1.9) / 30.0
    if years < 3:
        annual += 0.02  # infant fragility
    annual += (100 - c["health"]) * 0.0009
    monthly = annual / 12.0
    return min(monthly, 0.25)


# --- The monthly tick ------------------------------------------------------

def advance_month(world: dict[str, Any]) -> dict[str, Any]:
    world["tick"] += 1
    tick = world["tick"]
    rng = _rng(world)
    season = worldmod.season(tick)
    weather = rng.choice(data.WEATHER_BY_SEASON[season])
    world["weather"] = weather

    chron: dict[str, Any] = {
        "tick": tick,
        "date": worldmod.date_str(tick),
        "season": season,
        "weather": weather,
        "events": [],
        "births": 0,
        "deaths": 0,
    }

    def record(kind: str, text: str, ids: list[str] | None = None, notable: bool = False):
        chron["events"].append({"kind": kind, "text": text, "ids": ids or []})
        if notable:
            world["history"].append({"tick": tick, "kind": kind, "text": text})

    # 1. Age everyone a month.
    for c in living(world):
        c["age_months"] += 1
        if c["age_months"] == ADULT:
            c["milestones"].append({"tick": tick, "text": "came of age"})

    # 2. Economy: each worker earns; the town taxes a little.
    _run_economy(world, rng, season, weather)

    # 3. Jobs: assign the unemployed to open posts.
    _assign_jobs(world, rng)

    # 4. Relationships: friendships, rivalries, courtship, marriage, children.
    _social_round(world, rng, tick, chron, record)

    # 5. Construction: the town invests its coffers in new buildings.
    _maybe_build(world, rng, tick, record)

    # 6. Mood drift influenced by weather, wealth, and ties.
    _update_moods(world, rng, season, weather)

    # 7. Mortality.
    _run_mortality(world, rng, tick, chron, record)

    # 8. Rare town-wide events (festivals, disasters, discoveries).
    _town_events(world, rng, tick, season, chron, record)

    # 9. Reconcile reputations and award newly-earned titles.
    _award_titles(world, tick, record)

    # 10. Record time series.
    _snapshot(world, chron)

    return chron


# --- Economy ---------------------------------------------------------------

def _run_economy(world, rng, season, weather):
    harvest_bonus = 1.0
    if season in ("summer", "autumn"):
        harvest_bonus = 1.3
    if any(w in weather for w in ("heat", "thunder", "snow", "sleet")):
        harvest_bonus *= 0.85

    income = 0
    for c in living(world):
        if not c["job"]:
            continue
        base = 2
        if c["job"] in ("farmer", "shepherd", "orchardist", "miller"):
            base = int(round(3 * harvest_bonus))
        elif c["job"] in ("merchant", "trader", "grocer", "blacksmith", "innkeeper"):
            base = 4
        elif c["job"] in ("mayor", "priest", "astronomer", "playwright"):
            base = 5
        if _has(c, "industrious", "ambitious"):
            base += 1
        if _has(c, "lazy"):
            base = max(1, base - 1)
        c["wealth"] += base
        income += base
    world["treasury"] += income // 5


# --- Jobs ------------------------------------------------------------------

def _open_positions(world) -> list[tuple[str, str]]:
    """Return (building_id, job_title) pairs that are currently unfilled."""
    out = []
    for b in world["buildings"].values():
        spec = data.BUILDING_TYPES[b["type"]]
        if not spec["jobs"]:
            continue
        live_workers = [w for w in b["workers"]
                        if w in world["citizens"] and world["citizens"][w]["alive"]]
        slots = spec["employs"] - len(live_workers)
        for i in range(slots):
            title = spec["jobs"][i % len(spec["jobs"])]
            out.append((b["id"], title))
    return out


def _assign_jobs(world, rng):
    seekers = [c for c in living(world)
               if c["job"] is None and c["age_months"] >= ADULT and _age_years(c) < 68]
    rng.shuffle(seekers)
    positions = _open_positions(world)
    rng.shuffle(positions)
    seekers.sort(key=lambda c: -_trait_score(c, data.TRAIT_AMBITIOUS))

    for c in seekers:
        if not positions:
            break
        bid, title = positions.pop()
        b = world["buildings"][bid]
        c["job"] = title
        c["workplace"] = bid
        if c["id"] not in b["workers"]:
            b["workers"].append(c["id"])
        c["milestones"].append({"tick": world["tick"], "text": f"became {title} at {b['name']}"})


# --- Social round ----------------------------------------------------------

def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _social_round(world, rng, tick, chron, record):
    pop = living(world)
    if len(pop) < 2:
        return

    # Friendships & rivalries from chance encounters.
    encounters = min(len(pop), 4 + len(pop) // 6)
    for _ in range(encounters):
        a, b = rng.sample(pop, 2)
        if b["id"] in a["friends"] or b["id"] in a["rivals"]:
            continue
        social = _trait_score(a, data.TRAIT_SOCIAL) + _trait_score(b, data.TRAIT_SOCIAL)
        prickly = _trait_score(a, data.TRAIT_PRICKLY) + _trait_score(b, data.TRAIT_PRICKLY)
        roll = rng.random() + social * 0.06 - prickly * 0.05
        if roll > 0.85:
            a["friends"].append(b["id"]); b["friends"].append(a["id"])
            a["reputation"] += 1; b["reputation"] += 1
            record("friendship",
                   f"{a['name']} and {b['name']} struck up a fast friendship.",
                   [a["id"], b["id"]])
        elif roll < 0.18 and prickly > 0:
            a["rivals"].append(b["id"]); b["rivals"].append(a["id"])
            a["reputation"] -= 1; b["reputation"] -= 1
            record("rivalry",
                   f"A quarrel soured things between {a['name']} and {b['name']}.",
                   [a["id"], b["id"]])

    # Reconciliation: old rivals can bury the hatchet, the more so if either is
    # patient or tender-hearted. A healed feud sometimes becomes a friendship.
    for a in pop:
        for rid in list(a["rivals"]):
            b = world["citizens"].get(rid)
            if not b or not b["alive"] or a["id"] >= b["id"]:
                continue  # handle each pair once, in id order
            mend = 0.04 + 0.03 * (_has(a, "patient", "tender-hearted", "humble")
                                  + _has(b, "patient", "tender-hearted", "humble"))
            if rng.random() < mend:
                a["rivals"].remove(rid)
                if a["id"] in b["rivals"]:
                    b["rivals"].remove(a["id"])
                if rng.random() < 0.45 and b["id"] not in a["friends"]:
                    a["friends"].append(b["id"]); b["friends"].append(a["id"])
                    a["reputation"] += 1; b["reputation"] += 1
                    record("reconciliation",
                           f"{a['name']} and {b['name']} made peace at last, their "
                           f"old quarrel turning to friendship.",
                           [a["id"], b["id"]], notable=True)
                else:
                    record("reconciliation",
                           f"{a['name']} and {b['name']} quietly set aside their feud.",
                           [a["id"], b["id"]])

    # Courtship & marriage.
    singles = [c for c in pop
               if c["partner"] is None and c["age_months"] >= ADULT and _age_years(c) < 70]
    rng.shuffle(singles)
    used: set[str] = set()
    for a in singles:
        if a["id"] in used or rng.random() > 0.12:
            continue
        candidates = [b for b in singles
                      if b["id"] != a["id"] and b["id"] not in used
                      and b["id"] not in a["rivals"]
                      and abs(a["age_months"] - b["age_months"]) < 18 * 12]
        if not candidates:
            continue
        candidates.sort(key=lambda b: (b["id"] not in a["friends"], rng.random()))
        b = candidates[0]
        a["partner"], b["partner"] = b["id"], a["id"]
        used.add(a["id"]); used.add(b["id"])
        _move_in_together(world, a, b)
        a["milestones"].append({"tick": tick, "text": f"married {b['name']}"})
        b["milestones"].append({"tick": tick, "text": f"married {a['name']}"})
        record("marriage",
               f"{a['name']} and {b['name']} were wed beneath the {worldmod.season(tick)} sky.",
               [a["id"], b["id"]], notable=True)

    # Births to married couples of fertile age.
    couples_done: set[tuple[str, str]] = set()
    for a in pop:
        if not a["partner"]:
            continue
        b = world["citizens"].get(a["partner"])
        if not b or not b["alive"]:
            continue
        key = _pair_key(a["id"], b["id"])
        if key in couples_done:
            continue
        couples_done.add(key)
        if not (MIN_FERTILE <= a["age_months"] <= MAX_FERTILE
                and MIN_FERTILE <= b["age_months"] <= MAX_FERTILE):
            continue
        chance = 0.035 * (0.7 ** len(a["children"]))
        if rng.random() < chance:
            home = a["home"] or b["home"]
            surname = a["surname"] if rng.random() < 0.5 else b["surname"]
            child = worldmod.make_citizen(world, rng, age_months=0,
                                          surname=surname, home=home)
            child["parents"] = [a["id"], b["id"]]
            child["wealth"] = 0
            a["children"].append(child["id"]); b["children"].append(child["id"])
            if home and home in world["buildings"]:
                world["buildings"][home]["residents"].append(child["id"])
            a["reputation"] += 1; b["reputation"] += 1
            chron["births"] += 1
            record("birth",
                   f"{child['name']} was born to {a['name']} and {b['name']}.",
                   [child["id"], a["id"], b["id"]])


def _move_in_together(world, a, b):
    home = a["home"] or b["home"]
    if not home:
        return
    a["home"] = b["home"] = home
    b_home = world["buildings"].get(home)
    if b_home:
        for cid in (a["id"], b["id"]):
            if cid not in b_home["residents"]:
                b_home["residents"].append(cid)


# --- Construction ----------------------------------------------------------

def _maybe_build(world, rng, tick, record):
    pop = len(living(world))

    # Build houses when crowding gets bad.
    houses = [b for b in world["buildings"].values() if b["type"] == "house"]
    housed = sum(len(b["residents"]) for b in houses)
    if houses and housed / max(1, len(houses)) > 4 \
            and world["treasury"] >= data.BUILDING_TYPES["house"]["cost"]:
        world["treasury"] -= data.BUILDING_TYPES["house"]["cost"]
        worldmod.make_building(world, rng, "house")

    # Build the next civic structure in order, if affordable & warranted.
    have = {b["type"] for b in world["buildings"].values()}
    for btype in data.CIVIC_BUILD_ORDER:
        if btype in have:
            continue
        spec = data.BUILDING_TYPES[btype]
        if pop >= spec["min_pop"] and world["treasury"] >= spec["cost"]:
            world["treasury"] -= spec["cost"]
            b = worldmod.make_building(world, rng, btype)
            record("construction",
                   f"The townsfolk raised {b['name']} -- {spec['desc']}.",
                   notable=True)
            break  # one civic project per month

    # A second (or third) farm once the town is sizeable.
    farms = [b for b in world["buildings"].values() if b["type"] == "farm"]
    if pop > 18 and len(farms) < (pop // 14) and world["treasury"] >= 30:
        world["treasury"] -= 30
        worldmod.make_building(world, rng, "farm")


# --- Mood ------------------------------------------------------------------

def _update_moods(world, rng, season, weather):
    for c in living(world):
        delta = rng.randint(-3, 3)
        if season == "summer" or any(w in weather for w in ("warm", "golden", "sun")):
            delta += 1
        if any(w in weather for w in ("frost", "sleet", "bitter")):
            delta -= 1
        if c["job"]:
            delta += 1
        if c["partner"]:
            delta += 1
        delta += len(c["friends"]) - len(c["rivals"])
        if _has(c, "merry", "dreamy"):
            delta += 1
        if _has(c, "melancholy", "dour", "anxious"):
            delta -= 1
        c["mood"] = max(0, min(100, c["mood"] + delta))


# --- Mortality -------------------------------------------------------------

EPITAPHS = [
    "remembered for a ready laugh",
    "who never let a stranger go hungry",
    "whose stories outlived the telling",
    "a steady hand in every storm",
    "gone to the quiet fields",
    "who loved this town to the last",
    "missed at every hearth",
    "whose work still stands",
]


def _run_mortality(world, rng, tick, chron, record):
    for c in living(world):
        if rng.random() < _monthly_death_chance(c):
            c["alive"] = False
            c["died_tick"] = tick
            c["epitaph"] = rng.choice(EPITAPHS)
            chron["deaths"] += 1
            if c["workplace"] and c["workplace"] in world["buildings"]:
                wk = world["buildings"][c["workplace"]]["workers"]
                if c["id"] in wk:
                    wk.remove(c["id"])
            if c["partner"] and c["partner"] in world["citizens"]:
                p = world["citizens"][c["partner"]]
                if p["alive"]:
                    p["partner"] = None
                    p["milestones"].append({"tick": tick, "text": f"was widowed by {c['name']}"})
            years = _age_years(c)
            founder = any("founder of the town" in m["text"] for m in c["milestones"])
            titled = bool(c.get("title"))
            notable = years >= 70 or founder or titled or c["job"] in ("mayor", "priest")
            who = full_name(c)
            record("death",
                   f"{who} died at {years}, {c['epitaph']}.",
                   [c["id"]], notable=notable)


# --- Town-wide events ------------------------------------------------------

def _town_events(world, rng, tick, season, chron, record):
    pop = len(living(world))
    if pop == 0:
        return
    roll = rng.random()

    # Harvest festival each autumn.
    if season == "autumn" and tick % 12 == 8 and rng.random() < 0.8:
        for c in living(world):
            c["mood"] = min(100, c["mood"] + 6)
        record("festival",
               "The Harvest Festival filled the square with lanterns, music, "
               "and the smell of spiced cider.", notable=True)
        return

    if roll < 0.04 and pop >= 6:
        kind = rng.choice(["fire", "storm", "fever"])
        if kind == "fire":
            houses = [b for b in world["buildings"].values()
                      if b["type"] == "house" and b["residents"]]
            if houses:
                b = rng.choice(houses)
                record("disaster",
                       f"A fire gutted {b['name']}; neighbors took the family in "
                       f"while it was rebuilt.", notable=True)
                for cid in b["residents"]:
                    cc = world["citizens"].get(cid)
                    if cc and cc["alive"]:
                        cc["mood"] = max(0, cc["mood"] - 12)
        elif kind == "storm":
            world["treasury"] = max(0, world["treasury"] - rng.randint(8, 20))
            record("disaster",
                   "A violent storm tore through the town, costing the coffers "
                   "dearly in repairs.", notable=True)
        else:
            victims = rng.sample(living(world), min(pop, rng.randint(2, 5)))
            for v in victims:
                v["health"] = max(10, v["health"] - rng.randint(15, 35))
            record("disaster",
                   f"A fever passed through {world['name']}, laying {len(victims)} "
                   f"of the townsfolk low.", notable=True)
    elif roll > 0.97 and pop >= 10:
        wonders = [
            "A traveling cartographer mapped the hills and named three new lanes.",
            "Children found a clutch of fossils in the creek bed.",
            "A rare comet hung over the valley for a week of clear nights.",
            "The town's first cider won praise from passing merchants.",
            "An old well, long dry, suddenly ran sweet and cold again.",
        ]
        record("wonder", rng.choice(wonders), notable=True)


# --- Reputation & earned titles --------------------------------------------

def _job_tenure_months(c: dict[str, Any], tick: int) -> int:
    """Months since the citizen last took up their current post."""
    if not c["job"]:
        return 0
    starts = [m["tick"] for m in c["milestones"] if m["text"].startswith("became ")]
    return tick - max(starts) if starts else 0


def _best_title(c: dict[str, Any], tick: int) -> str | None:
    """Choose the most fitting earned title for a citizen this month.

    Evaluated from most to least prestigious; the first qualifying title wins.
    A citizen never *loses* a title once earned (see ``_award_titles``), but a
    grander one can supersede it.
    """
    years = _age_years(c)
    friends, rivals = len(c["friends"]), len(c["rivals"])
    founder = any("founder of the town" in m["text"] for m in c["milestones"])

    if years >= 80:
        return data.TITLE_THE_PATRIARCH
    if years >= 68:
        return data.TITLE_THE_ELDER
    if founder and years >= 55:
        return data.TITLE_THE_FOUNDER
    if c["job"] in data.SKILLED_JOBS and _job_tenure_months(c, tick) >= 18 * 12:
        return data.TITLE_THE_MASTER
    if len(c["children"]) >= 5:
        return data.TITLE_THE_PROLIFIC
    if friends >= 5 and rivals == 0 and c["reputation"] >= 6:
        return data.TITLE_THE_BELOVED
    if c["job"] in data.SCHOLARLY_JOBS and _job_tenure_months(c, tick) >= 8 * 12:
        return data.TITLE_THE_LEARNED
    # Wealth grows slowly and is never spent, so "the Wealthy" must be both a
    # large fortune and a settled life -- not something a young earner trips.
    if c["wealth"] >= 500 and years >= 35:
        return data.TITLE_THE_WEALTHY
    if _trait_score(c, data.TRAIT_SOCIAL) >= 2 and c["reputation"] >= 8:
        return data.TITLE_THE_KIND
    if rivals >= 3 and c["reputation"] <= -4:
        return data.TITLE_THE_QUARRELSOME
    return None


# Rough prestige ranking so a citizen only ever trades up to a grander title.
_TITLE_RANK = {
    data.TITLE_THE_QUARRELSOME: 0,
    data.TITLE_THE_WEALTHY: 1,
    data.TITLE_THE_LEARNED: 2,
    data.TITLE_THE_KIND: 2,
    data.TITLE_THE_BELOVED: 3,
    data.TITLE_THE_PROLIFIC: 3,
    data.TITLE_THE_MASTER: 4,
    data.TITLE_THE_FOUNDER: 5,
    data.TITLE_THE_ELDER: 6,
    data.TITLE_THE_PATRIARCH: 7,
}


def _award_titles(world, tick, record):
    for c in living(world):
        # A little reputation reverts toward zero each year so the living must
        # keep earning it; deeds and ties counter the drift.
        if tick % 12 == 0 and c["reputation"]:
            c["reputation"] -= 1 if c["reputation"] > 0 else -1

        candidate = _best_title(c, tick)
        if not candidate:
            continue
        current = c.get("title")
        if candidate == current:
            continue
        # Only adopt a title at least as prestigious as the one already held.
        if current and _TITLE_RANK.get(candidate, 0) <= _TITLE_RANK.get(current, 0):
            continue
        c["title"] = candidate
        c["milestones"].append({"tick": tick, "text": f"became known as {full_name(c)}"})
        # The Quarrelsome earns no honor; everything else is a point of pride.
        if candidate != data.TITLE_THE_QUARRELSOME:
            record("title",
                   f"{c['name']} came to be known throughout {world['name']} as "
                   f"{full_name(c)}.",
                   [c["id"]], notable=True)
        else:
            record("title",
                   f"{c['name']} earned a sharp reputation as {full_name(c)}.",
                   [c["id"]])


# --- Snapshot --------------------------------------------------------------

def _snapshot(world, chron):
    pop = living(world)
    ts = world["timeseries"]
    ts["population"].append(len(pop))
    ts["treasury"].append(world["treasury"])
    ts["buildings"].append(len(world["buildings"]))
    ts["avg_mood"].append(round(sum(c["mood"] for c in pop) / len(pop), 1) if pop else 0)
    ts["births"].append(chron["births"])
    ts["deaths"].append(chron["deaths"])
