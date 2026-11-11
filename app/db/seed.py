import os
import yaml
from sqlalchemy.orm import Session
from app.db.session import engine, Base, SessionLocal
from app.db.models import Sector
from app.core.logging import logger

SECTORS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base", "sectors.yaml")


def init_db():
    """Create all database tables."""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")


def seed_sectors(db: Session = None) -> int:
    """Seed or update sectors from YAML file."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        if not os.path.exists(SECTORS_FILE):
            logger.warning(f"Sectors file not found at {SECTORS_FILE}")
            return 0

        with open(SECTORS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sectors_data = data.get("sectors", [])
        count = 0
        for s in sectors_data:
            existing = db.query(Sector).filter(Sector.id == s["sector_id"]).first()
            if existing:
                existing.name = s["sector_name"]
                existing.description = s["description"]
                existing.keywords = s.get("keywords", [])
                existing.examples = s.get("example_businesses", [])
                existing.notes = s.get("disambiguation_notes", "")
                existing.active = s.get("active_status", True)
            else:
                new_sector = Sector(
                    id=s["sector_id"],
                    name=s["sector_name"],
                    description=s["description"],
                    keywords=s.get("keywords", []),
                    examples=s.get("example_businesses", []),
                    notes=s.get("disambiguation_notes", ""),
                    active=s.get("active_status", True)
                )
                db.add(new_sector)
                count += 1

        db.commit()
        logger.info(f"Seeded/synchronized {len(sectors_data)} sectors ({count} newly inserted).")
        return len(sectors_data)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed sectors: {e}")
        raise e
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    init_db()
    seed_sectors()
