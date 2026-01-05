"""
Main Application Module

This module creates and configures the FastAPI application with all
middleware, routes, and lifecycle events.

Author: ANPR Team
Created: 2025
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events.
    """
    # Startup
    print("=" * 60)
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)

    # Initialize database
    init_db()

    print("✓ Application started successfully")
    print(f"✓ API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 60)

    yield

    # Shutdown
    print("=" * 60)
    print("Shutting down application...")

    # Stop all workers
    from app.services.worker_service import ACTIVE_WORKERS
    if ACTIVE_WORKERS:
        print(f"Stopping {len(ACTIVE_WORKERS)} active workers...")
        for camera_id, worker in list(ACTIVE_WORKERS.items()):
            try:
                worker.stop()
                del ACTIVE_WORKERS[camera_id]
                print(f"✓ Stopped worker for camera {camera_id}")
            except Exception as e:
                print(f"✗ Error stopping worker {camera_id}: {e}")

    # Stop all streams
    from app.services.stream_service import STREAM_THREADS
    if STREAM_THREADS:
        print(f"Stopping {len(STREAM_THREADS)} active streams...")
        # Use a temporary DB session for shutdown
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            from app.services.stream_service import StreamService
            stream_service = StreamService(db)
            result = stream_service.stop_all_streams()
            print(f"✓ Stopped {result['stopped_count']} streams")
        except Exception as e:
            print(f"✗ Error stopping streams: {e}")
        finally:
            db.close()

    print("✓ Application shutdown complete")
    print("=" * 60)


def create_application() -> FastAPI:
    """
    Application Factory

    Creates and configures the FastAPI application instance.

    Returns:
        FastAPI: Configured application instance
    """
    # Create FastAPI application
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="ANPR Client Backend - Object Detection & Management System",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Mount static files for detection images
    app.mount("/detections", StaticFiles(directory=str(settings.DETECTIONS_DIR)), name="detections")

    # Root endpoint
    @app.get("/", tags=["root"])
    def root():
        """
        Root endpoint

        Returns basic application information.
        """
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc"
        }

    # Health check endpoint
    @app.get("/health", tags=["health"])
    def health_check():
        """
        Health check endpoint

        Returns application health status.
        """
        from app.services.worker_service import ACTIVE_WORKERS

        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "active_workers": len(ACTIVE_WORKERS)
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """
        Global exception handler

        Catches all unhandled exceptions and returns formatted error response.
        """
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if settings.DEBUG else "An error occurred"
            }
        )

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    """
    Run application with uvicorn

    For development only. Use gunicorn/uvicorn for production.
    """
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower()
    )