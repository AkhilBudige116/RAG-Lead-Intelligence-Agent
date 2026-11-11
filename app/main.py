from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.db.seed import init_db, seed_sectors
from app.rag.indexer import SectorKnowledgeIndexer

from app.api.uploads import router as uploads_router
from app.api.emails import router as emails_router
from app.api.batches import router as batches_router
from app.api.leads import router as leads_router
from app.api.sectors import router as sectors_router
from app.api.stats import router as stats_router
from app.api.duplicates import router as duplicates_router
from app.api.review import router as review_router
from app.api.export import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up RAG-Based Lead Segregation Agent service...")
    try:
        init_db()
        seed_sectors()
        indexer = SectorKnowledgeIndexer()
        indexer.reindex_all_sectors()
        logger.info("System startup routines and knowledge base indexing completed.")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}")
    yield
    # Shutdown
    logger.info("Shutting down RAG Lead Segregation Agent service.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade RAG-Based Lead Intelligence and Sector Segregation Platform.",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred.",
            "path": request.url.path
        }
    )


# Health Check
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "vector_store": settings.VECTOR_STORE,
        "embedding_provider": settings.EMBEDDING_PROVIDER
    }


# Register API Routers
app.include_router(uploads_router)
app.include_router(emails_router)
app.include_router(batches_router)
app.include_router(leads_router)
app.include_router(sectors_router)
app.include_router(stats_router)
app.include_router(duplicates_router)
app.include_router(review_router)
app.include_router(export_router)
