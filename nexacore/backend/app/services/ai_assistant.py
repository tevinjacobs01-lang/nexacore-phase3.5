"""
Thin wrapper around the Anthropic API for the AI Assistant feature:
- summarizing a property
- explaining why it received its lead score
- recommending which listings to prioritize
- answering natural-language questions about the portfolio

Kept as a separate service module so the endpoint layer stays thin and this
can be swapped for a different provider later without touching routes.
"""
from __future__ import annotations

import json

import anthropic

from app.core.config import settings
from app.models.property import Property


def _client() -> anthropic.Anthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env to enable the AI assistant."
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _property_context(prop: Property) -> str:
    return json.dumps(
        {
            "address": prop.address,
            "suburb": prop.suburb,
            "city": prop.city,
            "listing_type": prop.listing_type,
            "property_type": prop.property_type,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "asking_price": float(prop.asking_price) if prop.asking_price else None,
            "monthly_rental": float(prop.monthly_rental) if prop.monthly_rental else None,
            "days_on_market": prop.days_on_market,
            "lead_score": prop.lead_score,
            "is_relisted": prop.is_relisted,
            "price_reduced": bool(prop.price_reduced_at),
            "contact_status": prop.contact_status,
            "notes": prop.notes,
        },
        default=str,
    )


def summarize_property(prop: Property) -> str:
    client = _client()
    msg = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "Summarize this property listing in 2-3 sentences for a busy real "
                "estate agent glancing at their dashboard. Be concrete and factual, "
                "no fluff.\n\n" + _property_context(prop)
            ),
        }],
    )
    return msg.content[0].text


def explain_score(prop: Property, breakdown: dict[str, int]) -> str:
    client = _client()
    msg = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "This property has a lead score of "
                f"{prop.lead_score}, made up of these rule contributions: "
                f"{json.dumps(breakdown)}. Explain in plain language, in 2-3 "
                "sentences, why this is or isn't a strong lead right now.\n\n"
                + _property_context(prop)
            ),
        }],
    )
    return msg.content[0].text


def prioritize_listings(properties: list[Property]) -> str:
    client = _client()
    context = [json.loads(_property_context(p)) | {"id": str(p.id)} for p in properties]
    msg = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                "Given these leads, recommend which to prioritize calling first "
                "today and briefly say why. Return a short ranked list (max 10), "
                "referencing address and suburb.\n\n" + json.dumps(context, default=str)
            ),
        }],
    )
    return msg.content[0].text


def answer_question(question: str, properties: list[Property]) -> str:
    client = _client()
    context = [json.loads(_property_context(p)) | {"id": str(p.id)} for p in properties]
    msg = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                "You are a real estate lead assistant. Answer the agent's question "
                "using only the property data provided below. Be concise.\n\n"
                f"Question: {question}\n\nProperty data:\n{json.dumps(context, default=str)}"
            ),
        }],
    )
    return msg.content[0].text
