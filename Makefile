POETRY ?= poetry
PYTHON ?= python3
UVICORN_HOST ?= 0.0.0.0
UVICORN_PORT ?= 8000
APP_MODULE ?= app.main:app

.PHONY: install up down run migrate seed-rbac compile lint lint-fix test check

install:
	$(POETRY) install

up:
	docker compose up -d db

down:
	docker compose down

run:
	$(POETRY) run uvicorn $(APP_MODULE) --host $(UVICORN_HOST) --port $(UVICORN_PORT) --reload

migrate:
	$(POETRY) run alembic upgrade head

seed-rbac:
	$(POETRY) run python -m app.scripts.seed_rbac

compile:
	$(PYTHON) -m compileall app tests alembic

lint:
	$(POETRY) run ruff check .

lint-fix:
	$(POETRY) run ruff check . --fix

test:
	$(POETRY) run pytest -q

check: compile lint test
