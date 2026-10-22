from __future__ import annotations

from conftest import CAFE_ELEMENTS
from osm_poi.dedupe import dedupe, distance_m, normalize_name
from osm_poi.models import Poi
from osm_poi.normalize import normalize_element, normalize_elements
from osm_poi.presets import load_builtin_presets, select_presets

PRESETS = select_presets(load_builtin_presets(), ["cafe", "restaurant"])


def make(osm_id: int, name: str = "X", lat: float = 40.0, lon: float = 29.0, **kw: str) -> Poi:
    return Poi(
        osm_type="node",
        osm_id=osm_id,
        osm_url=f"https://www.openstreetmap.org/node/{osm_id}",
        name=name,
        category="cafe",
        lat=lat,
        lon=lon,
        **kw,
    )


def test_normalize_node_fields() -> None:
    poi = normalize_element(CAFE_ELEMENTS[0], PRESETS)
    assert poi is not None
    assert poi.name == "Kahve Evi"
    assert poi.category == "cafe"
    assert (poi.lat, poi.lon) == (40.99, 29.03)
    assert poi.street == "Moda Caddesi" and poi.housenumber == "10"
    assert poi.phone == "+90 216 000 00 00"
    assert poi.opening_hours == "Mo-Su 08:00-22:00"
    assert poi.osm_url == "https://www.openstreetmap.org/node/1"


def test_normalize_way_uses_center() -> None:
    poi = normalize_element(CAFE_ELEMENTS[1], PRESETS)
    assert poi is not None
    assert (poi.osm_type, poi.lat, poi.lon) == ("way", 40.9902, 29.0301)


def test_unnamed_skipped_unless_requested() -> None:
    assert normalize_element(CAFE_ELEMENTS[3], PRESETS) is None
    poi = normalize_element(CAFE_ELEMENTS[3], PRESETS, include_unnamed=True)
    assert poi is not None and poi.name == ""


def test_name_fallbacks_and_contact_keys() -> None:
    element = {
        "type": "node",
        "id": 9,
        "lat": 1,
        "lon": 2,
        "tags": {"amenity": "cafe", "brand": "Chain", "contact:phone": "123", "addr:town": "T"},
    }
    poi = normalize_element(element, PRESETS)
    assert poi is not None
    assert (poi.name, poi.phone, poi.city) == ("Chain", "123", "T")


def test_malformed_elements_skipped() -> None:
    bad = [
        {"type": "node", "id": 1, "tags": {"amenity": "cafe", "name": "n"}},  # no coordinates
        {"type": "area", "id": 1, "lat": 1, "lon": 1, "tags": {"name": "n"}},
        {"type": "node", "id": "x", "lat": 1, "lon": 1, "tags": {"amenity": "cafe", "name": "n"}},
        {"type": "node", "id": 2, "lat": 1, "lon": 1, "tags": {"amenity": "bank", "name": "n"}},
        {"type": "node", "id": 3, "lat": 1, "lon": 1},
    ]
    assert normalize_elements(bad, PRESETS) == []


def test_first_matching_category_wins() -> None:
    both = select_presets(load_builtin_presets(), ["restaurant", "cafe"])
    element = {
        "type": "node",
        "id": 1,
        "lat": 1,
        "lon": 1,
        "tags": {"amenity": "restaurant", "name": "n"},
    }
    poi = normalize_element(element, both)
    assert poi is not None and poi.category == "restaurant"


def test_normalize_name_folds_turkish_and_punctuation() -> None:
    assert normalize_name("Çay Evi!") == "cay evi"
    assert normalize_name("ISPARTA  Kahvesi") == normalize_name("ısparta kahvesi")
    assert normalize_name("---") == ""


def test_distance_known_value() -> None:
    a, b = make(1, lat=0.0, lon=0.0), make(2, lat=0.0, lon=1.0)
    assert abs(distance_m(a, b) - 111_195) < 200


def test_dedupe_same_osm_id_keeps_most_complete() -> None:
    sparse, rich = make(1), make(1, phone="1", website="w")
    assert dedupe([sparse, rich]) == [rich]


def test_dedupe_near_duplicates_by_name() -> None:
    node = make(1, "Kahve Evi", 40.99, 29.03)
    way = make(2, "kahve evi", 40.9902, 29.0301, phone="1")
    far = make(3, "Kahve Evi", 41.5, 29.03)
    other = make(4, "Baska", 40.99, 29.03)
    result = dedupe([node, way, far, other])
    assert result == [way, far, other]


def test_dedupe_radius_zero_disables_proximity_pass() -> None:
    node, way = make(1, "A"), make(2, "A")
    assert len(dedupe([node, way], radius_m=0)) == 2


def test_dedupe_different_category_is_kept() -> None:
    a = make(1, "A")
    b = Poi(**{**a.as_dict(), "osm_id": 2, "category": "restaurant"})
    assert len(dedupe([a, b])) == 2


def test_dedupe_unnamed_never_merged() -> None:
    assert len(dedupe([make(1, ""), make(2, "")])) == 2


def test_contact_fallbacks_and_multiple_phones() -> None:
    element = {
        "type": "node",
        "id": 10,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {
            "amenity": "cafe",
            "name": "Çay Bahçesi",
            "contact:phone": "+90 216 111 22 33;  +90 216 111 22 34 ; +90 216 111 22 35",
            "contact:website": "www.caybahcesi.com.tr",
            "contact:email": "info@caybahcesi.com.tr",
        },
    }
    poi = normalize_element(element, PRESETS)
    assert poi is not None
    assert poi.phone == "+90 216 111 22 33; +90 216 111 22 34; +90 216 111 22 35"
    assert poi.website == "https://www.caybahcesi.com.tr"
    assert poi.email == "info@caybahcesi.com.tr"


def test_addr_full_fallback() -> None:
    element = {
        "type": "node",
        "id": 11,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {
            "amenity": "cafe",
            "name": "Köşe Kafe",
            "addr:full": "Caferağa Mah. Moda Cad. No:15 Kadıköy/İstanbul",
        },
    }
    poi = normalize_element(element, PRESETS)
    assert poi is not None
    assert poi.street == "Caferağa Mah. Moda Cad. No:15 Kadıköy/İstanbul"


def test_turkish_dotted_dotless_i_handling() -> None:
    element = {
        "type": "node",
        "id": 12,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {
            "amenity": "cafe",
            "name": "İnci Pastanesi",
        },
    }
    poi = normalize_element(element, PRESETS)
    assert poi is not None
    assert poi.name == "İnci Pastanesi"

    # Verify deduplication folds 'İnci Pastanesi' and 'inci pastanesi'
    duplicate = make(13, name="inci pastanesi", lat=41.0001, lon=29.0001)
    res = dedupe([poi, duplicate])
    assert len(res) == 1


def test_name_language_fallbacks_and_brand_operator() -> None:
    # name:tr only
    el_tr = {
        "type": "node",
        "id": 14,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "name:tr": "Türk Kahvecisi"},
    }
    poi_tr = normalize_element(el_tr, PRESETS)
    assert poi_tr is not None and poi_tr.name == "Türk Kahvecisi"

    # name:en only
    el_en = {
        "type": "node",
        "id": 15,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "name:en": "Coffee Hub"},
    }
    poi_en = normalize_element(el_en, PRESETS)
    assert poi_en is not None and poi_en.name == "Coffee Hub"

    # brand fallback
    el_brand = {
        "type": "node",
        "id": 16,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "brand": "BrandCafe"},
    }
    poi_brand = normalize_element(el_brand, PRESETS)
    assert poi_brand is not None and poi_brand.name == "BrandCafe"

    # operator fallback
    el_op = {
        "type": "node",
        "id": 17,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "operator": "City Municipality"},
    }
    poi_op = normalize_element(el_op, PRESETS)
    assert poi_op is not None and poi_op.name == "City Municipality"

    # completely unnamed
    el_unnamed = {
        "type": "node",
        "id": 18,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe"},
    }
    assert normalize_element(el_unnamed, PRESETS, include_unnamed=False) is None
    poi_unnamed = normalize_element(el_unnamed, PRESETS, include_unnamed=True)
    assert poi_unnamed is not None and poi_unnamed.name == ""


def test_website_without_scheme_adds_https() -> None:
    el_no_scheme = {
        "type": "node",
        "id": 19,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "name": "Web Kafe", "website": "example.org/menu"},
    }
    poi = normalize_element(el_no_scheme, PRESETS)
    assert poi is not None
    assert poi.website == "https://example.org/menu"

    el_with_http = {
        "type": "node",
        "id": 20,
        "lat": 41.0,
        "lon": 29.0,
        "tags": {"amenity": "cafe", "name": "Web Kafe 2", "website": "http://example.org"},
    }
    poi2 = normalize_element(el_with_http, PRESETS)
    assert poi2 is not None
    assert poi2.website == "http://example.org"
