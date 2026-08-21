"""
Verification-driven test (added during Phase 2 verification): confirms a
Lead can actually be linked to both a Property (listing) and a Contact —
the exact relationship the verification spec calls out. Prior to this fix,
Contact had no creation path, so this path was untestable.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.contact import Contact
from app.models.lead import Lead


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_lead_links_to_both_property_and_contact(db):
    prop = Property(address="1 Test St", suburb="Testville")
    contact = Contact(name="Jane Agent", phone="+27821234567", email="jane@example.com")
    db.add_all([prop, contact])
    db.commit()
    db.refresh(prop)
    db.refresh(contact)

    lead = Lead(property_id=prop.id, contact_id=contact.id, priority="high")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    fetched = db.query(Lead).filter(Lead.id == lead.id).first()
    assert fetched.property_id == prop.id
    assert fetched.contact_id == contact.id

    linked_property = db.query(Property).filter(Property.id == fetched.property_id).first()
    linked_contact = db.query(Contact).filter(Contact.id == fetched.contact_id).first()
    assert linked_property.address == "1 Test St"
    assert linked_contact.email == "jane@example.com"


def test_lead_can_exist_without_a_contact(db):
    prop = Property(address="2 Test St", suburb="Testville")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    assert lead.contact_id is None
