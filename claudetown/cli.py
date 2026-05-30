"""Command-line interface for ClaudeTown.

Usage:
    python3 -m claudetown.cli found [--seed N] [--name NAME]   # create a new town
    python3 -m claudetown.cli tick [--months N]                # advance the town
    python3 -m claudetown.cli status                           # print a summary
    python3 -m claudetown.cli who [--id ID | --search TEXT]    # inspect citizens
    python3 -m claudetown.cli rebuild                          # re-export artifacts

The town's whole life is in ``state/world.json``. ``tick`` advances time,
writes chronicle prose under ``chronicles/``, and refreshes the web map and
README stats.
"""

from __future__ import annotations

import argparse
import sys

from . import chronicle, render, simulation
from . import world as worldmod
from .simulation import living, _age_years


def _require_world():
    if not worldmod.exists():
        print("No town yet. Run:  python3 -m claudetown.cli found", file=sys.stderr)
        sys.exit(1)
    return worldmod.load()


def cmd_found(args):
    if worldmod.exists() and not args.force:
        print("A town already exists. Use --force to raze it and start over.",
              file=sys.stderr)
        sys.exit(1)
    world = worldmod.found_town(seed=args.seed, name=args.name)
    worldmod.save(world)
    render.export_all(world)
    print(f"Founded {world['name']} (seed {world['seed']}) with "
          f"{len(world['citizens'])} settlers.")
    print(world["history"][0]["text"])


def cmd_tick(args):
    world = _require_world()
    months = args.months
    summary = {"births": 0, "deaths": 0, "notable": []}
    surfaced = {"marriage", "construction", "festival", "disaster", "wonder", "death"}
    for _ in range(months):
        chron = simulation.advance_month(world)
        chronicle.append_month(world, chron)
        summary["births"] += chron["births"]
        summary["deaths"] += chron["deaths"]
        for ev in chron["events"]:
            # Surface notable events; deaths only when they reached the history log.
            if ev["kind"] in surfaced and (ev["kind"] != "death" or
                                           _in_history(world, chron["tick"], ev["text"])):
                summary["notable"].append(f"  [{chron['date']}] {ev['text']}")
    worldmod.save(world)
    render.export_all(world)

    print(f"Advanced {months} month(s) to {worldmod.date_str(world['tick'])}.")
    print(f"  Population: {len(living(world))}   Treasury: {world['treasury']}   "
          f"Buildings: {len(world['buildings'])}")
    print(f"  Births: {summary['births']}   Deaths: {summary['deaths']}")
    if summary["notable"]:
        print("  Notable events:")
        for line in summary["notable"][:40]:
            print(line)


def _in_history(world, tick, text):
    return any(h["tick"] == tick and h["text"] == text for h in world["history"][-12:])


def cmd_status(args):
    world = _require_world()
    alive = living(world)
    print(f"=== {world['name']} ===")
    print(f"Date: {worldmod.date_str(world['tick'])}   (tick {world['tick']})")
    print(f"Founded: {world['founded']}   Seed: {world['seed']}")
    print(f"Population: {len(alive)} living ({len(world['citizens'])} ever recorded)")
    print(f"Buildings: {len(world['buildings'])}   Treasury: {world['treasury']} coins")
    print(f"Weather: {world['weather']}")
    print()
    print("Buildings:")
    for b in sorted(world["buildings"].values(), key=lambda b: b["founded_tick"]):
        workers = [world["citizens"][w]["name"] for w in b["workers"]
                   if w in world["citizens"] and world["citizens"][w]["alive"]]
        extra = f" — staff: {', '.join(workers)}" if workers else ""
        print(f"  [{b['type']}] {b['name']}{extra}")
    print()
    print("Recent history:")
    for ev in world["history"][-8:]:
        print(f"  {worldmod.date_str(ev['tick'])}: {ev['text']}")


def cmd_who(args):
    world = _require_world()
    if args.id:
        c = world["citizens"].get(args.id)
        if not c:
            print("No such citizen.", file=sys.stderr)
            sys.exit(1)
        _print_citizen(world, c)
        return
    matches = [c for c in world["citizens"].values()
               if not args.search or args.search.lower() in c["name"].lower()]
    matches.sort(key=lambda c: (not c["alive"], -c["age_months"]))
    for c in matches[: args.limit]:
        status = "" if c["alive"] else " (deceased)"
        job = f", {c['job']}" if c["job"] else ""
        print(f"  {c['id']}: {c['name']}, {_age_years(c)}{job}{status}")


def _print_citizen(world, c):
    print(f"=== {c['name']} (id {c['id']}) ===")
    print(f"Age: {_age_years(c)}   {'alive' if c['alive'] else 'deceased'}")
    print(f"Traits: {', '.join(c['traits'])}")
    if c["job"]:
        wp = world["buildings"].get(c["workplace"], {}).get("name", "?")
        print(f"Work: {c['job']} at {wp}")
    if c["partner"] and c["partner"] in world["citizens"]:
        print(f"Partner: {world['citizens'][c['partner']]['name']}")
    if c["children"]:
        kids = [world["citizens"][k]["name"] for k in c["children"] if k in world["citizens"]]
        print(f"Children: {', '.join(kids)}")
    print(f"Wealth: {c['wealth']}   Mood: {c['mood']}   Health: {c['health']}")
    if c["milestones"]:
        print("Life:")
        for m in c["milestones"]:
            print(f"  {worldmod.date_str(m['tick'])}: {m['text']}")
    if not c["alive"] and c["epitaph"]:
        print(f"Epitaph: {c['epitaph']}")


def cmd_rebuild(args):
    world = _require_world()
    render.export_all(world)
    print("Re-exported web/world.js and README stats.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="claudetown", description="A persistent generative town.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("found", help="create a new town")
    pf.add_argument("--seed", type=int, default=None)
    pf.add_argument("--name", type=str, default=None)
    pf.add_argument("--force", action="store_true")
    pf.set_defaults(func=cmd_found)

    pt = sub.add_parser("tick", help="advance the town in time")
    pt.add_argument("--months", type=int, default=1)
    pt.set_defaults(func=cmd_tick)

    ps = sub.add_parser("status", help="print a summary of the town")
    ps.set_defaults(func=cmd_status)

    pw = sub.add_parser("who", help="inspect citizens")
    pw.add_argument("--id", type=str, default=None)
    pw.add_argument("--search", type=str, default=None)
    pw.add_argument("--limit", type=int, default=25)
    pw.set_defaults(func=cmd_who)

    pr = sub.add_parser("rebuild", help="re-export web + README artifacts")
    pr.set_defaults(func=cmd_rebuild)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
