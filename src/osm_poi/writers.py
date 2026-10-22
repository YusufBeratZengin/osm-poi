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


def write_csv(
    pois: Sequence[Poi],
    stream: TextIO,
    fields: Sequence[str] | None = None,
) -> None:
    cols = tuple(fields) if fields is not None else FIELDS
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(cols)
    for poi in pois:
        row = poi.as_dict()
        writer.writerow(
            [safe_cell(row.get(col, "")) if isinstance(row.get(col, ""), str) else row.get(col, "") for col in cols]
        )


def geojson_document(
    pois: Sequence[Poi],
    fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    cols = set(fields) if fields is not None else set(FIELDS)
    features = []
    for poi in pois:
        properties = {
            k: v for k, v in poi.as_dict().items() if k not in {"lat", "lon"} and k in cols
        }
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


def write_geojson(
    pois: Sequence[Poi],
    stream: TextIO,
    fields: Sequence[str] | None = None,
) -> None:
    json.dump(geojson_document(pois, fields=fields), stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def write_jsonl(
    pois: Sequence[Poi],
    stream: TextIO,
    fields: Sequence[str] | None = None,
) -> None:
    cols = tuple(fields) if fields is not None else None
    for poi in pois:
        d = poi.as_dict()
        if cols is not None:
            d = {col: d.get(col, "") for col in cols}
        stream.write(json.dumps(d, ensure_ascii=False) + "\n")


def render(
    pois: Sequence[Poi],
    fmt: str,
    fields: Sequence[str] | None = None,
) -> str:
    buffer = io.StringIO()
    if fmt == "csv":
        write_csv(pois, buffer, fields=fields)
    elif fmt == "geojson":
        write_geojson(pois, buffer, fields=fields)
    elif fmt == "jsonl":
        write_jsonl(pois, buffer, fields=fields)
    else:
        raise OsmPoiError(f"Unknown output format {fmt!r}.")
    return buffer.getvalue()


def attribution_path(output: Path) -> Path:
    return output.with_name(output.name + ".ATTRIBUTION.txt")


def write_output(
    pois: Sequence[Poi],
    target: str,
    fmt: str,
    fields: Sequence[str] | None = None,
) -> Path | None:
    """Write to a file (plus attribution file) or to stdout when ``target`` is ``-``.

    Returns the attribution file path, or None for stdout.
    """
    text = render(pois, fmt, fields=fields)
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
