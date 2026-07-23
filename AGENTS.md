# Backend Guidelines

## Scope and Structure

Build the API with FastAPI and Python, managed by uv. Place production code in `app/`, tests in `tests/`, and Alembic revisions in `alembic/versions/`. Separate HTTP routers, Pydantic schemas, SQLAlchemy models, repositories, and domain services. Expose endpoints under `/api/v1` and run the local server on port `8080`.

## Commands

Maintain these entry points when scaffolding the backend:

```bash
docker compose up -d db
uv sync
uv run pytest
uv run pytest tests/path/test_file.py -q
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "add analysis table"
uv run uvicorn app.main:app --reload --port 8080
```

Use PostgreSQL, SQLAlchemy, and Alembic. Obtain `DATABASE_URL` and AI provider credentials from environment variables; never commit real secrets.

## TDD and Testing

Follow Red, Green, Refactor for each behavior change. Write a failing `test_*.py` first, implement the smallest passing change, then refactor. Use pytest for unit and API tests. Keep domain calculations testable without the database or AI provider. Add integration tests for repositories, migrations, transaction behavior, validation errors, and SSE streaming. Replace external AI calls with deterministic fakes in the regular test suite.

## Architecture and AI Boundaries

Calculate affordability, repayments, and risk metrics in deterministic domain services. Pydantic AI may retrieve approved data and explain results, but must not invent authoritative financial values. Use typed dependencies and structured outputs, persist conversation records in PostgreSQL, and keep provider-specific code behind an adapter. FastAPI routes should validate and delegate rather than contain business logic.

## Style and Migrations

Use four-space indentation, type hints, `snake_case` functions/modules, and `PascalCase` classes. Prefer async consistently across FastAPI, database access, and AI calls. Every schema change requires an Alembic migration, an upgrade test where practical, and downgrade consideration; never edit an applied migration.
