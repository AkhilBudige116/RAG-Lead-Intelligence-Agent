from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.session import get_db
from app.db.models import Company, Contact, Email
from app.export.exporter import generate_csv_export, generate_excel_export
from app.core.logging import logger

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("")
def export_leads(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    sector: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_confidence: Optional[float] = None,
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exports filtered leads as CSV or XLSX (with multiple sector sheets).
    Includes formula injection sanitization.
    """
    query = db.query(Company).filter(Company.status != "merged")

    if sector and sector != "all":
        query = query.filter(Company.sector_id == sector)

    if status and status != "all":
        query = query.filter(Company.status == status)

    if min_confidence is not None:
        query = query.filter(Company.confidence >= min_confidence)

    if batch_id:
        query = query.join(Email, Email.company_id == Company.id).filter(Email.batch_id == batch_id).distinct()

    if search:
        search_term = f"%{search.strip()}%"
        query = query.outerjoin(Contact, Contact.company_id == Company.id).filter(
            or_(
                Company.name.ilike(search_term),
                Company.domain.ilike(search_term),
                Contact.name.ilike(search_term),
                Contact.email.ilike(search_term)
            )
        ).distinct()

    companies = query.order_by(Company.created_at.desc()).all()

    # Format records
    records = []
    for comp in companies:
        primary_contact = comp.contacts[0] if comp.contacts else None
        records.append({
            "company_name": comp.name or "N/A",
            "contact_name": primary_contact.name if primary_contact else "N/A",
            "email": primary_contact.email if primary_contact else "N/A",
            "phone": primary_contact.phone if primary_contact else "N/A",
            "website": comp.website or "N/A",
            "sector_name": comp.sector.name if comp.sector else "Unassigned",
            "confidence": comp.confidence or 0.0,
            "classification_reason": comp.classification_reason or "",
            "status": comp.status,
            "is_duplicate": False
        })

    if format == "csv":
        csv_bytes = generate_csv_export(records)
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
        )
    else:
        xlsx_bytes = generate_excel_export(records, split_by_sector=True)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads_export.xlsx"}
        )
