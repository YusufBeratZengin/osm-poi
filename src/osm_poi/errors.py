"""Exception types raised by osm-poi."""

from __future__ import annotations


class OsmPoiError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(OsmPoiError):
    """Invalid or missing configuration."""


class AreaError(OsmPoiError):
    """The search area could not be resolved or is invalid."""


class PresetError(OsmPoiError):
    """Unknown or malformed category preset."""


class HttpError(OsmPoiError):
    """A remote request failed after all retries."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class OverpassError(OsmPoiError):
    """Overpass answered but reported a problem (for example a runtime error)."""
