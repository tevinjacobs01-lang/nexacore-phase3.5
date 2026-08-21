"""
Notes endpoints (Sprint 23) — attachable to listings, contacts, leads, or
deals via (entity_type, entity_id). Private notes are only ever returned to
their author (see get_notes below); nothing exposes them more broadly.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.note import Note, NOTE_ENTITY_TYPES
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut

router = APIRouter()

_ENTITY_MODEL_MAP = None  # populated lazily to avoid import-order issues


def _get_entity_model_map():
    global _ENTITY_MODEL_MAP
    if _ENTITY_MODEL_MAP is None:
        from app.models.property import Property
        from app.models.contact import Contact
        from app.models.lead import Lead
        _ENTITY_MODEL_MAP = {"listing": Property, "contact": Contact, "lead": Lead}
    return _ENTITY_MODEL_MAP


@router.post("/", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.entity_type not in NOTE_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"entity_type must be one of {sorted(NOTE_ENTITY_TYPES)}")

    model = _get_entity_model_map().get(payload.entity_type)
    if model is not None and not db.query(model).filter(model.id == payload.entity_id).first():
        raise HTTPException(status_code=404, detail=f"No {payload.entity_type} found with that id")

    note = Note(**payload.model_dump(), author_id=user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/", response_model=list[NoteOut])
def get_notes(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Private notes are filtered to their author only — never exposed to
    other users, including other agents viewing the same entity."""
    query = db.query(Note).filter(Note.entity_type == entity_type, Note.entity_id == entity_id)
    from sqlalchemy import or_
    query = query.filter(or_(Note.is_private.is_(False), Note.author_id == user.id))
    return query.order_by(Note.created_at.desc()).all()


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can delete this note")
    db.delete(note)
    db.commit()
