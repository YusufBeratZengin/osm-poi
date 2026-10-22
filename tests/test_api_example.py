from __future__ import annotations

import osm_poi
from conftest import CAFE_ELEMENTS, FakeServer
from osm_poi import Poi, fetch_pois


def test_public_api_exports() -> None:
    assert "__all__" in dir(osm_poi)
    assert "fetch_pois" in osm_poi.__all__
    assert "Poi" in osm_poi.__all__
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
    assert "Kahve Evi | cafe | 40.99, 29.03 | +90 216 000 00 00" == output_line
