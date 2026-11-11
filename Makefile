.PHONY: up down logs migrate demo-data research statements-check export-labeled test lint format typecheck check backup restore

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

# H-ML1 comparison; with DATA=data/labeled.csv runs on real anonymized data.
research:
	uv run python -m research.evaluate $(DATA)

# H-DEV2: real statements named <bank>_<anything>.csv|xlsx in data/statements/.
statements-check:
	uv run python -m research.statements_check data/statements

# H-ML1 pilot: a participant's checked categories from the local database → data/labeled.csv.
# From the host the database is localhost, not db, so the URL is built from .env.
export-labeled:
	@test -n "$(EMAIL)" -a -n "$(NAME)" || (echo "Usage: make export-labeled EMAIL=... NAME=participant-1" && exit 1)
	set -a && . ./.env && set +a && \
		DATABASE_URL=postgresql+psycopg://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost:5432/$$POSTGRES_DB \
		uv run python -m research.export_labeled $(EMAIL) $(NAME)

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
	uv run mypy app tests scripts research

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
