from alembic import command
from sqlalchemy import Engine, inspect

from tests.conftest import alembic_config

EXPECTED_TABLES = {
    "users",
    "categories",
    "imports",
    "transactions",
    "merchant_rules",
    "events",
    "budget_lines",
    "goals",
}


def test_migrations_downgrade_and_upgrade_again(engine: Engine, db_url: str) -> None:
    config = alembic_config(db_url)

    command.downgrade(config, "base")
    assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
