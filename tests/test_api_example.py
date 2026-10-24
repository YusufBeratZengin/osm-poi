from __future__ import annotations

import pytest

import osm_poi
from conftest import CAFE_ELEMENTS, FakeServer
from osm_poi import BBox, Config, Poi, Polygon, fetch_pois
from osm_poi.errors import AreaError


def test_public_api_exports() -> None:
    assert "__all__" in dir(osm_poi)
    assert "fetch_pois" in osm_poi.__all__
    assert "Poi" in osm_poi.__all__
    assert "BBox" in osm_poi.__all__
    assert "Polygon" in osm_poi.__all__
    assert "Config" in osm_poi.__all__
    assert "load_config" in osm_poi.__all__
    assert "__version__" in osm_poi.__all__


def test_fetch_pois_example_against_fake_server(fake_server: FakeServer) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})

    pois = fetch_pois(
        bbox="40.95,29.00,41.03,29.11",
        categories=["cafe"],
        user_agent="my-app/1.0 (contact@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )

    assert len(pois) == 1
    poi = pois[0]
    assert isinstance(poi, Poi)
    assert poi.name == "Kahve Evi"
    assert poi.category == "cafe"
    assert poi.lat == 40.99
    assert poi.lon == 29.03
    assert poi.phone == "+90 216 000 00 00"

    # Verify formatting output matches example in documentation
    output_line = f"{poi.name} | {poi.category} | {poi.lat}, {poi.lon} | {poi.phone}"
    assert output_line == "Kahve Evi | cafe | 40.99, 29.03 | +90 216 000 00 00"


def test_fetch_pois_with_bbox_types_and_config(fake_server: FakeServer) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})

    # Test with tuple bbox
    pois_tuple = fetch_pois(
        bbox=(40.95, 29.00, 41.03, 29.11),
        categories="cafe",
        user_agent="my-app/1.0 (contact@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois_tuple) == 1

    # Test with BBox instance and Config instance
    cfg = Config(user_agent="my-cfg/1.0 (user@example.org)")
    pois_bbox = fetch_pois(
        bbox=BBox(40.95, 29.00, 41.03, 29.11),
        categories=["cafe"],
        config=cfg,
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois_bbox) == 1


def test_fetch_pois_polygon_and_split(fake_server: FakeServer) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})

    coords = [(40.95, 29.00), (41.03, 29.00), (41.03, 29.11), (40.95, 29.11)]
    poly = Polygon(coords)

    # Sequence of coords
    pois = fetch_pois(
        polygon=coords,
        categories=["cafe"],
        user_agent="my-app/1.0 (contact@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois) == 1

    # Polygon object
    pois_poly = fetch_pois(
        polygon=poly,
        categories=["cafe"],
        user_agent="my-app/1.0 (contact@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois_poly) == 1

    # Split tiled bounding box
    pois_split = fetch_pois(
        bbox="40.95,29.00,41.03,29.11",
        categories=["cafe"],
        split=2,
        user_agent="my-app/1.0 (contact@example.org)",
        overpass_url=fake_server.base_url + "/interpreter",
    )
    assert len(pois_split) == 1


def test_fetch_pois_validation_errors() -> None:
    # No area provided
    with pytest.raises(AreaError, match="Provide at least one area"):
        fetch_pois(categories=["cafe"], user_agent="app/1.0 (a@b.com)")

    # Invalid split < 1
    with pytest.raises(AreaError, match="Split must be at least 1"):
        fetch_pois(bbox="40,29,41,30", categories=["cafe"], split=0, user_agent="app/1.0 (a@b.com)")

    # Split > 1 without bbox
    coords = [(40.0, 29.0), (41.0, 29.0), (41.0, 30.0)]
    with pytest.raises(AreaError, match="can only be used with bbox"):
        fetch_pois(
            polygon=coords,
            categories=["cafe"],
            split=2,
            user_agent="app/1.0 (a@b.com)",
        )

    # Large area without allow_large
    with pytest.raises(AreaError, match="exceeds the limit"):
        fetch_pois(
            bbox="40.0,29.0,42.0,32.0",  # 2 x 3 = 6 sq degrees >> 0.25
            categories=["cafe"],
            user_agent="app/1.0 (a@b.com)",
        )

    # Large polygon without allow_large
    large_poly = [(40.0, 29.0), (42.0, 29.0), (42.0, 32.0), (40.0, 32.0)]
    with pytest.raises(AreaError, match="exceeds the limit"):
        fetch_pois(
            polygon=large_poly,
            categories=["cafe"],
            user_agent="app/1.0 (a@b.com)",
        )
