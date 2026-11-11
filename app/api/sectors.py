from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Sector, Company
from app.rag.indexer import SectorKnowledgeIndexer
from app.core.logging import logger

router = APIRouter(prefix="/api/sectors", tags=["Sectors"])


class SectorCreate(BaseModel):
    id: str = Field(description="Unique snake_case sector identifier, e.g. 'clean_energy'")
    name: str = Field(description="Human-readable sector title, e.g. 'Clean Energy & Utilities'")
    description: str = Field(description="Comprehensive sector description for RAG matching")
    keywords: List[str] = Field(default_factory=list, description="Industry keywords")
    examples: List[str] = Field(default_factory=list, description="Representative companies")
    notes: Optional[str] = Field(default=None, description="Disambiguation guidance")
    active: bool = Field(default=True)


class SectorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
def list_sectors(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """List sectors for administration and dropdown filtering."""
    query = db.query(Sector)
    if not include_inactive:
        query = query.filter(Sector.active == True)

    sectors = query.order_by(Sector.name.asc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "keywords": s.keywords,
            "examples": s.examples,
            "notes": s.notes,
            "active": s.active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in sectors
    ]


@router.post("")
def create_sector(payload: SectorCreate, db: Session = Depends(get_db)):
    """Creates a new industry sector and indexes it in the vector store."""
    existing = db.query(Sector).filter(Sector.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Sector with ID '{payload.id}' already exists.")

    sector = Sector(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        keywords=payload.keywords,
        examples=payload.examples,
        notes=payload.notes,
        active=payload.active
    )
    db.add(sector)
    db.commit()
    db.refresh(sector)

    # Re-index sector in vector store
    indexer = SectorKnowledgeIndexer()
    indexer.index_single_sector(sector)

    return {"message": f"Sector '{sector.name}' created and indexed successfully.", "sector_id": sector.id}


@router.patch("/{sector_id}")
def update_sector(sector_id: str, payload: SectorUpdate, db: Session = Depends(get_db)):
    """Updates sector definition and automatically updates the vector store."""
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found.")

    if payload.name is not None:
        sector.name = payload.name
    if payload.description is not None:
        sector.description = payload.description
    if payload.keywords is not None:
        sector.keywords = payload.keywords
    if payload.examples is not None:
        sector.examples = payload.examples
    if payload.notes is not None:
        sector.notes = payload.notes
    if payload.active is not None:
        sector.active = payload.active

    db.commit()
    db.refresh(sector)

    indexer = SectorKnowledgeIndexer()
    indexer.index_single_sector(sector)

    return {"message": f"Sector '{sector.name}' updated and re-indexed successfully."}


@router.delete("/{sector_id}")
def deactivate_sector(sector_id: str, db: Session = Depends(get_db)):
    """
    Safely deactivates a sector rather than deleting it to preserve historical lead references.
    """
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found.")

    sector.active = False
    db.commit()

    indexer = SectorKnowledgeIndexer()
    indexer.index_single_sector(sector)  # Will remove from active vector search

    return {"message": f"Sector '{sector.name}' deactivated safely. Historical leads preserved."}


@router.post("/{sector_id}/reindex")
def reindex_sector(sector_id: str, db: Session = Depends(get_db)):
    """Manually re-indexes a single sector."""
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found.")

    indexer = SectorKnowledgeIndexer()
    indexer.index_single_sector(sector)
    return {"message": f"Sector '{sector.name}' re-indexed successfully."}


@router.post("/reindex-all")
def reindex_all_sectors(db: Session = Depends(get_db)):
    """Triggers complete vector re-indexing for all active sectors."""
    indexer = SectorKnowledgeIndexer()
    chunks_count = indexer.reindex_all_sectors(db, force=True)
    return {"message": f"All active sectors re-indexed successfully ({chunks_count} chunks generated)."}
