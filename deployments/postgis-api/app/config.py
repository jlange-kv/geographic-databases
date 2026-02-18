"""
Configuration management using pydantic-settings.
Loads settings from environment variables with fallback defaults.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql://postgres:postgres@localhost:5432/geodata"

    class Config:
        env_file = ".env"  # Optional: load from .env file if present


# Global settings instance
settings = Settings()
