"""
API routes for feature CRUD operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from shared.models import Feature, FeatureCollection, FeatureCreate
from shared.storage import StorageBackend

from app.dependencies import get_backend

router = APIRouter(tags=["features"])


@router.post("/features", response_model=Feature, status_code=201)
async def create_feature(
    feature: FeatureCreate,
    backend: StorageBackend = Depends(get_backend),
):
    """Create a new feature."""
    result = await backend.create_feature(feature)
    return result


@router.get("/features/{feature_id}", response_model=Feature)
async def get_feature(
    feature_id: int,
    backend: StorageBackend = Depends(get_backend),
):
    """Get a feature by ID."""
    result = await backend.get_feature(feature_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Feature id number {feature_id} not found"
        )
    return result


@router.get("/features", response_model=FeatureCollection)
async def list_features(
    minx: float | None = Query(None, description="Minimum longitude (bbox)"),
    miny: float | None = Query(None, description="Minimum latitude (bbox)"),
    maxx: float | None = Query(None, description="Maximum longitude (bbox)"),
    maxy: float | None = Query(None, description="Maximum latitude (bbox)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    backend: StorageBackend = Depends(get_backend),
):
    """List features with optional bounding box filter."""
    bbox = (minx, miny, maxx, maxy)
    if any(v is None for v in (minx, maxx, miny, maxy)):
        bbox = None
    features = await backend.list_features(bbox, limit, offset)
    return FeatureCollection(features=features)


@router.put("/features/{feature_id}", response_model=Feature)
async def update_feature(
    feature_id: int,
    feature: FeatureCreate,
    backend: StorageBackend = Depends(get_backend),
):
    """Update an existing feature."""
    result = await backend.update_feature(feature_id, feature)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Feature with id {feature_id} not found"
        )
    return result


@router.delete("/features/{feature_id}", status_code=204)
async def delete_feature(
    feature_id: int,
    backend: StorageBackend = Depends(get_backend),
):
    """Delete a feature."""
    result = await backend.delete_feature(feature_id)
    if not result:
        raise HTTPException(status_code=404, detail="Feature not found")


@router.get("/features/stats/count", response_model=dict)
async def count_features(
    backend: StorageBackend = Depends(get_backend),
):
    """Get the total count of features."""
    count = await backend.count_features()
    return {"count": count}
