import uuid
from typing import List, Union, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UploadBatch
from app.ingestion.parser import parse_json_content
from app.pipeline import pipeline_processor
from app.core.logging import logger

router = APIRouter(prefix="/api/emails", tags=["Emails"])


class EmailPayload(BaseModel):
    sender_name: Union[str, None] = None
    sender_email: str = Field(description="Sender email address")
    subject: Union[str, None] = None
    body: str = Field(description="Plain text or HTML email body")
    signature: Union[str, None] = None
    evidence_sources: List[str] = Field(default_factory=lambda: ["body"])


@router.post("/ingest")
async def ingest_json_email(
    payload: Union[EmailPayload, List[EmailPayload]],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Accepts authorized JSON email data (single email or list of emails) for ingestion.
    """
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise HTTPException(status_code=400, detail="Empty email payload.")

    batch_id = str(uuid.uuid4())
    batch = UploadBatch(
        id=batch_id,
        filename=f"API Ingest ({len(items)} items)",
        total_emails=len(items),
        processed_count=0,
        failed_count=0,
        status="pending"
    )
    db.add(batch)
    db.commit()

    raw_json_data = [item.model_dump() for item in items]
    parsed_list = parse_json_content(raw_json_data, filename="api_ingest.json")

    # Process items synchronously or asynchronously
    processed = 0
    failed = 0
    lead_results = []
    for p in parsed_list:
        try:
            res = pipeline_processor.process_email_item(p, batch_id=batch_id, db=db)
            processed += 1
            lead_results.append({
                "company_id": res.company.id,
                "company_name": res.company.name,
                "sector": res.company.sector_id,
                "confidence": res.company.confidence,
                "status": res.company.status,
                "is_duplicate": res.is_duplicate
            })
        except Exception as e:
            logger.error(f"Error processing JSON email: {e}")
            failed += 1

    batch.processed_count = processed
    batch.failed_count = failed
    batch.status = "completed" if failed == 0 else "completed_with_errors"
    db.commit()

    return {
        "batch_id": batch_id,
        "total": len(items),
        "processed": processed,
        "failed": failed,
        "results": lead_results
    }
