"""Source detection for user-supplied public property URLs.

Detection is provenance only.  It never changes retrieval permissions or
pretends a portal-specific integration exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PropertySource:
    key: str
    label: str
    domain: str
    adapter: str = "generic_public_html"


_KNOWN_PORTALS = {
    "property24": ("property24.co.za", "www.property24.com", "property24.com"),
    "private_property": ("privateproperty.co.za", "www.privateproperty.co.za"),
    "myproperty": ("myproperty.co.za", "www.myproperty.co.za"),
    "gumtree_property": ("gumtree.co.za", "www.gumtree.co.za"),
}


def detect_property_source(url: str | None) -> PropertySource:
    """Classify a public URL without making a network request."""
    domain = (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    for key, domains in _KNOWN_PORTALS.items():
        if domain in {item.removeprefix("www.") for item in domains}:
            return PropertySource(key=key, label=key.replace("_", " "), domain=domain)
    # Agency and independent listing sites intentionally use the generic
    # adapter.  A host is retained so reviewers can see exactly where facts
    # originated, without maintaining brittle per-agency scrapers.
    return PropertySource(
        key="agency_or_public_property_site",
        label="agency or public property site",
        domain=domain,
    )
