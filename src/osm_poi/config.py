"""Configuration: defaults, optional JSON file, environment variables."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from osm_poi.errors import ConfigError

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"

ENV_PREFIX = "OSM_POI_"
_GENERIC_AGENT_PREFIXES = ("python-", "mozilla/", "curl/", "java/")


@dataclass(frozen=True)
class Config:
    """Runtime settings. ``user_agent`` has no default on purpose."""

    user_agent: str = ""
    overpass_url: str = DEFAULT_OVERPASS_URL
    nominatim_url: str = DEFAULT_NOMINATIM_URL
    timeout: float = 90.0
    retries: int = 3
    backoff: float = 2.0
    overpass_interval: float = 1.0
    nominatim_interval: float = 1.0
    cache_dir: Path | None = None
    cache_ttl_hours: float = 24.0 * 7
    use_cache: bool = True
    max_area: float = 0.25

    def resolved_cache_dir(self) -> Path:
        return self.cache_dir if self.cache_dir is not None else default_cache_dir()

    def require_user_agent(self) -> str:
        """Return the User-Agent or raise; the Nominatim policy forbids anonymous clients."""
        agent = self.user_agent.strip()
        if not agent:
            raise ConfigError(
                "A User-Agent is required. Set OSM_POI_USER_AGENT, pass --user-agent, or put "
                '"user_agent" in the config file. Example: "my-project/1.0 (me@example.org)".'
            )
        if agent.lower().startswith(_GENERIC_AGENT_PREFIXES):
            raise ConfigError(
                "The User-Agent looks generic. Use one that identifies your application "
                'and a contact, e.g. "my-project/1.0 (me@example.org)".'
            )
        return agent


def default_cache_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "osm-poi" / "cache"


def default_config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "osm-poi" / "config.json"


_FLOAT_KEYS = (
    "timeout",
    "backoff",
    "overpass_interval",
    "nominatim_interval",
    "cache_ttl_hours",
    "max_area",
)
_STR_KEYS = ("user_agent", "overpass_url", "nominatim_url")


def _to_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError(raw)


def _apply(config: Config, values: Mapping[str, Any], source: str) -> Config:
    updates: dict[str, Any] = {}
    for key, raw in values.items():
        try:
            if key in _STR_KEYS:
                updates[key] = str(raw)
            elif key in _FLOAT_KEYS:
                updates[key] = float(raw)
            elif key == "retries":
                updates[key] = int(raw)
            elif key == "cache_dir":
                updates[key] = Path(str(raw))
            elif key == "use_cache":
                updates[key] = _to_bool(raw)
            else:
                raise ConfigError(f"Unknown setting {key!r} in {source}.")
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"Invalid value for {key!r} in {source}: {raw!r}") from exc
    return replace(config, **updates)


def load_config(
    path: Path | None = None,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Config:
    """Build a Config. Precedence: defaults < file < environment < overrides."""
    environment = os.environ if env is None else env
    config = Config()

    env_path = environment.get(ENV_PREFIX + "CONFIG")
    explicit = path is not None or bool(env_path)
    file_path = path or (Path(env_path) if env_path else default_config_path())
    if file_path.is_file():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Cannot read config file {file_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"Config file {file_path} must contain a JSON object.")
        config = _apply(config, data, str(file_path))
    elif explicit:
        raise ConfigError(f"Config file not found: {file_path}")

    env_values: dict[str, Any] = {}
    for key in (*_STR_KEYS, *_FLOAT_KEYS, "retries", "cache_dir", "use_cache"):
        value = environment.get(ENV_PREFIX + key.upper())
        if value not in (None, ""):
            env_values[key] = value
    config = _apply(config, env_values, "environment")

    if overrides:
        given = {k: v for k, v in overrides.items() if v is not None}
        config = _apply(config, given, "command line")
    return config
