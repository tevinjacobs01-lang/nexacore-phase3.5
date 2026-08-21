"""
Template rendering (Sprint 29). Pure string substitution — no sending
integration, no external calls. `{{variable}}` placeholders are replaced;
any variable not supplied is left as a visible placeholder so the agent
notices it before sending, rather than silently dropping it.
"""
from __future__ import annotations

import re

VARIABLE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_template(body: str, variables: dict[str, str | None]) -> str:
    """Replaces every {{key}} in `body` with str(variables[key]) if present
    and non-None; otherwise leaves the placeholder untouched."""

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        value = variables.get(key)
        return str(value) if value is not None else match.group(0)

    return VARIABLE_RE.sub(_replace, body)


def extract_variables(body: str) -> list[str]:
    """Returns the unique list of {{variable}} names referenced in a template body."""
    seen: list[str] = []
    for match in VARIABLE_RE.finditer(body):
        key = match.group(1)
        if key not in seen:
            seen.append(key)
    return seen


def build_lead_variables(*, contact_name=None, property_address=None, property_price=None,
                          agent_name=None, suburb=None, listing_url=None) -> dict[str, str | None]:
    """Convenience builder matching the exact variable names from the spec."""
    return {
        "contact_name": contact_name,
        "property_address": property_address,
        "property_price": f"R{property_price:,.0f}" if property_price is not None else None,
        "agent_name": agent_name,
        "suburb": suburb,
        "listing_url": listing_url,
    }
