"""
Attachment endpoints (Sprint 23). Upload/list/download/delete, all
authenticated. No route ever returns a public URL — downloads stream
through this endpoint only.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.attachment import Attachment, ATTACHMENT_ENTITY_TYPES
from app.models.user import User
from app.schemas.attachment import AttachmentOut
from app.services.file_storage import save_file, read_file, delete_file

router = APIRouter()

_ENTITY_MODEL_MAP = None


def _get_entity_model_map():
    global _ENTITY_MODEL_MAP
    if _ENTITY_MODEL_MAP is None:
        from app.models.property import Property
        from app.models.contact import Contact
        from app.models.lead import Lead
        _ENTITY_MODEL_MAP = {"listing": Property, "contact": Contact, "lead": Lead}
    return _ENTITY_MODEL_MAP


@router.post("/", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    entity_type: str,
    entity_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if entity_type not in ATTACHMENT_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"entity_type must be one of {sorted(ATTACHMENT_ENTITY_TYPES)}")

    model = _get_entity_model_map().get(entity_type)
    if model is not None and not db.query(model).filter(model.id == entity_id).first():
        raise HTTPException(status_code=404, detail=f"No {entity_type} found with that id")

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB upload limit",
        )

    storage_path = save_file(file_bytes, file.filename or "upload")
    attachment = Attachment(
        entity_type=entity_type, entity_id=entity_id,
        original_filename=file.filename or "upload",
        storage_path=storage_path, content_type=file.content_type,
        size_bytes=len(file_bytes), uploaded_by=user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/", response_model=list[AttachmentOut])
def list_attachments(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    return (
        db.query(Attachment)
        .filter(Attachment.entity_type == entity_type, Attachment.entity_id == entity_id)
        .order_by(Attachment.created_at.desc())
        .all()
    )


@router.get("/{attachment_id}/download")
def download_attachment(attachment_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_bytes = read_file(attachment.storage_path)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{attachment.original_filename}"'},
    )


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Only the uploader can delete this attachment")
    delete_file(attachment.storage_path)
    db.delete(attachment)
    db.commit()
