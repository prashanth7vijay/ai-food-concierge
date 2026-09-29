"""
Centralized application configuration.

All configuration is sourced from environment variables so that no
credentials or environment-specific values are hardcoded in source.
See `.env.example` at the repo root for the full list of variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "AI Food Concierge"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero external
    # services for local development/testing. Production deployments should
    # set DATABASE_URL to a PostgreSQL DSN, e.g.:
    #   postgresql+psycopg://user:pass@localhost:5432/food_concierge
    DATABASE_URL: str = "sqlite:///./food_concierge.db"

    # --- Redis ---
    # Optional. If unset, the app falls back to in-process caching/rate
    # limiting (fine for local dev/tests, not for multi-instance prod).
    REDIS_URL: str | None = None

    # --- LLM Provider ---
    LLM_PROVIDER: Literal["gemini", "ollama", "mock"] = "mock"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_MAX_RETRIES: int = 2

    # --- Retrieval / ranking ---
    EMBEDDING_DIM: int = 384
    RANKING_WEIGHT_CONSTRAINT_MATCH: float = 0.35
    RANKING_WEIGHT_SEMANTIC: float = 0.20
    RANKING_WEIGHT_RATING: float = 0.20
    RANKING_WEIGHT_PRICE_FIT: float = 0.15
    RANKING_WEIGHT_CUISINE_MATCH: float = 0.10

    # --- Rate limiting ---
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
