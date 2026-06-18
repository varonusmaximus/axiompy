# @!documentation

"""
Application configuration management using AxiomPy config patterns.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    debug: bool = Field(default=False, description="Debug mode")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")

    # Database Configuration
    database_url: Optional[str] = Field(None, description="Database connection URL")

    # API Configuration
    api_title: str = Field(default="AxiomPy Template API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
