"""
Pure-function unit tests for the normalization service. No DB needed.
"""
from app.services.normalization import (
    normalize_price, normalize_phone, normalize_email, normalize_suburb,
    normalize_province, normalize_property_type, normalize_int_count,
    normalize_listing_date, normalize_url, validate_listing,
)


def test_normalize_price_handles_currency_formatting():
    assert normalize_price("R 1 250 000") == 1250000.0
    assert normalize_price("R1,250,000.00") == 1250000.0
    assert normalize_price(1250000) == 1250000.0
    assert normalize_price("") is None
    assert normalize_price(None) is None


def test_normalize_phone_adds_country_code():
    assert normalize_phone("082 123 4567") == "+27821234567"
    assert normalize_phone("+27821234567") == "+27821234567"
    assert normalize_phone(None) is None


def test_normalize_email_lowercases_and_validates():
    assert normalize_email("Jane@Example.COM") == "jane@example.com"
    assert normalize_email("not-an-email") is None


def test_normalize_place_names_titlecase():
    assert normalize_suburb("roodepoort") == "Roodepoort"
    assert normalize_province("gp") == "Gauteng"


def test_normalize_property_type_synonyms():
    assert normalize_property_type("flat") == "Apartment"
    assert normalize_property_type("townhouse") == "Townhouse"


def test_normalize_int_count_handles_studio():
    assert normalize_int_count("3.0") == 3
    assert normalize_int_count("studio") == 0
    assert normalize_int_count("garbage") is None


def test_normalize_url_adds_scheme():
    assert normalize_url("example.com/listing/1") == "https://example.com/listing/1"
    assert normalize_url(None) is None


def test_validate_listing_flags_missing_key_fields():
    problems = validate_listing({"asking_price": -5})
    assert "missing both address and listing_reference" in problems
    assert "asking_price is negative" in problems


def test_validate_listing_passes_clean_data():
    assert validate_listing({"address": "1 Main St", "asking_price": 100000, "listing_type": "sale"}) == []
