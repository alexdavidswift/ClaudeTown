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

    order = ["birth", "marriage", "friendship", "rivalry", "construction",
             "festival", "wonder", "disaster", "death"]
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
