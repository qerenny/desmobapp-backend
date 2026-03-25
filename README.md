# Coworking Booking Backend

Backend for the coworking booking system.

## Stack

- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy 2.x async
- Alembic
- Poetry
- Docker / Docker Compose

## Local run

1. Copy `.env.example` to `.env`.
2. Install dependencies:

```bash
make install
```

3. Start PostgreSQL:

```bash
make up
```

4. Apply migrations:

```bash
make migrate
```

5. Seed RBAC data:

```bash
make seed-rbac
```

6. Start API:

```bash
make run
```

7. Open:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Live health: `http://localhost:8000/health/live`
- Ready health: `http://localhost:8000/health/ready`

## Developer commands

```bash
make lint
make lint-fix
make test
make compile
make check
```

## CI

GitHub Actions workflow lives in `.github/workflows/ci.yml`.
It runs:

- Alembic migrations
- RBAC seed
- `compileall`
- `ruff check`
- `pytest -q`

## Project layout

```text
app/
  api/
  core/
  db/
  schemas/
  services/
  repositories/
  tasks/
alembic/
tests/
```
