"""
FastAPI application with PostGIS backend.
Handles application lifecycle (startup/shutdown) and route registration.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.dependencies import set_backend
from app.postgis_backend import PostGISBackend
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    Runs on startup (before yield) and shutdown (after yield).
    """
    # Startup: initialize and connect backend
    backend = PostGISBackend(settings.database_url)
    await backend.connect()
    set_backend(backend)
    print("✓ Connected to PostGIS")

    yield  # Application runs here

    # Shutdown: disconnect backend
    await backend.disconnect()
    print("✓ Disconnected from PostGIS")


# Create FastAPI application
app = FastAPI(
    title="PostGIS Feature API",
    description="REST API for storing and querying geographic features",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "PostGIS Feature API"}
