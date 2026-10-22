"""Remove duplicate features.

Two passes: identical OSM objects, then near-duplicates (same normalized name and
category within a small distance, typically a building outline plus a node).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable

from osm_poi.models import Poi

EARTH_RADIUS_M = 6_371_000.0
DEFAULT_RADIUS_M = 75.0

_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_TR_FOLD = str.maketrans({"ı": "i", "İ": "i", "ß": "ss", "ø": "o", "đ": "d", "ł": "l"})


def normalize_name(name: str) -> str:
    """Casefold, strip accents and punctuation: 'Çay Evi!' -> 'cay evi'."""
    folded = name.translate(_TR_FOLD).casefold()
    decomposed = unicodedata.normalize("NFKD", folded)
    ascii_like = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", ascii_like).strip()


def distance_m(a: Poi, b: Poi) -> float:
    """Great-circle distance in metres (haversine)."""
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = phi2 - phi1
    dlmb = math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def _better(candidate: Poi, current: Poi) -> bool:
    return candidate.completeness() > current.completeness()


def dedupe(pois: Iterable[Poi], radius_m: float = DEFAULT_RADIUS_M) -> list[Poi]:
    """Return unique features, keeping the most complete record. Order is preserved."""
    by_id: dict[tuple[str, int], Poi] = {}
    for poi in pois:
        key = (poi.osm_type, poi.osm_id)
        existing = by_id.get(key)
        if existing is None or _better(poi, existing):
            by_id[key] = poi

    kept: list[Poi] = []
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for poi in by_id.values():
        name = normalize_name(poi.name)
        if not name or radius_m <= 0:
            kept.append(poi)
            continue
        group = groups[(name, poi.category)]
        match = next((i for i in group if distance_m(kept[i], poi) <= radius_m), None)
        if match is None:
            group.append(len(kept))
            kept.append(poi)
        elif _better(poi, kept[match]):
            kept[match] = poi
    return kept
