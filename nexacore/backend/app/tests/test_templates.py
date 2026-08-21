"""
Template rendering tests (Sprint 29). Pure functions, no DB needed.
"""
from app.services.templates import render_template, extract_variables, build_lead_variables


def test_render_fills_all_known_variables():
    body = "Hi {{contact_name}}, re {{property_address}} in {{suburb}} at {{property_price}}. - {{agent_name}}"
    variables = build_lead_variables(
        contact_name="Jane", property_address="12 Oak St", property_price=1850000,
        agent_name="Bongani", suburb="Roodepoort", listing_url="https://x.com/1",
    )
    rendered = render_template(body, variables)
    assert "Jane" in rendered
    assert "R1,850,000" in rendered
    assert "Bongani" in rendered
    assert "{{" not in rendered


def test_render_leaves_unknown_placeholder_visible():
    rendered = render_template("Hi {{contact_name}}, re {{unknown_var}}", {"contact_name": "Jane"})
    assert "{{unknown_var}}" in rendered
    assert "Jane" in rendered


def test_render_leaves_none_value_placeholder_visible():
    rendered = render_template("Price: {{property_price}}", {"property_price": None})
    assert "{{property_price}}" in rendered


def test_extract_variables_returns_unique_ordered_list():
    body = "{{contact_name}} {{suburb}} {{contact_name}}"
    assert extract_variables(body) == ["contact_name", "suburb"]


def test_build_lead_variables_formats_price():
    variables = build_lead_variables(property_price=1250000)
    assert variables["property_price"] == "R1,250,000"


def test_build_lead_variables_handles_missing_price():
    variables = build_lead_variables(property_price=None)
    assert variables["property_price"] is None
