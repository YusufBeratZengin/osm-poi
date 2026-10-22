"""Search areas: bounding box, GeoJSON polygon, or an OSM area id."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osm_poi.errors import AreaError

_RELATION_AREA_OFFSET = 3_600_000_000
_WAY_AREA_OFFSET = 2_400_000_000


@dataclass(frozen=True)
class BBox:
    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if not (-90 <= self.south <= 90 and -90 <= self.north <= 90):
            raise AreaError("Latitude must be between -90 and 90.")
        if not (-180 <= self.west <= 180 and -180 <= self.east <= 180):
            raise AreaError("Longitude must be between -180 and 180.")
        if self.south >= self.north:
            raise AreaError("Bounding box: south must be smaller than north.")
        if self.west >= self.east:
            raise AreaError("Bounding box: west must be smaller than east.")

    def overpass_filter(self) -> str:
        return f"({_num(self.south)},{_num(self.west)},{_num(self.north)},{_num(self.east)})"


@dataclass(frozen=True)
class Polygon:
    """A closed ring of (lat, lon) points."""

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 3:
            raise AreaError("A polygon needs at least three points.")
        for lat, lon in self.points:
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise AreaError(f"Polygon point out of range: {lat}, {lon}")

    def overpass_filter(self) -> str:
        coords = " ".join(f"{_num(lat)} {_num(lon)}" for lat, lon in self.points)
        return f'(poly:"{coords}")'


@dataclass(frozen=True)
class OsmArea:
    """An administrative area referenced by its Overpass area id."""

    area_id: int
    label: str = ""

    def overpass_filter(self) -> str:
        return f"(area.a{self.area_id})"

    def definition(self) -> str:
        return f"area({self.area_id})->.a{self.area_id};"


Area = BBox | Polygon | OsmArea


def _num(value: float) -> str:
    return f"{value:.7f}".rstrip("0").rstrip(".") or "0"


def parse_bbox(text: str) -> BBox:
    """Parse ``south,west,north,east`` (the Overpass order)."""
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise AreaError("Bounding box must be 'south,west,north,east'.")
    try:
        south, west, north, east = (float(p) for p in parts)
    except ValueError as exc:
        raise AreaError(f"Bounding box has a non-numeric value: {text!r}") from exc
    return BBox(south, west, north, east)


def area_id_for(osm_type: str, osm_id: int) -> int | None:
    """Overpass area id for a relation or way, or None for other types."""
    if osm_type == "relation":
        return _RELATION_AREA_OFFSET + osm_id
    if osm_type == "way":
        return _WAY_AREA_OFFSET + osm_id
    return None


def _ring(coords: Any) -> Polygon:
    try:
        points = tuple((float(lat), float(lon)) for lon, lat, *_ in coords)
    except (TypeError, ValueError) as exc:
        raise AreaError("Malformed polygon coordinates in GeoJSON.") from exc
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    return Polygon(points)


def _collect(geometry: Any, out: list[Polygon]) -> None:
    if not isinstance(geometry, dict):
        raise AreaError("GeoJSON geometry must be an object.")
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon" and isinstance(coords, list) and coords:
        out.append(_ring(coords[0]))  # outer ring only; holes are ignored
    elif kind == "MultiPolygon" and isinstance(coords, list):
        for polygon in coords:
            if isinstance(polygon, list) and polygon:
                out.append(_ring(polygon[0]))
    elif kind == "GeometryCollection":
        for item in geometry.get("geometries", []):
            _collect(item, out)
    else:
        raise AreaError(f"Unsupported GeoJSON geometry: {kind!r} (use Polygon or MultiPolygon).")


def polygons_from_geojson(data: Any) -> list[Polygon]:
    """Extract outer rings from a Feature, FeatureCollection or bare geometry."""
    polygons: list[Polygon] = []
    if not isinstance(data, dict):
        raise AreaError("GeoJSON must be a JSON object.")
    kind = data.get("type")
    if kind == "FeatureCollection":
        for feature in data.get("features", []):
            _collect(feature.get("geometry") if isinstance(feature, dict) else None, polygons)
    elif kind == "Feature":
        _collect(data.get("geometry"), polygons)
    else:
        _collect(data, polygons)
    if not polygons:
        raise AreaError("No polygons found in the GeoJSON file.")
    return polygons


def load_polygon_file(path: Path) -> list[Polygon]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AreaError(f"Cannot read polygon file {path}: {exc}") from exc
    return polygons_from_geojson(data)
