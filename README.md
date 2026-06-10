# Менторика — Лендинг сервиса менторинга

Django-лендинг с дизайн-системой [Plasma UI](https://plasma.sberdevices.ru/ui), Docker и PostgreSQL.

## Быстрый старт (Docker)

```bash
# 1. Скопировать переменные окружения
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 2. Запустить контейнеры
docker compose up --build
```

Откройте http://127.0.0.1:8000/

Админка с заявками: http://127.0.0.1:8000/admin/

```bash
# Создать суперпользователя
docker compose exec web python manage.py createsuperuser
```

## Сервисы

| Сервис | Контейнер | Порт | Описание |
|--------|-----------|------|----------|
| `web` | mentoring_web | 8000 | Django-приложение |
| `db` | mentoring_db | 5432 | PostgreSQL 16 |

При старте `web` автоматически ждёт PostgreSQL и выполняет миграции.

## Переменные окружения (.env)

```env
POSTGRES_DB=mentoring
POSTGRES_USER=mentoring
POSTGRES_PASSWORD=mentoring
POSTGRES_HOST=db          # db — в Docker, localhost — без Docker
POSTGRES_PORT=5432

DJANGO_SECRET_KEY=change-me-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web
```

## Локальный запуск без Docker

Нужен установленный PostgreSQL на машине:

```bash
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

# В .env укажите POSTGRES_HOST=localhost
python manage.py migrate
python manage.py runserver
```

## Структура проекта

```
mentoring/
├── config/              # Настройки Django
├── landing/             # Лендинг
├── static/              # Plasma UI CSS/JS
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh        # Ожидание БД + migrate
└── requirements.txt
```

## Plasma UI

- Тема Eva (фиолетовый акцент #7558D5)
- Светлая и тёмная тема
- Шрифт: IBM Plex Sans
