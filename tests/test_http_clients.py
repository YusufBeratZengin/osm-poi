from __future__ import annotations

from pathlib import Path

import pytest

from conftest import CAFE_ELEMENTS, FakeServer, json_reply
from osm_poi.areas import BBox, OsmArea
from osm_poi.cache import DiskCache, cache_key
from osm_poi.errors import AreaError, HttpError, OverpassError
from osm_poi.http import HttpClient
from osm_poi.nominatim import NominatimClient
from osm_poi.overpass import OverpassClient

UA = "osm-poi-tests/0.1 (tests@example.org)"


def client(server: FakeServer, sleeps: list[float] | None = None, **kw: float) -> HttpClient:
    record = sleeps if sleeps is not None else []
    return HttpClient(UA, timeout=5, min_interval=0, sleep=record.append, **kw)  # type: ignore[arg-type]


def test_sends_user_agent_and_form(fake_server: FakeServer) -> None:
    fake_server.set_default("/api", 200, {"ok": True})
    http = client(fake_server)
    assert http.post_form(fake_server.base_url + "/api", {"data": "q"}) == b'{"ok": true}'
    request = fake_server.requests[0]
    assert request["user_agent"] == UA
    assert request["form"] == {"data": ["q"]}


def test_get_encodes_params(fake_server: FakeServer) -> None:
    fake_server.set_default("/s", 200, [])
    client(fake_server).get(fake_server.base_url + "/s", {"q": "Kadıköy, İstanbul"})
    assert fake_server.requests[0]["query"] == {"q": ["Kadıköy, İstanbul"]}


def test_retries_on_429_and_504_with_backoff(fake_server: FakeServer) -> None:
    fake_server.script("/api", json_reply({}, 429), json_reply({}, 504), json_reply({"ok": 1}))
    sleeps: list[float] = []
    http = client(fake_server, sleeps, retries=3, backoff=2.0)
    assert http.get(fake_server.base_url + "/api") == b'{"ok": 1}'
    assert fake_server.count("/api") == 3
    assert sleeps == [2.0, 4.0]


def test_retry_after_header_is_honoured(fake_server: FakeServer) -> None:
    fake_server.script("/api", json_reply({}, 429, {"Retry-After": "7"}), json_reply({}))
    sleeps: list[float] = []
    client(fake_server, sleeps).get(fake_server.base_url + "/api")
    assert sleeps == [7.0]


def test_gives_up_after_retries(fake_server: FakeServer) -> None:
    fake_server.set_default("/api", 503, {})
    http = client(fake_server, retries=2)
    with pytest.raises(HttpError) as info:
        http.get(fake_server.base_url + "/api")
    assert info.value.status == 503
    assert fake_server.count("/api") == 3


def test_client_errors_are_not_retried(fake_server: FakeServer) -> None:
    fake_server.set_default("/api", 400, {})
    with pytest.raises(HttpError) as info:
        client(fake_server).get(fake_server.base_url + "/api")
    assert info.value.status == 400
    assert fake_server.count("/api") == 1


def test_connection_error_is_reported() -> None:
    http = HttpClient(UA, timeout=1, retries=1, min_interval=0, sleep=lambda _s: None)
    with pytest.raises(HttpError):
        http.get("http://127.0.0.1:1/")


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(HttpError):
        client(None).get("file:///etc/passwd")  # type: ignore[arg-type]


def test_min_interval_spaces_requests(fake_server: FakeServer) -> None:
    fake_server.set_default("/api", 200, {})
    sleeps: list[float] = []
    now = [100.0]
    http = HttpClient(UA, min_interval=1.0, sleep=sleeps.append, clock=lambda: now[0])
    http.get(fake_server.base_url + "/api")
    now[0] += 0.25
    http.get(fake_server.base_url + "/api")
    assert sleeps == [pytest.approx(0.75)]


def test_cache_roundtrip_ttl_and_clear(tmp_path: Path) -> None:
    now = [1000.0]
    cache = DiskCache(tmp_path, ttl_seconds=60, now=lambda: now[0])
    key = cache_key("a", "b")
    assert cache.get(key) is None
    cache.put(key, {"x": [1, 2]})
    assert cache.get(key) == {"x": [1, 2]}
    now[0] += 61
    assert cache.get(key) is None
    cache.put(key, 1)
    assert cache.clear() == 1
    assert cache.get(key) is None


def test_cache_key_depends_on_parts() -> None:
    assert cache_key("a", "bc") != cache_key("ab", "c")


def test_disabled_cache_never_stores(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path, ttl_seconds=60, enabled=False)
    cache.put("k", 1)
    assert cache.get("k") is None
    assert not list(tmp_path.glob("*.json"))


def test_corrupt_cache_entry_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "k.json").write_text("{not json", encoding="utf-8")
    assert DiskCache(tmp_path, ttl_seconds=60).get("k") is None


def test_overpass_runs_and_caches(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})
    cache = DiskCache(tmp_path, ttl_seconds=3600)
    overpass = OverpassClient(fake_server.base_url + "/interpreter", client(fake_server), cache)
    first = overpass.run("[out:json];")
    second = overpass.run("[out:json];")
    assert first == second == CAFE_ELEMENTS
    assert fake_server.count("/interpreter") == 1
    assert fake_server.requests[0]["form"] == {"data": ["[out:json];"]}
    overpass.run("[out:json];out;")
    assert fake_server.count("/interpreter") == 2


def test_overpass_runtime_error_not_cached(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default(
        "/interpreter", 200, {"elements": [], "remark": "runtime error: Query timed out"}
    )
    overpass = OverpassClient(
        fake_server.base_url + "/interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    with pytest.raises(OverpassError, match="timed out"):
        overpass.run("q")
    with pytest.raises(OverpassError):
        overpass.run("q")
    assert fake_server.count("/interpreter") == 2


def test_overpass_invalid_json(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, b"<html>busy</html>")
    overpass = OverpassClient(
        fake_server.base_url + "/interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    with pytest.raises(HttpError):
        overpass.run("q")


RELATION = {
    "osm_type": "relation",
    "osm_id": 1688,
    "category": "boundary",
    "display_name": "Kadikoy, Istanbul",
    "boundingbox": ["40.95", "41.03", "29.00", "29.11"],
}


def nominatim(server: FakeServer, tmp_path: Path) -> NominatimClient:
    return NominatimClient(server.base_url, client(server), DiskCache(tmp_path, 3600))


def test_nominatim_relation_becomes_area(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/search", 200, [RELATION])
    area = nominatim(fake_server, tmp_path).resolve("Kadikoy, Istanbul")
    assert area == OsmArea(3_600_001_688, "Kadikoy, Istanbul")
    request = fake_server.requests[0]
    assert request["query"]["q"] == ["Kadikoy, Istanbul"]
    assert request["query"]["format"] == ["jsonv2"]
    assert request["user_agent"] == UA


def test_nominatim_results_are_cached(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/search", 200, [RELATION])
    service = nominatim(fake_server, tmp_path)
    service.resolve("Kadikoy")
    service.resolve("  kadikoy ")
    assert fake_server.count("/search") == 1


def test_nominatim_node_falls_back_to_bbox(fake_server: FakeServer, tmp_path: Path) -> None:
    place = {**RELATION, "osm_type": "node", "category": "place"}
    fake_server.set_default("/search", 200, [place])
    assert nominatim(fake_server, tmp_path).resolve("x") == BBox(40.95, 29.0, 41.03, 29.11)


def test_nominatim_no_result(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/search", 200, [])
    with pytest.raises(AreaError, match="no place"):
        nominatim(fake_server, tmp_path).resolve("Nowhere")


def test_nominatim_empty_name(fake_server: FakeServer, tmp_path: Path) -> None:
    with pytest.raises(AreaError):
        nominatim(fake_server, tmp_path).resolve("  ")


def test_overpass_empty_elements(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": []})
    overpass = OverpassClient(
        fake_server.base_url + "/interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    assert overpass.run("q") == []


def test_overpass_gzip_response(fake_server: FakeServer, tmp_path: Path) -> None:
    import gzip

    compressed = gzip.compress(b'{"elements": [{"type": "node", "id": 1, "lat": 1, "lon": 2}]}')
    fake_server.script("/interpreter", (200, {"Content-Encoding": "gzip"}, compressed))
    overpass = OverpassClient(
        fake_server.base_url + "/interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    elements = overpass.run("q")
    assert len(elements) == 1
    assert elements[0]["id"] == 1


def test_overpass_redirect_followed(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.script(
        "/old_interpreter",
        (307, {"Location": fake_server.base_url + "/new_interpreter"}, b""),
    )
    fake_server.script(
        "/new_interpreter",
        (200, {}, b'{"elements": [{"type": "node", "id": 42, "lat": 1, "lon": 2}]}'),
    )
    overpass = OverpassClient(
        fake_server.base_url + "/old_interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    elements = overpass.run("q")
    assert len(elements) == 1
    assert elements[0]["id"] == 42


def test_overpass_non_json_runtime_error(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, b"runtime error: Query timed out in processing.")
    overpass = OverpassClient(
        fake_server.base_url + "/interpreter", client(fake_server), DiskCache(tmp_path, 3600)
    )
    with pytest.raises(OverpassError, match="Query timed out"):
        overpass.run("q")


def test_http_redirect_loop_detected(fake_server: FakeServer) -> None:
    fake_server.set_default(
        "/loop", 302, b"", headers={"Location": fake_server.base_url + "/loop"}
    )
    http = client(fake_server)
    with pytest.raises(HttpError, match="Too many redirects"):
        http.get(fake_server.base_url + "/loop")


