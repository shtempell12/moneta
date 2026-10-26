import pytest

from app.core.config import Settings


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/test")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql://user:pass@db:5432/test"
