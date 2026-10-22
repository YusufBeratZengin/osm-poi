"""Resolve an administrative area name through Nominatim (cached, 1 request per second)."""

from __future__ import annotations

import json
from typing import Any

from osm_poi.areas import Area, BBox, OsmArea, area_id_for
from osm_poi.cache import DiskCache, cache_key
from osm_poi.errors import AreaError, HttpError
from osm_poi.http import HttpClient


class NominatimClient:
    def __init__(self, base_url: str, http: HttpClient, cache: DiskCache) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.cache = cache

    def search(self, name: str) -> dict[str, Any]:
        """Return the best match for ``name`` as a dict."""
        query = name.strip()
        if not query:
            raise AreaError("The area name is empty.")
        key = cache_key("nominatim", self.base_url, query.casefold())
        cached = self.cache.get(key)
        if isinstance(cached, dict):
            return cached

        raw = self.http.get(
            f"{self.base_url}/search",
            {"q": query, "format": "jsonv2", "limit": "1", "addressdetails": "0"},
        )
        try:
            results = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpError("Nominatim returned a response that is not valid JSON.") from exc
        if not isinstance(results, list) or not results or not isinstance(results[0], dict):
            raise AreaError(f"Nominatim found no place named {name!r}.")
        best: dict[str, Any] = results[0]
        self.cache.put(key, best)
        return best

    def resolve(self, name: str) -> Area:
        """Turn a place name into an Overpass area, falling back to its bounding box."""
        place = self.search(name)
        osm_type = str(place.get("osm_type", ""))
        try:
            osm_id = int(place["osm_id"])
        except (KeyError, TypeError, ValueError):
            osm_id = -1
        area_id = area_id_for(osm_type, osm_id) if osm_id >= 0 else None
        if area_id is not None and place.get("category", place.get("class")) == "boundary":
            return OsmArea(area_id, str(place.get("display_name", name)))
        return _bbox_of(place, name)


def _bbox_of(place: dict[str, Any], name: str) -> BBox:
    try:
        south, north, west, east = (float(v) for v in place["boundingbox"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AreaError(f"Nominatim result for {name!r} has no usable bounding box.") from exc
    return BBox(south, west, north, east)
