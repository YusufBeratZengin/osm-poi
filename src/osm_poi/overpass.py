"""Overpass API client with on-disk caching."""

from __future__ import annotations

import json
from typing import Any

from osm_poi.cache import DiskCache, cache_key
from osm_poi.errors import HttpError, OverpassError
from osm_poi.http import HttpClient


class OverpassClient:
    def __init__(self, endpoint: str, http: HttpClient, cache: DiskCache) -> None:
        self.endpoint = endpoint
        self.http = http
        self.cache = cache

    def run(self, query: str) -> list[dict[str, Any]]:
        """Run a query (or reuse a cached answer) and return the ``elements`` list."""
        key = cache_key("overpass", self.endpoint, query)
        cached = self.cache.get(key)
        if isinstance(cached, dict):
            return _elements(cached)

        raw = self.http.post_form(self.endpoint, {"data": query})
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpError("Overpass returned a response that is not valid JSON.") from exc
        if not isinstance(document, dict):
            raise OverpassError("Unexpected Overpass response shape.")
        elements = _elements(document)  # raises on runtime errors; failed runs are not cached
        self.cache.put(key, {"elements": elements})
        return elements


def _elements(document: dict[str, Any]) -> list[dict[str, Any]]:
    remark = document.get("remark")
    if isinstance(remark, str) and "error" in remark.lower():
        raise OverpassError(f"Overpass reported a problem: {remark}")
    elements = document.get("elements")
    if not isinstance(elements, list):
        raise OverpassError("Overpass response has no 'elements' list.")
    return [e for e in elements if isinstance(e, dict)]
