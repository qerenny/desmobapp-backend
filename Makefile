POETRY ?= poetry
PYTHON ?= python3
UVICORN_HOST ?= 0.0.0.0
UVICORN_PORT ?= 8000
APP_MODULE ?= app.main:app
PRE_COMMIT_HOME ?= .cache/pre-commit

.PHONY: install up down run migrate seed-rbac seed-demo seed-tariffs compile lint lint-fix test check precommit-install precommit-run

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

seed-demo:
	$(POETRY) run python -m app.scripts.seed_demo

seed-tariffs:
	$(POETRY) run python -m app.scripts.seed_tariffs

compile:
	$(PYTHON) -m compileall app tests alembic

lint:
	$(POETRY) run ruff check .

lint-fix:
	$(POETRY) run ruff check . --fix

test:
	$(POETRY) run pytest -q

precommit-install:
	PRE_COMMIT_HOME=$(PRE_COMMIT_HOME) $(POETRY) run pre-commit install --hook-type pre-commit --hook-type pre-push

precommit-run:
	PRE_COMMIT_HOME=$(PRE_COMMIT_HOME) $(POETRY) run pre-commit run --all-files

check: compile lint test
