"""
Integration tests for the scan manager (Sprints 13, 16, 17): running a scan
end-to-end via the registered CSVCollector, duplicate classification during
a scan, and a scan against a disabled source failing cleanly.
"""

import base64
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.source import Source
from app.models.scan_job import ScanJob
from app.models.duplicate_match import DuplicateMatch
from app.services.scan_manager import run_scan
from app.services.scoring_engine import seed_default_rules
import app.collectors  # noqa: F401


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    seed_default_rules(session)

    yield session

    session.close()


def _csv_source(
    db,
    csv_bytes: bytes,
    filename: str = "listings.csv",
) -> Source:
    config = json.dumps({
        "file_bytes_b64": base64.b64encode(csv_bytes).decode(),
        "filename": filename,
    })

    source = Source(
        name=f"Test CSV Source {filename}",
        source_key=f"test_csv_{filename}",
        collector_type="csv_upload",
        is_enabled=True,
        config=config,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return source


def test_scan_creates_new_listings(db):
    csv_bytes = (
        b"Address,Suburb,Asking Price\n"
        b"1 Test St,Testville,1000000\n"
        b"2 Test St,Testville,2000000\n"
    )

    source = _csv_source(db, csv_bytes)
    scan = run_scan(db, source)

    assert scan.status == "completed"
    assert scan.new_listings == 2
    assert db.query(Property).count() == 2


def test_scan_against_disabled_source_fails_cleanly(db):
    source = Source(
        name="Disabled Source",
        source_key="disabled_test",
        collector_type="csv_upload",
        is_enabled=False,
        disabled_reason="No approved access",
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    scan = run_scan(db, source)

    assert scan.status == "failed"
    assert "disabled" in scan.errors.lower()
    assert db.query(Property).count() == 0


def test_scan_flags_likely_duplicate_without_auto_merging(db):
    first_csv = (
        b"Address,Suburb,Phone,Asking Price\n"
        b"12 Oak St,Roodepoort,0821234567,1850000\n"
    )

    source1 = _csv_source(db, first_csv, "first.csv")
    run_scan(db, source1)

    assert db.query(Property).count() == 1

    second_csv = (
        b"Address,Suburb,Phone,Asking Price\n"
        b"12 Oak St,Roodepoort,0821234567,1850000\n"
    )

    source2 = _csv_source(db, second_csv, "second.csv")
    scan2 = run_scan(db, source2)

    assert scan2.duplicate_listings == 1
    assert db.query(Property).count() == 2

    assert db.query(DuplicateMatch).count() == 1

    match = db.query(DuplicateMatch).first()

    assert match.match_type in ("likely", "possible")
    assert match.resolved is False


def test_scan_records_error_stats_for_invalid_rows(db):
    csv_bytes = b"Bedrooms\n3\n"

    source = _csv_source(db, csv_bytes)
    scan = run_scan(db, source)

    assert scan.status == "completed"
    assert scan.error_count == 1
    assert scan.new_listings == 0


def test_scan_job_relationships_and_source_stats_update(db):
    csv_bytes = (
        b"Address,Suburb,Asking Price\n"
        b"1 Test St,Testville,1000000\n"
    )

    source = _csv_source(db, csv_bytes)
    scan = run_scan(db, source)

    db.refresh(source)

    assert source.listings_collected_count == 1
    assert source.last_successful_scan_at is not None

    fetched_scan = (
        db.query(ScanJob)
        .filter(ScanJob.id == scan.id)
        .first()
    )

    assert fetched_scan.source_id == source.id