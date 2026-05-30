# ClaudeTown

> A persistent, generative town that grows a little more each session.

ClaudeTown is a tiny simulated settlement that lives **inside this repository**.
Every time the town advances, its people are born, grow up, take up trades, fall
in love, quarrel and reconcile, earn names for themselves, raise new buildings,
weather storms and festivals, and eventually pass on — and every month of its
life is written down. The whole world is a single committed JSON file, and the
engine is **deterministic from a seed**, so the town's entire history is
reproducible and accumulates over time.

This is built to be continued. Each session adds to the story.

🌐 **Live viewer:** https://alexdavidswift.github.io/ClaudeTown/

<!-- TOWN-STATS:START -->

**Hearthvale** &nbsp;·&nbsp; *Frostwane, Year 15* &nbsp;·&nbsp; founded Frostwane, Year 1

| Metric | Value |
|:--|:--|
| Population (living) | **11** |
| Souls ever recorded | 17 (6 at rest) |
| Buildings | 11 |
| Treasury | 405 coins |
| Employed | 6 of 11 |
| Years simulated | 15 |
| Eldest resident | Petra Greenhollow the Wealthy, age 50 |
| Largest family | the Thistledowns (6) |
| Citizens of note | Bran Coppersmith the Wealthy, Roman Thistledown the Prolific, Petra Greenhollow the Wealthy, Viktor Greenhollow the Wealthy |

_Stats and the map under `web/` regenerate every time the town advances._

<!-- TOWN-STATS:END -->

## What's here

```
claudetown/        the engine (pure Python standard library, no dependencies)
  data.py          names, traits, building types, titles, the calendar
  world.py         world creation, persistence, schema migration, date math
  simulation.py    the monthly "tick": aging, work, love, building, death, fame
  chronicle.py     turns each month's events into prose + a yearly review
  render.py        exports the web viewer data + these README stats
  cli.py           the command line
state/world.json   the entire town — the single source of truth
chronicles/        the town's written history, one Markdown file per year
web/               a zero-dependency visual viewer (open web/index.html)
tests/             invariants: determinism, integrity, capacity, round-trips
```

## Running it

```bash
# Advance the town by a year and write the chronicle
python3 -m claudetown.cli tick --months 12

# See where things stand
python3 -m claudetown.cli status

# Look someone up (titles, family, life story)
python3 -m claudetown.cli who --search Thistledown
python3 -m claudetown.cli who --id 3

# Re-export the web viewer + README stats without advancing time
python3 -m claudetown.cli rebuild

# Start an entirely new town (overwrites the current one)
python3 -m claudetown.cli found --seed 1848 --name Hearthvale --force
```

Then open **`web/index.html`** in a browser (or visit the live link above) to
see the map, growth charts, the roster of townsfolk, and the timeline of
notable events.

## How it works

Each tick is one in-world month. The month's randomness is seeded from
`f"{seed}:{tick}"`, so the same town always unfolds the same way. A tick:

1. ages everyone by a month,
2. pays out wages and tithes the treasury,
3. fills open jobs (ambitious folk first),
4. runs the social round — friendships, rivalries, **reconciliations**,
   courtship, marriage, births,
5. builds the next civic structure when the town is large and flush enough,
   placing it at **stable map coordinates** in a named district,
6. drifts everyone's mood with the weather and their relationships,
7. applies mortality (a gentle age-rising hazard),
8. rolls for town-wide events — harvest festivals, fires, storms, fevers, wonders,
9. reconciles reputations and awards **earned titles** ("the Elder", "the
   Prolific", "Master", "the Beloved"…),
10. records a data point for the growth charts.

At each year's end the chronicler writes a **Year in Review** that counts the
weddings, births, and trials and calls them against the town's deeper past
("the eighth Harvest Festival in the town's memory").

The result is a small, legible piece of emergent history. Read the
[`chronicles/`](chronicles/) to follow the story.

## Tests

```bash
python3 tests/test_simulation.py      # or: python3 -m pytest -q
```

---

*ClaudeTown is an experiment in software that accrues: a world that is a little
larger and a little older every time someone returns to it.*
