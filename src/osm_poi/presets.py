"""Category presets: friendly names mapped to OSM tag filters.

A preset holds one or more *tag sets*. A feature matches the preset when it
matches at least one tag set (OR); inside a tag set every key must match (AND).
A value is a string, a list of strings (any of), or ``"*"`` (key exists).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from osm_poi.errors import PresetError

ANY = "*"

TagSet = Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class Preset:
    name: str
    label: str
    tag_sets: tuple[TagSet, ...]

    def matches(self, tags: Mapping[str, str]) -> bool:
        for tag_set in self.tag_sets:
            if all(_value_matches(tags.get(key), values) for key, values in tag_set.items()):
                return True
        return False


def _value_matches(actual: str | None, wanted: tuple[str, ...]) -> bool:
    if actual is None:
        return False
    return wanted == (ANY,) or actual in wanted


def _parse_tag_set(preset: str, raw: Any) -> TagSet:
    if not isinstance(raw, dict) or not raw:
        raise PresetError(f"Preset {preset!r}: each tag set must be a non-empty object.")
    parsed: dict[str, tuple[str, ...]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise PresetError(f"Preset {preset!r}: tag keys must be non-empty strings.")
        if isinstance(value, str) and value:
            parsed[key] = (value,)
        elif isinstance(value, list) and value and all(isinstance(v, str) and v for v in value):
            parsed[key] = tuple(value)
        else:
            raise PresetError(
                f"Preset {preset!r}: value of {key!r} must be a string or a list of strings."
            )
    return parsed


def parse_presets(data: Any) -> dict[str, Preset]:
    """Validate a decoded presets document and return Preset objects."""
    if not isinstance(data, dict):
        raise PresetError("Presets must be a JSON object keyed by preset name.")
    presets: dict[str, Preset] = {}
    for name, body in data.items():
        if not isinstance(name, str) or not name.replace("_", "").isalnum():
            raise PresetError(f"Invalid preset name {name!r}: use letters, digits and _ only.")
        if not isinstance(body, dict) or not isinstance(body.get("tags"), list) or not body["tags"]:
            raise PresetError(f"Preset {name!r} needs a non-empty 'tags' list.")
        label = body.get("label", name)
        if not isinstance(label, str):
            raise PresetError(f"Preset {name!r}: 'label' must be a string.")
        tag_sets = tuple(_parse_tag_set(name, item) for item in body["tags"])
        presets[name] = Preset(name=name, label=label, tag_sets=tag_sets)
    return presets


def load_builtin_presets() -> dict[str, Preset]:
    text = resources.files("osm_poi").joinpath("data/presets.json").read_text(encoding="utf-8")
    return parse_presets(json.loads(text))


def load_presets(extra_file: Path | None = None) -> dict[str, Preset]:
    """Built-in presets, optionally extended or overridden by a JSON file."""
    presets = load_builtin_presets()
    if extra_file is not None:
        try:
            extra = json.loads(extra_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PresetError(f"Cannot read presets file {extra_file}: {exc}") from exc
        presets.update(parse_presets(extra))
    return presets


def select_presets(presets: Mapping[str, Preset], names: Sequence[str]) -> list[Preset]:
    """Resolve category names (case-insensitive, deduplicated, order kept)."""
    if not names:
        raise PresetError("At least one category is required.")
    chosen: list[Preset] = []
    for raw in names:
        name = raw.strip().lower().replace("-", "_")
        if not name:
            continue
        preset = presets.get(name)
        if preset is None:
            available = ", ".join(sorted(presets))
            raise PresetError(f"Unknown category {raw!r}. Available: {available}")
        if preset not in chosen:
            chosen.append(preset)
    if not chosen:
        raise PresetError("At least one category is required.")
    return chosen
