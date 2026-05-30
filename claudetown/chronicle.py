"""Render a month's events into a prose chronicle entry.

The simulation produces structured event lists; this module turns them into the
town's written record. Chronicles are append-only: each year gets its own file
under ``chronicles/`` so the town's story accumulates as readable Markdown.
"""

from __future__ import annotations

import os
from typing import Any

from . import world as worldmod

_OPENERS = {
    "winter": [
        "Snow lay on the rooftops as",
        "Through the short cold days of",
        "Under a hard frost in",
    ],
    "spring": [
        "With the thaw of",
        "As the first green returned in",
        "In the soft rains of",
    ],
    "summer": [
        "Under the long sun of",
        "Through the warm weeks of",
        "In the golden light of",
    ],
    "autumn": [
        "As the leaves turned in",
        "Through the harvest weeks of",
        "Under amber skies in",
    ],
}


def _opener(tick: int, season: str, month_name: str) -> str:
    options = _OPENERS[season]
    return f"{options[tick % len(options)]} {month_name}"


def render_month(world: dict[str, Any], chron: dict[str, Any]) -> str:
    """Return a Markdown block for a single month."""
    tick = chron["tick"]
    month_name = chron["date"].split(",")[0]
    lines: list[str] = [f"### {chron['date']}", ""]

    if not chron["events"]:
        lines.append(
            f"{_opener(tick, chron['season'], month_name)}, "
            f"{world['name']} passed a quiet month under {chron['weather']}. "
            f"{_population_note(world)}"
        )
        lines.append("")
        return "\n".join(lines)

    lines.append(
        f"{_opener(tick, chron['season'], month_name)}, the weather turned to "
        f"{chron['weather']}."
    )
    lines.append("")

    order = ["birth", "marriage", "title", "friendship", "reconciliation",
             "rivalry", "construction", "festival", "wonder", "disaster", "death"]
    grouped: dict[str, list[str]] = {}
    for ev in chron["events"]:
        grouped.setdefault(ev["kind"], []).append(ev["text"])

    for kind in order:
        for text in grouped.get(kind, []):
            lines.append(f"- {text}")
    for kind, texts in grouped.items():
        if kind not in order:
            for text in texts:
                lines.append(f"- {text}")

    lines.append("")
    lines.append(_population_note(world))
    lines.append("")
    return "\n".join(lines)


def _population_note(world: dict[str, Any]) -> str:
    pop = sum(1 for c in world["citizens"].values() if c["alive"])
    bld = len(world["buildings"])
    return (
        f"*{world['name']} now numbers {pop} souls across {bld} buildings, "
        f"with {world['treasury']} coins in the common treasury.*"
    )


_ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh",
             "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth",
             "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth",
             "nineteenth", "twentieth"]


def _ordinal(n: int) -> str:
    if 1 <= n <= len(_ORDINALS):
        return _ORDINALS[n - 1]
    return f"{n}th"


def render_year_review(world: dict[str, Any], year: int, months: list[dict[str, Any]]) -> str:
    """Render a reflective summary of a completed year.

    ``months`` is the list of month-chronicles produced during the year. This
    reads only facts already recorded (it draws no randomness), so it stays
    deterministic. It also reaches back into ``world['history']`` to call the
    present moment against the past -- "the third Harvest Festival", and so on.
    """
    births = sum(m["births"] for m in months)
    deaths = sum(m["deaths"] for m in months)
    evs = [e for m in months for e in m["events"]]

    def of(kind):
        return [e for e in evs if e["kind"] == kind]

    lines: list[str] = ["", "---", "", f"### The Year in Review — Year {year}", ""]

    pop = sum(1 for c in world["citizens"].values() if c["alive"])
    opening = (
        f"So closed the {_ordinal(year)} year of {world['name']}. "
        f"The town counted {pop} living souls as the snows of Yuleweald came on"
    )
    weddings = of("marriage")
    new_builds = of("construction")
    titles = of("title")
    disasters = of("disaster")
    festivals = of("festival")

    if births or deaths:
        opening += (
            f", having welcomed {births} new {_plural(births, 'child', 'children')} "
            f"and laid {deaths} to rest"
        )
    opening += "."
    lines.append(opening)
    lines.append("")

    if weddings:
        lines.append(f"- **{len(weddings)} {_plural(len(weddings), 'wedding', 'weddings')}** "
                     "were celebrated.")
    if new_builds:
        names = "; ".join(e["text"].split("raised ", 1)[-1].split(" -- ")[0]
                          for e in new_builds)
        lines.append(f"- The town raised **{names}**.")
    if titles:
        for e in titles:
            lines.append(f"- {e['text']}")
    if festivals:
        n_fest = _count_prior(world, "festival", year)
        lines.append(f"- The Harvest Festival was held — the {_ordinal(n_fest)} in the "
                     f"town's memory.")
    if disasters:
        n_dis = _count_prior(world, "disaster", year)
        lines.append(f"- The town endured hardship: {disasters[0]['text'].rstrip('.')}"
                     f" — the {_ordinal(len(disasters))} such trial this year, and the "
                     f"{_ordinal(n_dis)} in all its years.")

    lines.append("")
    lines.append(_population_note(world))
    lines.append("")
    return "\n".join(lines)


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _count_prior(world: dict[str, Any], kind: str, through_year: int) -> int:
    """How many events of a kind have occurred in the town's whole history,
    counting only up through the end of the given year."""
    cutoff = through_year * 12  # exclusive upper bound on tick
    return sum(1 for h in world["history"]
               if h["kind"] == kind and h["tick"] < cutoff)


def append_year_review(world: dict[str, Any], year: int, months: list[dict[str, Any]]) -> str:
    """Append the year-in-review to the year's chronicle file."""
    if not months:
        return ""
    path = chronicle_path(world, months[-1]["tick"])
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(render_year_review(world, year, months))
        fh.write("\n")
    return path


def chronicle_path(world: dict[str, Any], tick: int) -> str:
    year, _ = worldmod.date_parts(tick)
    folder = os.path.join(worldmod.root(), "chronicles")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"year-{year + 1:03d}.md")


def append_month(world: dict[str, Any], chron: dict[str, Any]) -> str:
    """Append a month's rendered chronicle to the right yearly file."""
    path = chronicle_path(world, chron["tick"])
    year, _ = worldmod.date_parts(chron["tick"])
    new_file = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        if new_file:
            fh.write(f"# {world['name']} — Year {year + 1}\n\n")
            fh.write(
                "_From the Chronicle of "
                f"{world['name']}, founded {world['founded']}._\n\n"
            )
        fh.write(render_month(world, chron))
        fh.write("\n")
    return path
