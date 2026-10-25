from __future__ import annotations

import json
import urllib.error
import zlib
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import CAFE_ELEMENTS, FakeServer
from osm_poi.api import fetch_pois
from osm_poi.areas import (
    BBox,
    OsmArea,
    Polygon,
    _ring,
    load_polygon_file,
    parse_bbox,
    polygons_from_geojson,
)
from osm_poi.cli import main, resolve_fields
from osm_poi.config import load_config
from osm_poi.errors import AreaError, ConfigError, HttpError, OsmPoiError, PresetError
from osm_poi.http import HttpClient, retry_after_seconds
from osm_poi.nominatim import NominatimClient, _bbox_of
from osm_poi.presets import (
    _parse_tag_set,
    load_builtin_presets,
    load_presets,
    parse_presets,
    select_presets,
)
from osm_poi.query import build_query
from osm_poi.writers import render, write_output

# ==============================================================================
# Areas & Geometries Edge Cases
# ==============================================================================


def test_polygon_out_of_range_coords() -> None:
    with pytest.raises(AreaError, match="Polygon point out of range"):
        Polygon(((95.0, 20.0), (10.0, 20.0), (10.0, 30.0)))

    with pytest.raises(AreaError, match="Polygon point out of range"):
        Polygon(((10.0, 195.0), (10.0, 20.0), (20.0, 20.0)))


def test_osm_area_sq_degrees() -> None:
    area = OsmArea(12345, "Test Area")
    assert area.area_sq_degrees() == 0.0


def test_ring_malformed_coords() -> None:
    with pytest.raises(AreaError, match="Malformed polygon coordinates in GeoJSON"):
        _ring([["invalid", "coords"]])


def test_ring_unclosed_and_closed() -> None:
    # Rings where start == end should drop the duplicate closing point
    coords = [[29.0, 40.0], [29.1, 40.0], [29.1, 40.1], [29.0, 40.0]]
    poly = _ring(coords)
    assert len(poly.points) == 3


def test_polygons_from_geojson_validation(tmp_path: Path) -> None:
    # Non-dict data
    with pytest.raises(AreaError, match="GeoJSON must be a JSON object"):
        polygons_from_geojson(["not", "a", "dict"])

    # Geometry not a dict inside feature
    with pytest.raises(AreaError, match="GeoJSON geometry must be an object"):
        polygons_from_geojson({"type": "Feature", "geometry": "not a dict"})

    # Unsupported geometry type
    with pytest.raises(AreaError, match="Unsupported GeoJSON geometry"):
        polygons_from_geojson(
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [29.0, 41.0]}}
        )

    # Empty FeatureCollection
    with pytest.raises(AreaError, match="No polygons found in the GeoJSON file"):
        polygons_from_geojson({"type": "FeatureCollection", "features": []})

    # GeometryCollection handling
    geom_col = {
        "type": "GeometryCollection",
        "geometries": [
            {
                "type": "Polygon",
                "coordinates": [[[29.0, 40.0], [29.1, 40.0], [29.1, 40.1], [29.0, 40.0]]],
            }
        ],
    }
    polys = polygons_from_geojson(geom_col)
    assert len(polys) == 1

    # Unreadable file
    non_existent = tmp_path / "missing.geojson"
    with pytest.raises(AreaError, match="Cannot read polygon file"):
        load_polygon_file(non_existent)

    # Corrupt JSON file
    corrupt = tmp_path / "corrupt.geojson"
    corrupt.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(AreaError, match="Cannot read polygon file"):
        load_polygon_file(corrupt)


def test_parse_bbox_invalid() -> None:
    with pytest.raises(AreaError, match="Bounding box must be 'south,west,north,east'"):
        parse_bbox("40.0,29.0,41.0")

    with pytest.raises(AreaError, match="Bounding box has a non-numeric value"):
        parse_bbox("40.0,invalid,41.0,29.0")


# ==============================================================================
# API Edge Cases
# ==============================================================================


def test_fetch_pois_with_polygon_file(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})

    poly_file = tmp_path / "test_poly.geojson"
    poly_file.write_text(
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": [
                    [[29.00, 40.95], [29.11, 40.95], [29.11, 41.03], [29.00, 41.03], [29.00, 40.95]]
                ],
            }
        ),
        encoding="utf-8",
    )

    pois = fetch_pois(
        polygon=poly_file,
        categories=["cafe"],
        user_agent="test-app/1.0 (test@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois) == 1


def test_fetch_pois_with_area_name_and_split(fake_server: FakeServer) -> None:
    # Nominatim returns an OsmArea boundary
    fake_server.set_default(
        "/search",
        200,
        [
            {
                "osm_type": "relation",
                "osm_id": 9999,
                "class": "boundary",
                "display_name": "Test District",
                "boundingbox": ["40.95", "41.03", "29.00", "29.11"],
            }
        ],
    )
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})

    pois = fetch_pois(
        bbox="40.95,29.00,41.03,29.11",
        area="Test District",
        categories=["cafe"],
        split=2,
        user_agent="test-app/1.0 (test@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
        nominatim_url=fake_server.base_url,
    )
    assert len(pois) == 1


# ==============================================================================
# CLI Edge Cases
# ==============================================================================


def test_resolve_fields_all_excluded() -> None:
    with pytest.raises(ConfigError, match="No fields selected for export"):
        resolve_fields("phone,website,email", no_contact=True)


def test_cli_split_and_area_validation() -> None:
    # split < 1
    code = main(["fetch", "--bbox", "40,29,41,30", "-c", "cafe", "--split", "0"])
    assert code == 2

    # split > 1 without bbox or area (only polygon)
    polygon_path = Path(__file__).parent / "test_poly.geojson"
    code = main(["fetch", "--polygon", str(polygon_path), "-c", "cafe", "--split", "2"])
    assert code == 2


def test_cli_large_polygon_rejected(tmp_path: Path) -> None:
    large_poly = tmp_path / "large.geojson"
    large_poly.write_text(
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": [
                    [[28.0, 40.0], [31.0, 40.0], [31.0, 42.0], [28.0, 42.0], [28.0, 40.0]]
                ],
            }
        ),
        encoding="utf-8",
    )
    code = main(["fetch", "--polygon", str(large_poly), "-c", "cafe"])
    assert code == 2


def test_cli_keyboard_interrupt() -> None:
    with patch("osm_poi.cli._cmd_fetch", side_effect=KeyboardInterrupt):
        code = main(["fetch", "--bbox", "40,29,41,30", "-c", "cafe", "--dry-run"])
        assert code == 130


# ==============================================================================
# Config Edge Cases
# ==============================================================================


def test_config_invalid_bool_value(tmp_path: Path) -> None:
    bad_cfg = tmp_path / "bad.json"
    bad_cfg.write_text(json.dumps({"use_cache": "not_a_boolean"}), encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid value for 'use_cache'"):
        load_config(path=bad_cfg)


def test_config_malformed_json_or_type(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{bad json", encoding="utf-8")
    with pytest.raises(ConfigError, match="Cannot read config file"):
        load_config(path=corrupt)

    not_dict = tmp_path / "list.json"
    not_dict.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigError, match="must contain a JSON object"):
        load_config(path=not_dict)


# ==============================================================================
# HTTP Edge Cases
# ==============================================================================


def test_retry_after_parsing() -> None:
    assert retry_after_seconds(None) is None

    msg = Message()
    msg["Retry-After"] = "not-a-number"
    assert retry_after_seconds(msg) is None


def test_http_deflate_decompression() -> None:
    raw_text = b'{"status": "ok"}'
    compressed = zlib.compress(raw_text)

    mock_resp = MagicMock()
    mock_resp.read.return_value = compressed
    mock_resp.headers = {"Content-Encoding": "deflate"}
    mock_resp.__enter__.return_value = mock_resp

    client = HttpClient("app/1.0", timeout=5)
    with patch.object(client._opener, "open", return_value=mock_resp):
        res = client.get("https://example.org/test")
        assert res == raw_text


def test_http_decompression_error() -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"corrupted bytes"
    mock_resp.headers = {"Content-Encoding": "deflate"}
    mock_resp.__enter__.return_value = mock_resp

    client = HttpClient("app/1.0", timeout=5)
    with (
        patch.object(client._opener, "open", return_value=mock_resp),
        pytest.raises(HttpError, match="Failed to decompress deflate response"),
    ):
        client.get("https://example.org/test")


def test_http_redirect_missing_location() -> None:
    client = HttpClient("app/1.0", timeout=5, retries=0)
    err = urllib.error.HTTPError(
        "https://example.org/test", 301, "Moved Permanently", Message(), None
    )
    with (
        patch.object(client._opener, "open", side_effect=err),
        pytest.raises(HttpError, match="redirect missing Location header"),
    ):
        client.get("https://example.org/test")


def test_http_303_see_other_redirect() -> None:
    client = HttpClient("app/1.0", timeout=5, retries=1)

    msg_303 = Message()
    msg_303["Location"] = "https://example.org/target"
    err_303 = urllib.error.HTTPError("https://example.org/source", 303, "See Other", msg_303, None)

    ok_resp = MagicMock()
    ok_resp.read.return_value = b'{"success": true}'
    ok_resp.headers = {}
    ok_resp.__enter__.return_value = ok_resp

    # First call returns 303 redirect, second call on redirected target returns 200
    with patch.object(client._opener, "open", side_effect=[err_303, ok_resp]):
        res = client.post_form("https://example.org/source", {"key": "val"})
        assert res == b'{"success": true}'


# ==============================================================================
# Nominatim Edge Cases
# ==============================================================================


def test_nominatim_invalid_json_response() -> None:
    client = NominatimClient("https://nominatim.example.org", MagicMock(), MagicMock())
    client.http.get.return_value = b"<html>Not JSON</html>"

    with pytest.raises(HttpError, match="Nominatim returned a response that is not valid JSON"):
        client.search("Somewhere")


def test_nominatim_bbox_parsing_error() -> None:
    place = {"osm_id": "none", "boundingbox": ["invalid", "coords", "1", "2"]}
    with pytest.raises(AreaError, match="has no usable bounding box"):
        _bbox_of(place, "Somewhere")


# ==============================================================================
# Presets Edge Cases
# ==============================================================================


def test_presets_parsing_validation() -> None:
    # Key not a non-empty string
    with pytest.raises(PresetError, match="tag keys must be non-empty strings"):
        _parse_tag_set("test", {"": "val"})

    # Label not a string
    with pytest.raises(PresetError, match="'label' must be a string"):
        parse_presets({"my_preset": {"label": 1234, "tags": [{"amenity": "cafe"}]}})

    # Non-existent or invalid extra preset file
    with pytest.raises(PresetError, match="Cannot read presets file"):
        load_presets(Path("non_existent_preset_file.json"))

    # Empty category selection (only whitespace)
    builtin = load_builtin_presets()
    with pytest.raises(PresetError, match="At least one category is required"):
        select_presets(builtin, ["   ", ""])


# ==============================================================================
# Query & Writers Edge Cases
# ==============================================================================


def test_query_no_presets() -> None:
    with pytest.raises(ValueError, match="At least one preset is required"):
        build_query([BBox(40, 29, 41, 30)], [])


def test_writers_unknown_format() -> None:
    with pytest.raises(OsmPoiError, match="Unknown output format 'xml'"):
        render([], "xml")


def test_write_output_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    res = write_output([], "-", "csv")
    assert res is None
    captured = capsys.readouterr().out
    assert "osm_type,osm_id,osm_url" in captured
