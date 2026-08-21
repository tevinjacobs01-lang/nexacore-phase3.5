"""
Generic collector framework (Sprint 11).

Every data source — approved API, licensed feed, public dataset, permissive
site, or manual file upload — implements BaseCollector so the rest of the
app (scan management, dedupe, scoring) never needs to know which source it's
talking to.

Nothing in this module or its subclasses is permitted to defeat CAPTCHAs,
login walls, anti-bot systems, or robots.txt restrictions (Sprint 17). A
source that requires that kind of bypass to collect from is not a valid
collector target — it should stay as a disabled Source with a documented
reason instead (see app/services/source_manager.py).
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Callable

logger = logging.getLogger("nexacore.collectors")


@dataclass
class Listing:
    """Standardized listing shape every collector must normalize into,
    regardless of source. Field names intentionally mirror the Property
    model so results can be mapped in directly."""
    listing_reference: str | None = None
    address: str | None = None
    suburb: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    listing_type: str | None = None  # "sale" | "rent"
    property_type: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    garages: int | None = None
    floor_size_sqm: float | None = None
    stand_size_sqm: float | None = None
    asking_price: float | None = None
    monthly_rental: float | None = None
    listing_date: date | None = None
    days_on_market: int | None = None
    listing_source: str | None = None
    listing_url: str | None = None
    agent_name: str | None = None
    contact_number: str | None = None
    email: str | None = None
    notes: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)  # original source record, for debugging


@dataclass
class CollectorError:
    message: str
    raw_record: dict[str, Any] | None = None
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CollectorResult:
    """Standardized output of a single collection run."""
    listings: list[Listing] = field(default_factory=list)
    errors: list[CollectorError] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def add_error(self, message: str, raw_record: dict[str, Any] | None = None) -> None:
        self.errors.append(CollectorError(message=message, raw_record=raw_record))
        logger.warning("Collector error: %s", message)

    def finalize_stats(self) -> None:
        self.stats.setdefault("listings_discovered", len(self.listings))
        self.stats.setdefault("errors", len(self.errors))


class CollectorConfigError(Exception):
    """Raised when a collector is misconfigured (missing credentials, etc.)."""


class BaseCollector(ABC):
    """
    Subclass this for every new data source. Only `fetch_raw` and
    `normalize` are source-specific; everything else (timeouts, retry,
    rate limiting, logging) is handled uniformly by `run`.
    """

    source_key: str = "base"
    default_timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 1.5
    min_seconds_between_requests: float = 0.0  # simple rate limit

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._last_request_time: float = 0.0

    # ---- Source-specific: implement these ----

    @abstractmethod
    def fetch_raw(self) -> list[dict[str, Any]]:
        """Retrieve raw records from the source. May raise; `run()` handles
        retries and error capture."""

    @abstractmethod
    def normalize(self, raw_record: dict[str, Any]) -> Listing:
        """Convert one raw record into a standardized Listing. Should raise
        ValueError on unrecoverable bad data — `run()` will capture it."""

    def validate(self, listing: Listing) -> list[str]:
        """Return a list of validation problems (empty list = valid).
        Default implementation delegates to the shared normalization
        service; override for source-specific rules."""
        from app.services.normalization import validate_listing
        return validate_listing(listing)

    # ---- Shared machinery: safety, retries, rate limiting ----

    def _respect_rate_limit(self) -> None:
        if self.min_seconds_between_requests <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        wait = self.min_seconds_between_requests - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    def _fetch_with_retry(self) -> list[dict[str, Any]]:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                self._respect_rate_limit()
                return self.fetch_raw()
            except Exception as exc:  # noqa: BLE001 — deliberately broad, we log & retry
                last_exc = exc
                logger.warning(
                    "%s: fetch attempt %d/%d failed: %s",
                    self.source_key, attempt, self.max_retries + 1, exc,
                )
                if attempt <= self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
        assert last_exc is not None
        raise last_exc

    def run(self) -> CollectorResult:
        """Runs the full collect → normalize → validate pipeline safely.
        Never raises for per-record problems; only raises if fetching the
        source itself fails after all retries (caller / ScanJob records
        that as a failed scan)."""
        result = CollectorResult()
        raw_records = self._fetch_with_retry()

        for raw in raw_records:
            try:
                listing = self.normalize(raw)
                problems = self.validate(listing)
                if problems:
                    result.add_error(f"Validation failed: {'; '.join(problems)}", raw_record=raw)
                    continue
                listing.listing_source = listing.listing_source or self.source_key
                result.listings.append(listing)
            except Exception as exc:  # noqa: BLE001
                result.add_error(str(exc), raw_record=raw)

        result.finalize_stats()
        return result


class CollectorRegistry:
    """Maps a collector_type string (stored on Source.collector_type) to a
    BaseCollector subclass, so new sources can be added by registering a
    class here without touching scan/source management code."""

    _registry: dict[str, type[BaseCollector]] = {}

    @classmethod
    def register(cls, key: str) -> Callable[[type[BaseCollector]], type[BaseCollector]]:
        def decorator(collector_cls: type[BaseCollector]) -> type[BaseCollector]:
            collector_cls.source_key = key
            cls._registry[key] = collector_cls
            return collector_cls
        return decorator

    @classmethod
    def get(cls, key: str) -> type[BaseCollector]:
        if key not in cls._registry:
            raise CollectorConfigError(f"No collector registered for '{key}'")
        return cls._registry[key]

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())
