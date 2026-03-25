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

## 3.1 Быстрый старт через Postman

Если фронт нужно быстро отлаживать без ручной сборки запросов, используй готовые файлы:

- [docs/postman_collection.json](/Users/qerenny/Library/Mobile Documents/com~apple~CloudDocs/Documents/ITMO/DesMobAndNetApps/backend/docs/postman_collection.json)
- [docs/postman_environment.json](/Users/qerenny/Library/Mobile Documents/com~apple~CloudDocs/Documents/ITMO/DesMobAndNetApps/backend/docs/postman_environment.json)

Что сделать в Postman:

1. Import collection
2. Import environment
3. Выбрать environment `Coworking Backend Local`
4. Выполнить `Diagnostics / Health Ready`
5. Выполнить `Auth / Login Demo Client`
6. Выполнить `Auth / Login Demo Admin`

Коллекция после этого сама сохраняет:

- `accessToken`
- `adminAccessToken`
- `venueId`
- `roomId`
- `seatId`
- `holdId`
- `bookingId`
- `transactionId`

И также автоматически генерирует:

- `bookingDate`
- `holdStartTime`
- `holdEndTime`
- `analyticsStartDate`
- `analyticsEndDate`

Время внутри коллекции уже подобрано под seeded demo-расписание:

- `10:00-11:00` по `Europe/Moscow`
- это `07:00-08:00Z`

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

## 8.1 Рекомендуемый порядок запросов в Postman

Для клиентского сценария:

1. `Auth / Login Demo Client`
2. `Browse / Get Venues`
3. `Browse / Get Venue Details`
4. `Browse / Get Venue Rooms`
5. `Browse / Get Room Seats`
6. `Booking Flow / Get Availability`
7. `Booking Flow / Create Hold`
8. `Booking Flow / Create Booking`
9. `Booking Flow / Get Booking`
10. `Booking Flow / Check In Booking`
11. `Booking Flow / Mock Payment`
12. `Booking Flow / Update Notification Preferences`
13. `Booking Flow / Cancel Booking`

Для admin-сценария:

1. `Auth / Login Demo Admin`
2. `Admin / Get Occupancy Analytics`
3. `Admin / Create Venue`
4. `Admin / Update Room Layout`

Особенности:

- `Cancel Hold (Optional)` запускается только если нужно отменить hold до создания booking
- `Update Room Layout` добавляет новое место в уже выбранную room, поэтому перед ним надо хотя бы один раз выполнить `Browse / Get Venue Rooms`
- `Register Random User` нужен только для ручных тестов регистрации, для основной demo-цепочки он не нужен

## 9. Примеры запросов

Если используешь Postman-коллекцию, эти body уже лежат внутри запросов и подставляются автоматически.

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

В Postman это автоматизировано:

- после `Get Venues` сохраняется первый `venueId`
- после `Get Venue Rooms` сохраняется первый `roomId`
- после `Get Room Seats` сохраняется первый `seatId`
- после `Create Hold` сохраняется `holdId`
- после `Create Booking` сохраняется `bookingId`
- после `Mock Payment` сохраняется `transactionId`

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

## 13. Postman

Для фронтендера уже подготовлены:

- [docs/postman_collection.json](/Users/qerenny/Library/Mobile Documents/com~apple~CloudDocs/Documents/ITMO/DesMobAndNetApps/backend/docs/postman_collection.json)
- [docs/postman_environment.json](/Users/qerenny/Library/Mobile Documents/com~apple~CloudDocs/Documents/ITMO/DesMobAndNetApps/backend/docs/postman_environment.json)

Что умеет коллекция:

- покрывать весь текущий `P0`-контракт из `swagger.yaml`, который реально нужен фронту
- логинить `client` и `admin`
- автоматически сохранять `accessToken`, `adminAccessToken`
- автоматически сохранять `venueId`, `roomId`, `seatId`, `holdId`, `bookingId`, `transactionId`
- автоматически считать `bookingDate`, `holdStartTime`, `holdEndTime` на следующий день
- отдельно прогонять `Browse`, `Booking Flow`, `Admin`
- запускать happy path без ручного копирования body и UUID между запросами

Рекомендуемый порядок запуска в Postman:

1. Import collection
2. Import environment
3. Выбрать environment `Coworking Backend Local`
4. Выполнить `Diagnostics / Health Ready`
5. Выполнить `Auth / Login Demo Client`
6. Выполнить `Auth / Login Demo Admin`
7. Выполнить папку `Browse`
8. Выполнить папку `Booking Flow`
9. При необходимости выполнить папку `Admin`

Если frontend работает не на `localhost:8000`, надо поменять только `baseUrl` в environment.

## 14. Что пойдёт следующим этапом

Это ещё не готово для фронта, но будет полезно позже:

- `refresh/logout/me`
- список бронирований пользователя
- управление пользователями и ролями
- invites flow
- более богатая аналитика
- реальные платежи
