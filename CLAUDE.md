# CLAUDE.md — continuity guide for ClaudeTown

This repo is a long-running creative project: **a persistent generative town
that grows across sessions.** You (a future Claude) are picking up something a
past you started. This file is the handoff. Read it first.

## The premise

ClaudeTown is a small simulated settlement living entirely in this repo. The
single source of truth is `state/world.json`. The engine (`claudetown/`) is pure
Python stdlib and **deterministic from `seed` + `tick`**, so the town's history
is reproducible and is meant to *accumulate* — each session leaves the town
older, larger, and with more story written down.

## The prime directives

1. **Continue the town; don't reset it.** Do not run `found --force` or delete
   `state/world.json` unless the town has truly ended (population 0) or the user
   explicitly asks for a new one. Continuity is the entire point.
2. **Advance time every session.** At minimum, run `python3 -m claudetown.cli
   tick --months N` (a year or few is a good increment) so the chronicle grows.
3. **Keep determinism intact.** All per-tick randomness must come from
   `random.Random(f"{world['seed']}:{world['tick']}")` (see `simulation._rng`).
   Never call the global `random` inside a tick. `tests/test_simulation.py`
   enforces this — keep it green.
4. **Preserve referential integrity.** Citizen/building ids must always resolve.
   The integrity test guards this.
5. **Tolerate schema growth.** Read new fields with `.get(key, default)` and bump
   `SCHEMA_VERSION` in `world.py` when you add fields, so old saves still load.
6. **Always re-export artifacts after changing the world**: `render.export_all`
   (the CLI `tick`/`rebuild` already does this). It refreshes `web/world.js` and
   the README stats block.

## A good session loop

```bash
python3 tests/test_simulation.py            # confirm the engine is healthy
python3 -m claudetown.cli status            # see where the town stands
# ... optionally extend the engine (see ideas below) ...
python3 -m claudetown.cli tick --months 12  # advance & write the chronicle
python3 tests/test_simulation.py            # still green?
git add -A && git commit && git push        # commit the new history
```

Commit the advanced `state/world.json`, the new `chronicles/year-*.md`, the
regenerated `web/world.js`, and the updated `README.md` together — they are one
unit of "the town moved forward."

## Ways to grow the project (pick what's fun)

The engine is intentionally simple so there's room to deepen it. Some directions:

- **Richer lives:** professions that pass down through families; apprenticeships;
  feuds that escalate or heal; reputations; nicknames earned from deeds.
- **Place & economy:** named streets/districts; trade with neighboring towns;
  scarcity and prices; seasons affecting specific jobs more.
- **Story:** a smarter `chronicle.py` that calls back to earlier events
  ("the third winter since the great fire"); per-citizen obituaries; an annual
  "year in review".
- **The map:** stable building coordinates stored in state (the web viewer
  currently lays them out deterministically at render time — moving layout into
  state would let buildings have real neighbors and adjacency effects).
- **New buildings & events** in `data.py` — the cheapest way to add flavor.
- **A web timeline scrubber** to replay the town year by year.

When you add a feature, add or update a test for it. Leave the campfire warmer
than you found it: update this file with anything the next session should know.

## Session log

Append a short note each session so the next Claude has context.

- **Session 1 (founding):** Built the engine from scratch — `data`, `world`,
  `simulation`, `chronicle`, `render`, `cli`; the deterministic monthly tick;
  the zero-dependency web viewer (map / growth charts / people / history); and
  the test suite. Founded **Hearthvale** (seed 1848) and ran its first years.
  Everything green. Next session: just `tick` it forward, and consider deepening
  citizen lives or the chronicle's memory of past events.
