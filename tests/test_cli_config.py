from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import CAFE_ELEMENTS, FakeServer
from osm_poi.cli import main
from osm_poi.config import load_config
from osm_poi.errors import ConfigError

UA = "osm-poi-tests/0.1 (tests@example.org)"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(__import__("os").environ):
        if name.startswith("OSM_POI_"):
            monkeypatch.delenv(name)


def base_args(server: FakeServer, tmp_path: Path) -> list[str]:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps({"overpass_interval": 0, "nominatim_interval": 0, "backoff": 0}),
        encoding="utf-8",
    )
    return [
        "--config", str(config),
        "--user-agent", UA,
        "--overpass-url", server.base_url + "/interpreter",
        "--nominatim-url", server.base_url,
        "--cache-dir", str(tmp_path / "cache"),
    ]  # fmt: skip


def test_dry_run_with_bbox_prints_query_without_network(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["fetch", "--bbox", "40.9,29,41,29.1", "-c", "cafe,restaurant", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("[out:json][timeout:90];")
    assert '"amenity"="cafe"' in out and '"amenity"="restaurant"' in out


def test_fetch_bbox_to_csv_end_to_end(
    fake_server: FakeServer, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})
    target = tmp_path / "out.csv"
    args = ["fetch", "--bbox", "40.9,29,41,29.1", "-c", "cafe,restaurant", "-o", str(target)]
    assert main([*args, *base_args(fake_server, tmp_path)]) == 0
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + deduplicated cafe + restaurant
    assert (tmp_path / "out.csv.ATTRIBUTION.txt").is_file()
    assert "OpenStreetMap contributors" in capsys.readouterr().err
    assert fake_server.requests[0]["user_agent"] == UA


def test_fetch_area_name_geojson_uses_cache_second_time(
    fake_server: FakeServer, tmp_path: Path
) -> None:
    fake_server.set_default(
        "/search",
        200,
        [{"osm_type": "relation", "osm_id": 5, "category": "boundary", "display_name": "X"}],
    )
    fake_server.set_default("/interpreter", 200, {"elements": CAFE_ELEMENTS})
    target = tmp_path / "out.geojson"
    argv = ["fetch", "--area", "Kadikoy, Istanbul", "-c", "cafe", "-o", str(target)]
    argv += base_args(fake_server, tmp_path)
    assert main(argv) == 0
    assert main(argv) == 0
    assert fake_server.count("/search") == 1
    assert fake_server.count("/interpreter") == 1
    query = fake_server.requests[-1]["form"]["data"][0]
    assert "area(3600000005)->.a3600000005;" in query
    doc = json.loads(target.read_text(encoding="utf-8"))
    assert doc["features"] and doc["attribution"]


def test_no_cache_flag_hits_server_every_time(fake_server: FakeServer, tmp_path: Path) -> None:
    fake_server.set_default("/interpreter", 200, {"elements": []})
    argv = [
        "fetch",
        "--bbox",
        "1,2,3,4",
        "-c",
        "cafe",
        "-o",
        str(tmp_path / "o.jsonl"),
        "--no-cache",
    ]
    argv += base_args(fake_server, tmp_path)
    main(argv)
    main(argv)
    assert fake_server.count("/interpreter") == 2


def test_missing_user_agent_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSM_POI_CONFIG", str(tmp_path / "none.json"))
    (tmp_path / "none.json").write_text("{}", encoding="utf-8")
    code = main(["fetch", "--bbox", "1,2,3,4", "-c", "cafe", "-o", str(tmp_path / "o.csv")])
    assert code == 2
    assert "User-Agent" in capsys.readouterr().err


def test_generic_user_agent_rejected(tmp_path: Path) -> None:
    config = load_config(path=None, env={"OSM_POI_USER_AGENT": "python-urllib/3.12"})
    with pytest.raises(ConfigError):
        config.require_user_agent()


def test_no_area_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fetch", "-c", "cafe", "--dry-run"]) == 2
    assert "--area" in capsys.readouterr().err


def test_unknown_category_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fetch", "--bbox", "1,2,3,4", "-c", "spaceport", "--dry-run"]) == 2
    assert "Unknown category" in capsys.readouterr().err


def test_unknown_extension_is_an_error(
    fake_server: FakeServer, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["fetch", "--bbox", "1,2,3,4", "-c", "cafe", "-o", str(tmp_path / "o.xyz")]
    assert main([*argv, *base_args(fake_server, tmp_path)]) == 2
    assert "output format" in capsys.readouterr().err


def test_presets_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["presets"]) == 0
    assert "real_estate_agent" in capsys.readouterr().out


def test_cache_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cache_dir = tmp_path / "c"
    cache_dir.mkdir()
    (cache_dir / "a.json").write_text("{}", encoding="utf-8")
    assert main(["cache", "path", "--cache-dir", str(cache_dir)]) == 0
    assert str(cache_dir) in capsys.readouterr().out
    assert main(["cache", "clear", "--cache-dir", str(cache_dir)]) == 0
    assert "Removed 1" in capsys.readouterr().out


def test_config_precedence(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"user_agent": "file/1", "timeout": 10}), encoding="utf-8")
    env = {"OSM_POI_USER_AGENT": "env/1", "OSM_POI_RETRIES": "5", "OSM_POI_USE_CACHE": "false"}
    config = load_config(path, env, {"timeout": 3.0, "user_agent": None})
    assert (config.user_agent, config.timeout, config.retries) == ("env/1", 3.0, 5)
    assert config.use_cache is False


def test_config_rejects_unknown_key_and_bad_values(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"bogus": 1}), encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown"):
        load_config(path, {})
    with pytest.raises(ConfigError, match="Invalid"):
        load_config(None, {"OSM_POI_TIMEOUT": "abc", "OSM_POI_CONFIG": ""})
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.json", {})
