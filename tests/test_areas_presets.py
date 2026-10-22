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


def test_bbox_area_and_tiling_math() -> None:
    box = BBox(40.0, 28.0, 41.0, 29.0)
    assert box.area_sq_degrees() == pytest.approx(1.0)

    # Split 1 returns self
    assert box.split(1) == [box]

    # Split 2 returns 4 tiles
    tiles = box.split(2)
    assert len(tiles) == 4
    assert tiles[0] == BBox(40.0, 28.0, 40.5, 28.5)
    assert tiles[1] == BBox(40.0, 28.5, 40.5, 29.0)
    assert tiles[2] == BBox(40.5, 28.0, 41.0, 28.5)
    assert tiles[3] == BBox(40.5, 28.5, 41.0, 29.0)

    total_tile_area = sum(t.area_sq_degrees() for t in tiles)
    assert total_tile_area == pytest.approx(box.area_sq_degrees())

    with pytest.raises(AreaError):
        box.split(0)


def test_polygon_area_math() -> None:
    # 1x1 degree square polygon
    poly = Polygon(((40.0, 28.0), (40.0, 29.0), (41.0, 29.0), (41.0, 28.0)))
    assert poly.area_sq_degrees() == pytest.approx(1.0)


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


def test_builtin_presets_schema_and_uniqueness() -> None:
    from importlib import resources

    raw_text = resources.files("osm_poi").joinpath("data/presets.json").read_text(encoding="utf-8")
    data = json.loads(raw_text)

    assert isinstance(data, dict)
    assert len(data) >= 40

    required_new = {
        "supermarket",
        "clothes",
        "gym",
        "school",
        "car_repair",
        "lawyer",
        "estate_agent",
        "stationery",
        "notary",
        "car_wash",
        "butcher",
        "dry_cleaning",
        "driving_school",
    }
    assert required_new <= set(data.keys())

    seen_names: set[str] = set()
    for name, spec in data.items():
        assert name not in seen_names, f"Duplicate preset name {name}"
        seen_names.add(name)
        assert isinstance(name, str) and name.replace("_", "").isalnum()
        assert isinstance(spec, dict)
        assert "label" in spec and isinstance(spec["label"], str) and spec["label"].strip()
        tags = spec.get("tags")
        assert isinstance(tags, list) and len(tags) > 0, f"Preset {name} has empty tags"
        for tag_set in tags:
            assert isinstance(tag_set, dict) and len(tag_set) > 0
            for k, v in tag_set.items():
                assert isinstance(k, str) and k.strip()
                if isinstance(v, list):
                    assert len(v) > 0
                    assert all(isinstance(item, str) and item.strip() for item in v)
                else:
                    assert isinstance(v, str) and v.strip()
