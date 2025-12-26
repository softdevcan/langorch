from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.api.v1.router import api_router

# Structured logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="SaaS RAG Orkestrasyon Platformu",
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": f"{settings.API_PREFIX}/docs",
    }


@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Initialize Qdrant collection for documents
    try:
        from app.core.qdrant_client import qdrant_store

        await qdrant_store.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIMENSIONS,
        )
        logger.info(
            "qdrant_collection_initialized",
            collection=settings.QDRANT_COLLECTION_NAME,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    except Exception as e:
        logger.error(
            "qdrant_collection_initialization_failed",
            error=str(e),
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("application_shutdown", app_name=settings.APP_NAME)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.APP_DEBUG,
        log_level="info" if settings.APP_DEBUG else "warning",
    )
