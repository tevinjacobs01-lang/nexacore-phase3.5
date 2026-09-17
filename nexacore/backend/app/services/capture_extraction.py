"""Field-aware image extraction for Capture Listing, with human review required."""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass

from app.core.config import settings
from app.services import normalization as norm


@dataclass(frozen=True)
class ExtractionResult:
    data: dict
    field_confidence: dict[str, str]
    candidates: dict[str, list[str]]
    raw_text: str | None
    method: str
    notes: list[str]


def _add(data: dict, confidence: dict, candidates: dict, field: str, value, level: str = "high"):
    if value not in (None, ""):
        data[field] = value
        confidence[field] = level
        candidates.setdefault(field, [str(value)])


def extract_visible_text(text: str | None) -> tuple[dict, list[str]]:
    result = structure_listing_text(text or "")
    return result.data, result.notes


def structure_listing_text(text: str) -> ExtractionResult:
    """Parse only values explicitly present in OCR or supplied listing text."""
    data: dict = {}
    confidence: dict[str, str] = {}
    candidates: dict[str, list[str]] = {}
    notes: list[str] = []
    if not text.strip():
        return ExtractionResult(data, confidence, candidates, None, "unavailable", ["No image text was detected. Review the listing manually."])
    lower = text.lower()
    if re.search(r"\b(for rent|to let|rental|rent)\b", lower):
        _add(data, confidence, candidates, "listing_type", "rent")
    elif re.search(r"\b(for sale|sale)\b", lower):
        _add(data, confidence, candidates, "listing_type", "sale")
    for field, pattern in (("bedrooms", r"(\d+)\s*(?:bed(?:room)?s?|beds?)"), ("bathrooms", r"(\d+)\s*(?:bath(?:room)?s?|baths?)"), ("garages", r"(\d+)\s*(?:garage|parking|parkings?)")):
        match = re.search(pattern, lower)
        if match: _add(data, confidence, candidates, field, int(match.group(1)))
    price = re.search(r"(?:r|zar|price)[ \t]*([\d][\d ,.]*\d|\d)", lower)
    if price:
        parsed = norm.normalize_price(price.group(1))
        if parsed is not None: _add(data, confidence, candidates, "monthly_rental" if data.get("listing_type") == "rent" else "asking_price", parsed)
    for field, pattern in (("floor_size_sqm", r"(\d+(?:[.,]\d+)?)\s*(?:m²|sqm|sq\s*m)"), ("stand_size_sqm", r"(?:stand|land|erf)\s*(\d+(?:[.,]\d+)?)\s*(?:m²|sqm|sq\s*m)")):
        match = re.search(pattern, lower)
        if match: _add(data, confidence, candidates, field, float(match.group(1).replace(",", ".")), "medium")
    owner = re.search(r"(owner selling|private seller|selling privately|direct from owner|no agents|private landlord)", lower)
    agency = re.search(r"\b(estate agent|property agent|rental agent|property manager|estate agency|realty|properties)\b", lower)
    if owner:
        _add(data, confidence, candidates, "owner_evidence", owner.group(1), "medium")
    if agency:
        seller_type = "agent" if "agent" in agency.group(1) or "manager" in agency.group(1) else "agency"
        _add(data, confidence, candidates, "seller_type", seller_type, "medium")
        _add(data, confidence, candidates, "is_owner_listed", False, "medium")
    elif owner:
        _add(data, confidence, candidates, "seller_type", "owner", "medium")
        _add(data, confidence, candidates, "is_owner_listed", True, "medium")
    for property_type in ("apartment", "townhouse", "house", "flat", "duplex", "plot", "vacant land", "commercial"):
        if re.search(rf"\b{re.escape(property_type)}\b", lower):
            _add(data, confidence, candidates, "property_type", property_type, "medium"); break
    phone_matches = re.findall(r"(?:call|phone|tel|whatsapp)\s*[:.-]?\s*(\+?\d[\d\s()-]{7,})", text, re.I)
    if not phone_matches:
        phone_matches = re.findall(r"(?<![\d,])((?:\+27|0)\d[\d\s()-]{7,})(?![\d,])", text)
    phone_values = [norm.normalize_phone(value) for value in phone_matches]
    phone_values = [value for value in phone_values if value]
    if phone_values: _add(data, confidence, candidates, "contact_number", phone_values[0]); candidates["contact_number"] = phone_values
    emails = re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    if emails: _add(data, confidence, candidates, "email", norm.normalize_email(emails[0])); candidates["email"] = [norm.normalize_email(item) for item in emails]
    reference = re.search(r"(?:ref(?:erence)?|listing\s*(?:id|ref)?)\s*[:#-]?\s*([A-Za-z0-9-]{4,})", text, re.I)
    if reference: _add(data, confidence, candidates, "listing_reference", reference.group(1), "medium")
    # Browser chrome (the "https://" scheme/padlock icon) is frequently dropped by OCR,
    # leaving a bare "portal.co.za/path" address bar reading - detect that too, and only
    # add back a scheme so the link is clickable; the original host/path is never replaced.
    url = re.search(
        r"https?://\S+|www\.\S+|(?<![\w@.])(?:[a-z0-9-]+\.)+(?:co\.za|com|co\.uk|org|net|io)(?:/\S*)?",
        text,
        re.I,
    )
    if url:
        detected_url = url.group(0).rstrip(".,)")
        if not re.match(r"https?://", detected_url, re.I):
            detected_url = f"https://{detected_url}"
        _add(data, confidence, candidates, "source_url", detected_url)
    portal_methods = []
    for label, pattern in (
        ("WhatsApp Agent", r"\bwhatsapp\s+agent\b"),
        ("Call Agent", r"\bcall\s+agent\b"),
        ("Email Agent", r"\bemail\s+agent\b"),
        ("Contact Agent", r"\bcontact\s+agent\b"),
    ):
        if re.search(pattern, lower):
            portal_methods.append(label)
    if portal_methods:
        _add(data, confidence, candidates, "portal_contact_methods", portal_methods, "medium")
    address = re.search(r"\b\d{1,5}[ \t]+[A-Za-z0-9 .'-]+[ \t]+(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|crescent|close)\b", text, re.I)
    if address: _add(data, confidence, candidates, "address", address.group(0), "medium")
    if "listing_type" not in data: notes.append("Listing intent needs review.")
    if "asking_price" not in data and "monthly_rental" not in data: notes.append("Price needs review.")
    if "contact_number" not in data and "email" not in data:
        notes.append("Portal-mediated contact is available." if portal_methods else "Contact information was not detected.")
    return ExtractionResult(data, confidence, candidates, text, "text_parser", notes)


def _tesseract_text(image: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
        from io import BytesIO
        configured_path = settings.TESSERACT_CMD
        windows_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if configured_path:
            pytesseract.pytesseract.tesseract_cmd = configured_path
        elif os.path.exists(windows_default):
            pytesseract.pytesseract.tesseract_cmd = windows_default
        return pytesseract.image_to_string(Image.open(BytesIO(image)))
    except ImportError as exc:
        raise RuntimeError("Local OCR is unavailable: install pytesseract and the Tesseract binary.") from exc
    except Exception as exc:
        raise RuntimeError(f"Local OCR could not read this image: {exc}") from exc


def _vision_extract(image: bytes, content_type: str | None) -> ExtractionResult:
    if not settings.ANTHROPIC_API_KEY or not settings.CAPTURE_VISION_ENABLED:
        raise RuntimeError("Vision extraction is unavailable until CAPTURE_VISION_ENABLED and a backend Anthropic key are configured.")
    import anthropic
    prompt = "Extract only clearly visible property-listing facts. Return JSON with known CaptureData keys and null for unknown values. Never infer phone, email, address, price, advertiser, owner, or agency."
    response = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY).messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": content_type or "image/jpeg", "data": base64.b64encode(image).decode()}}, {"type": "text", "text": prompt}]}],
    )
    raw = response.content[0].text
    try:
        payload = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
    except Exception as exc:
        raise RuntimeError("Vision provider did not return structured listing data.") from exc
    result = structure_listing_text("\n".join(str(value) for value in payload.values() if value is not None))
    for field, value in payload.items():
        if value is not None and field in {"address", "suburb", "city", "province", "postal_code", "listing_type", "property_type", "asking_price", "monthly_rental", "bedrooms", "bathrooms", "garages", "contact_name", "contact_number", "email", "source_url", "portal_contact_methods", "listing_reference", "agent_name", "agency_name", "seller_type", "is_owner_listed", "floor_size_sqm", "stand_size_sqm"}:
            _add(result.data, result.field_confidence, result.candidates, field, value, "medium")
    return ExtractionResult(result.data, result.field_confidence, result.candidates, raw, "anthropic_vision", result.notes)


def extract_listing_image(image: bytes, content_type: str | None, supplied_text: str | None = None) -> ExtractionResult:
    if supplied_text and supplied_text.strip():
        result = structure_listing_text(supplied_text)
        return ExtractionResult(result.data, result.field_confidence, result.candidates, supplied_text, "supplied_text", result.notes)
    if settings.CAPTURE_OCR_PROVIDER == "anthropic_vision":
        return _vision_extract(image, content_type)
    text = _tesseract_text(image)
    result = structure_listing_text(text)
    return ExtractionResult(result.data, result.field_confidence, result.candidates, text, "tesseract_ocr", result.notes)

def extract_visible_text(text: str | None) -> tuple[dict, list[str]]:
    """Compatibility helper backed by the canonical field-aware parser."""
    result = structure_listing_text(text or "")
    return result.data, result.notes