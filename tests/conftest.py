import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import Base, get_db
from app.db.seed import seed_sectors
from app.rag.indexer import SectorKnowledgeIndexer

TEST_DB_URL = "sqlite:///./test_lead_agent.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Create test tables
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_sectors(db)
    indexer = SectorKnowledgeIndexer()
    indexer.reindex_all_sectors(db, force=True)
    db.close()
    yield
    # Teardown
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_lead_agent.db"):
        try:
            os.remove("./test_lead_agent.db")
        except Exception:
            pass


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
