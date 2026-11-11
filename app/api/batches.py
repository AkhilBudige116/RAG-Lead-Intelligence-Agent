from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UploadBatch

router = APIRouter(prefix="/api/batches", tags=["Batches"])


@router.get("")
def list_batches(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Returns batch history ordered by newest first."""
    query = db.query(UploadBatch).order_by(UploadBatch.created_at.desc())
    total = query.count()
    batches = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": b.id,
                "filename": b.filename,
                "total_emails": b.total_emails,
                "processed_count": b.processed_count,
                "failed_count": b.failed_count,
                "status": b.status,
                "error_message": b.error_message,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in batches
        ]
    }


@router.get("/{batch_id}")
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Returns real-time processing status and counts for a specific batch."""
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    return {
        "id": batch.id,
        "filename": batch.filename,
        "total_emails": batch.total_emails,
        "processed_count": batch.processed_count,
        "failed_count": batch.failed_count,
        "status": batch.status,
        "error_message": batch.error_message,
        "created_at": batch.created_at.isoformat() if batch.created_at else None
    }
