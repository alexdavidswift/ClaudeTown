"""World state: creation, loading, and saving.

The entire town is a single JSON document (``state/world.json``). Keeping the
state as plain dicts -- rather than rich objects -- means it serializes
trivially and tolerates schema growth: new sessions can add fields and read old
worlds with ``.get(key, default)`` without migrations.

Schema (top level):
    seed        int      -- master seed; the sim is reproducible from this
    name        str      -- the town's name
    founded     str      -- human date string of founding
    tick        int      -- months elapsed since founding (0-based)
    next_id     int      -- monotonic id allocator for citizens & buildings
    citizens    {id: citizen}
    buildings   {id: building}
    treasury    int      -- the town's shared coffers
    history     [event]  -- notable events, each {tick, kind, text}
    timeseries  {metric: [values]} -- one value per tick, for charts
    weather     str      -- current month's weather
    schema_version int
"""

from __future__ import annotations

import json
import os
import random
from typing import Any

from . import data

SCHEMA_VERSION = 2

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(_ROOT, "state", "world.json")


def root() -> str:
    return _ROOT


# --- Persistence -----------------------------------------------------------

def exists() -> bool:
    return os.path.exists(STATE_PATH)


def load() -> dict[str, Any]:
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        world = json.load(fh)
    return migrate(world)


def migrate(world: dict[str, Any]) -> dict[str, Any]:
    """Upgrade an older save in place so new fields exist on every record.

    Old worlds remain valid: we only *add* fields with sensible defaults and
    backfill stable building coordinates deterministically from the seed, so a
    town founded under schema v1 keeps unfolding without a reset.
    """
    ver = world.get("schema_version", 1)
    if ver >= SCHEMA_VERSION:
        return world

    if ver < 2:
        for c in world["citizens"].values():
            c.setdefault("reputation", 0)
            c.setdefault("title", None)
            c.setdefault("deeds", [])
        # Backfill placement for buildings that predate stored coordinates.
        # Rebuild a temporary world view so _place_building sees a growing set.
        mrng = random.Random(f"{world['seed']}:migrate-v2")
        placed: dict[str, Any] = {}
        shim = {"buildings": placed}
        for bid, b in sorted(world["buildings"].items(),
                             key=lambda kv: kv[1].get("founded_tick", 0)):
            if "x" not in b or "y" not in b:
                place = _place_building(shim, mrng, b["type"])
                b["x"], b["y"], b["district"] = place["x"], place["y"], place["district"]
            placed[bid] = b

    world["schema_version"] = SCHEMA_VERSION
    return world


def save(world: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(world, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, STATE_PATH)


# --- Date helpers ----------------------------------------------------------

def date_parts(tick: int) -> tuple[int, int]:
    """Return (year, month_index) for a given tick (month count)."""
    return tick // 12, tick % 12


def date_str(tick: int) -> str:
    year, month = date_parts(tick)
    return f"{data.MONTHS[month]}, Year {year + 1}"


def season(tick: int) -> str:
    return data.SEASON_OF_MONTH[tick % 12]


# --- Construction helpers --------------------------------------------------

def _new_id(world: dict[str, Any]) -> str:
    nid = world["next_id"]
    world["next_id"] = nid + 1
    return str(nid)


def make_citizen(
    world: dict[str, Any],
    rng: random.Random,
    *,
    age_months: int,
    gender: str | None = None,
    surname: str | None = None,
    home: str | None = None,
) -> dict[str, Any]:
    """Create and register a citizen, returning the new record."""
    if gender is None:
        gender = rng.choices(["f", "m", "n"], weights=[47, 47, 6])[0]
    if gender == "f":
        given = rng.choice(data.GIVEN_NAMES_F)
    elif gender == "m":
        given = rng.choice(data.GIVEN_NAMES_M)
    else:
        given = rng.choice(data.GIVEN_NAMES_N)
    if surname is None:
        surname = rng.choice(data.SURNAMES)

    n_traits = rng.choice([2, 2, 3, 3, 3, 4])
    traits = rng.sample(data.TRAITS, n_traits)

    cid = _new_id(world)
    citizen = {
        "id": cid,
        "name": f"{given} {surname}",
        "given": given,
        "surname": surname,
        "gender": gender,
        "age_months": age_months,
        "born_tick": world["tick"] - age_months,
        "traits": traits,
        "job": None,
        "workplace": None,
        "home": home,
        "wealth": rng.randint(0, 8),
        "health": rng.randint(70, 100),
        "mood": rng.randint(45, 75),
        "partner": None,
        "children": [],
        "parents": [],
        "friends": [],
        "rivals": [],
        "alive": True,
        "died_tick": None,
        "epitaph": None,
        "milestones": [],
        # Reputation & identity (schema v2). Reputation drifts with deeds and
        # office; title is an earned epithet ("the Elder", "the Kind", ...).
        "reputation": 0,
        "title": None,
        "deeds": [],
    }
    world["citizens"][cid] = citizen
    return citizen


# --- Building placement ----------------------------------------------------

def _place_building(world: dict[str, Any], rng: random.Random, btype: str) -> dict[str, float]:
    """Assign stable map coordinates (and a district) at construction time.

    Buildings are laid out on a golden-angle spiral around the town square so
    the town grows organically outward and the layout never reshuffles as new
    buildings appear -- a building keeps the same neighbors for life. Civic
    structures cluster near the centre, homes ring them, farms sit outermost.
    Coordinates live in an abstract 0..100 space; the viewer scales them.
    """
    import math

    if btype == "farm":
        category, base, step = "farm", 30.0, 4.2
    elif btype == "house":
        category, base, step = "house", 16.0, 3.4
    else:
        category, base, step = "civic", 3.0, 3.0

    index = sum(1 for b in world["buildings"].values()
                if _category(b["type"]) == category)
    angle = index * 2.39996323  # golden angle in radians
    radius = base + step * math.sqrt(index + 1)
    jitter = (rng.random() - 0.5) * 4.0
    cx, cy = 50.0, 46.0
    x = cx + (radius + jitter) * math.cos(angle)
    y = cy + (radius + jitter) * math.sin(angle) * 0.8  # squash: town is wider than tall
    return {
        "x": round(max(2.0, min(98.0, x)), 2),
        "y": round(max(2.0, min(98.0, y)), 2),
        "district": _district_for(x, y),
    }


def _category(btype: str) -> str:
    if btype == "farm":
        return "farm"
    if btype == "house":
        return "house"
    return "civic"


def _district_for(x: float, y: float) -> str:
    """Name a quarter of town from a coordinate, for flavor."""
    ns = "North" if y < 46 else "South"
    ew = "East" if x >= 50 else "West"
    # The very centre is the Square regardless of quadrant.
    if 38 <= x <= 62 and 34 <= y <= 58:
        return "the Market Square"
    return f"the {ns}{ew.lower()} Quarter"


def make_building(
    world: dict[str, Any],
    rng: random.Random,
    btype: str,
    *,
    name: str | None = None,
) -> dict[str, Any]:
    spec = data.BUILDING_TYPES[btype]
    if name is None:
        if btype == "house":
            name = "Cottage"
        else:
            name = (
                f"{rng.choice(data.BUILDING_NAME_ADJ)} "
                f"{rng.choice(data.BUILDING_NAME_NOUN)} "
                f"{btype.replace('_', ' ').title()}"
            )
    place = _place_building(world, rng, btype)
    bid = _new_id(world)
    building = {
        "id": bid,
        "name": name,
        "type": btype,
        "icon": spec["icon"],
        "founded_tick": world["tick"],
        "employs": spec["employs"],
        "workers": [],
        "residents": [],
        # Stable map placement (schema v2).
        "x": place["x"],
        "y": place["y"],
        "district": place["district"],
    }
    world["buildings"][bid] = building
    return building


# --- Founding --------------------------------------------------------------

TIMESERIES_METRICS = ["population", "treasury", "buildings", "avg_mood", "births", "deaths"]


def found_town(seed: int | None = None, name: str | None = None) -> dict[str, Any]:
    """Create a brand-new town with a handful of founding families."""
    if seed is None:
        seed = random.randint(1, 2**31)
    rng = random.Random(f"{seed}:founding")

    if name is None:
        name = (
            f"{rng.choice(data.BUILDING_NAME_ADJ)}"
            f"{rng.choice(data.BUILDING_NAME_NOUN).lower()}"
        )

    world: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "name": name,
        "founded": date_str(0),
        "tick": 0,
        "next_id": 1,
        "citizens": {},
        "buildings": {},
        "treasury": 40,
        "history": [],
        "timeseries": {m: [] for m in TIMESERIES_METRICS},
        "weather": rng.choice(data.WEATHER_BY_SEASON[season(0)]),
    }

    # The founders: three or four families plus a couple of lone settlers.
    n_families = rng.randint(3, 4)
    for _ in range(n_families):
        surname = rng.choice(data.SURNAMES)
        home = make_building(world, rng, "house")
        a = make_citizen(world, rng, age_months=rng.randint(22 * 12, 40 * 12),
                         gender="f", surname=surname, home=home["id"])
        b = make_citizen(world, rng, age_months=rng.randint(22 * 12, 40 * 12),
                         gender="m", surname=surname, home=home["id"])
        a["partner"], b["partner"] = b["id"], a["id"]
        a["milestones"].append({"tick": 0, "text": "a founder of the town"})
        b["milestones"].append({"tick": 0, "text": "a founder of the town"})
        home["residents"] = [a["id"], b["id"]]
        if rng.random() < 0.6:
            child = make_citizen(world, rng, age_months=rng.randint(0, 16 * 12),
                                 surname=surname, home=home["id"])
            child["parents"] = [a["id"], b["id"]]
            a["children"].append(child["id"])
            b["children"].append(child["id"])
            home["residents"].append(child["id"])

    for _ in range(rng.randint(1, 2)):
        home = make_building(world, rng, "house")
        loner = make_citizen(world, rng, age_months=rng.randint(20 * 12, 55 * 12),
                             home=home["id"])
        loner["milestones"].append({"tick": 0, "text": "a founder of the town"})
        home["residents"] = [loner["id"]]

    # The founding farm feeds everyone.
    make_building(world, rng, "farm", name="The Old Commons")

    world["history"].append({
        "tick": 0,
        "kind": "founding",
        "text": (
            f"{name} was founded in {date_str(0)} by "
            f"{len(world['citizens'])} settlers, who raised their first roofs "
            f"and broke ground on the Old Commons."
        ),
    })
    return world
