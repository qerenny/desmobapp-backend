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
make precommit-install
make precommit-run
```

## Demo data for frontend

```bash
make seed-demo
```

Подробная инструкция для фронтендера лежит в:

`docs/frontend_handoff.md`

Postman-файлы для быстрого API flow:

- `docs/postman_collection.json`
- `docs/postman_environment.json`

Быстрый сценарий в Postman:

1. Import оба файла
2. Выбрать environment `Coworking Backend Local`
3. Выполнить `Auth / Login Demo Client`
4. Выполнить `Browse / Get Venues -> Get Venue Rooms -> Get Room Seats`
5. Выполнить `Booking Flow / Get Availability -> Create Hold -> Create Booking`

Коллекция сама сохраняет токены и основные `id` из ответов.

Скрипт создаёт:

- demo-аккаунты с разными ролями
- готовое demo venue
- комнаты, места, room hours и booking rules

Единый пароль для demo-аккаунтов:

`demo12345`

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
