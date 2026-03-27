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

Чек-лист для ручной проверки backend лежит в:

`docs/manual_test_checklist.md`

Сводка всего реализованного backend лежит в:

`docs/implemented_backend_features.md`

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

Что уже доступно сверх базового happy path:

- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /me`
- `PATCH /me`
- `GET /me/bookings`
- `GET /bookings/history`
- `PATCH /bookings/{bookingId}/reschedule`
- `POST /bookings/{bookingId}/repeat`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /notifications`
- `POST /devices/push-tokens`
- `GET /rooms/{roomId}`
- `GET /features`
- `GET /room-hours/{roomId}`
- `GET /tariffs`
- `GET /booking-rules/{scope}`
- `GET /payments/{paymentId}`
- `POST /payments/{paymentId}/capture`
- `POST /payments/{paymentId}/refund`
- `POST /payments/webhooks/{provider}`

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

## Additional Settings

In `.env.example` you can also tune:

- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`

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
