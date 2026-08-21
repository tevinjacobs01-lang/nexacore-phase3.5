"""
Scan Management endpoints (Sprint 16). Trigger a scan for a source and view
scan history.
"""
import base64
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.source import Source
from app.models.scan_job import ScanJob
from app.schemas.scan import ScanJobOut
from app.services.scan_manager import run_scan

router = APIRouter()


@router.get("/", response_model=list[ScanJobOut])
def list_scans(
    skip: int = 0,
    limit: int = 20,
    source_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(ScanJob)
    if source_id:
        query = query.filter(ScanJob.source_id == source_id)
    return query.order_by(ScanJob.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{source_id}/run", response_model=ScanJobOut)
async def trigger_scan(
    source_id: uuid.UUID,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Runs a scan for the given source. For file-based collectors
    (e.g. csv_upload), attach the file as multipart form data."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if file is not None:
        import json
        file_bytes = await file.read()
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB upload limit",
            )
        config = json.loads(source.config) if source.config else {}
        config["file_bytes_b64"] = base64.b64encode(file_bytes).decode()
        config["filename"] = file.filename
        source.config = json.dumps(config)
        db.commit()

    return run_scan(db, source)
