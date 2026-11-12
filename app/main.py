import os
import gc
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.db.seed import init_db, seed_sectors
from app.rag.indexer import SectorKnowledgeIndexer
from app.rag.embeddings import get_embedding_provider

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
    logger.info("==================================================================")
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (PID: {os.getpid()})")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Host: {settings.HOST} | Configured Port: {settings.PORT}")
    logger.info("==================================================================")
    try:
        # Step 1: Database Initialization
        logger.info("[STARTUP 1/5] Initializing database schema and tables...")
        init_db()
        logger.info("[STARTUP 1/5 COMPLETE] Database schema verified.")

        # Step 2: Sector Seeding
        logger.info("[STARTUP 2/5] Seeding/verifying 13 standard industry sectors...")
        seed_sectors()
        logger.info("[STARTUP 2/5 COMPLETE] 13 industry sectors ready in database.")

        # Step 3: Vector Database Check & Indexing
        logger.info(f"[STARTUP 3/5] Initializing vector store (provider: {settings.VECTOR_STORE})...")
        indexer = SectorKnowledgeIndexer()
        chunks_indexed = indexer.reindex_all_sectors(force=False)
        logger.info(f"[STARTUP 3/5 COMPLETE] Vector store ready with {chunks_indexed} sector chunks.")

        # Step 4: Shared FastEmbed Embedding Model Singleton
        logger.info(f"[STARTUP 4/5] Verifying shared embedding service (provider: {settings.EMBEDDING_PROVIDER})...")
        embedding_provider = get_embedding_provider()
        if not settings.IS_SERVERLESS and hasattr(embedding_provider, "warmup"):
            embedding_provider.warmup()
        logger.info(f"[STARTUP 4/5 COMPLETE] Shared embedding provider ready: {embedding_provider.model_version}")

        # Step 5: Server Startup Success & Memory Cleanup
        gc.collect()
        logger.info(
            f"[STARTUP 5/5 COMPLETE] Server startup routines completed successfully! "
            f"Ready on http://{settings.HOST}:{settings.PORT}"
        )
    except Exception as e:
        logger.error(f"Startup initialization error: {e}", exc_info=True)
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


# Root Welcome Endpoint
@app.get("/", tags=["Root"])
def root():
    """Welcome endpoint returning API metadata, docs, and health route."""
    return {
        "application": settings.APP_NAME,
        "status": "Running",
        "documentation": "/docs",
        "health": "/api/health",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Favicon Endpoint to avoid unnecessary 404 logs
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Returns 204 No Content to silence browser favicon requests."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Health Check
@app.get("/api/health", tags=["Health"])
def health_check():
    """
    Health check endpoint reporting application readiness and dependency status:
    - Database connectivity
    - Vector Store availability and indexed sector chunks
    - Embedding Provider readiness
    """
    db_status = "connected"
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    vector_count = 0
    vector_status = "ready"
    try:
        from app.rag.vector_store import get_vector_store
        vs = get_vector_store()
        vector_count = vs.count()
    except Exception as e:
        vector_status = f"unhealthy: {str(e)}"

    embedding_status = "ready"
    embedding_model = settings.EMBEDDING_MODEL
    try:
        ep = get_embedding_provider()
        embedding_model = ep.model_version
    except Exception as e:
        embedding_status = f"unhealthy: {str(e)}"

    overall_healthy = db_status == "connected" and not vector_status.startswith("unhealthy")

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": db_status,
            "vector_store": {
                "provider": settings.VECTOR_STORE,
                "status": vector_status,
                "indexed_chunks": vector_count
            },
            "embedding": {
                "provider": settings.EMBEDDING_PROVIDER,
                "model": embedding_model,
                "status": embedding_status
            }
        },
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
