"""
Unit tests for the duplicate-detection engine. No DB needed — operates on
plain dicts.
"""
from app.services.dedupe import classify_duplicate, find_duplicates

BASE = {
    "listing_source": "CSV Import", "listing_url": "https://example.com/1",
    "listing_reference": "REF-1", "address": "12 Oak Street", "suburb": "Roodepoort",
    "contact_number": "+27821234567", "email": "jane@example.com",
    "asking_price": 1850000, "monthly_rental": None,
    "property_type": "House", "bedrooms": 3, "bathrooms": 2,
}


def test_exact_match_by_source_and_url():
    candidate = dict(BASE, listing_reference="DIFFERENT")
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "exact"


def test_exact_match_by_source_and_reference():
    candidate = dict(BASE, listing_url="https://example.com/DIFFERENT")
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "exact"


def test_likely_match_same_address_and_contact():
    candidate = dict(BASE, listing_source="Feed B", listing_url="https://other.com/x", listing_reference="X")
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "likely"


def test_possible_match_same_address_only():
    candidate = dict(
        BASE, listing_source="Feed B", listing_url="https://other.com/x", listing_reference="X",
        contact_number="+27000000000", email="other@example.com", asking_price=999999,
    )
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "possible"


def test_possible_match_same_contact_different_address():
    candidate = dict(
        BASE, address="99 Different Rd", listing_source="Feed C",
        listing_url="https://x.com/y", listing_reference="ZZZ",
    )
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "possible"


def test_unique_when_nothing_matches():
    candidate = {
        "address": "1 Nowhere St", "suburb": "Faraway", "contact_number": "+27111111111",
        "email": "nobody@nowhere.com", "asking_price": 1, "property_type": "Vacant Land",
        "bedrooms": None, "bathrooms": None, "listing_source": "X",
        "listing_url": "", "listing_reference": "",
    }
    result = classify_duplicate(candidate, BASE)
    assert result.match_type == "unique"


def test_find_duplicates_excludes_unique():
    pool = [
        BASE,
        {"address": "99 Nowhere", "suburb": "Elsewhere", "listing_source": "Y",
         "listing_url": "", "listing_reference": "", "contact_number": "", "email": ""},
    ]
    candidate = dict(BASE, listing_reference="DIFFERENT")
    matches = find_duplicates(candidate, pool)
    assert len(matches) == 1
    assert matches[0][1].match_type == "exact"
