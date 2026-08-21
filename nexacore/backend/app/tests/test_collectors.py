"""
Collector framework tests (Sprint 11/17): retry logic, error capture,
registry, and the CSVCollector's normalization mapping. No DB needed.
"""
import base64
import pytest

from app.collectors.base import BaseCollector, CollectorResult, CollectorRegistry, Listing
import app.collectors  # noqa: F401 — registers CSVCollector


class FlakyCollector(BaseCollector):
    """Fails `fail_times` times, then succeeds — used to test retry logic."""
    source_key = "flaky_test"
    max_retries = 2
    retry_backoff_seconds = 0  # keep tests fast

    def __init__(self, config=None, fail_times=0):
        super().__init__(config)
        self.fail_times = fail_times
        self.attempts = 0

    def fetch_raw(self):
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise ConnectionError("simulated network failure")
        return [{"address": "1 Main St", "asking_price": "100000"}]

    def normalize(self, raw_record):
        return Listing(address=raw_record["address"], asking_price=float(raw_record["asking_price"]))


class AlwaysFailsCollector(BaseCollector):
    source_key = "always_fails_test"
    max_retries = 1
    retry_backoff_seconds = 0

    def fetch_raw(self):
        raise ConnectionError("always fails")

    def normalize(self, raw_record):
        return Listing()


def test_collector_succeeds_after_transient_failures():
    collector = FlakyCollector(fail_times=2)
    result = collector.run()
    assert collector.attempts == 3
    assert len(result.listings) == 1
    assert result.listings[0].address == "1 Main St"


def test_collector_raises_after_exhausting_retries():
    collector = AlwaysFailsCollector()
    with pytest.raises(ConnectionError):
        collector.run()


def test_collector_result_captures_errors_without_raising():
    result = CollectorResult()
    result.add_error("bad record", raw_record={"foo": "bar"})
    result.finalize_stats()
    assert len(result.errors) == 1
    assert result.stats["errors"] == 1


def test_invalid_listing_is_captured_as_error_not_raised():
    class InvalidDataCollector(BaseCollector):
        source_key = "invalid_data_test"

        def fetch_raw(self):
            return [{"bedrooms": 3}]  # missing address AND listing_reference

        def normalize(self, raw_record):
            return Listing(bedrooms=raw_record["bedrooms"])

    result = InvalidDataCollector().run()
    assert len(result.listings) == 0
    assert len(result.errors) == 1
    assert "Validation failed" in result.errors[0].message


def test_registry_lookup():
    assert "csv_upload" in CollectorRegistry.available()
    collector_cls = CollectorRegistry.get("csv_upload")
    assert collector_cls.source_key == "csv_upload"


def test_registry_missing_key_raises_config_error():
    from app.collectors.base import CollectorConfigError
    with pytest.raises(CollectorConfigError):
        CollectorRegistry.get("does_not_exist")


def test_csv_collector_normalizes_realistic_row():
    from app.collectors.csv_collector import CSVCollector

    csv_bytes = (
        b"Listing Reference,Address,Suburb,Asking Price,Type,Bedrooms,Phone\n"
        b"REF-1,12 Oak Street,roodepoort,R 1 250 000,flat,3,082 123 4567\n"
    )
    config = {
        "file_bytes_b64": base64.b64encode(csv_bytes).decode(),
        "filename": "test.csv",
    }
    collector = CSVCollector(config=config)
    result = collector.run()

    assert len(result.listings) == 1
    listing = result.listings[0]
    assert listing.suburb == "Roodepoort"
    assert listing.property_type == "Apartment"
    assert listing.asking_price == 1250000.0
    assert listing.contact_number == "+27821234567"
