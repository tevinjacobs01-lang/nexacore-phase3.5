"""
Scan job management (Sprint 16). Runs a registered collector against a
Source, records a ScanJob with full stats, and (for now) hands resulting
listings to the same dedupe-aware upsert path the CSV importer uses.
"""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.collectors.base import CollectorRegistry, CollectorConfigError
from app.models.source import Source
from app.models.scan_job import ScanJob
from app.models.property import Property
from app.models.duplicate_match import DuplicateMatch
from app.services.dedupe import classify_duplicate
from app.services.scoring_engine import recompute_score


def run_scan(db: Session, source: Source) -> ScanJob:
    scan = ScanJob(source_id=source.id, status="running", started_at=datetime.utcnow())
    db.add(scan)
    db.commit()
    db.refresh(scan)

    if not source.is_enabled:
        scan.status = "failed"
        scan.errors = f"Source '{source.name}' is disabled: {source.disabled_reason or 'no reason recorded'}"
        scan.finished_at = datetime.utcnow()
        db.commit()
        return scan

    start = time.monotonic()
    try:
        collector_cls = CollectorRegistry.get(source.collector_type)
        collector = collector_cls(config=_parse_config(source.config))
        result = collector.run()
    except CollectorConfigError as exc:
        scan.status = "failed"
        scan.errors = str(exc)
        scan.finished_at = datetime.utcnow()
        scan.duration_seconds = time.monotonic() - start
        db.commit()
        return scan
    except Exception as exc:  # noqa: BLE001 — source fetch failed after retries
        scan.status = "failed"
        scan.errors = f"Collector run failed: {exc}"
        scan.finished_at = datetime.utcnow()
        scan.duration_seconds = time.monotonic() - start
        source.last_error = str(exc)
        db.commit()
        return scan

    new_count = updated_count = dup_count = 0
    existing_pool = db.query(Property).all()  # fine at MVP scale; index/optimize later

    for listing in result.listings:
        matches = []
        for existing in existing_pool:
            classification = classify_duplicate(listing, existing)
            if classification.match_type != "unique":
                matches.append((existing, classification))

        if matches:
            best_existing, best_classification = matches[0]

            if best_classification.match_type == "exact":
                # Treat as an update to the existing record rather than a new row —
                # no DuplicateMatch needed since nothing new was created.
                for field in (
                    "asking_price", "monthly_rental", "days_on_market", "notes",
                    "agent_name", "contact_number", "email",
                ):
                    value = getattr(listing, field, None)
                    if value is not None:
                        setattr(best_existing, field, value)
                updated_count += 1
            else:
                # "likely" or "possible": create the new row but flag it for
                # human review rather than silently merging or dropping it.
                new_prop = Property(
                    listing_reference=listing.listing_reference, address=listing.address,
                    suburb=listing.suburb, city=listing.city, province=listing.province,
                    postal_code=listing.postal_code, listing_type=listing.listing_type,
                    property_type=listing.property_type, bedrooms=listing.bedrooms,
                    bathrooms=listing.bathrooms, garages=listing.garages,
                    asking_price=listing.asking_price, monthly_rental=listing.monthly_rental,
                    listing_date=listing.listing_date, days_on_market=listing.days_on_market,
                    listing_source=listing.listing_source, listing_url=listing.listing_url,
                    agent_name=listing.agent_name, contact_number=listing.contact_number,
                    email=listing.email, notes=listing.notes,
                )
                db.add(new_prop)
                db.flush()  # assign new_prop.id before referencing it below
                recompute_score(db, new_prop)
                db.add(DuplicateMatch(
                    property_id=new_prop.id,
                    matched_property_id=best_existing.id,
                    match_type=best_classification.match_type,
                    match_reason=best_classification.reason,
                ))
                existing_pool.append(new_prop)
                dup_count += 1
        else:
            new_prop = Property(
                listing_reference=listing.listing_reference, address=listing.address,
                suburb=listing.suburb, city=listing.city, province=listing.province,
                postal_code=listing.postal_code, listing_type=listing.listing_type,
                property_type=listing.property_type, bedrooms=listing.bedrooms,
                bathrooms=listing.bathrooms, garages=listing.garages,
                asking_price=listing.asking_price, monthly_rental=listing.monthly_rental,
                listing_date=listing.listing_date, days_on_market=listing.days_on_market,
                listing_source=listing.listing_source, listing_url=listing.listing_url,
                agent_name=listing.agent_name, contact_number=listing.contact_number,
                email=listing.email, notes=listing.notes,
            )
            db.add(new_prop)
            db.flush()
            recompute_score(db, new_prop)
            existing_pool.append(new_prop)
            new_count += 1

    scan.listings_discovered = len(result.listings)
    scan.new_listings = new_count
    scan.updated_listings = updated_count
    scan.duplicate_listings = dup_count
    scan.error_count = len(result.errors)
    scan.errors = "\n".join(e.message for e in result.errors)[:4000] if result.errors else None
    scan.status = "completed"
    scan.finished_at = datetime.utcnow()
    scan.duration_seconds = time.monotonic() - start

    source.last_successful_scan_at = datetime.utcnow()
    source.listings_collected_count += len(result.listings)
    if result.errors:
        source.last_error = result.errors[-1].message

    db.commit()
    db.refresh(scan)
    return scan


def _parse_config(config_str: str | None) -> dict:
    import json
    if not config_str:
        return {}
    try:
        return json.loads(config_str)
    except (ValueError, TypeError):
        return {}
