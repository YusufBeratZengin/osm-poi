from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from osm_poi.errors import OsmPoiError
from osm_poi.models import FIELDS, Poi
from osm_poi.writers import (
    attribution_path,
    guess_format,
    render,
    safe_cell,
    write_output,
)


def poi(name: str = "Kahve, Evi", **kw: str) -> Poi:
    return Poi(
        osm_type="node",
        osm_id=7,
        osm_url="https://www.openstreetmap.org/node/7",
        name=name,
        category="cafe",
        lat=40.5,
        lon=29.5,
        **kw,
    )


def test_csv_header_rows_and_quoting() -> None:
    text = render([poi(phone="+90 216 000")], "csv")
    rows = list(csv.reader(io.StringIO(text)))
    assert tuple(rows[0]) == FIELDS
    assert rows[1][FIELDS.index("name")] == "Kahve, Evi"
    assert rows[1][FIELDS.index("phone")] == "+90 216 000"
    assert rows[1][FIELDS.index("lat")] == "40.5"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("=SUM(A1)", "'=SUM(A1)"),
        ("@cmd", "'@cmd"),
        ("-1+2", "'-1+2"),
        ("+90 (216) 000-00", "+90 (216) 000-00"),
        ("Normal", "Normal"),
        ("", ""),
    ],
)
def test_safe_cell(raw: str, expected: str) -> None:
    assert safe_cell(raw) == expected


def test_csv_neutralizes_formulas() -> None:
    text = render([poi(name='=HYPERLINK("http://x")')], "csv")
    assert "'=HYPERLINK" in text


def test_geojson_structure_and_attribution() -> None:
    doc = json.loads(render([poi()], "geojson"))
    assert doc["type"] == "FeatureCollection"
    assert "OpenStreetMap contributors" in doc["attribution"]
    assert doc["license"] == "ODbL-1.0"
    feature = doc["features"][0]
    assert feature["geometry"] == {"type": "Point", "coordinates": [29.5, 40.5]}
    assert feature["id"] == "node/7"
    assert feature["properties"]["name"] == "Kahve, Evi"
    assert "lat" not in feature["properties"]


def test_jsonl_one_object_per_line() -> None:
    lines = render([poi(), poi("B")], "jsonl").splitlines()
    assert [json.loads(line)["name"] for line in lines] == ["Kahve, Evi", "B"]


def test_empty_outputs() -> None:
    assert render([], "jsonl") == ""
    assert json.loads(render([], "geojson"))["features"] == []
    assert render([], "csv").strip().split(",")[0] == "osm_type"


def test_guess_format() -> None:
    assert guess_format("a.CSV") == "csv"
    assert guess_format("a.geojson") == "geojson"
    assert guess_format("a.json") == "geojson"
    assert guess_format("a.jsonl") == "jsonl"
    with pytest.raises(OsmPoiError):
        guess_format("a.txt")


def test_write_output_creates_file_and_attribution(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "out.csv"
    notice = write_output([poi()], str(target), "csv")
    assert target.read_text(encoding="utf-8").startswith("osm_type,")
    assert notice == attribution_path(target)
    assert notice is not None
    assert "Open Database License" in notice.read_text(encoding="utf-8")


def test_write_output_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert write_output([poi()], "-", "jsonl") is None
    assert json.loads(capsys.readouterr().out)["name"] == "Kahve, Evi"


def test_unicode_survives(tmp_path: Path) -> None:
    target = tmp_path / "o.jsonl"
    write_output([poi("Çiçek Kafe")], str(target), "jsonl")
    assert "Çiçek Kafe" in target.read_text(encoding="utf-8")


def test_render_with_custom_fields_csv() -> None:
    p = poi("Test Kafe", phone="+90 216 111", email="k@example.com")
    text = render([p], "csv", fields=["name", "category", "phone"])
    lines = text.strip().splitlines()
    assert lines[0] == "name,category,phone"
    assert lines[1] == "Test Kafe,cafe,+90 216 111"


def test_render_with_custom_fields_geojson() -> None:
    p = poi("Test Kafe", phone="+90 216 111", email="k@example.com")
    doc = json.loads(render([p], "geojson", fields=["name", "category"]))
    feature = doc["features"][0]
    assert feature["geometry"]["coordinates"] == [29.5, 40.5]
    assert feature["properties"] == {"name": "Test Kafe", "category": "cafe"}


def test_render_with_custom_fields_jsonl() -> None:
    p = poi("Test Kafe", phone="+90 216 111", email="k@example.com")
    line = render([p], "jsonl", fields=["name", "category"]).strip()
    assert json.loads(line) == {"name": "Test Kafe", "category": "cafe"}

