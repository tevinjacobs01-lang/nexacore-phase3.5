"""
CSV/Excel import endpoints.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.import_log import ImportLog
from app.models.user import User
from app.services.importer import import_file

router = APIRouter()


@router.post("/upload")
async def upload_import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB upload limit",
        )
    log = import_file(file_bytes, file.filename, db, user_id=user.id)

    return {
        "import_log_id": log.id,
        "filename": log.filename,
        "rows_processed": log.rows_processed,
        "rows_created": log.rows_created,
        "rows_updated": log.rows_updated,
        "rows_skipped": log.rows_skipped,
        "errors": log.errors.split("\n") if log.errors else [],
    }


@router.get("/")
def list_import_logs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    logs = (
        db.query(ImportLog)
        .order_by(ImportLog.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "filename": l.filename,
            "source_type": l.source_type,
            "rows_processed": l.rows_processed,
            "rows_created": l.rows_created,
            "rows_updated": l.rows_updated,
            "rows_skipped": l.rows_skipped,
            "started_at": l.started_at,
            "finished_at": l.finished_at,
        }
        for l in logs
    ]


@router.get("/{import_log_id}")
def get_import_log(
    import_log_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    log = db.query(ImportLog).filter(ImportLog.id == import_log_id).first()
    if not log:
        return {"detail": "Import log not found"}
    return {
        "id": log.id,
        "filename": log.filename,
        "rows_processed": log.rows_processed,
        "rows_created": log.rows_created,
        "rows_updated": log.rows_updated,
        "rows_skipped": log.rows_skipped,
        "errors": log.errors.split("\n") if log.errors else [],
        "started_at": log.started_at,
        "finished_at": log.finished_at,
    }
