"""On-disk JSON cache keyed by a hash of the request."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def cache_key(*parts: str) -> str:
    """Stable SHA-256 hex digest of the given parts."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


class DiskCache:
    """Stores JSON-serializable values as ``<key>.json`` files with a time-to-live."""

    def __init__(
        self,
        directory: Path,
        ttl_seconds: float,
        enabled: bool = True,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self._now = now

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        path = self._path(key)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            stored_at = float(record["stored_at"])
            value = record["value"]
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if self.ttl_seconds >= 0 and self._now() - stored_at > self.ttl_seconds:
            return None
        return value

    def put(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"stored_at": self._now(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, path)

    def clear(self) -> int:
        """Delete all cache entries; return how many were removed."""
        removed = 0
        if self.directory.is_dir():
            for path in self.directory.glob("*.json"):
                path.unlink(missing_ok=True)
                removed += 1
        return removed
