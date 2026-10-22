from __future__ import annotations

import json
from pathlib import Path

import pytest

from osm_poi.areas import (
    BBox,
    OsmArea,
    Polygon,
    area_id_for,
    load_polygon_file,
    parse_bbox,
    polygons_from_geojson,
)
from osm_poi.errors import AreaError, PresetError
from osm_poi.presets import load_builtin_presets, load_presets, parse_presets, select_presets


def test_parse_bbox() -> None:
    assert parse_bbox("40.9, 29.0, 41.0, 29.1") == BBox(40.9, 29.0, 41.0, 29.1)


@pytest.mark.parametrize(
    "text", ["1,2,3", "a,b,c,d", "5,0,1,1", "0,5,1,1", "-95,0,1,1", "0,0,1,200"]
)
def test_parse_bbox_rejects_bad_input(text: str) -> None:
    with pytest.raises(AreaError):
        parse_bbox(text)


def test_area_ids() -> None:
    assert area_id_for("relation", 5) == 3_600_000_005
    assert area_id_for("way", 5) == 2_400_000_005
    assert area_id_for("node", 5) is None
    assert OsmArea(3_600_000_005).overpass_filter() == "(area.a3600000005)"


def test_polygon_needs_three_points() -> None:
    with pytest.raises(AreaError):
        Polygon(((0.0, 0.0), (1.0, 1.0)))


def test_geojson_polygon_drops_closing_point_and_swaps_axes() -> None:
    data = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[29.0, 40.9], [29.1, 40.9], [29.1, 41.0], [29.0, 40.9]]],
        },
    }
    (polygon,) = polygons_from_geojson(data)
    assert polygon.points == ((40.9, 29.0), (40.9, 29.1), (41.0, 29.1))


def test_geojson_multipolygon_and_collection() -> None:
    ring = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]
    multi = {"type": "MultiPolygon", "coordinates": [[ring], [ring]]}
    collection = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": multi}]}
    assert len(polygons_from_geojson(collection)) == 2


def test_geojson_rejects_points(tmp_path: Path) -> None:
    path = tmp_path / "p.geojson"
    path.write_text(json.dumps({"type": "Point", "coordinates": [0, 0]}), encoding="utf-8")
    with pytest.raises(AreaError):
        load_polygon_file(path)


def test_builtin_presets_load_and_select() -> None:
    presets = load_builtin_presets()
    assert {"cafe", "restaurant", "pharmacy", "dentist", "real_estate_agent"} <= set(presets)
    chosen = select_presets(presets, ["Cafe", "real-estate-agent", "cafe"])
    assert [p.name for p in chosen] == ["cafe", "real_estate_agent"]


def test_unknown_category_lists_available() -> None:
    with pytest.raises(PresetError, match="Available"):
        select_presets(load_builtin_presets(), ["nope"])


def test_empty_selection_fails() -> None:
    with pytest.raises(PresetError):
        select_presets(load_builtin_presets(), [])


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"x": {}},
        {"x": {"tags": []}},
        {"x": {"tags": [{}]}},
        {"x": {"tags": [{"a": 1}]}},
        {"bad name": {"tags": [{"a": "b"}]}},
    ],
)
def test_parse_presets_rejects_malformed(data: object) -> None:
    with pytest.raises(PresetError):
        parse_presets(data)


def test_preset_matching() -> None:
    (preset,) = parse_presets(
        {"x": {"tags": [{"amenity": ["bar", "pub"]}, {"shop": "*"}]}}
    ).values()
    assert preset.matches({"amenity": "pub"})
    assert preset.matches({"shop": "anything"})
    assert not preset.matches({"amenity": "cafe"})


def test_custom_presets_file_overrides(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    path.write_text(json.dumps({"cafe": {"tags": [{"shop": "coffee"}]}}), encoding="utf-8")
    presets = load_presets(path)
    assert presets["cafe"].tag_sets == ({"shop": ("coffee",)},)
    assert "restaurant" in presets
