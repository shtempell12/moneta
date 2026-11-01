from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings read from environment variables and the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql://moneta:moneta@localhost:5432/moneta"


# Cached so the .env file is read once per process, not on every request.
@lru_cache
def get_settings() -> Settings:
    return Settings()
