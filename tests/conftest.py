from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings


def _create_database_if_missing(url: str) -> None:
    database = make_url(url).database
    server = create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
    server.dispose()


def alembic_config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def db_url() -> str:
    url = get_settings().test_database_url
    _create_database_if_missing(url)
    return url


@pytest.fixture(scope="session")
def engine(db_url: str) -> Iterator[Engine]:
    """Test database migrated from scratch once per test run."""
    config = alembic_config(db_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Session whose changes are rolled back after each test, so tests do not affect each other."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
