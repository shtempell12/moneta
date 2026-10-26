# Монета

Веб-сервис для ведения семейного бюджета: траты автоматически раскладываются по личным категориям пользователя, есть план/факт по месяцам, цели накопления и выгрузка в Excel.

Учебный стартап-проект (МФТИ, НИР).

## Стек

Python 3.12, FastAPI, PostgreSQL 16, Docker Compose. Зависимости — через [uv](https://docs.astral.sh/uv/).

## Запуск

Нужны Docker Desktop и uv.

```bash
cp .env.example .env    # затем поменяй пароли в .env
make up                 # поднимает app + Postgres
curl localhost:8000/health
```

Документация API: http://localhost:8000/docs

## Разработка

```bash
uv sync         # установить зависимости в .venv
make test       # pytest
make lint       # ruff check + ruff format --check
make format     # автоформатирование
make typecheck  # mypy
make check      # всё сразу — то же, что проверяет CI
```

## Бэкап базы

```bash
make backup                                     # дамп в backups/
make restore FILE=backups/moneta_<дата>.sql     # восстановление
```

## Структура

```
app/
  domain/        чистая логика без FastAPI и БД
  services/      сценарии, связывают domain и репозитории
  repositories/  доступ к БД
  db/            модели SQLAlchemy
  api/           JSON-эндпоинты
  web/           страницы (Jinja2 + HTMX)
  core/          конфиг, безопасность
research/        офлайн-оценка категоризации
tests/           тесты
```
