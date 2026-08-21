"""
CSV / Excel importer.

Responsibilities:
- Read an uploaded file (.csv, .xls, .xlsx) into a normalized list of dict rows.
- Map flexible source column names onto Property model fields.
- Detect duplicates: primary key is listing_reference; fallback is
  (address + suburb) case-insensitive match when no reference is present.
- Create new properties, update existing ones (only overwriting fields that
  actually changed), and track what changed for the import log.
- Never raise on a single bad row — collect the error and keep going.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.import_log import ImportLog

# Map of accepted incoming column names (lowercased, stripped) -> Property field.
# Add synonyms here as real-world source files are seen.
COLUMN_MAP: dict[str, str] = {
    "listing reference": "listing_reference",
    "reference": "listing_reference",
    "ref": "listing_reference",
    "address": "address",
    "suburb": "suburb",
    "city": "city",
    "province": "province",
    "postal code": "postal_code",
    "postcode": "postal_code",
    "latitude": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "sale or rent": "listing_type",
    "listing type": "listing_type",
    "type": "property_type",
    "property type": "property_type",
    "bedrooms": "bedrooms",
    "beds": "bedrooms",
    "bathrooms": "bathrooms",
    "baths": "bathrooms",
    "garages": "garages",
    "floor size": "floor_size_sqm",
    "floor size (sqm)": "floor_size_sqm",
    "stand size": "stand_size_sqm",
    "stand size (sqm)": "stand_size_sqm",
    "asking price": "asking_price",
    "price": "asking_price",
    "monthly rental": "monthly_rental",
    "rental": "monthly_rental",
    "listing date": "listing_date",
    "date listed": "listing_date",
    "days on market": "days_on_market",
    "listing source": "listing_source",
    "source": "listing_source",
    "listing url": "listing_url",
    "url": "listing_url",
    "agent name": "agent_name",
    "agent": "agent_name",
    "contact number": "contact_number",
    "phone": "contact_number",
    "email": "email",
    "notes": "notes",
}

INT_FIELDS = {"bedrooms", "bathrooms", "garages", "days_on_market"}
DECIMAL_FIELDS = {
    "latitude", "longitude", "floor_size_sqm", "stand_size_sqm",
    "asking_price", "monthly_rental",
}
DATE_FIELDS = {"listing_date"}


class ImportResult:
    def __init__(self):
        self.rows_processed = 0
        self.rows_created = 0
        self.rows_updated = 0
        self.rows_skipped = 0
        self.errors: list[str] = []
        self.touched_ids: list = []


def _read_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(io.BytesIO(file_bytes))
    raise ValueError(f"Unsupported file type for '{filename}'. Use .csv, .xls, or .xlsx.")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip().lower())
    mapped = {}
    for col in df.columns:
        target = COLUMN_MAP.get(col)
        if target:
            mapped[col] = target
    df = df.rename(columns=mapped)
    # Drop any columns that didn't map to a known Property field
    known = set(COLUMN_MAP.values())
    keep = [c for c in df.columns if c in known]
    return df[keep]


def _coerce_value(field: str, raw):
    if pd.isna(raw):
        return None
    try:
        if field in INT_FIELDS:
            return int(float(raw))
        if field in DECIMAL_FIELDS:
            return float(Decimal(str(raw)))
        if field in DATE_FIELDS:
            if isinstance(raw, (date, datetime)):
                return raw if isinstance(raw, date) and not isinstance(raw, datetime) else raw.date()
            return pd.to_datetime(raw).date()
        if field == "listing_type":
            val = str(raw).strip().lower()
            if val in ("sale", "for sale", "s"):
                return "sale"
            if val in ("rent", "to let", "for rent", "r"):
                return "rent"
            return val
        return str(raw).strip()
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError(f"Could not parse value '{raw}' for field '{field}'")


def _find_existing(db: Session, row: dict) -> Property | None:
    ref = row.get("listing_reference")
    if ref:
        existing = db.query(Property).filter(Property.listing_reference == ref).first()
        if existing:
            return existing

    address = row.get("address")
    suburb = row.get("suburb")
    if address and suburb:
        return (
            db.query(Property)
            .filter(
                Property.address.ilike(address),
                Property.suburb.ilike(suburb),
            )
            .first()
        )
    return None


def import_file(file_bytes: bytes, filename: str, db: Session, user_id=None) -> ImportLog:
    log = ImportLog(
        user_id=user_id,
        filename=filename,
        source_type="excel" if filename.lower().endswith((".xls", ".xlsx")) else "csv",
    )
    result = ImportResult()

    try:
        df = _read_dataframe(file_bytes, filename)
        df = _normalize_columns(df)
    except Exception as exc:  # bad file entirely
        log.errors = str(exc)
        log.rows_processed = 0
        log.finished_at = datetime.utcnow()
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    for idx, raw_row in enumerate(df.to_dict(orient="records")):
        result.rows_processed += 1
        row_num = idx + 2  # account for header row, 1-indexed for humans

        try:
            row: dict = {}
            for field, raw_value in raw_row.items():
                row[field] = _coerce_value(field, raw_value)

            if not row.get("address") and not row.get("listing_reference"):
                result.rows_skipped += 1
                result.errors.append(f"Row {row_num}: missing both address and listing reference — skipped")
                continue

            existing = _find_existing(db, row)

            if existing:
                changed = False

                # Relisting signal: listing_date moved forward while days_on_market
                # dropped noticeably — a classic relist pattern.
                new_dom = row.get("days_on_market")
                new_listing_date = row.get("listing_date")
                if (
                    new_dom is not None
                    and existing.days_on_market is not None
                    and new_dom < existing.days_on_market - 5
                    and new_listing_date
                    and existing.listing_date
                    and new_listing_date > existing.listing_date
                ):
                    existing.is_relisted = True
                    changed = True

                # Price reduction signal
                new_price = row.get("asking_price")
                if (
                    new_price is not None
                    and existing.asking_price is not None
                    and float(new_price) < float(existing.asking_price)
                ):
                    existing.previous_asking_price = existing.asking_price
                    existing.price_reduced_at = datetime.utcnow()
                    changed = True

                for field, value in row.items():
                    if value is not None and getattr(existing, field, None) != value:
                        setattr(existing, field, value)
                        changed = True
                if changed:
                    result.rows_updated += 1
                    result.touched_ids.append(existing.id)
                else:
                    result.rows_skipped += 1
            else:
                new_prop = Property(**row)
                db.add(new_prop)
                db.flush()  # assign an id without ending the transaction
                result.rows_created += 1
                result.touched_ids.append(new_prop.id)

        except Exception as exc:
            result.rows_skipped += 1
            result.errors.append(f"Row {row_num}: {exc}")
            continue

    db.commit()

    if result.touched_ids:
        from app.services.scoring_engine import recompute_score  # local import avoids a circular import

        touched = db.query(Property).filter(Property.id.in_(result.touched_ids)).all()
        for prop in touched:
            recompute_score(db, prop)
        db.commit()

    log.rows_processed = result.rows_processed
    log.rows_created = result.rows_created
    log.rows_updated = result.rows_updated
    log.rows_skipped = result.rows_skipped
    log.errors = "\n".join(result.errors)[:4000] if result.errors else None
    log.finished_at = datetime.utcnow()
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
