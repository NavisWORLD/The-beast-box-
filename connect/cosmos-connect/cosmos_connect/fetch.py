"""Bounded public HTTP reads. No credentials and no user-supplied URLs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "NavisWORLD/The-beast-box-"
GITHUB_API = f"https://api.github.com/repos/{REPO}"
RAW_ROOT = f"https://raw.githubusercontent.com/{REPO}"
RELEASE_URL = "https://beastboxcosmos.xyz/api/release"
FRONTEND_URL = "https://beastboxcosmos.xyz/"
BRIDGE_ORIGIN = "https://cosmos-owner-bridge-production.up.railway.app"
USER_AGENT = "BeastBox-COSMOS-CONNECT/0.1 (read-only public connector; +https://github.com/NavisWORLD/The-beast-box-)"
ALLOWED_HOSTS = {
    "beastboxcosmos.xyz",
    "www.beastboxcosmos.xyz",
    "cosmos-owner-bridge-production.up.railway.app",
    "api.github.com",
    "raw.githubusercontent.com",
}


class SourceError(Exception):
    def __init__(self, code: str, message: str, source: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.source = source or {}


@dataclass
class FetchResult:
    status: int
    body: bytes
    url: str
    content_type: str = ""
    truncated: bool = False


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def commit_url() -> str:
    return f"{GITHUB_API}/commits/main"


def raw_url(sha: str, path: str) -> str:
    return f"{RAW_ROOT}/{sha}/{path}"


def workflow_runs_url(filename: str, limit: int) -> str:
    return f"{GITHUB_API}/actions/workflows/{filename}/runs?per_page={limit}"


def bridge_url(path: str) -> str:
    return BRIDGE_ORIGIN + path


def _host_allowed(url: str) -> bool:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS and not parts.username


def urllib_fetch(url: str, timeout: float, max_bytes: int = 400_000) -> FetchResult:
    if not _host_allowed(url):
        raise SourceError("UPSTREAM_UNAVAILABLE", "URL is outside the public allowlist")
    accept = (
        "application/vnd.github+json" if "api.github.com" in url else "application/json, text/plain, text/html;q=0.5"
    )
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            return FetchResult(
                status=getattr(response, "status", 200),
                body=body[:max_bytes],
                url=response.geturl(),
                content_type=response.headers.get("Content-Type", ""),
                truncated=len(body) > max_bytes,
            )
    except HTTPError as exc:
        body = exc.read(max_bytes + 1)
        return FetchResult(
            status=exc.code,
            body=body[:max_bytes],
            url=url,
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            truncated=len(body) > max_bytes,
        )
    except TimeoutError as exc:
        raise SourceError("UPSTREAM_TIMEOUT", "upstream timed out") from exc
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            raise SourceError("UPSTREAM_TIMEOUT", "upstream timed out") from exc
        raise SourceError("UPSTREAM_UNAVAILABLE", "upstream unreachable") from exc
    except OSError as exc:
        raise SourceError("UPSTREAM_UNAVAILABLE", "upstream unreachable") from exc


class SourceBook:
    """Short-lived cache so one page view does not stampede the GitHub API."""

    def __init__(
        self,
        fetch: Callable[..., FetchResult] | None = None,
        clock: Callable[[], datetime] | None = None,
        ttl: float = 45.0,
        timeout: float = 8.0,
    ):
        self.fetch = fetch or urllib_fetch
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.ttl = ttl
        self.timeout = timeout
        self._cache: dict[str, tuple[float, FetchResult, str]] = {}

    def now(self) -> str:
        return iso(self.clock())

    def get_response(self, url: str) -> tuple[FetchResult, dict]:
        import time

        cached = self._cache.get(url)
        if cached and (time.monotonic() - cached[0]) < self.ttl:
            result, retrieved = cached[1], cached[2]
            return result, self._source(url, result, retrieved, cached=True)
        try:
            result = self.fetch(url, self.timeout)
        except SourceError:
            raise
        except TimeoutError as exc:
            raise SourceError("UPSTREAM_TIMEOUT", "upstream timed out", {"url": url}) from exc
        except OSError as exc:
            raise SourceError("UPSTREAM_UNAVAILABLE", "upstream unreachable", {"url": url}) from exc
        if not isinstance(result, FetchResult):
            raise SourceError("UPSTREAM_UNAVAILABLE", "fetcher returned an unexpected result", {"url": url})
        retrieved = self.now()
        if 200 <= result.status < 300:
            self._cache[url] = (time.monotonic(), result, retrieved)
        return result, self._source(url, result, retrieved, cached=False)

    def _source(self, url: str, result: FetchResult, retrieved: str, cached: bool) -> dict:
        return {
            "url": result.url or url,
            "requested_url": url,
            "http_status": result.status,
            "retrieved_at": retrieved,
            "cached": cached,
        }

    def get_json(self, url: str) -> tuple[object, dict]:
        result, source = self.get_response(url)
        self._raise_for_transport(result, source)
        if result.truncated:
            raise SourceError("UPSTREAM_UNAVAILABLE", "JSON response exceeded the read bound", source)
        try:
            return json.loads(result.body.decode("utf-8")), source
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceError("UPSTREAM_UNAVAILABLE", "response was not JSON", source) from exc

    def get_text(self, url: str, limit: int = 20000) -> tuple[str, bool, dict]:
        result, source = self.get_response(url)
        self._raise_for_transport(result, source)
        text = result.body.decode("utf-8", errors="replace")
        clipped = result.truncated or len(text) > limit
        return text[:limit], clipped, source

    def _raise_for_transport(self, result: FetchResult, source: dict) -> None:
        if result.status in {403, 429} and _rate_limited(result):
            raise SourceError("UPSTREAM_RATE_LIMIT", "GitHub or upstream rate limit", source)
        if result.status == 404:
            raise SourceError("NOT_FOUND", "source returned HTTP 404", source)
        if result.status < 200 or result.status >= 300:
            raise SourceError("UPSTREAM_UNAVAILABLE", f"upstream HTTP {result.status}", source)


def _rate_limited(result: FetchResult) -> bool:
    if result.status == 429:
        return True
    text = result.body.decode("utf-8", errors="replace").lower()
    return "rate limit" in text or "secondary rate" in text
