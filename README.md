# Tutoring Platform — Система управления образовательной платформой (репетиторство)
# Tutoring Platform — Система управления образовательной платформой (репетиторство)

Распределённая микросервисная система для организации онлайн-репетиторства: поиск преподавателей, запись на занятия, управление расписанием, оплата, отзывы и аналитика.

Проект выполнен в рамках лабораторных работ по курсу проектирования архитектуры программных систем.

## Описание проекта

Система автоматизирует процессы онлайн-репетиторства:

- **Ученики** ищут преподавателей по предмету, рейтингу и цене, записываются на занятия, оплачивают их и оставляют отзывы.
- **Преподаватели** управляют профилем, расписанием, проводят занятия и отслеживают отзывы.
- **Администратор** управляет пользователями, предметами и анализирует агрегированные показатели платформы.

### Ключевые бизнес-процессы

1. Регистрация и аутентификация пользователей.
2. Создание и обновление профиля преподавателя.
3. Формирование расписания преподавателя.
4. Поиск преподавателей по предмету, рейтингу и стоимости.
5. Запись ученика на занятие.
6. Оплата занятия.
7. Отмена и перенос занятий.
8. Проведение занятия и фиксация результата.
9. Добавление отзывов и формирование рейтингов.
10. Отправка уведомлений.
11. Формирование аналитики по занятиям, доходам и оценкам.

### Роли пользователей

| Роль | Возможности |
|---|---|
| **Ученик** | Поиск преподавателей, запись, оплата, отзывы, уведомления |
| **Преподаватель** | Профиль, расписание, проведение занятий, просмотр отзывов |
| **Администратор** | Управление пользователями, предметами, аналитика |

---

## Архитектура

Система построена на микросервисной архитектуре. Внешний доступ осуществляется через **Traefik Edge Gateway** и **GraphQL API** (BFF). Внутри сервисы общаются через **gRPC** (синхронно) и **Kafka** (асинхронно).

```
                    ┌─────────────────┐
                    │     Клиент      │
                    └────────┬────────┘
                             │ HTTPS
                    ┌────────▼────────┐
                    │      Traefik    │
                    │  Edge Gateway   │
                    └────────┬────────┘
                             │ /graphql
                    ┌────────▼────────┐
                    │   GraphQL API   │
                    │      (BFF)      │
                    └────────┬────────┘
                             │ gRPC
        ┌────────────┬───────┼────────┬────────────┬─────────────┐
        ▼            ▼       ▼        ▼            ▼             ▼
   ┌─────────┐ ┌─────────┐ ┌─────┐ ┌───────┐ ┌─────────┐ ┌──────────┐
   │Identity │ │ Catalog │ │Sche-│ │Booking│ │ Payment │ │  Review  │
   │ Service │ │ Service │ │duling│ │Service│ │ Service │ │  Service │
   └────┬────┘ └────┬────┘ └──┬──┘ └───┬───┘ └────┬────┘ └─────┬────┘
        │           │         │        │          │            │
        ▼           ▼         ▼        ▼          ▼            ▼
     ┌──────┐   ┌──────┐  ┌──────┐ ┌──────┐ ┌──────┐     ┌──────┐
     │  DB  │   │  DB  │  │  DB  │ │  DB  │ │  DB  │     │  DB  │
     └──────┘   └──────┘  └──────┘ └──────┘ └──────┘     └──────┘

        ┌──────────────────────────────────────────────┐
        │              Kafka (события)                 │
        └──────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌─────────────┐
       │Notification│ │ Analytics  │ │   Другие    │
       │  Service   │ │  Service   │ │  сервисы    │
       └────────────┘ └────────────┘ └─────────────┘
```

### Принципы

- Каждый сервис владеет **собственной базой данных**.
- Внешние ключи используются **только внутри** базы одного сервиса.
- Клиент взаимодействует **только** через GraphQL API.
- Синхронные проверки — через **gRPC**, асинхронные события — через **Kafka**.

---

## Технологический стек

### Язык и окружение

| Компонент | Технология | Версия |
|---|---|---|
| Язык | Python | **3.14** |
| Менеджер зависимостей | [uv](https://docs.astral.sh/uv/) | latest |
| Workspace | uv workspaces | — |

### Backend

| Компонент | Технология |
|---|---|
| Веб-фреймворк | FastAPI |
| ASGI-сервер | Uvicorn |
| GraphQL | Strawberry / Ariadne |
| gRPC | grpcio / grpcio-tools |
| ORM | SQLAlchemy 2.x (async) |
| Миграции | Alembic |
| Kafka-клиент | aiokafka |
| Валидация | Pydantic v2 |

### Инфраструктура

| Компонент | Технология |
|---|---|
| Контейнеризация | Docker / Docker Compose |
| Edge Gateway | Traefik v3 |
| База данных | PostgreSQL 16 |
| Кэш | Redis 7 |
| Брокер сообщений | Apache Kafka (KRaft, Bitnami) |

### Observability

| Компонент | Технология |
|---|---|
| Сбор метрик | Prometheus |
| Дашборды | Grafana |
| Экспортеры | redis-exporter, postgres-exporter |
| Kafka UI | Kafka UI (provectuslabs) |

### Качество кода

| Инструмент | Назначение |
|---|---|
| ruff | Линтер и форматтер Python |
| buf | Линтер и форматтер Protobuf |
| pre-commit | Git-хуки |

---

## Структура проекта

```
.
├── db/
│   └── init/
│       └── 01-create-dbs.sql           # Создание БД для каждого сервиса
├── docker-compose.yml                  # Вся инфраструктура
├── Makefile                            # Команды для разработки
├── pyproject.toml                      # Корневой uv workspace
├── uv.lock                             # Зафиксированные зависимости
├── README.md
│
├── packages/
│   └── shared/                         # Общий код (логирование, kafka, grpc)
│       ├── pyproject.toml
│       └── src/shared/
│           ├── __init__.py
│           ├── grpc.py
│           ├── kafka.py
│           └── logging.py
│
├── proto/                              # gRPC контракты (protobuf)
│   ├── booking/
│   ├── catalog/
│   ├── identity/
│   ├── payment/
│   ├── review/
│   └── scheduling/
│
├── services/                           # Микросервисы
│   ├── graphql-api/
│   ├── identity-service/
│   ├── catalog-service/
│   ├── scheduling-service/
│   ├── booking-service/
│   ├── payment-service/
│   ├── review-service/
│   ├── notification-service/
│   └── analytics-service/
│
└── traefik/                            # Конфигурация Traefik
    ├── certs/
    ├── dynamic/
    │   ├── middlewares.yml
    │   └── tls.yml
    └── traefik.yml
```

---

## Таблица портов

### Микросервисы приложения

| Сервис | Назначение | HTTP | gRPC |
|---|---|---|---|
| graphql-api | Внешний GraphQL API | `4000` | — |
| identity-service | Пользователи и роли | `8001` | `50051` |
| catalog-service | Преподаватели и предметы | `8002` | `50052` |
| scheduling-service | Расписание и занятия | `8003` | `50053` |
| booking-service | Записи на занятия | `8004` | `50054` |
| payment-service | Оплата | `8005` | `50055` |
| review-service | Отзывы и рейтинги | `8006` | `50056` |
| notification-service | Уведомления | `8007` | `50057` |
| analytics-service | Аналитика | `8008` | `50058` |

### Инфраструктура

| Компонент | Порт | Назначение |
|---|---|---|
| traefik | `80`, `443` | HTTP/HTTPS вход |
| traefik dashboard | `8080` | UI Traefik |
| postgres | `5432` | PostgreSQL |
| redis | `6379` | Redis |
| kafka | `9092` | Kafka internal |
| kafka | `9094` | Kafka external (отладка) |
| kafka-ui | `8081` | Kafka UI |
| prometheus | `9090` | Метрики |
| grafana | `3000` | Дашборды |
| redis-exporter | `9121` | Метрики Redis |
| postgres-exporter | `9187` | Метрики PostgreSQL |

### Публичные домены (через Traefik)

| URL | Сервис |
|---|---|
| `http://api.localhost` | GraphQL API |
| `http://kafka.localhost` | Kafka UI |
| `http://prometheus.localhost` | Prometheus |
| `http://grafana.localhost` | Grafana |
| `http://traefik.localhost` | Traefik Dashboard |

> Все сервисы кроме `graphql-api` доступны только во внутренней сети `tutoring-platform_internal` и не пробрасываются наружу.

---

## Требования

Перед началом работы установи:

| Инструмент | Минимальная версия | Проверка |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Python | **3.14** | `python --version` |
| uv | latest | `uv --version` |
| pre-commit | 4+ | `pre-commit --version` |

### Установка uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# или через pip
pip install uv

# установка Python 3.14 через uv
uv python install 3.14
```

### Установка pre-commit

```bash
# рекомендуется через uv
uv tool install pre-commit

# или через pip
pip install pre-commit
```

---

## Быстрый старт

### 1. Клонирование и установка зависимостей

```bash
git clone <repo-url>
cd tutoring-platform

# установка всех зависимостей (все сервисы + shared)
uv sync --all-packages

# установка git-хуков
uv run pre-commit install
```

### 2. Настройка окружения

Создай файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Пример `.env`:

```env
# Postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret_password

# Redis
REDIS_PASSWORD=redis_secret

# Kafka
KAFKA_BROKERS=kafka:9092

# Grafana
GRAFANA_ADMIN_PASSWORD=admin

# JWT
JWT_SECRET=change_me_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

### 3. Запуск всей инфраструктуры

```bash
# запуск всех сервисов
docker compose up -d --build

# посмотреть логи
docker compose logs -f

# только конкретный сервис
docker compose logs -f booking-service
```

### 4. Проверка работоспособности

```bash
# статус контейнеров
docker compose ps

# GraphQL API
curl http://api.localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'

# healthcheck сервиса
curl http://localhost:8001/health
```

### 5. Остановка

```bash
docker compose down        # остановить
docker compose down -v     # остановить и удалить данные
```

---

## Переменные окружения

### Общие (для всех сервисов)

| Переменная | Описание | Пример |
|---|---|---|
| `ENV` | Окружение | `development`, `production` |
| `LOG_LEVEL` | Уровень логирования | `INFO`, `DEBUG` |
| `JWT_SECRET` | Секрет для JWT | `change_me` |

### Identity Service

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | URL БД | `postgresql://...@postgres:5432/identity_db` |
| `REDIS_URL` | URL Redis | `redis://:password@redis:6379/0` |
| `JWT_EXPIRE_MINUTES` | Время жизни токена | `60` |

### Остальные сервисы

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | URL БД сервиса | `postgresql://...@postgres:5432/booking_db` |
| `KAFKA_BROKERS` | Адреса Kafka | `kafka:9092` |
| `GRPC_PORT` | Порт gRPC | `50054` |
| `HTTP_PORT` | Порт HTTP/health | `8004` |

---

## Полезные команды

### Make-команды

```bash
make help              # список всех команд
make install           # установка зависимостей + хуков
make sync              # синхронизация зависимостей
make lint              # проверка кода (pre-commit)
make format            # форматирование кода
make test              # запуск тестов
```

### Управление зависимостями через uv

```bash
# добавить зависимость в сервис
uv add fastapi --package booking-service

# добавить зависимость в общий пакет
uv add pydantic --package shared

# добавить dev-зависимость в корень
uv add --group dev pytest

# синхронизировать всё
uv sync --all-packages
```

### Запуск сервисов локально (без Docker)

```bash
# каждый сервис в отдельном терминале
uv run --package identity-service uvicorn identity_service.main:app --reload --port 8001
uv run --package catalog-service uvicorn catalog_service.main:app --reload --port 8002
uv run --package scheduling-service uvicorn scheduling_service.main:app --reload --port 8003
uv run --package booking-service uvicorn booking_service.main:app --reload --port 8004
uv run --package payment-service uvicorn payment_service.main:app --reload --port 8005
uv run --package review-service uvicorn review_service.main:app --reload --port 8006
uv run --package notification-service python -m notification_service.consumer
uv run --package analytics-service analytics-service
uv run --package graphql-api uvicorn graphql_api.main:app --reload --port 4000
```

### Работа с Docker

```bash
# пересборка конкретного сервиса
docker compose build booking-service
docker compose up -d booking-service

# зайти внутрь контейнера
docker compose exec booking-service bash

# выполнить миграции вручную
docker compose exec booking-service uv run --package booking-service alembic upgrade head

# посмотреть события Kafka
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic booking.created --from-beginning
```

### Работа с базой данных

```bash
# подключиться к postgres
docker compose exec postgres psql -U postgres

# список баз
docker compose exec postgres psql -U postgres -c "\l"

# подключиться к конкретной БД
docker compose exec postgres psql -U postgres -d booking_db
```

---

## Разработка

### Монорепо на uv

Проект использует **uv workspaces** — единый монорепо с общим `uv.lock`. Все сервисы и общий пакет `shared` синхронизируются одной командой:

```bash
uv sync --all-packages
```

### Линтеры и форматтеры

Перед каждым коммитом автоматически запускаются:

- **базовые проверки**: пробелы, конец файла, валидность YAML/TOML;
- **ruff**: линтер и форматтер Python;
- **buf**: линтер и форматтер Protobuf.

Ручной запуск:

```bash
uv run pre-commit run --all-files
```

Обновление версий хуков:

```bash
pre-commit autoupdate
```

### Прото-файлы и gRPC

Контракты лежат в `proto/`. Структура:

```
proto/
├── booking/
│   └── booking.proto
├── catalog/
│   └── catalog.proto
├── identity/
│   └── identity.proto
├── payment/
│   └── payment.proto
├── review/
│   └── review.proto
└── scheduling/
    └── scheduling.proto
```

Проверка контрактов:

```bash
buf lint
buf format -w
```

## Доступ к сервисам

### Веб-интерфейсы

| Сервис | URL | Учётные данные |
|---|---|---|
| **GraphQL Playground** | http://api.localhost/graphql | — |
| **Kafka UI** | http://kafka.localhost | — |
| **Prometheus** | http://prometheus.localhost | basic-auth |
| **Grafana** | http://grafana.localhost | `admin` / `$GRAFANA_ADMIN_PASSWORD` |
| **Traefik Dashboard** | http://traefik.localhost | — |

### GraphQL API

Основная точка взаимодействия с системой:

```
POST http://api.localhost/graphql
Content-Type: application/json
```

Пример запроса:

```graphql
query {
  teachers(filter: { subjectId: "math", minRating: 4.5 }) {
    items {
      id
      about
      pricePerLesson
      rating { avgRating reviewsCount }
    }
  }
}
```

Пример мутации:

```graphql
mutation {
  bookLesson(input: { lessonId: "uuid-lesson" }) {
    id
    status
    price
  }
}
```

### gRPC (внутренняя сеть)

gRPC-порты сервисов доступны **только внутри** сети `tutoring-platform_internal`:

```
identity-service:50051
catalog-service:50052
scheduling-service:50053
booking-service:50054
payment-service:50055
review-service:50056
notification-service:50057
analytics-service:50058
```

Для локальной отладки можно использовать [grpcurl](https://github.com/fullstorydev/grpcurl) или [Postman gRPC](https://learning.postman.com/docs/sending-requests/grpc/first-grpc-request/).

### Kafka

Внутренний брокер:

```
kafka:9092
```

Основные топики:

| Топик | Назначение |
|---|---|
| `identity.user.registered` | Пользователь зарегистрирован |
| `catalog.teacher.updated` | Профиль преподавателя обновлён |
| `scheduling.lesson.created` | Занятие создано |
| `scheduling.lesson.completed` | Занятие завершено |
| `booking.created` | Запись создана |
| `booking.confirmed` | Запись подтверждена |
| `booking.cancelled` | Запись отменена |
| `payment.completed` | Оплата выполнена |
| `payment.failed` | Ошибка оплаты |
| `review.created` | Отзыв добавлен |
| `review.rating.updated` | Рейтинг обновлён |

---

## Мониторинг

### Метрики

Сервисы отдают метрики в формате Prometheus на порту `9090` (через `/metrics`).

### Дашборды

Стандартные дашборды Grafana доступны из коробки:

- **PostgreSQL** — подключение, запросы, размер БД;
- **Redis** — операции, память, ключи;
- **Сервисы** — HTTP/gRPC запросы, время ответа.

---

## ❗ Решение типовых проблем

### Порт уже занят

```bash
# найти процесс, слушающий порт
lsof -i :8004

# убить процесс
kill -9 <PID>
```

### Traefik не видит сервисы

Убедись, что сервисы подключены к правильной сети:

```bash
docker network inspect tutoring-platform_internal
```

### Миграции не применяются

```bash
# проверить, что БД создана
docker compose exec postgres psql -U postgres -c "\l"

# применить миграции вручную
docker compose exec booking-service uv run --package booking-service alembic upgrade head
```

### Kafka не подключается

```bash
# проверить, что брокер жив
docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
```
