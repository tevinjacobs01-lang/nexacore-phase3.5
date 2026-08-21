"""
Source Management endpoints (Sprint 18). Admin-only: enable/disable connectors.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.source import Source
from app.schemas.source import SourceOut, SourceUpdate

router = APIRouter()


@router.get("/", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Source).order_by(Source.name).all()


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: uuid.UUID,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source
