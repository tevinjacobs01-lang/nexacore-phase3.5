"""Safe, source-agnostic property research for the existing Copilot."""
from __future__ import annotations

import json
import ipaddress
import re
from datetime import datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.models.capture import Capture
from app.models.contact import Contact
from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.interaction import Interaction
from app.models.lead import Lead
from app.models.lead_stage_history import LeadStageHistory
from app.models.listing_history import ListingHistory
from app.models.listing_observation import ListingObservation
from app.models.property import Property
from app.models.property_research import PropertyResearch
from app.services import ai_assistant

_ACTIONS = {"research_property", "research_listing", "owner_or_agent", "missing_information", "check_price", "full_intelligence"}
_USER_AGENT = "NexaCorePropertyResearch/1.0 (+permitted-public-retrieval)"


def _value(value):
    return float(value) if hasattr(value, "as_tuple") else value


def _public_url(url: str | None) -> bool:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    if parsed.hostname.lower() == "localhost":
        return False
    try:
        return not ipaddress.ip_address(parsed.hostname).is_private
    except ValueError:
        return True


def retrieve_public_source(url: str | None) -> tuple[str, str | None, str | None]:
    """Retrieve a small public HTML document only when robots permits it.

    This deliberately does not authenticate, solve challenges, render JavaScript,
    or retry around access controls.
    """
    if not _public_url(url):
        return "invalid_url", None, "Original source could not be accessed for verification."
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        # Keep TLS verification on for the robots request as well.  The
        # stdlib RobotFileParser hides transport causes, which made a TLS
        # failure indistinguishable from an unavailable robots policy.
        with httpx.Client(timeout=8.0, follow_redirects=False, headers={"User-Agent": _USER_AGENT}) as client:
            robots_response = client.get(robots_url)
        if robots_response.status_code in {401, 403}:
            return "robots_disallowed", None, "Original source could not be accessed for verification."
        if robots_response.status_code == 404:
            robots = None
        elif robots_response.status_code != 200:
            return "robots_unavailable", None, "Original source could not be accessed for verification."
        else:
            robots = RobotFileParser()
            robots.parse(robots_response.text.splitlines())
        if robots is not None and not robots.can_fetch(_USER_AGENT, url):
            return "robots_disallowed", None, "Original source could not be accessed for verification."
    except httpx.TimeoutException:
        return "timeout", None, "Original source could not be accessed for verification."
    except httpx.ConnectError as exc:
        if "certificate verify failed" in str(exc).lower():
            return "tls_verification_failed", None, "The original source could not be verified securely in this environment."
        return "robots_unavailable", None, "Original source could not be accessed for verification."
    except httpx.HTTPError:
        # Be conservative: a source whose rules cannot be checked is not fetched.
        return "robots_unavailable", None, "Original source could not be accessed for verification."

    try:
        with httpx.Client(timeout=8.0, follow_redirects=False, headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}) as client:
            response = client.get(url)
        if response.status_code != 200:
            return f"http_{response.status_code}", None, "Original source could not be accessed for verification."
        content_type = response.headers.get("content-type", "")
        body = response.text[:120_000]
        lower = body.lower()
        if "text/html" not in content_type or any(token in lower for token in ("captcha", "access denied", "sign in to continue", "login required", "enable javascript to continue")):
            return "blocked_or_interactive", None, "Original source could not be accessed for verification."
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()[:20_000]
        return "accessed", text, None
    except httpx.TimeoutException:
        return "timeout", None, "Original source could not be accessed for verification."
    except httpx.ConnectError as exc:
        # Keep certificate verification enabled. A trust-store problem must
        # never be worked around by accepting an unverified listing.
        if "certificate verify failed" in str(exc).lower():
            return "tls_verification_failed", None, "The original source could not be verified securely in this environment."
        return "unavailable", None, "Original source could not be accessed for verification."
    except httpx.HTTPError:
        return "unavailable", None, "Original source could not be accessed for verification."


def build_context(db, property_record: Property, lead: Lead | None) -> tuple[dict, str | None]:
    observations = db.query(ListingObservation).filter(ListingObservation.property_id == property_record.id).order_by(ListingObservation.observed_at.desc()).limit(10).all()
    captures = db.query(Capture).filter(Capture.property_id == property_record.id).order_by(Capture.created_at.desc()).limit(5).all()
    history = db.query(ListingHistory).filter(ListingHistory.property_id == property_record.id).order_by(ListingHistory.changed_at.desc()).limit(10).all()
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.property_id == property_record.id).order_by(DiscoveryOpportunity.created_at.desc()).first()
    research_history = db.query(PropertyResearch).filter(PropertyResearch.property_id == property_record.id).order_by(PropertyResearch.created_at.desc()).limit(8).all()
    contact = db.query(Contact).filter(Contact.id == lead.contact_id).first() if lead and lead.contact_id else None
    interactions = db.query(Interaction).filter(Interaction.lead_id == lead.id).order_by(Interaction.occurred_at.desc()).limit(10).all() if lead else []
    stages = db.query(LeadStageHistory).filter(LeadStageHistory.lead_id == lead.id).order_by(LeadStageHistory.changed_at.desc()).limit(10).all() if lead else []
    original_url = property_record.listing_url or next((item.canonical_url for item in observations if item.canonical_url), None)
    property_data = {key: _value(getattr(property_record, key)) for key in (
        "address", "suburb", "city", "province", "listing_type", "property_type", "bedrooms", "bathrooms", "garages",
        "floor_size_sqm", "stand_size_sqm", "asking_price", "monthly_rental", "listing_status", "listing_reference",
        "listing_source", "agent_name", "contact_number", "email", "seller_type", "is_owner_listed", "lead_score",
    )}
    context = {
        "nexacore_record": {
            "property": property_data,
            "lead": {"status": lead.status, "priority": lead.priority, "score": lead.lead_score, "source": lead.source, "notes": lead.notes} if lead else None,
            "contact": {"name": contact.name, "phone": contact.phone, "email": contact.email, "type": contact.contact_type, "source": contact.source, "notes": contact.notes} if contact else None,
        },
        "original_listing": {"url": original_url, "observations": [{"url": x.canonical_url, "contact_name": x.contact_name, "agency": x.contact_agency, "company": x.contact_company, "phone": x.contact_phone, "email": x.contact_email, "status": x.lifecycle_status, "observed_at": x.observed_at} for x in observations]},
        "capture_evidence": [{"extracted_data": x.extracted_data, "created_at": x.created_at, "notes": x.extraction_notes} for x in captures],
        "price_history": [{"previous_price": _value(x.previous_price), "new_price": _value(x.new_price), "changed_at": x.changed_at} for x in history],
        "discovery_opportunity": {
            "classification": opportunity.classification,
            "qualification_status": opportunity.qualification_status,
            "opportunity_score": opportunity.opportunity_score,
            "recommended_action": opportunity.recommended_action,
        } if opportunity else None,
        "crm_history": {
            "interactions": [{"type": item.interaction_type, "direction": item.direction, "outcome": item.outcome, "notes": item.notes, "occurred_at": item.occurred_at} for item in interactions],
            "stage_history": [{"from": item.from_stage, "to": item.to_stage, "changed_at": item.changed_at} for item in stages],
        },
        "previous_research": [{"action": item.action, "source_status": item.source_status, "researched_at": item.created_at, "result": item.result[:2500]} for item in research_history],
    }
    return context, original_url


def run_research(db, property_record: Property, lead: Lead | None, action: str) -> tuple[str, dict, str, str | None]:
    if action not in _ACTIONS:
        raise ValueError("Unsupported property research action")
    context, url = build_context(db, property_record, lead)
    status, source_text, access_error = retrieve_public_source(url)
    evidence = {"nexacore_record": context["nexacore_record"], "original_listing": context["original_listing"], "capture_evidence": context["capture_evidence"], "source_status": status}
    if source_text:
        evidence["retrieved_source"] = {"url": url, "source_type": "original_listing", "snippet": source_text[:3000], "retrieved_at": datetime.utcnow().isoformat()}
        context["retrieved_source"] = evidence["retrieved_source"]
    instructions = {
        "research_property": "Use headings: Property, Source, Intelligence, Recommended next action. Produce a concise practical report.",
        "research_listing": "Use headings: Newly discovered from original listing, Already known, Unable to verify, Conflicts. Identify only information newly discovered from the original listing.",
        "owner_or_agent": "Start with 'Likely agent' or 'Likely owner/direct', include a percentage and confidence, then Evidence bullets. Never state ownership as fact unless source explicitly proves it.",
        "missing_information": "Use headings: Already known, Newly discovered, Missing, Unable to verify, Conflicting information. Base every item on supplied evidence.",
        "check_price": "Start with 'Price changed: Yes/No/Unknown'. Compare current, capture/observation/history, prior research and retrieved prices. Show dated values and difference only when evidence supports it; otherwise state historical evidence is insufficient.",
        "full_intelligence": "Use exactly these concise headings: Property, Source, Advertiser, Contact, Intelligence, Missing information, Recommended next action.",
    }[action]
    prompt = (
        "You are NexaCore's property research Copilot. " + instructions +
        " Use only the supplied evidence. Mark each statement as [NexaCore record], [Original listing], or [AI inference]. "
        "Do not invent missing values. Do not recommend automatic database changes. "
        + ("External listing unavailable. Analyse existing NexaCore and Capture evidence instead. " if access_error else "") +
        "\n\nEvidence:\n" + json.dumps(context, default=str)
    )
    answer = ai_assistant.answer_question(prompt, [property_record])
    if access_error:
        answer = f"{access_error}\nExternal listing unavailable. I analysed the existing Capture, Property and Discovery records instead.\n\n{answer}"
    return answer, evidence, status, url
