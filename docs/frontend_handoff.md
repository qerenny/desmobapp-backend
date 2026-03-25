# Frontend Handoff

Документ для фронтенд-разработчика: как поднять backend, чем он уже умеет пользоваться, какие есть demo-данные и какими маршрутами можно закрыть MVP-сценарии.

## 1. Что уже готово

Сейчас backend уже реализует весь `P0`-контракт из `docs/swagger.yaml`:

- `POST /auth/register`
- `POST /auth/login`
- `GET /venues`
- `GET /venues/{venueId}`
- `GET /venues/{venueId}/rooms`
- `GET /rooms/{roomId}/seats`
- `GET /availability`
- `POST /holds`
- `DELETE /holds/{holdId}`
- `POST /bookings`
- `GET /bookings/{bookingId}`
- `DELETE /bookings/{bookingId}`
- `POST /bookings/{bookingId}/checkin`
- `POST /payments`
- `PUT /notifications/preferences`
- `POST /admin/venues`
- `PUT /admin/rooms/{roomId}/layout`
- `GET /admin/analytics/occupancy`

Дополнительно:

- `/docs`
- `/openapi.json`
- `/health/live`
- `/health/ready`

## 2. Важные текущие ограничения

- `payments` сейчас mock, реального провайдера нет
- `check-in` сейчас MVP-уровня: без полноценной валидации геозоны и реального QR
- `analytics` сейчас базовая загрузка помещений, без сложной бизнес-аналитики
- `refresh/logout/me` пока ещё не реализованы, это следующий этап

## 3. Быстрый запуск backend

```bash
make install
make up
make migrate
make seed-rbac
make seed-demo
make run
```

После запуска:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 4. CORS для фронта

В `.env` уже включены стандартные dev-origin:

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

Если фронт будет запускаться с другого origin, нужно просто добавить его в `CORS_ORIGINS`.

## 5. Demo-аккаунты

После `make seed-demo` доступны такие пользователи.

Пароль у всех одинаковый:

`demo12345`

Аккаунты:

- `demo.client@example.com` — обычный клиент
- `demo.admin@example.com` — глобальный admin
- `demo.manager@example.com` — venue-scoped manager
- `demo.owner@example.com` — venue-scoped owner
- `demo.support@example.com` — support
- `demo.billing@example.com` — billing
- `demo.auditor@example.com` — auditor

## 6. Demo-данные для UI

После `make seed-demo` в базе уже есть готовое пространство для интерфейса:

- venue: `Demo Frontend Coworking`
- address: `Saint Petersburg, Kronverkskiy pr. 49`
- timezone: `Europe/Moscow`

Features:

- `Wi-Fi`
- `Coffee`
- `Meeting Rooms`
- `Parking`
- `Silent Zone`

Rooms:

- `Open Space A`
- `Meeting Room B`

Seats:

- `Open Space A`: `A-1`, `A-2`, `A-3`, `A-4`, `A-5`, `A-6`
- `Meeting Room B`: `B-1`, `B-2`, `B-3`, `B-4`

Рабочие часы:

- каждый день с `09:00` до `21:00` по `Europe/Moscow`

Правила бронирования:

- venue-level: `30..480` минут
- meeting room: `60..180` минут
- hold TTL: `900` секунд
- оплата не обязательна, но mock payment доступен

## 7. Что можно строить на фронте уже сейчас

### 7.1 Auth flow

- экран регистрации
- экран логина
- хранение `accessToken`
- авторизованные запросы через `Authorization: Bearer <token>`

### 7.2 Browse flow

- список помещений
- карточка помещения
- список комнат помещения
- схема мест комнаты

Базовый маршрутный сценарий:

1. `GET /venues`
2. `GET /venues/{venueId}`
3. `GET /venues/{venueId}/rooms`
4. `GET /rooms/{roomId}/seats`

### 7.3 Booking flow

Полный MVP-сценарий бронирования уже можно собрать:

1. `GET /availability`
2. `POST /holds`
3. `POST /bookings`
4. `GET /bookings/{bookingId}`
5. `POST /bookings/{bookingId}/checkin`
6. `POST /payments`
7. `DELETE /bookings/{bookingId}` при отмене

### 7.4 Profile settings

Можно сделать экран уведомлений:

- `PUT /notifications/preferences`

### 7.5 Admin flow

Для `demo.admin@example.com` уже можно строить admin UI:

1. `POST /admin/venues`
2. `PUT /admin/rooms/{roomId}/layout`
3. `GET /admin/analytics/occupancy`

## 8. Рекомендуемый happy path для фронта

Если нужно быстро собрать demo:

1. Логин под `demo.client@example.com`
2. Загрузить `GET /venues`
3. Открыть `Demo Frontend Coworking`
4. Получить rooms и seats
5. Проверить `GET /availability` для одного seat
6. Создать `hold`
7. Создать `booking`
8. Открыть карточку бронирования
9. Выполнить `check-in`
10. Выполнить mock `payment`

Для admin-demo:

1. Логин под `demo.admin@example.com`
2. Открыть occupancy analytics
3. Создать новое venue
4. Обновить layout у комнаты

## 9. Примеры запросов

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "demo.client@example.com",
  "password": "demo12345"
}
```

### Availability

`date` должен быть локальной датой площадки, а не timestamp.

Пример:

```http
GET /availability?level=seat&seatId=<seat-id>&date=2026-03-30&durationMinutes=60
Authorization: Bearer <accessToken>
```

### Hold

```http
POST /holds
Authorization: Bearer <accessToken>
Content-Type: application/json

{
  "level": "seat",
  "seatId": "<seat-id>",
  "startTime": "2026-03-30T07:00:00Z",
  "endTime": "2026-03-30T08:00:00Z"
}
```

### Booking

```http
POST /bookings
Authorization: Bearer <accessToken>
Content-Type: application/json

{
  "level": "seat",
  "seatId": "<seat-id>",
  "holdId": "<hold-id>",
  "startTime": "2026-03-30T07:00:00Z",
  "endTime": "2026-03-30T08:00:00Z"
}
```

### Mock payment

```http
POST /payments
Authorization: Bearer <accessToken>
Content-Type: application/json

{
  "bookingId": "<booking-id>",
  "amountCents": 1500,
  "currency": "RUB",
  "provider": "mock"
}
```

## 10. Как фронту получать актуальные IDs

Backend не требует ручного копирования UUID из базы.

Рабочая цепочка такая:

1. взять `venueId` из `GET /venues`
2. взять `roomId` из `GET /venues/{venueId}` или `GET /venues/{venueId}/rooms`
3. взять `seatId` из `GET /rooms/{roomId}/seats`
4. взять `holdId` из `POST /holds`
5. взять `bookingId` из `POST /bookings`

## 11. Что важно учитывать на фронте

- почти все бизнес-ручки требуют bearer token
- без токена backend вернёт `401`
- у неактивного пользователя будет `403`
- ошибки отдаются в формате:

```json
{
  "detail": "..."
}
```

или для validation errors:

```json
{
  "detail": [
    ...
  ]
}
```

## 12. Полезные команды для разработчиков

```bash
make lint
make test
make check
make precommit-install
make precommit-run
```

## 13. Что пойдёт следующим этапом

Это ещё не готово для фронта, но будет полезно позже:

- `refresh/logout/me`
- список бронирований пользователя
- управление пользователями и ролями
- invites flow
- более богатая аналитика
- реальные платежи
