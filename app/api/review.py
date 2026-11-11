from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Company, Classification, Sector
from app.rag.indexer import SectorKnowledgeIndexer
from app.core.logging import logger

router = APIRouter(prefix="/api/review", tags=["Review Queue"])


class ReviewActionRequest(BaseModel):
    action: str = Field(description="'accept' or 'change'")
    target_sector_id: Optional[str] = Field(default=None, description="Required if action is 'change'")
    reviewer_name: str = Field(default="Reviewer", description="Name of the human reviewer")
    notes: Optional[str] = Field(default=None, description="Reviewer reasoning")
    learn_as_example: bool = Field(default=False, description="Add to sector knowledge base examples")


@router.get("/queue")
def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns all leads flagged as 'needs_review', including AI suggested sector,
    model confidence, reasoning, and evidence snippets.
    """
    query = (
        db.query(Company)
        .filter(Company.status == "needs_review")
        .order_by(Company.created_at.desc())
    )
    total = query.count()
    offset = (page - 1) * page_size
    leads = query.offset(offset).limit(page_size).all()

    items = []
    for comp in leads:
        # Get latest classification trace
        latest_cls = (
            db.query(Classification)
            .filter(Classification.company_id == comp.id)
            .order_by(Classification.created_at.desc())
            .first()
        )
        primary_contact = comp.contacts[0] if comp.contacts else None

        items.append({
            "id": comp.id,
            "company_name": comp.name or "Unknown Company",
            "contact_name": primary_contact.name if primary_contact else "N/A",
            "email": primary_contact.email if primary_contact else "N/A",
            "website": comp.website,
            "domain": comp.domain,
            "suggested_sector_id": comp.sector_id,
            "suggested_sector_name": comp.sector.name if comp.sector else "Needs Review",
            "confidence": comp.confidence,
            "llm_confidence": latest_cls.llm_confidence if latest_cls else None,
            "top_retrieval_similarity": latest_cls.top_retrieval_similarity if latest_cls else None,
            "reason": comp.classification_reason,
            "evidence": latest_cls.evidence if latest_cls else [],
            "created_at": comp.created_at.isoformat() if comp.created_at else None
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.post("/{lead_id}/action")
def process_review_action(
    lead_id: int,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db)
):
    """
    Processes human review decision: accepts AI suggestion or overrides with corrected sector.
    """
    comp = db.query(Company).filter(Company.id == lead_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Lead not found.")

    if payload.action == "accept":
        if not comp.sector_id:
            raise HTTPException(status_code=400, detail="Cannot accept suggestion when no sector was suggested.")
        sector = comp.sector
        reason_msg = f"Confirmed AI suggestion by {payload.reviewer_name}."
    elif payload.action == "change":
        if not payload.target_sector_id:
            raise HTTPException(status_code=400, detail="target_sector_id is required when changing sector.")
        sector = db.query(Sector).filter(Sector.id == payload.target_sector_id).first()
        if not sector:
            raise HTTPException(status_code=400, detail=f"Sector ID '{payload.target_sector_id}' does not exist.")
        comp.sector_id = sector.id
        reason_msg = f"Overridden by {payload.reviewer_name} to {sector.name}."
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'accept' or 'change'.")

    if payload.notes:
        reason_msg += f" Note: {payload.notes}"

    comp.status = "classified"
    comp.confidence = 1.0  # Human validated
    comp.classification_reason = reason_msg

    # Add audit classification record
    cls_audit = Classification(
        company_id=comp.id,
        sector_id=comp.sector_id,
        confidence=1.0,
        reason=reason_msg,
        evidence=["Human Review Decision"],
        model_version="human_review",
        reviewed_by=payload.reviewer_name
    )
    db.add(cls_audit)
    db.commit()

    # Optionally add to knowledge base examples
    if payload.learn_as_example and comp.name and comp.sector_id:
        indexer = SectorKnowledgeIndexer()
        indexer.add_example_to_sector(comp.sector_id, comp.name, db=db)

    logger.info(f"Reviewer {payload.reviewer_name} processed review for lead {lead_id}: {comp.status} ({comp.sector_id}).")
    return {
        "id": comp.id,
        "sector_id": comp.sector_id,
        "sector_name": comp.sector.name if comp.sector else None,
        "status": comp.status,
        "message": "Lead review successfully saved."
    }
