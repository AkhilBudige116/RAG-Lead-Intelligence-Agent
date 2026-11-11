from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.db.session import get_db
from app.db.models import Company, Contact, Email, Classification, Sector
from app.rag.indexer import SectorKnowledgeIndexer
from app.core.logging import logger

router = APIRouter(prefix="/api/leads", tags=["Leads"])


class SectorUpdateRequest(BaseModel):
    sector_id: str = Field(description="Target Sector ID")
    reviewer_name: Optional[str] = Field(default="Reviewer", description="Name or ID of the reviewer")
    reviewer_notes: Optional[str] = Field(default=None, description="Reviewer justification or notes")
    add_as_knowledge_example: bool = Field(default=False, description="Whether to append company name to sector examples in vector index")


@router.get("")
def list_leads(
    sector: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    batch_id: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|confidence|name)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns paginated lead records with comprehensive search and filtering capabilities.
    """
    query = db.query(Company).filter(Company.status != "merged")

    if sector and sector != "all":
        query = query.filter(Company.sector_id == sector)

    if status and status != "all":
        query = query.filter(Company.status == status)

    if min_confidence is not None:
        query = query.filter(Company.confidence >= min_confidence)

    if max_confidence is not None:
        query = query.filter(Company.confidence <= max_confidence)

    if batch_id:
        query = query.join(Email, Email.company_id == Company.id).filter(Email.batch_id == batch_id).distinct()

    if search:
        search_term = f"%{search.strip()}%"
        query = query.outerjoin(Contact, Contact.company_id == Company.id).filter(
            or_(
                Company.name.ilike(search_term),
                Company.domain.ilike(search_term),
                Company.website.ilike(search_term),
                Contact.name.ilike(search_term),
                Contact.email.ilike(search_term)
            )
        ).distinct()

    total = query.count()

    # Sort
    col_attr = getattr(Company, sort_by)
    query = query.order_by(desc(col_attr) if sort_order == "desc" else asc(col_attr))

    # Paginate
    offset = (page - 1) * page_size
    companies = query.offset(offset).limit(page_size).all()

    items = []
    for comp in companies:
        primary_contact = comp.contacts[0] if comp.contacts else None
        items.append({
            "id": comp.id,
            "company_name": comp.name or "Unknown Company",
            "contact_name": primary_contact.name if primary_contact else "N/A",
            "email": primary_contact.email if primary_contact else "N/A",
            "phone": primary_contact.phone if primary_contact else None,
            "website": comp.website,
            "domain": comp.domain,
            "sector_id": comp.sector_id,
            "sector_name": comp.sector.name if comp.sector else "Unassigned",
            "confidence": comp.confidence,
            "status": comp.status,
            "classification_reason": comp.classification_reason,
            "contacts_count": len(comp.contacts),
            "created_at": comp.created_at.isoformat() if comp.created_at else None
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "items": items
    }


@router.get("/{lead_id}")
def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    """
    Returns complete lead details, including company info, contact roster,
    associated emails, latest classification trace, and historical logs.
    """
    company = db.query(Company).filter(Company.id == lead_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Lead not found.")

    # Primary Contact & All Contacts
    contacts_data = [
        {
            "id": c.id,
            "name": c.name,
            "title": c.title,
            "email": c.email,
            "phone": c.phone,
            "email_count": c.email_count,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in company.contacts
    ]

    # Associated Emails
    emails_data = [
        {
            "id": e.id,
            "batch_id": e.batch_id,
            "sender_name": e.sender_name,
            "sender_email": e.sender_email,
            "subject": e.subject,
            "body": e.body,
            "signature": e.signature,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "source_file": e.source_file,
            "raw_hash": e.raw_hash,
            "evidence_sources": e.evidence_sources
        }
        for e in company.emails
    ]

    # Latest Classification Trace
    latest_cls = db.query(Classification).filter(
        Classification.company_id == company.id
    ).order_by(Classification.created_at.desc()).first()

    classification_trace = None
    if latest_cls:
        classification_trace = {
            "id": latest_cls.id,
            "sector_id": latest_cls.sector_id,
            "sector_name": latest_cls.sector.name if latest_cls.sector else "Unknown",
            "confidence": latest_cls.confidence,
            "llm_confidence": latest_cls.llm_confidence,
            "top_retrieval_similarity": latest_cls.top_retrieval_similarity,
            "reason": latest_cls.reason,
            "evidence": latest_cls.evidence,
            "retrieved_sector_ids": latest_cls.retrieved_sector_ids,
            "model_version": latest_cls.model_version,
            "reviewed_by": latest_cls.reviewed_by,
            "created_at": latest_cls.created_at.isoformat() if latest_cls.created_at else None
        }

    return {
        "id": company.id,
        "name": company.name,
        "normalized_name": company.normalized_name,
        "domain": company.domain,
        "website": company.website,
        "sector_id": company.sector_id,
        "sector_name": company.sector.name if company.sector else "Unassigned",
        "confidence": company.confidence,
        "classification_reason": company.classification_reason,
        "status": company.status,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
        "contacts": contacts_data,
        "emails": emails_data,
        "latest_classification": classification_trace
    }


@router.patch("/{lead_id}/sector")
def update_lead_sector(
    lead_id: int,
    payload: SectorUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Allows a human reviewer to confirm or correct a lead's sector assignment.
    Records reviewer name, notes, and audit trace.
    """
    company = db.query(Company).filter(Company.id == lead_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Lead not found.")

    target_sector = db.query(Sector).filter(Sector.id == payload.sector_id).first()
    if not target_sector:
        raise HTTPException(status_code=400, detail=f"Sector ID '{payload.sector_id}' does not exist.")

    # Record reviewer update
    old_sector_name = company.sector.name if company.sector else "None"
    company.sector_id = target_sector.id
    company.status = "classified"
    company.confidence = 1.0  # Human-verified confidence

    reason_msg = f"Confirmed by {payload.reviewer_name}: Changed from {old_sector_name} to {target_sector.name}."
    if payload.reviewer_notes:
        reason_msg += f" Note: {payload.reviewer_notes}"
    company.classification_reason = reason_msg

    # Add classification audit entry
    audit_entry = Classification(
        company_id=company.id,
        sector_id=target_sector.id,
        confidence=1.0,
        llm_confidence=None,
        top_retrieval_similarity=None,
        reason=reason_msg,
        evidence=["Human Reviewer Verified"],
        retrieved_sector_ids=[target_sector.id],
        model_version="human_review",
        reviewed_by=payload.reviewer_name
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(company)

    # Optionally add company name to sector examples in vector index
    if payload.add_as_knowledge_example and company.name:
        indexer = SectorKnowledgeIndexer()
        indexer.add_example_to_sector(target_sector.id, company.name, db=db)

    logger.info(f"Reviewer '{payload.reviewer_name}' updated lead {lead_id} to sector '{target_sector.name}'.")
    return {
        "id": company.id,
        "sector_id": company.sector_id,
        "sector_name": target_sector.name,
        "status": company.status,
        "confidence": company.confidence,
        "message": f"Successfully updated lead sector to {target_sector.name}."
    }
