"""CSV, GeoJSON and JSONL writers. Every output gets an attribution file next to it."""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from osm_poi.attribution import COPYRIGHT_URL, SHORT, attribution_text
from osm_poi.errors import OsmPoiError
from osm_poi.models import FIELDS, Poi

FORMATS = ("csv", "geojson", "jsonl")
_EXTENSIONS = {".csv": "csv", ".geojson": "geojson", ".json": "geojson", ".jsonl": "jsonl"}
_PHONE_LIKE = re.compile(r"^\+?[\d\s()./;-]+$")


def guess_format(path: str) -> str:
    """Pick an output format from a file extension."""
    suffix = Path(path).suffix.lower()
    try:
        return _EXTENSIONS[suffix]
    except KeyError:
        raise OsmPoiError(
            f"Cannot infer the output format from {path!r}; use --format csv|geojson|jsonl."
        ) from None


def safe_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection in text cells.

    Cells starting with ``= @ TAB CR`` (or ``+``/``-`` when not a phone number) get a
    leading apostrophe so Excel and LibreOffice treat them as text.
    """
    if not value:
        return value
    first = value[0]
    if first in "=@\t\r" or (first in "+-" and not _PHONE_LIKE.match(value)):
        return "'" + value
    return value


def write_csv(pois: Sequence[Poi], stream: TextIO) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(FIELDS)
    for poi in pois:
        row = poi.as_dict()
        writer.writerow([safe_cell(v) if isinstance(v, str) else v for v in row.values()])


def geojson_document(pois: Sequence[Poi]) -> dict[str, Any]:
    features = []
    for poi in pois:
        properties = {k: v for k, v in poi.as_dict().items() if k not in {"lat", "lon"}}
        features.append(
            {
                "type": "Feature",
                "id": f"{poi.osm_type}/{poi.osm_id}",
                "geometry": {"type": "Point", "coordinates": [poi.lon, poi.lat]},
                "properties": properties,
            }
        )
    return {
        "type": "FeatureCollection",
        "attribution": SHORT,
        "license": "ODbL-1.0",
        "copyright": COPYRIGHT_URL,
        "features": features,
    }


def write_geojson(pois: Sequence[Poi], stream: TextIO) -> None:
    json.dump(geojson_document(pois), stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def write_jsonl(pois: Sequence[Poi], stream: TextIO) -> None:
    for poi in pois:
        stream.write(json.dumps(poi.as_dict(), ensure_ascii=False) + "\n")


def render(pois: Sequence[Poi], fmt: str) -> str:
    buffer = io.StringIO()
    if fmt == "csv":
        write_csv(pois, buffer)
    elif fmt == "geojson":
        write_geojson(pois, buffer)
    elif fmt == "jsonl":
        write_jsonl(pois, buffer)
    else:
        raise OsmPoiError(f"Unknown output format {fmt!r}.")
    return buffer.getvalue()


def attribution_path(output: Path) -> Path:
    return output.with_name(output.name + ".ATTRIBUTION.txt")


def write_output(pois: Sequence[Poi], target: str, fmt: str) -> Path | None:
    """Write to a file (plus attribution file) or to stdout when ``target`` is ``-``.

    Returns the attribution file path, or None for stdout.
    """
    text = render(pois, fmt)
    if target == "-":
        sys.stdout.write(text)
        return None
    path = Path(target)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    notice = attribution_path(path)
    notice.write_text(attribution_text(), encoding="utf-8", newline="")
    return notice
