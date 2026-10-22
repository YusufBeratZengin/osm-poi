"""Overpass QL query builder."""

from __future__ import annotations

import re
from collections.abc import Sequence

from osm_poi.areas import Area, OsmArea
from osm_poi.errors import AreaError
from osm_poi.presets import ANY, Preset, TagSet

_REGEX_SPECIAL = re.compile(r"([.^$*+?()\[\]{}|\\])")


def quote(value: str) -> str:
    """Quote a string for Overpass QL."""
    if "\n" in value or "\r" in value:
        raise ValueError("Newlines are not allowed in query values.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _regex_escape(value: str) -> str:
    return _REGEX_SPECIAL.sub(r"\\\1", value)


def tag_filter(key: str, values: tuple[str, ...]) -> str:
    """One ``["key"="value"]`` style filter."""
    if values == (ANY,):
        return f"[{quote(key)}]"
    if len(values) == 1:
        return f"[{quote(key)}={quote(values[0])}]"
    pattern = "^(" + "|".join(_regex_escape(v) for v in values) + ")$"
    return f"[{quote(key)}~{quote(pattern)}]"


def tag_set_filter(tag_set: TagSet) -> str:
    return "".join(tag_filter(key, values) for key, values in tag_set.items())


def build_query(
    areas: Sequence[Area],
    presets: Sequence[Preset],
    timeout: int = 90,
    max_size: int | None = None,
) -> str:
    """Return an Overpass QL query selecting nodes, ways and relations (with centres)."""
    if not areas:
        raise AreaError("At least one search area is required.")
    if not presets:
        raise ValueError("At least one preset is required.")

    header = f"[out:json][timeout:{int(timeout)}]"
    if max_size is not None:
        header += f"[maxsize:{int(max_size)}]"
    lines = [header + ";"]

    seen_ids: set[int] = set()
    for area in areas:
        if isinstance(area, OsmArea) and area.area_id not in seen_ids:
            seen_ids.add(area.area_id)
            lines.append(area.definition())

    lines.append("(")
    for area in areas:
        scope = area.overpass_filter()
        for preset in presets:
            for tag_set in preset.tag_sets:
                lines.append(f"  nwr{tag_set_filter(tag_set)}{scope};")
    lines.append(");")
    lines.append("out center tags;")
    return "\n".join(lines) + "\n"
