"""
Live API smoke test (Phase 3.5, Tasks 5 + 11).

Exercises the COMPLETE Phase 3 workflow through real HTTP calls against a
running server — not internal function calls. This script has NEVER been
executed (this sandbox cannot run a live FastAPI server or make outbound
HTTP calls to it — see docs/SETUP.md). Written and reviewed for
correctness only.

Run it locally once the backend is up:
    cd backend
    uvicorn app.main:app --reload &
    python scripts/smoke_test_api.py

Requires `httpx` (already in requirements.txt).

Covers, in order:
  Authentication -> Contact -> Listing -> Lead -> Pipeline movement ->
  Stage history -> Interaction -> Note -> Task -> Follow-up -> Appointment
  -> Template render -> Assignment -> CRM dashboard

Exits non-zero on the first failed assertion, printing exactly which step
and what was expected vs received.
"""
import sys
import httpx

BASE_URL = "http://localhost:8000/api/v1"
client = httpx.Client(base_url=BASE_URL, timeout=10.0)

results = []


def step(name):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            try:
                out = fn(*args, **kwargs)
                results.append((name, "PASS"))
                print(f"PASS: {name}")
                return out
            except AssertionError as e:
                results.append((name, f"FAIL: {e}"))
                print(f"FAIL: {name} — {e}")
                sys.exit(1)
            except httpx.ConnectError:
                print(f"ERROR: {name} — could not connect to {BASE_URL}. Is the server running?")
                sys.exit(2)
        return wrapper
    return decorator


@step("1. Register + login (authentication)")
def auth():
    email = "smoketest@example.com"
    password = "smoketestpass123"
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Smoke Test"})
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login expected 200, got {r.status_code}: {r.text}"
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    # Unauthenticated request must be rejected
    unauth_client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    r2 = unauth_client.get("/properties/")
    assert r2.status_code == 401, f"unauthenticated request expected 401, got {r2.status_code}"
    return token


@step("2. Create contact")
def create_contact():
    r = client.post("/contacts/", json={
        "name": "Smoke Test Seller", "phone": "+27821112222", "email": "seller@example.com",
        "contact_type": "seller", "force_create": True,
    })
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"
    contact = r.json()
    assert contact["name"] == "Smoke Test Seller"
    return contact["id"]


@step("3. Create listing (property)")
def create_listing():
    r = client.post("/properties/", json={
        "address": "1 Smoke Test Ave", "suburb": "Testville", "asking_price": 1000000,
        "listing_type": "sale", "property_type": "House",
    })
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"
    return r.json()["id"]


@step("4. Create lead")
def create_lead(property_id, contact_id):
    r = client.post("/leads/", json={"property_id": property_id, "contact_id": contact_id, "priority": "high"})
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"
    lead = r.json()
    assert lead["status"] == "new"
    return lead["id"]


@step("5. Move lead through pipeline (invalid stage rejected, valid stage accepted)")
def move_pipeline(lead_id):
    bad = client.patch(f"/leads/{lead_id}", json={"status": "not_a_real_stage"})
    assert bad.status_code == 400, f"invalid stage expected 400, got {bad.status_code}"

    good = client.patch(f"/leads/{lead_id}", json={"status": "contacted"})
    assert good.status_code == 200, f"expected 200, got {good.status_code}: {good.text}"
    assert good.json()["status"] == "contacted"


@step("6. Verify stage history recorded")
def check_stage_history(lead_id):
    r = client.get(f"/leads/{lead_id}/stage-history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) >= 2, f"expected at least 2 stage-history entries, got {len(history)}"


@step("7. Log interaction")
def log_interaction(lead_id, contact_id):
    r = client.post("/interactions/", json={
        "lead_id": lead_id, "contact_id": contact_id,
        "interaction_type": "call", "direction": "outgoing", "outcome": "spoke, interested",
    })
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"

    # Invalid entity id should 404, not 500
    bad = client.post("/interactions/", json={
        "lead_id": "00000000-0000-0000-0000-000000000000",
        "interaction_type": "call", "direction": "outgoing",
    })
    assert bad.status_code == 404, f"invalid lead_id expected 404, got {bad.status_code}"


@step("8. Add note (and verify private notes stay private)")
def add_note(lead_id):
    r = client.post("/notes/", json={"entity_type": "lead", "entity_id": lead_id, "content": "Public note", "is_private": False})
    assert r.status_code == 201

    r2 = client.post("/notes/", json={"entity_type": "lead", "entity_id": lead_id, "content": "Private note", "is_private": True})
    assert r2.status_code == 201

    # A second, different user should see the public note but not the private one
    email2, password2 = "smoketest2@example.com", "smoketestpass456"
    client.post("/auth/register", json={"email": email2, "password": password2})
    login2 = client.post("/auth/login", json={"email": email2, "password": password2})
    token2 = login2.json()["access_token"]
    client2 = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {token2}"}, timeout=10.0)

    notes = client2.get("/notes/", params={"entity_type": "lead", "entity_id": lead_id}).json()
    contents = [n["content"] for n in notes]
    assert "Public note" in contents, "second user should see the public note"
    assert "Private note" not in contents, "second user should NOT see the first user's private note"


@step("9. Create task")
def create_task(lead_id):
    r = client.post("/tasks/", json={"title": "Smoke test task", "lead_id": lead_id, "priority": "medium"})
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"


@step("10. Create follow-up")
def create_follow_up(lead_id):
    r = client.post("/follow-ups/", json={
        "lead_id": lead_id, "follow_up_type": "call", "due_at": "2027-01-01T10:00:00Z",
    })
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"


@step("11. Create appointment")
def create_appointment(lead_id):
    r = client.post("/appointments/", json={
        "lead_id": lead_id, "starts_at": "2027-01-02T14:00:00Z", "appointment_type": "viewing",
    })
    assert r.status_code == 201, f"expected 201, got {r.status_code}: {r.text}"

    valid_transitions = ["confirmed", "completed"]
    appt_id = r.json()["id"]
    for status in valid_transitions:
        upd = client.patch(f"/appointments/{appt_id}", json={"status": status})
        assert upd.status_code == 200, f"status transition to {status} expected 200, got {upd.status_code}"


@step("12. Render communication template")
def render_template(lead_id):
    tmpl = client.post("/templates/", json={
        "name": "Smoke Test Template", "template_type": "follow_up",
        "body": "Hi {{contact_name}}, following up on {{property_address}}.",
    })
    assert tmpl.status_code == 201, f"expected 201, got {tmpl.status_code}: {tmpl.text}"
    template_id = tmpl.json()["id"]

    rendered = client.post(f"/templates/{template_id}/render", json={"lead_id": lead_id})
    assert rendered.status_code == 200
    body = rendered.json()["body"]
    assert "{{contact_name}}" not in body or "Smoke Test Seller" in body, "template should render contact_name"


@step("13. Assign lead")
def assign_lead(lead_id, agent_user_id):
    r = client.post(f"/leads/{lead_id}/assign", json={"agent_id": agent_user_id})
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    assert r.json()["assigned_agent_id"] == agent_user_id


@step("14. CRM dashboard reflects the workflow")
def check_dashboard():
    r = client.get("/dashboard/crm")
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["lead_metrics"]["total_leads"] >= 1
    assert "conversion_metrics" in data
    assert "agent_metrics" in data


@step("15. Attachment download requires authentication")
def check_attachment_auth():
    unauth_client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    r = unauth_client.get("/attachments/00000000-0000-0000-0000-000000000000/download")
    assert r.status_code == 401, f"unauthenticated download expected 401, got {r.status_code}"


def main():
    auth()
    contact_id = create_contact()
    property_id = create_listing()
    lead_id = create_lead(property_id, contact_id)
    move_pipeline(lead_id)
    check_stage_history(lead_id)
    log_interaction(lead_id, contact_id)
    add_note(lead_id)
    create_task(lead_id)
    create_follow_up(lead_id)
    create_appointment(lead_id)
    render_template(lead_id)
    # Note: assign_lead needs a real user id — left commented since this
    # script doesn't have a way to fetch "my own user id" via the current
    # API (no GET /auth/me endpoint exists). Add one, or pass a known
    # agent's id, before running this step for real.
    # assign_lead(lead_id, agent_user_id="<uuid-of-an-existing-user>")
    check_dashboard()
    check_attachment_auth()

    print(f"\n{len(results)}/{len(results)} steps passed (script completed without early exit)")


if __name__ == "__main__":
    main()
