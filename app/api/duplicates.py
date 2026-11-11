from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Company, DuplicateLog
from app.dedup.consolidator import manual_merge_companies, undo_merge
from app.core.logging import logger

router = APIRouter(prefix="/api/duplicates", tags=["Duplicates"])


class MergeRequest(BaseModel):
    kept_company_id: int
    merged_company_id: int


class UndoMergeRequest(BaseModel):
    duplicate_log_id: int


class RejectDuplicateRequest(BaseModel):
    duplicate_log_id: int


@router.get("")
def list_duplicates(db: Session = Depends(get_db)):
    """
    Returns potential duplicates awaiting review, confirmed merges, and audit history.
    """
    # 1. Potential Duplicates (Flagged by Rule 3)
    potential_logs = (
        db.query(DuplicateLog)
        .filter(DuplicateLog.rule == "RULE_3_POTENTIAL_DUPLICATE_FLAG", DuplicateLog.active == False)
        .order_by(DuplicateLog.created_at.desc())
        .all()
    )
    potential_items = []
    for p in potential_logs:
        comp_a = db.query(Company).filter(Company.id == p.kept_company_id).first()
        comp_b = db.query(Company).filter(Company.id == p.merged_company_id).first()
        if comp_a and comp_b and comp_b.status != "merged":
            potential_items.append({
                "log_id": p.id,
                "rule": p.rule,
                "similarity": p.details.get("score") if isinstance(p.details, dict) else 85.0,
                "company_a": {
                    "id": comp_a.id,
                    "name": comp_a.name,
                    "domain": comp_a.domain,
                    "sector": comp_a.sector.name if comp_a.sector else "Unassigned",
                    "confidence": comp_a.confidence,
                    "contacts_count": len(comp_a.contacts)
                },
                "company_b": {
                    "id": comp_b.id,
                    "name": comp_b.name,
                    "domain": comp_b.domain,
                    "sector": comp_b.sector.name if comp_b.sector else "Unassigned",
                    "confidence": comp_b.confidence,
                    "contacts_count": len(comp_b.contacts)
                },
                "created_at": p.created_at.isoformat() if p.created_at else None
            })

    # 2. Confirmed Merged Records
    merged_logs = (
        db.query(DuplicateLog)
        .filter(DuplicateLog.active == True)
        .order_by(DuplicateLog.created_at.desc())
        .all()
    )
    merged_items = []
    for m in merged_logs:
        kept = db.query(Company).filter(Company.id == m.kept_company_id).first()
        merged = db.query(Company).filter(Company.id == m.merged_company_id).first()
        merged_items.append({
            "log_id": m.id,
            "rule": m.rule,
            "kept_company": {
                "id": kept.id if kept else m.kept_company_id,
                "name": kept.name if kept else "Unknown",
                "domain": kept.domain if kept else None
            },
            "merged_company": {
                "id": merged.id if merged else m.merged_company_id,
                "name": merged.name if merged else "Merged Entity",
                "domain": merged.domain if merged else None
            },
            "details": m.details,
            "merged_at": m.created_at.isoformat() if m.created_at else None
        })

    return {
        "potential_duplicates": potential_items,
        "confirmed_merges": merged_items
    }


@router.post("/merge")
def confirm_merge(payload: MergeRequest, db: Session = Depends(get_db)):
    """Confirms manual merge of two duplicate companies."""
    log_entry = manual_merge_companies(payload.kept_company_id, payload.merged_company_id, db)
    if not log_entry:
        raise HTTPException(status_code=400, detail="Unable to merge specified companies. Verify IDs.")
    return {"message": "Companies merged successfully.", "log_id": log_entry.id}


@router.post("/reject")
def reject_duplicate(payload: RejectDuplicateRequest, db: Session = Depends(get_db)):
    """Rejects duplicate recommendation, removing it from potential duplicate queue."""
    log_entry = db.query(DuplicateLog).filter(DuplicateLog.id == payload.duplicate_log_id).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Duplicate log record not found.")

    db.delete(log_entry)
    db.commit()
    return {"message": "Potential duplicate suggestion rejected."}


@router.post("/undo")
def undo_company_merge(payload: UndoMergeRequest, db: Session = Depends(get_db)):
    """Undoes a previous company merge, restoring original company status and contacts."""
    success = undo_merge(payload.duplicate_log_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to undo merge. Log entry not found or already undone.")
    return {"message": "Merge successfully reverted. Original company status restored."}
