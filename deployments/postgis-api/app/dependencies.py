"""
Dependency injection for FastAPI routes.
Provides access to the storage backend.
"""
from shared.storage import StorageBackend

# Backend instance (initialized in main.py)
_backend: StorageBackend | None = None


def set_backend(backend: StorageBackend) -> None:
    """Set the global backend instance (called during app startup)."""
    global _backend
    _backend = backend


def get_backend() -> StorageBackend:
    """Dependency that provides the storage backend to route handlers."""
    if _backend is None:
        raise RuntimeError("Backend not initialized")
    return _backend
