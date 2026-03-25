# Coworking Booking Backend

Backend skeleton for the coworking booking system.

## Stack

- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy 2.x async
- Alembic
- Poetry
- Docker / Docker Compose

## Local run

1. Copy `.env.example` to `.env`.
2. Start infrastructure:

```bash
docker compose up --build
```

3. Open:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Live health: `http://localhost:8000/health/live`
- Ready health: `http://localhost:8000/health/ready`

4. Seed RBAC data:

```bash
poetry run python -m app.scripts.seed_rbac
```

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
# desmobapp-backend
