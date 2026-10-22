"""Turn raw Overpass elements into normalized Poi records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from osm_poi.models import Poi
from osm_poi.presets import Preset

_OSM_TYPES = {"node", "way", "relation"}


def _first(tags: Mapping[str, str], *keys: str) -> str:
    for key in keys:
        value = tags.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def _coordinates(element: Mapping[str, Any]) -> tuple[float, float] | None:
    lat: Any = element.get("lat")
    lon: Any = element.get("lon")
    if lat is None or lon is None:
        center = element.get("center")
        if isinstance(center, dict):
            lat, lon = center.get("lat"), center.get("lon")
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def normalize_element(
    element: Mapping[str, Any],
    presets: Sequence[Preset],
    include_unnamed: bool = False,
) -> Poi | None:
    """Normalize one element; return None when it should be skipped."""
    osm_type = element.get("type")
    osm_id = element.get("id")
    raw_tags = element.get("tags")
    if osm_type not in _OSM_TYPES or not isinstance(osm_id, int) or not isinstance(raw_tags, dict):
        return None
    tags = {str(k): str(v) for k, v in raw_tags.items()}

    coords = _coordinates(element)
    if coords is None:
        return None

    name = _first(tags, "name", "name:en", "brand", "operator")
    if not name and not include_unnamed:
        return None

    category = next((p.name for p in presets if p.matches(tags)), "")
    if not category:
        return None

    return Poi(
        osm_type=str(osm_type),
        osm_id=osm_id,
        osm_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        name=name,
        category=category,
        lat=round(coords[0], 7),
        lon=round(coords[1], 7),
        street=_first(tags, "addr:street"),
        housenumber=_first(tags, "addr:housenumber"),
        postcode=_first(tags, "addr:postcode"),
        city=_first(tags, "addr:city", "addr:town", "addr:village", "addr:province"),
        country=_first(tags, "addr:country"),
        phone=_first(tags, "phone", "contact:phone"),
        website=_first(tags, "website", "contact:website", "url"),
        email=_first(tags, "email", "contact:email"),
        opening_hours=_first(tags, "opening_hours"),
    )


def normalize_elements(
    elements: Iterable[Mapping[str, Any]],
    presets: Sequence[Preset],
    include_unnamed: bool = False,
) -> list[Poi]:
    pois = (normalize_element(e, presets, include_unnamed) for e in elements)
    return [p for p in pois if p is not None]
