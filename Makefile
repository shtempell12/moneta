.PHONY: up down logs migrate demo-data test lint format typecheck check backup restore

up:
	docker compose up -d --build
	$(MAKE) migrate

down:
	docker compose down

logs:
	docker compose logs -f app

migrate:
	docker compose exec app alembic upgrade head

# Synthetic statement for demos, saved to data/ (not committed).
demo-data:
	uv run python scripts/make_demo_statement.py

# Needs the database container running (make up).
test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy app tests scripts

check: lint typecheck test

# Dump is taken inside the db container, so pg_dump does not need to be installed locally.
backup:
	mkdir -p backups
	docker compose exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --clean --if-exists' \
		> backups/moneta_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Saved to backups/"

# Usage: make restore FILE=backups/moneta_20261026_120000.sql
restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/<file>.sql" && exit 1)
	docker compose exec -T db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < $(FILE)
