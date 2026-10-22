"""Shared fixtures: a fake Overpass/Nominatim server bound to localhost only."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

Reply = tuple[int, dict[str, str], bytes]


@dataclass
class FakeServer:
    base_url: str
    requests: list[dict[str, Any]] = field(default_factory=list)
    # Queue of scripted replies per path; when empty the default handler is used.
    scripted: dict[str, list[Reply]] = field(default_factory=dict)
    default: dict[str, Reply] = field(default_factory=dict)

    def script(self, path: str, *replies: Reply) -> None:
        self.scripted.setdefault(path, []).extend(replies)

    def set_default(
        self, path: str, status: int, body: object, headers: dict[str, str] | None = None
    ) -> None:
        payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.default[path] = (status, headers or {}, payload)

    def count(self, path: str) -> int:
        return sum(1 for r in self.requests if r["path"] == path)


def json_reply(body: object, status: int = 200, headers: dict[str, str] | None = None) -> Reply:
    return status, headers or {}, json.dumps(body).encode("utf-8")


@pytest.fixture
def fake_server() -> Iterator[FakeServer]:
    state: FakeServer

    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else ""
            state.requests.append(
                {
                    "method": self.command,
                    "path": parsed.path,
                    "query": parse_qs(parsed.query),
                    "form": parse_qs(body),
                    "user_agent": self.headers.get("User-Agent"),
                }
            )
            queue = state.scripted.get(parsed.path)
            if queue:
                status, headers, payload = queue.pop(0)
            else:
                status, headers, payload = state.default.get(
                    parsed.path, (404, {}, b'{"error": "not scripted"}')
                )
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = _serve
        do_POST = _serve

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state = FakeServer(base_url=f"http://127.0.0.1:{server.server_address[1]}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def no_sleep() -> Callable[[float], None]:
    return lambda _seconds: None


CAFE_ELEMENTS = [
    {
        "type": "node",
        "id": 1,
        "lat": 40.99,
        "lon": 29.03,
        "tags": {
            "amenity": "cafe",
            "name": "Kahve Evi",
            "addr:street": "Moda Caddesi",
            "addr:housenumber": "10",
            "phone": "+90 216 000 00 00",
            "website": "https://example.org",
            "opening_hours": "Mo-Su 08:00-22:00",
        },
    },
    {
        "type": "way",
        "id": 2,
        "center": {"lat": 40.9902, "lon": 29.0301},
        "tags": {"amenity": "cafe", "name": "Kahve Evi"},
    },
    {
        "type": "node",
        "id": 3,
        "lat": 40.98,
        "lon": 29.02,
        "tags": {"amenity": "restaurant", "name": "Lokanta"},
    },
    {"type": "node", "id": 4, "lat": 40.97, "lon": 29.01, "tags": {"amenity": "cafe"}},
]
