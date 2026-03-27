# Manual Test Checklist

Документ для ручной проверки всего текущего MVP backend.

Цель:

- проверить, что backend запускается
- проверить, что все `P0`-эндпоинты из `docs/swagger.yaml` работают
- проверить, что текущие `P1` user-facing эндпоинты работают
- проверить, что текущие `P2` pre-admin эндпоинты работают
- проверить happy path и основные негативные сценарии
- проверить роли, авторизацию и mock-функциональность

## 1. Что нужно перед началом

Должны быть установлены:

- Docker
- Poetry
- Postman

Backend должен запускаться так:

```bash
make install
make up
make migrate
make seed-rbac
make seed-demo
make run
```

После запуска должны открываться:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Для ручного тестирования через Postman используй:

- `docs/postman_collection.json`
- `docs/postman_environment.json`

Environment в Postman:

- `Coworking Backend Local`

## 2. Тестовые аккаунты

После `make seed-demo` должны существовать:

- `demo.client@example.com`
- `demo.admin@example.com`
- `demo.manager@example.com`
- `demo.owner@example.com`
- `demo.support@example.com`
- `demo.billing@example.com`
- `demo.auditor@example.com`

Пароль у всех:

`demo12345`

## 3. Что должно быть в demo-данных

Должен существовать venue:

- `Demo Frontend Coworking`

Должны существовать rooms:

- `Open Space A`
- `Meeting Room B`

Должны существовать seats:

- для `Open Space A`: `A-1` ... `A-6`
- для `Meeting Room B`: `B-1` ... `B-4`

Должны быть правила:

- рабочее время каждый день `09:00-21:00`
- hold TTL `900` секунд
- mock payment доступен

## 4. Smoke Check

### 4.1 Liveness

- Открыть `GET /health/live`
- Ожидание: `200 OK`

### 4.2 Readiness

- Открыть `GET /health/ready`
- Ожидание: `200 OK`

### 4.3 Swagger

- Открыть `/docs`
- Ожидание: Swagger UI открывается без ошибок

## 5. Подготовка Postman

### 5.1 Import

- Import `docs/postman_collection.json`
- Import `docs/postman_environment.json`
- Выбрать environment `Coworking Backend Local`

### 5.2 Проверка стартовых запросов

Выполнить:

1. `Diagnostics / Health Ready`
2. `Auth / Login Demo Client`
3. `Auth / Login Demo Admin`

Ожидание:

- `Health Ready` возвращает `200`
- `Login Demo Client` возвращает `200`
- `Login Demo Admin` возвращает `200`

После логина должны автоматически заполниться переменные коллекции:

- `accessToken`
- `adminAccessToken`
- `bookingDate`
- `holdStartTime`
- `holdEndTime`

## 6. Полный happy path клиента

Этот блок проверяет основной MVP-сценарий.

### 6.1 Login

Эндпоинт:

- `POST /auth/login`

Шаг:

- выполнить `Auth / Login Demo Client`

Ожидание:

- статус `200`
- в response есть `accessToken`
- в response есть `refreshToken`
- в response есть `user.id`, `user.email`, `user.name`

### 6.2 Получить список площадок

Эндпоинт:

- `GET /venues`

Шаг:

- выполнить `Browse / Get Venues`

Ожидание:

- статус `200`
- приходит массив
- в массиве есть `Demo Frontend Coworking`
- автоматически сохраняется `venueId`

### 6.3 Получить детали площадки

Эндпоинт:

- `GET /venues/{venueId}`

Шаг:

- выполнить `Browse / Get Venue Details`

Ожидание:

- статус `200`
- `id` совпадает с `venueId`
- есть `name`, `address`, `timezone`, `rooms`

### 6.4 Получить комнаты площадки

Эндпоинт:

- `GET /venues/{venueId}/rooms`

Шаг:

- выполнить `Browse / Get Venue Rooms`

Ожидание:

- статус `200`
- приходит массив комнат
- автоматически сохраняется `roomId`

### 6.5 Получить места комнаты

Эндпоинт:

- `GET /rooms/{roomId}/seats`

Шаг:

- выполнить `Browse / Get Room Seats`

Ожидание:

- статус `200`
- приходит массив мест
- автоматически сохраняется `seatId`

### 6.6 Проверить availability

Эндпоинт:

- `GET /availability`

Шаг:

- выполнить `Booking Flow / Get Availability`

Ожидание:

- статус `200`
- есть `date`
- есть массив `timeSlots`
- хотя бы один slot имеет `available=true`

### 6.7 Создать hold

Эндпоинт:

- `POST /holds`

Шаг:

- выполнить `Booking Flow / Create Hold`

Ожидание:

- статус `201`
- в response есть `id`
- в response есть `status`
- автоматически сохраняется `holdId`

### 6.8 Создать booking

Эндпоинт:

- `POST /bookings`

Шаг:

- выполнить `Booking Flow / Create Booking`

Ожидание:

- статус `201`
- в response есть `id`
- `holdId` совпадает с созданным hold
- автоматически сохраняется `bookingId`

### 6.9 Получить booking

Эндпоинт:

- `GET /bookings/{bookingId}`

Шаг:

- выполнить `Booking Flow / Get Booking`

Ожидание:

- статус `200`
- `id` совпадает с `bookingId`
- присутствуют `status`, `startTime`, `endTime`

### 6.10 Check-in

Эндпоинт:

- `POST /bookings/{bookingId}/checkin`

Шаг:

- выполнить `Booking Flow / Check In Booking`

Ожидание:

- статус `200`
- в response есть `bookingId`
- `bookingId` совпадает с текущим booking

### 6.11 Mock payment

Эндпоинт:

- `POST /payments`

Шаг:

- выполнить `Booking Flow / Mock Payment`

Ожидание:

- статус `201`
- в response есть `id`
- `status` равен `captured`
- сохраняется `transactionId`

### 6.12 Notification preferences

Эндпоинт:

- `PUT /notifications/preferences`

Шаг:

- выполнить `Booking Flow / Update Notification Preferences`

Ожидание:

- статус `200`
- в response есть `message`

### 6.13 Cancel booking

Эндпоинт:

- `DELETE /bookings/{bookingId}`

Шаг:

- выполнить `Booking Flow / Cancel Booking`

Ожидание:

- статус `204`
- body пустой

### 6.14 Повторно проверить availability после отмены

Эндпоинт:

- `GET /availability`

Шаг:

- снова выполнить `Booking Flow / Get Availability`

Ожидание:

- статус `200`
- slot на выбранное время снова доступен

## 7. Проверка admin-функций

### 7.1 Login admin

Эндпоинт:

- `POST /auth/login`

Шаг:

- выполнить `Auth / Login Demo Admin`

Ожидание:

- статус `200`
- сохранён `adminAccessToken`

### 7.2 Occupancy analytics

Эндпоинт:

- `GET /admin/analytics/occupancy`

Шаг:

- выполнить `Admin / Get Occupancy Analytics`

Ожидание:

- статус `200`
- есть `period.startDate`
- есть `period.endDate`
- есть `occupancyRate`
- есть `totalBookings`
- есть `revenue`

### 7.3 Create venue

Эндпоинт:

- `POST /admin/venues`

Шаг:

- выполнить `Admin / Create Venue`

Ожидание:

- статус `201`
- создаётся новый venue
- в response есть `id`
- сохраняется `createdVenueId`

### 7.4 Update room layout

Эндпоинт:

- `PUT /admin/rooms/{roomId}/layout`

Шаг:

- выполнить `Admin / Update Room Layout`

Ожидание:

- статус `200`
- в response есть массив `seats`
- в room появляется новое место

## 7A. Проверка P1 mobile integration

### 7A.1 Get current profile

Эндпоинт:

- `GET /me`

Шаг:

- отправить запрос с валидным `Authorization: Bearer <token>`

Ожидание:

- статус `200`
- в response есть `id`, `email`, `name`, `phone`

### 7A.2 Update current profile

Эндпоинт:

- `PATCH /me`

Шаг:

- отправить `name` и/или `phone`

Ожидание:

- статус `200`
- response содержит обновлённые поля

### 7A.3 Get current user bookings

Эндпоинт:

- `GET /me/bookings`

Шаг:

- выполнить после создания хотя бы одного booking

Ожидание:

- статус `200`
- в response есть `items`, `page`, `limit`, `total`
- в `items` присутствует созданный booking

### 7A.4 Get notification preferences

Эндпоинт:

- `GET /notifications/preferences`

Шаг:

- отправить запрос после логина

Ожидание:

- статус `200`
- в response есть `emailNotifications`, `pushNotifications`, `reminderBeforeBooking`, `promotionalEmails`

### 7A.5 Refresh session

Эндпоинт:

- `POST /auth/refresh`

Шаг:

- отправить валидный `refreshToken`, полученный при login

Ожидание:

- статус `200`
- возвращаются новый `accessToken` и новый `refreshToken`

### 7A.6 Logout session

Эндпоинт:

- `POST /auth/logout`

Шаг:

- отправить актуальный `refreshToken`

Ожидание:

- статус `200`
- повторный `POST /auth/refresh` с этим же токеном возвращает `401`

### 7A.7 Favorites flow

Эндпоинты:

- `GET /favorites`
- `POST /favorites`
- `DELETE /favorites/{venueId}`

Шаг:

1. выполнить `GET /favorites`
2. добавить venue в избранное через `POST /favorites`
3. снова выполнить `GET /favorites`
4. удалить venue через `DELETE /favorites/{venueId}`
5. снова выполнить `GET /favorites`

Ожидание:

- первый `GET` возвращает массив
- `POST` возвращает `201`
- второй `GET` содержит добавленный venue
- `DELETE` возвращает `204`
- финальный `GET` больше не содержит этот venue

## 7B. Проверка P2 pre-admin user flows

### 7B.1 Forgot password

Эндпоинт:

- `POST /auth/forgot-password`

Шаг:

- отправить email существующего пользователя

Ожидание:

- статус `200`
- в response есть `message`
- в dev-режиме есть `resetToken`

### 7B.2 Reset password

Эндпоинт:

- `POST /auth/reset-password`

Шаг:

1. взять `resetToken` из предыдущего шага
2. отправить новый пароль
3. попробовать `POST /auth/refresh` со старым refresh token
4. выполнить `POST /auth/login` с новым паролем

Ожидание:

- reset возвращает `200`
- старый refresh token больше не работает и даёт `401`
- login с новым паролем возвращает `200`

### 7B.3 Booking history

Эндпоинт:

- `GET /bookings/history`

Шаг:

1. создать booking
2. отменить booking
3. выполнить `GET /bookings/history`

Ожидание:

- статус `200`
- в `items` присутствует отменённый booking

### 7B.4 Reschedule booking

Эндпоинт:

- `PATCH /bookings/{bookingId}/reschedule`

Шаг:

- отправить новый `startTime/endTime` для активного booking

Ожидание:

- статус `200`
- `startTime` и `endTime` изменились

### 7B.5 Repeat booking

Эндпоинт:

- `POST /bookings/{bookingId}/repeat`

Шаг:

- отправить новый `startTime/endTime` для уже существующего booking

Ожидание:

- статус `200`
- возвращается новый booking с новым `id`

### 7B.6 Notification inbox

Эндпоинт:

- `GET /notifications`

Шаг:

- выполнить запрос после booking/payment/auth действий

Ожидание:

- статус `200`
- есть `items`, `page`, `limit`, `total`
- в `items` видны хотя бы события `booking_created` или `payment_captured`

### 7B.7 Push devices

Эндпоинты:

- `POST /devices/push-tokens`
- `DELETE /devices/push-tokens/{deviceId}`

Шаг:

1. зарегистрировать новый `pushToken`
2. удалить созданный device

Ожидание:

- `POST` возвращает `201`
- в response есть `id`
- `DELETE` возвращает `204`

### 7B.8 Space read-only configuration

Эндпоинты:

- `GET /rooms/{roomId}`
- `GET /features`
- `GET /room-hours/{roomId}`
- `GET /tariffs`
- `GET /booking-rules/{scope}`

Шаг:

- выполнить запросы для seeded demo-room

Ожидание:

- все ручки возвращают `200`
- room содержит `seats`
- `features` возвращает массив
- `room-hours` возвращает расписание
- `tariffs` возвращает массив тарифов или пустой массив, но без ошибки
- `booking-rules` возвращает объект правил

### 7B.9 Payment extensions

Эндпоинты:

- `GET /payments/{paymentId}`
- `POST /payments/{paymentId}/capture`
- `POST /payments/{paymentId}/refund`
- `POST /payments/webhooks/{provider}`

Шаг:

1. создать mock payment через `POST /payments`
2. получить payment по `id`
3. выполнить `capture`
4. выполнить `refund`
5. отправить mock webhook

Ожидание:

- `GET` возвращает `200`
- `capture` возвращает `200`
- `refund` возвращает `200`
- webhook возвращает `200`

## 8. Проверка auth и security

### 8.1 Register new user

Эндпоинт:

- `POST /auth/register`

Шаг:

- выполнить `Auth / Register Random User`

Ожидание:

- статус `201`
- в response есть `id`
- в response есть `email`

### 8.2 Login with wrong password

Эндпоинт:

- `POST /auth/login`

Шаг:

- вручную отправить неверный пароль через Swagger или Postman

Ожидание:

- статус `401`

### 8.3 Register duplicate email

Эндпоинт:

- `POST /auth/register`

Шаг:

- повторно зарегистрировать уже существующий email

Ожидание:

- статус `409`

### 8.4 Access business endpoint without token

Эндпоинт:

- `GET /venues`

Шаг:

- отправить запрос без `Authorization`

Ожидание:

- статус `401`

### 8.5 Access admin endpoint as client

Эндпоинт:

- `POST /admin/venues`

Шаг:

- выполнить admin-запрос с `accessToken` обычного клиента

Ожидание:

- статус `403`

## 9. Проверка негативных бизнес-кейсов

### 9.1 Повторный hold на тот же слот

Эндпоинт:

- `POST /holds`

Шаг:

1. создать hold
2. не удаляя его, повторить тот же запрос ещё раз

Ожидание:

- второй запрос возвращает `409`

### 9.2 Booking с невалидным hold

Эндпоинт:

- `POST /bookings`

Шаг:

- отправить booking с несуществующим или уже неактивным `holdId`

Ожидание:

- статус `400`

### 9.3 Payment для несуществующего booking

Эндпоинт:

- `POST /payments`

Шаг:

- отправить случайный `bookingId`

Ожидание:

- статус `404`

### 9.4 Analytics с плохим диапазоном дат

Эндпоинт:

- `GET /admin/analytics/occupancy`

Шаг:

- передать `endDate < startDate`

Ожидание:

- статус `400`

### 9.5 Availability с невалидным запросом

Эндпоинт:

- `GET /availability`

Шаг:

- не передать обязательный идентификатор ресурса или передать некорректную комбинацию параметров

Ожидание:

- статус `400`

## 10. Проверка Swagger UI

Нужно вручную проверить:

- все `P0`-эндпоинты видны в `/docs`
- для каждого эндпоинта видны request/response schema
- protected-ручки реально работают после нажатия `Authorize`

Минимальный список, который надо открыть в Swagger:

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
- `GET /payments/{paymentId}`
- `POST /payments/{paymentId}/capture`
- `POST /payments/{paymentId}/refund`
- `POST /payments/webhooks/{provider}`
- `PUT /notifications/preferences`
- `GET /notifications/preferences`
- `GET /notifications`
- `POST /devices/push-tokens`
- `DELETE /devices/push-tokens/{deviceId}`
- `GET /me`
- `PATCH /me`
- `GET /me/bookings`
- `GET /bookings/history`
- `PATCH /bookings/{bookingId}/reschedule`
- `POST /bookings/{bookingId}/repeat`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /rooms/{roomId}`
- `GET /features`
- `GET /room-hours/{roomId}`
- `GET /tariffs`
- `GET /booking-rules/{scope}`
- `POST /admin/venues`
- `PUT /admin/rooms/{roomId}/layout`
- `GET /admin/analytics/occupancy`

## 11. Финальный acceptance checklist

Считать MVP проверенным, если выполнены все пункты:

- backend поднимается без ручных правок
- health endpoints возвращают `200`
- demo seed создаёт пользователей и тестовые данные
- Postman happy path проходит от логина до mock payment
- booking можно отменить
- после отмены availability снова показывает слот свободным
- refresh/logout работают корректно
- forgot/reset password работают корректно
- профиль пользователя читается и обновляется
- список собственных bookings читается
- history/reschedule/repeat работают
- favorites flow работает
- inbox уведомлений и push devices работают
- read-only space config endpoints работают
- payment mock extensions работают
- клиент не может ходить в admin endpoints
- admin может выполнять admin endpoints
- негативные сценарии возвращают корректные `4xx`
- Swagger UI открывается и показывает актуальный контракт

## 12. Если что-то сломалось

Что проверить первым:

1. запущен ли Docker
2. выполнены ли `make migrate`, `make seed-rbac`, `make seed-demo`
3. выбран ли правильный Postman environment
4. есть ли `accessToken` и `adminAccessToken`
5. не остались ли старые `holdId`, `bookingId`, `roomId`, `seatId`

Если переменные в Postman устарели, проще всего:

1. заново выполнить логины
2. заново пройти `Browse`
3. заново пройти `Booking Flow`
