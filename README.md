# QR Studio

Генератор QR-кодов с веб-интерфейсом (FastAPI + vanilla JS). Проект рассчитан на локальное развёртывание: Docker Compose, один контейнер, минимум внешних зависимостей.

## Требования

- Python **3.12** или **3.13**
- [uv](https://docs.astral.sh/uv/) для управления зависимостями
- Docker + Docker Compose (опционально)

## Быстрый старт

```bash
# 1. Установить зависимости
uv sync --frozen --all-extras

# 2. Скопировать пример конфигурации
cp .env.example .env

# 3. Запустить в режиме разработки
make dev
```

Откройте http://localhost:8080 в браузере.

## Переменные окружения

Создайте файл `.env` на основе `.env.example`:

| Переменная | Описание | По умолчанию |
|---|---|---|
| `QR_HOST` | Хост, на котором слушает сервер | `0.0.0.0` |
| `QR_PORT` | Порт сервера | `8080` |
| `QR_WORKERS` | Количество worker-процессов Uvicorn | `1` |
| `QR_RELOAD` | Автоперезагрузка при изменении кода | `false` |
| `QR_LOG_LEVEL` | Уровень логирования | `INFO` |
| `QR_REQUEST_TIMEOUT` | Таймаут запроса в секундах | `10.0` |
| `QR_MAX_CONTENT_LENGTH` | Максимальный размер тела запроса | `2048` |
| `QR_RATE_LIMIT` | Лимит запросов с одного IP | `10/minute` |
| `QR_CORS_ORIGINS` | Разрешённые CORS-источники через запятую (пусто — CORS отключён) | *(пусто)* |
| `QR_QR_FILL_COLOR` | Цвет модулей QR | `#1e3a8a` |
| `QR_QR_BACK_COLOR` | Цвет фона QR | `#ffffff` |
| `QR_QR_MODULE_ROUND` | Скругление модулей QR | `0.4` |
| `QR_QR_BOX_SIZE` | Размер модуля в пикселях | `12` |
| `QR_QR_BORDER` | Ширина границы в модулях | `4` |

### Безопасность

- `QR_CORS_ORIGINS` по умолчанию пуст: кросс-доменные запросы запрещены. Для публичного API укажите доверенные источники, например `https://app.example.com`.
- `QR_RATE_LIMIT` работает в памяти текущего процесса. При запуске нескольких реплик за балансировщиком используйте общее хранилище (Redis) через собственную реализацию `RateLimitBackend`.
- `QR_MAX_CONTENT_LENGTH` и `QR_REQUEST_TIMEOUT` защищают от слишком больших тел запросов и долгой генерации.

## Запуск через Docker

```bash
docker compose up -d --build
```

Или через `Makefile`:

```bash
make up
```

## API

- `GET /api/health` — health check
- `POST /api/generate` — генерация QR-кода
  - `type`: `"url"` | `"text"`
  - `data`: строка URL или произвольный текст
  - `format`: `"png"` | `"svg"`

Интерактивная документация доступна по адресу http://localhost:8080/docs.

## Разработка

```bash
# Установить зависимости
make install

# Запустить линтер
make lint

# Запустить type checker
make type-check

# Запустить тесты с покрытием
make test

# Запустить все проверки
make check

# Аудит зависимостей на наличие CVE
make audit
```

## Структура проекта

```
app/
├── api/           # REST endpoint'ы
├── core/          # Конфигурация и логирование
├── middleware/    # HTTP middleware (request ID)
├── schemas/       # Pydantic-схемы
├── services/      # Бизнес-логика генерации QR
├── templates/     # HTML-шаблоны
└── main.py        # Точка входа

tests/
├── unit/          # Unit-тесты сервисов
└── integration/   # Интеграционные тесты API
```

## CI/CD

Репозиторий содержит GitHub Actions workflow:

- `pr.yml` — lint, format, type check, tests + сборка Docker + smoke test на каждый PR
- `main.yml` — tests + сборка Docker + smoke test после merge в `main`
- `audit.yml` — еженедельный аудит зависимостей через `pip-audit`
- `dependabot.yml` — автоматические PR с обновлениями зависимостей Python и GitHub Actions
