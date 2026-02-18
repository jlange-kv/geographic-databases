from typing import Any

from pydantic import BaseModel, Field


class Geometry(BaseModel):
    """GeoJSON Geometry object (Point, Polygon, etc.)."""

    type: str
    coordinates: list[Any]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "Point", "coordinates": [10.0, 59.0]},
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [10.0, 59.0],
                            [11.0, 59.0],
                            [11.0, 60.0],
                            [10.0, 60.0],
                            [10.0, 59.0],
                        ]
                    ],
                },
            ]
        }
    }


class FeatureCreate(BaseModel):
    """Input model for creating a feature. No id — the database assigns it."""

    geometry: Geometry
    properties: dict[str, Any] = Field(default_factory=dict)


class Feature(BaseModel):
    """A complete GeoJSON Feature with id, as returned by the API."""

    id: int
    type: str = "Feature"
    geometry: Geometry
    properties: dict[str, Any] = Field(default_factory=dict)


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection — wraps a list of Features."""

    type: str = "FeatureCollection"
    features: list[Feature]
