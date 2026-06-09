#!/usr/bin/env python3
"""Shared polite crawling settings for senzhang.me archive scripts."""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import asdict, dataclass, fields
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_USER_AGENT = (
    "senzhang-legacy-archive/1.1 "
    "(+https://github.com/zsenarchitect/senzhang-legacy-website-archive; "
    "polite personal-site archival crawler)"
)

RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})

PROFILES: dict[str, dict[str, Any]] = {
    "safe": {
        "page_delay_seconds": 1.25,
        "asset_delay_seconds": 0.85,
        "delay_jitter_seconds": 0.35,
        "request_timeout_seconds": 90,
        "max_retries": 4,
        "retry_backoff_seconds": 3.0,
        "retry_backoff_multiplier": 2.0,
        "max_retry_wait_seconds": 120.0,
        "respect_retry_after": True,
        "min_interval_seconds": 0.5,
    },
    "normal": {
        "page_delay_seconds": 0.5,
        "asset_delay_seconds": 0.25,
        "delay_jitter_seconds": 0.15,
        "request_timeout_seconds": 60,
        "max_retries": 3,
        "retry_backoff_seconds": 2.0,
        "retry_backoff_multiplier": 2.0,
        "max_retry_wait_seconds": 60.0,
        "respect_retry_after": True,
        "min_interval_seconds": 0.2,
    },
    "fast": {
        "page_delay_seconds": 0.2,
        "asset_delay_seconds": 0.15,
        "delay_jitter_seconds": 0.05,
        "request_timeout_seconds": 60,
        "max_retries": 2,
        "retry_backoff_seconds": 1.0,
        "retry_backoff_multiplier": 1.5,
        "max_retry_wait_seconds": 30.0,
        "respect_retry_after": True,
        "min_interval_seconds": 0.1,
    },
}


@dataclass
class CrawlConfig:
    user_agent: str = DEFAULT_USER_AGENT
    page_delay_seconds: float = 1.25
    asset_delay_seconds: float = 0.85
    delay_jitter_seconds: float = 0.35
    request_timeout_seconds: int = 90
    max_retries: int = 4
    retry_backoff_seconds: float = 3.0
    retry_backoff_multiplier: float = 2.0
    max_retry_wait_seconds: float = 120.0
    respect_retry_after: bool = True
    min_interval_seconds: float = 0.5
    profile: str = "safe"

    def delay_for(self, kind: str) -> float:
        base = self.page_delay_seconds if kind == "page" else self.asset_delay_seconds
        jitter = random.uniform(0.0, self.delay_jitter_seconds) if self.delay_jitter_seconds > 0 else 0.0
        return base + jitter

    def to_manifest_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["profiles_available"] = sorted(PROFILES)
        return data


def default_config_path() -> Path:
    return Path(__file__).resolve().parent / "crawl-config.json"


def _merge_dict(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged


def load_crawl_config(
    config_path: Path | None = None,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> CrawlConfig:
    path = config_path or default_config_path()
    file_data: dict[str, Any] = {}
    if path.is_file():
        file_data = json.loads(path.read_text(encoding="utf-8"))

    active_profile = profile or file_data.get("profile") or "safe"
    if active_profile not in PROFILES:
        raise ValueError("Unknown crawl profile: {}".format(active_profile))

    merged = _merge_dict(PROFILES[active_profile], file_data)
    merged["profile"] = active_profile
    if profile:
        merged["profile"] = profile

    if cli_overrides:
        merged = _merge_dict(merged, cli_overrides)

    allowed = {f.name for f in fields(CrawlConfig)}
    kwargs = {k: merged[k] for k in merged if k in allowed}
    return CrawlConfig(**kwargs)


def add_crawl_cli_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="JSON crawl settings file (default: scripts/crawl-config.json)",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        help="Delay/retry preset: safe (default), normal, or fast",
    )
    parser.add_argument("--page-delay", type=float, metavar="SEC", help="Pause after each HTML page fetch")
    parser.add_argument("--asset-delay", type=float, metavar="SEC", help="Pause after each asset download")
    parser.add_argument("--jitter", type=float, metavar="SEC", help="Random extra delay up to this many seconds")
    parser.add_argument("--timeout", type=int, metavar="SEC", help="Per-request timeout")
    parser.add_argument("--max-retries", type=int, metavar="N", help="Retries for transient HTTP/network errors")
    parser.add_argument(
        "--user-agent",
        metavar="UA",
        help="HTTP User-Agent string (identify this as an archival crawler)",
    )


def crawl_config_from_args(args: argparse.Namespace) -> CrawlConfig:
    overrides: dict[str, Any] = {}
    if getattr(args, "page_delay", None) is not None:
        overrides["page_delay_seconds"] = args.page_delay
    if getattr(args, "asset_delay", None) is not None:
        overrides["asset_delay_seconds"] = args.asset_delay
    if getattr(args, "jitter", None) is not None:
        overrides["delay_jitter_seconds"] = args.jitter
    if getattr(args, "timeout", None) is not None:
        overrides["request_timeout_seconds"] = args.timeout
    if getattr(args, "max_retries", None) is not None:
        overrides["max_retries"] = args.max_retries
    if getattr(args, "user_agent", None):
        overrides["user_agent"] = args.user_agent

    config_path = Path(args.config) if getattr(args, "config", None) else None
    return load_crawl_config(config_path=config_path, profile=args.profile, cli_overrides=overrides or None)


def print_crawl_config(config: CrawlConfig) -> None:
    print(
        "Crawl profile: {} (page {:.2f}s + jitter, asset {:.2f}s + jitter, "
        "retries {}, timeout {}s)".format(
            config.profile,
            config.page_delay_seconds,
            config.asset_delay_seconds,
            config.max_retries,
            config.request_timeout_seconds,
        )
    )


class PoliteFetcher:
    def __init__(self, config: CrawlConfig):
        self.config = config
        self._last_request_monotonic = 0.0

    def _enforce_min_interval(self) -> None:
        if self.config.min_interval_seconds <= 0:
            return
        if self._last_request_monotonic <= 0:
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        wait = self.config.min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    @staticmethod
    def _retry_after_seconds(error: HTTPError) -> float | None:
        header = error.headers.get("Retry-After") if error.headers else None
        if not header:
            return None
        try:
            return max(0.0, float(header))
        except ValueError:
            try:
                when = parsedate_to_datetime(header)
                return max(0.0, when.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return None

    def fetch(self, url: str) -> bytes:
        attempts = self.config.max_retries + 1
        backoff = self.config.retry_backoff_seconds
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            self._enforce_min_interval()
            req = Request(url, headers={"User-Agent": self.config.user_agent})
            try:
                with urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                    data = resp.read()
                self._last_request_monotonic = time.monotonic()
                return data
            except HTTPError as exc:
                last_error = exc
                if exc.code not in RETRYABLE_HTTP_CODES or attempt >= attempts:
                    raise
                wait = backoff
                if self.config.respect_retry_after:
                    retry_after = self._retry_after_seconds(exc)
                    if retry_after is not None:
                        wait = max(wait, retry_after)
                wait = min(wait, self.config.max_retry_wait_seconds)
                print(
                    "  retry {}/{} HTTP {} for {} (wait {:.1f}s)".format(
                        attempt, attempts - 1, exc.code, url, wait
                    ),
                    file=sys.stderr,
                )
                time.sleep(wait)
                backoff = min(
                    backoff * self.config.retry_backoff_multiplier,
                    self.config.max_retry_wait_seconds,
                )
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt >= attempts:
                    raise
                wait = min(backoff, self.config.max_retry_wait_seconds)
                print(
                    "  retry {}/{} {} for {} (wait {:.1f}s)".format(
                        attempt, attempts - 1, type(exc).__name__, url, wait
                    ),
                    file=sys.stderr,
                )
                time.sleep(wait)
                backoff = min(
                    backoff * self.config.retry_backoff_multiplier,
                    self.config.max_retry_wait_seconds,
                )

        if last_error:
            raise last_error
        raise RuntimeError("fetch failed without error: {}".format(url))

    def pause_after(self, kind: str) -> None:
        delay = self.config.delay_for(kind)
        if delay > 0:
            time.sleep(delay)
