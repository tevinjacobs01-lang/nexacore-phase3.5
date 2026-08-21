"""
Report endpoints: JSON view of each report, plus a shared export endpoint
for CSV/Excel/PDF.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.reports import REPORTS
from app.services.exporters import to_csv_bytes, to_excel_bytes, to_pdf_bytes, CONTENT_TYPES

router = APIRouter()


@router.get("/{report_type}")
def get_report(report_type: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    builder = REPORTS.get(report_type)
    if not builder:
        raise HTTPException(status_code=404, detail=f"Unknown report_type. Options: {list(REPORTS)}")
    df = builder(db)
    return df.to_dict(orient="records")


@router.get("/{report_type}/export")
def export_report(
    report_type: str,
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    builder = REPORTS.get(report_type)
    if not builder:
        raise HTTPException(status_code=404, detail=f"Unknown report_type. Options: {list(REPORTS)}")
    df = builder(db)

    if format == "csv":
        content = to_csv_bytes(df)
    elif format == "xlsx":
        content = to_excel_bytes(df)
    else:
        content = to_pdf_bytes(df, title=report_type.replace("-", " ").title())

    filename = f"{report_type}.{format}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=CONTENT_TYPES[format],
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
