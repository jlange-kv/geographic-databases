from abc import ABC, abstractmethod

from .models import Feature, FeatureCreate


class StorageBackend(ABC):
    """Interface for geographic feature storage.

    Each backend (PostGIS, DuckDB, GeoPackage) implements this ABC.
    The API routes depend only on this interface, never on a specific backend.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and release resources."""
        ...

    @abstractmethod
    async def create_feature(self, feature: FeatureCreate) -> Feature:
        """Insert a new feature. Returns the feature with its assigned id."""
        ...

    @abstractmethod
    async def get_feature(self, feature_id: int) -> Feature | None:
        """Retrieve a single feature by id. Returns None if not found."""
        ...

    @abstractmethod
    async def list_features(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Feature]:
        """List features, optionally filtered by bounding box.

        bbox is (min_lon, min_lat, max_lon, max_lat) in WGS84.
        """
        ...

    @abstractmethod
    async def update_feature(
        self, feature_id: int, feature: FeatureCreate
    ) -> Feature | None:
        """Replace a feature's geometry and properties. Returns None if not found."""
        ...

    @abstractmethod
    async def delete_feature(self, feature_id: int) -> bool:
        """Delete a feature by id. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def count_features(self) -> int:
        """Return total number of features."""
        ...
