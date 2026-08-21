"""
CSVCollector — the one fully-wired, approved data source: a user-provided
CSV/Excel upload. Demonstrates the BaseCollector interface using the same
normalization service every future collector will share.

Config expected: {"file_bytes_b64": "<base64>", "filename": "listings.csv"}
"""
from __future__ import annotations

import base64
import io
from typing import Any

import pandas as pd

from app.collectors.base import BaseCollector, CollectorRegistry, Listing, CollectorConfigError
from app.services import normalization as norm


@CollectorRegistry.register("csv_upload")
class CSVCollector(BaseCollector):
    def fetch_raw(self) -> list[dict[str, Any]]:
        b64 = self.config.get("file_bytes_b64")
        filename = self.config.get("filename", "upload.csv")
        if not b64:
            raise CollectorConfigError("CSVCollector requires 'file_bytes_b64' in config")

        file_bytes = base64.b64decode(b64)
        if filename.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            df = pd.read_csv(io.BytesIO(file_bytes))
        df = df.rename(columns=lambda c: str(c).strip().lower())
        return df.to_dict(orient="records")

    def normalize(self, raw_record: dict[str, Any]) -> Listing:
        get = lambda *keys: next((raw_record[k] for k in keys if k in raw_record and pd.notna(raw_record[k])), None)

        return Listing(
            listing_reference=get("listing reference", "reference", "ref"),
            address=get("address"),
            suburb=norm.normalize_suburb(get("suburb")),
            city=norm.normalize_city(get("city")),
            province=norm.normalize_province(get("province")),
            postal_code=str(get("postal code", "postcode") or "") or None,
            listing_type=self._normalize_listing_type(get("sale or rent", "listing type")),
            property_type=norm.normalize_property_type(get("type", "property type")),
            bedrooms=norm.normalize_int_count(get("bedrooms", "beds")),
            bathrooms=norm.normalize_int_count(get("bathrooms", "baths")),
            garages=norm.normalize_int_count(get("garages")),
            asking_price=norm.normalize_price(get("asking price", "price")),
            monthly_rental=norm.normalize_price(get("monthly rental", "rental")),
            listing_date=norm.normalize_listing_date(get("listing date", "date listed")),
            days_on_market=norm.normalize_int_count(get("days on market")),
            listing_source=get("listing source", "source") or "CSV Upload",
            listing_url=norm.normalize_url(get("listing url", "url")),
            agent_name=get("agent name", "agent"),
            contact_number=norm.normalize_phone(get("contact number", "phone")),
            email=norm.normalize_email(get("email")),
            notes=get("notes"),
            raw=raw_record,
        )

    @staticmethod
    def _normalize_listing_type(raw) -> str | None:
        if not raw:
            return None
        val = str(raw).strip().lower()
        if val in ("sale", "for sale", "s"):
            return "sale"
        if val in ("rent", "to let", "for rent", "r"):
            return "rent"
        return val
