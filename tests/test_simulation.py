"""Tests for the ClaudeTown engine.

These guard the invariants that future sessions must not break: determinism,
referential integrity of the world graph, and the round-trip of save/load.

Run with:  python3 -m pytest -q   (or)   python3 tests/test_simulation.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claudetown import simulation, world as worldmod, chronicle, render  # noqa: E402


def fresh(seed=12345, months=0):
    w = worldmod.found_town(seed=seed, name="Testburg")
    for _ in range(months):
        simulation.advance_month(w)
    return w


def check_integrity(w):
    ids = set(w["citizens"])
    bids = set(w["buildings"])
    for c in w["citizens"].values():
        if c["partner"]:
            assert c["partner"] in ids, "partner id dangling"
        for k in c["children"]:
            assert k in ids, "child id dangling"
        for p in c["parents"]:
            assert p in ids, "parent id dangling"
        if c["home"]:
            assert c["home"] in bids, "home id dangling"
        if c["workplace"]:
            assert c["workplace"] in bids, "workplace id dangling"
        for f in c["friends"]:
            assert f in ids
        for r in c["rivals"]:
            assert r in ids
    for b in w["buildings"].values():
        for wkr in b["workers"]:
            assert wkr in ids, "worker id dangling"


def test_founding_is_valid():
    w = fresh()
    assert w["tick"] == 0
    assert len(w["citizens"]) >= 6
    assert any(b["type"] == "farm" for b in w["buildings"].values())
    check_integrity(w)


def test_determinism():
    """Same seed -> identical history. This is the core guarantee."""
    a = fresh(seed=999, months=60)
    b = fresh(seed=999, months=60)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_seeds_diverge():
    a = fresh(seed=1, months=40)
    b = fresh(seed=2, months=40)
    assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


def test_integrity_over_time():
    w = fresh(seed=7, months=120)
    check_integrity(w)


def test_timeseries_length_matches_ticks():
    w = fresh(seed=3, months=30)
    for metric, vals in w["timeseries"].items():
        assert len(vals) == 30, f"{metric} has {len(vals)} entries, expected 30"


def test_workers_never_exceed_capacity():
    w = fresh(seed=42, months=200)
    from claudetown import data
    for b in w["buildings"].values():
        live = [x for x in b["workers"] if w["citizens"][x]["alive"]]
        assert len(live) <= data.BUILDING_TYPES[b["type"]]["employs"]


def test_dead_have_no_active_jobs():
    w = fresh(seed=8, months=150)
    for c in w["citizens"].values():
        if not c["alive"]:
            for b in w["buildings"].values():
                assert c["id"] not in b["workers"], f"dead {c['id']} still employed"


def test_save_load_roundtrip():
    w = fresh(seed=5, months=12)
    w2 = json.loads(json.dumps(w))
    assert json.dumps(w2, sort_keys=True) == json.dumps(w, sort_keys=True)


def test_chronicle_render_no_crash():
    w = worldmod.found_town(seed=11, name="Inkwell")
    for _ in range(24):
        chron = simulation.advance_month(w)
        text = chronicle.render_month(w, chron)
        assert isinstance(text, str) and text.strip()


def test_web_export_is_valid_js():
    w = fresh(seed=6, months=10)
    path = render.export_web(w)
    with open(path) as fh:
        content = fh.read()
    assert content.startswith("//")
    assert "window.WORLD =" in content


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed.")
