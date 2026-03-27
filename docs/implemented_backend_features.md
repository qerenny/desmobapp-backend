# Implemented Backend Features

Актуальная сводка того, что уже реализовано в backend на текущий момент.

Документ нужен как быстрый статус проекта:

- что уже написано;
- что реально работает;
- что покрыто тестами;
- что пока остаётся следующим этапом.

## 1. Infrastructure

Реализовано:

- FastAPI backend
- PostgreSQL + PostGIS
- SQLAlchemy 2.x async
- Alembic migrations
- Dockerfile
- `docker-compose.yml`
- `.env.example`
- health checks
- logging
- OpenAPI metadata
- CORS configuration

## 2. P0 API from `swagger.yaml`

Полностью реализовано:

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Space browsing
- `GET /venues`
- `GET /venues/{venueId}`
- `GET /venues/{venueId}/rooms`
- `GET /rooms/{roomId}/seats`

### Booking flow
- `GET /availability`
- `POST /holds`
- `DELETE /holds/{holdId}`
- `POST /bookings`
- `GET /bookings/{bookingId}`
- `DELETE /bookings/{bookingId}`
- `POST /bookings/{bookingId}/checkin`

### Payments
- `POST /payments`

Примечание:
- payment flow сейчас `mock only`

### Notifications
- `PUT /notifications/preferences`

### Admin
- `POST /admin/venues`
- `PUT /admin/rooms/{roomId}/layout`
- `GET /admin/analytics/occupancy`

## 3. P1 User-Facing Integration

Реализовано:

### Session
- `POST /auth/refresh`
- `POST /auth/logout`

Что делает:

- refresh token валидируется через БД
- logout ревокает refresh token
- refresh использует rotation: старый refresh revoke, новый refresh выдаётся заново

### Current user profile
- `GET /me`
- `PATCH /me`

Совместимые backend aliases:

- `GET /auth/me`
- `PATCH /users/me`

### User bookings
- `GET /me/bookings`

Поддержано:

- `status`
- `dateFrom`
- `dateTo`
- `page`
- `limit`

Совместимый alias:

- `GET /bookings`

### Notification preferences
- `GET /notifications/preferences`
- `PUT /notifications/preferences`

### Favorites
- `GET /favorites`
- `POST /favorites`
- `DELETE /favorites/{venueId}`

Текущий scope:

- избранное только для `venue`

## 4. Auth / Security / Access

Реализовано:

- password hashing
- JWT access tokens
- refresh tokens в БД
- forgot/reset password flow
- проверка `User.status`
- RBAC roles and permissions
- `client` роль назначается при регистрации
- `admin` routes защищены permission checks

## 5. Booking Logic

Реализовано:

- availability calculation
- hold creation/cancel
- booking creation/get/cancel
- booking history
- booking reschedule
- repeat booking
- hold to booking conversion
- check-in
- conflict detection между holds и bookings
- учёт room hours
- учёт booking rules

## 6. Payments

Реализовано:

- `POST /payments`
- `GET /payments/{paymentId}`
- `POST /payments/{paymentId}/capture`
- `POST /payments/{paymentId}/refund`
- `POST /payments/webhooks/{provider}`

Ограничение:

- всё по-прежнему `mock only`

## 7. Notifications

Реализовано:

- хранение notification preferences
- чтение notification preferences
- inbox `GET /notifications`
- push device registration
- удаление push device
- создание notification records на booking/payment/auth события

Пока не реализовано:

- delivery pipeline
- реальные email/push провайдеры
- background retries

## 8. Space Configuration Read API

Реализовано:

- `GET /rooms/{roomId}`
- `GET /features`
- `GET /room-hours/{roomId}`
- `GET /tariffs`
- `GET /booking-rules/{scope}`

## 9. Favorites

Реализовано:

- таблица `favorite_venues`
- добавление venue в избранное
- получение списка избранных venue
- удаление venue из избранного

## 10. Seed / Demo / Frontend Support

Реализовано:

- `seed_rbac`
- `seed_demo`
- demo-аккаунты
- demo venue / rooms / seats
- frontend handoff doc
- manual QA checklist
- Postman collection and environment

Документы:

- `docs/frontend_handoff.md`
- `docs/manual_test_checklist.md`
- `docs/postman_collection.json`
- `docs/postman_environment.json`

## 11. Tests and Tooling

Реализовано:

- `pytest`
- `ruff`
- `pre-commit`
- `Makefile`
- GitHub Actions CI

Автотестами покрыто:

- P0 contract smoke
- RBAC / space endpoints
- booking flow
- refresh / logout / me / notifications GET
- bookings list
- favorites
- forgot/reset password
- booking history / reschedule / repeat
- notification inbox / push devices
- room/features/tariffs/booking-rules read endpoints
- payment get / capture / refund / webhook mock extensions

## 12. What Is Still Next

Следующим этапом остаётся:

- admin users / roles / invites
- room hours / tariffs / booking rules admin endpoints
- admin notifications send
- admin bookings list / calendar / status updates
- richer analytics
- audit log endpoints

## 13. Current Known Constraints

- payments работают только в mock-режиме
- favorites пока только для venue
- logout работает по `refreshToken`, а не по access token
- password reset token в non-production сейчас возвращается в API-ответе для удобства разработки
- delivery pipeline уведомлений пока не отправляет реальные email/push
