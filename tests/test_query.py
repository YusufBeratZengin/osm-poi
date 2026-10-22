from __future__ import annotations

import pytest

from osm_poi.areas import BBox, OsmArea, Polygon
from osm_poi.errors import AreaError
from osm_poi.presets import load_builtin_presets, parse_presets, select_presets
from osm_poi.query import build_query, quote, tag_filter


def test_quote_escapes_quotes_and_backslashes() -> None:
    assert quote('a"b\\c') == '"a\\"b\\\\c"'


def test_quote_rejects_newlines() -> None:
    with pytest.raises(ValueError):
        quote("a\nb")


def test_tag_filter_variants() -> None:
    assert tag_filter("amenity", ("cafe",)) == '["amenity"="cafe"]'
    assert tag_filter("shop", ("*",)) == '["shop"]'
    assert tag_filter("shop", ("a", "b.c")) == '["shop"~"^(a|b\\\\.c)$"]'


def test_bbox_query() -> None:
    presets = select_presets(load_builtin_presets(), ["cafe"])
    query = build_query([BBox(40.9, 29.0, 41.0, 29.1)], presets, timeout=30)
    assert query == (
        "[out:json][timeout:30];\n"
        "(\n"
        '  nwr["amenity"="cafe"](40.9,29,41,29.1);\n'
        ");\n"
        "out center tags;\n"
    )


def test_multiple_categories_and_or_tag_sets() -> None:
    presets = select_presets(load_builtin_presets(), ["cafe", "bar"])
    query = build_query([BBox(1, 2, 3, 4)], presets)
    assert '["amenity"="cafe"]' in query
    assert '["amenity"~"^(bar|pub)$"]' in query
    assert query.count("nwr") == 2


def test_multi_key_tag_set_is_anded() -> None:
    presets = list(parse_presets({"x": {"tags": [{"shop": "a", "cuisine": "*"}]}}).values())
    query = build_query([BBox(1, 2, 3, 4)], presets)
    assert 'nwr["shop"="a"]["cuisine"](1,2,3,4);' in query


def test_polygon_and_area_scopes() -> None:
    presets = select_presets(load_builtin_presets(), ["cafe"])
    poly = Polygon(((1.0, 2.0), (1.0, 3.0), (2.0, 3.0)))
    query = build_query([poly, OsmArea(3600123), OsmArea(3600123)], presets)
    assert '(poly:"1 2 1 3 2 3")' in query
    assert query.count("area(3600123)->.a3600123;") == 1
    assert '["amenity"="cafe"](area.a3600123);' in query


def test_max_size_header() -> None:
    presets = select_presets(load_builtin_presets(), ["cafe"])
    query = build_query([BBox(1, 2, 3, 4)], presets, timeout=10, max_size=1000)
    assert query.startswith("[out:json][timeout:10][maxsize:1000];")


def test_requires_area() -> None:
    presets = select_presets(load_builtin_presets(), ["cafe"])
    with pytest.raises(AreaError):
        build_query([], presets)


def test_value_with_quote_cannot_break_out() -> None:
    presets = list(parse_presets({"x": {"tags": [{"name": 'a"];out;'}]}}).values())
    query = build_query([BBox(1, 2, 3, 4)], presets)
    assert '["name"="a\\"];out;"]' in query
