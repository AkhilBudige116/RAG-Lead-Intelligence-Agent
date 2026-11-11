from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models import Company, Contact, Email, UploadBatch, DuplicateLog, Sector

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Computes all actual backend metrics and chart data for the Overview Dashboard.
    """
    # 1. KPI Counts
    total_emails = db.query(Email).count()
    total_companies = db.query(Company).filter(Company.status != "merged").count()
    classified_leads = db.query(Company).filter(Company.status == "classified").count()
    needs_review_leads = db.query(Company).filter(Company.status == "needs_review").count()
    duplicates_detected = db.query(DuplicateLog).count()

    # 2. Sector-wise Lead Distribution
    sector_counts = (
        db.query(Sector.name, func.count(Company.id))
        .join(Company, Company.sector_id == Sector.id)
        .filter(Company.status != "merged")
        .group_by(Sector.name)
        .all()
    )
    sector_distribution = [
        {"sector": s_name, "count": count}
        for s_name, count in sorted(sector_counts, key=lambda x: x[1], reverse=True)
    ]

    # Add unassigned if any
    unassigned_count = db.query(Company).filter(
        Company.sector_id.is_(None),
        Company.status != "merged"
    ).count()
    if unassigned_count > 0:
        sector_distribution.append({"sector": "Unassigned / Review", "count": unassigned_count})

    # 3. Classification Status Distribution
    status_counts = (
        db.query(Company.status, func.count(Company.id))
        .group_by(Company.status)
        .all()
    )
    status_distribution = [
        {"status": s, "count": cnt} for s, cnt in status_counts
    ]

    # 4. Confidence Score Distribution (Histogram Bins)
    all_confs = [
        c[0] for c in db.query(Company.confidence).filter(
            Company.confidence.isnot(None),
            Company.status != "merged"
        ).all()
    ]
    bins = {
        "< 0.50": 0,
        "0.50 - 0.65": 0,
        "0.65 - 0.75": 0,
        "0.75 - 0.85": 0,
        "0.85 - 1.00": 0
    }
    for conf in all_confs:
        if conf < 0.50:
            bins["< 0.50"] += 1
        elif conf < 0.65:
            bins["0.50 - 0.65"] += 1
        elif conf < 0.75:
            bins["0.65 - 0.75"] += 1
        elif conf < 0.85:
            bins["0.75 - 0.85"] += 1
        else:
            bins["0.85 - 1.00"] += 1

    confidence_distribution = [{"range": k, "count": v} for k, v in bins.items()]

    # 5. Batch Statistics
    recent_batches = (
        db.query(UploadBatch)
        .order_by(UploadBatch.created_at.desc())
        .limit(5)
        .all()
    )
    batch_stats = [
        {
            "id": b.id[:8],
            "filename": b.filename,
            "total": b.total_emails,
            "processed": b.processed_count,
            "failed": b.failed_count,
            "status": b.status
        }
        for b in recent_batches
    ]

    # 6. Duplicate Breakdown
    dup_rules = (
        db.query(DuplicateLog.rule, func.count(DuplicateLog.id))
        .group_by(DuplicateLog.rule)
        .all()
    )
    duplicate_stats = [
        {"rule": r or "Unknown", "count": cnt} for r, cnt in dup_rules
    ]

    return {
        "kpis": {
            "total_emails": total_emails,
            "total_companies": total_companies,
            "classified_leads": classified_leads,
            "needs_review_leads": needs_review_leads,
            "duplicates_detected": duplicates_detected,
        },
        "sector_distribution": sector_distribution,
        "status_distribution": status_distribution,
        "confidence_distribution": confidence_distribution,
        "batch_stats": batch_stats,
        "duplicate_stats": duplicate_stats
    }
