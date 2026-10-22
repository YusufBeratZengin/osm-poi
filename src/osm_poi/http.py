"""Small polite HTTP client: User-Agent, spacing between requests, retries with backoff."""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from email.message import Message

from osm_poi.errors import HttpError

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER = 120.0


def _check_url(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in {"http", "https"}:
        raise HttpError(f"Only http and https URLs are supported: {url!r}")


def retry_after_seconds(headers: Message | None) -> float | None:
    """Parse a numeric Retry-After header; HTTP-date values are ignored."""
    if headers is None:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, min(float(raw), MAX_RETRY_AFTER))
    except ValueError:
        return None


class HttpClient:
    """Blocking client. ``sleep`` and ``clock`` are injectable for tests."""

    def __init__(
        self,
        user_agent: str,
        timeout: float = 60.0,
        retries: int = 3,
        backoff: float = 2.0,
        min_interval: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = max(0, retries)
        self.backoff = backoff
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None

    def _wait_turn(self) -> None:
        if self._last_request is not None and self.min_interval > 0:
            wait = self.min_interval - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    def get(self, url: str, params: Mapping[str, str] | None = None) -> bytes:
        if params:
            url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params)}"
        return self._request(url, None)

    def post_form(self, url: str, data: Mapping[str, str]) -> bytes:
        return self._request(url, urllib.parse.urlencode(data).encode("utf-8"))

    def _request(self, url: str, body: bytes | None) -> bytes:
        _check_url(url)
        last_error = "unknown error"
        last_status: int | None = None
        for attempt in range(self.retries + 1):
            self._wait_turn()
            request = urllib.request.Request(
                url,
                data=body,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            delay = self.backoff * (2**attempt)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload: bytes = response.read()
                    return payload
            except urllib.error.HTTPError as exc:
                last_status = exc.code
                last_error = f"HTTP {exc.code} {exc.reason}"
                if exc.code not in RETRY_STATUSES:
                    raise HttpError(f"{last_error} for {url}", exc.code) from exc
                hinted = retry_after_seconds(exc.headers)
                if hinted is not None:
                    delay = hinted
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_status = None
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < self.retries:
                self._sleep(delay)
        raise HttpError(
            f"Request failed after {self.retries + 1} attempts ({last_error}): {url}",
            last_status,
        )
