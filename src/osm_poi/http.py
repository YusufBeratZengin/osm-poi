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
MAX_REDIRECTS = 5


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


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
        self._opener = urllib.request.build_opener(_NoRedirectHandler())

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
        current_url = url
        current_body = body
        redirect_count = 0

        while True:
            last_error = "unknown error"
            last_status: int | None = None
            redirect_to: str | None = None

            for attempt in range(self.retries + 1):
                self._wait_turn()
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                }
                request = urllib.request.Request(
                    current_url,
                    data=current_body,
                    headers=headers,
                )
                delay = self.backoff * (2**attempt)
                try:
                    with self._opener.open(request, timeout=self.timeout) as response:
                        payload: bytes = response.read()
                        content_encoding = (response.headers.get("Content-Encoding") or "").lower()
                        if "gzip" in content_encoding or payload.startswith(b"\x1f\x8b"):
                            import gzip

                            try:
                                payload = gzip.decompress(payload)
                            except Exception as exc:
                                raise HttpError(
                                    f"Failed to decompress gzip response: {exc}"
                                ) from exc
                        elif "deflate" in content_encoding:
                            import zlib

                            try:
                                payload = zlib.decompress(payload)
                            except Exception as exc:
                                raise HttpError(
                                    f"Failed to decompress deflate response: {exc}"
                                ) from exc
                        return payload
                except urllib.error.HTTPError as exc:
                    last_status = exc.code
                    last_error = f"HTTP {exc.code} {exc.reason}"
                    if exc.code in {301, 302, 303, 307, 308}:
                        loc = exc.headers.get("Location")
                        if not loc:
                            raise HttpError(
                                f"HTTP {exc.code} redirect missing Location header: {current_url}",
                                exc.code,
                            ) from exc
                        redirect_to = urllib.parse.urljoin(current_url, loc)
                        if exc.code == 303:
                            current_body = None
                        break
                    if exc.code not in RETRY_STATUSES:
                        raise HttpError(f"{last_error} for {current_url}", exc.code) from exc
                    hinted = retry_after_seconds(exc.headers)
                    if hinted is not None:
                        delay = hinted
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                    last_status = None
                    last_error = f"{type(exc).__name__}: {exc}"
                if attempt < self.retries:
                    self._sleep(delay)

            if redirect_to is not None:
                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise HttpError(f"Too many redirects ({redirect_count}) for {url}")
                current_url = redirect_to
                _check_url(current_url)
                continue

            raise HttpError(
                f"Request failed after {self.retries + 1} attempts ({last_error}): {current_url}",
                last_status,
            )
