COMPOSE ?= docker compose
DOCKER_APP ?= $(COMPOSE) run --rm app
ENV_FILE ?= infra/.env
ENV_EXAMPLE ?= infra/env.example
APP_PORT ?= 8000

.PHONY: help install package lint type qa check test run build up down logs shell env compose-test

help:
	@echo "Available targets:"
	@echo "  install       Install dependencies with uv"
	@echo "  package       Build wheel/sdist inside docker"
	@echo "  lint          Ruff"
	@echo "  type          Run ty type checks (python -m ty)"
	@echo "  qa            lint + type"
	@echo "  check         lint + type + test"
	@echo "  test          Run pytest "
	@echo "  run           Run dev HTTP server"
	@echo "  build         Build docker images"
	@echo "  up            Start docker-compose stack"
	@echo "  down          Stop docker-compose stack"
	@echo "  logs          Tail app logs from docker-compose"
	@echo "  shell         Open bash in app container"

env:
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "Created $(ENV_FILE) from template"; \
	else \
		echo "$(ENV_FILE) already exists"; \
	fi

install:
	$(DOCKER_APP) uv pip install -e ".[dev]"

package:
	$(DOCKER_APP) uv build


lint:
	$(DOCKER_APP) uv run --extra dev ruff check .

type:
	$(DOCKER_APP) uv run --extra dev python -m ty check .

qa: lint type 

check: lint type test

run:
	APP_PORT=$(APP_PORT) $(UV) run python -m http.server $(APP_PORT)

build:
	$(COMPOSE) build

up: env
	$(COMPOSE) up -d

down:
	$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE) logs -f app

shell: env
	$(COMPOSE) run --rm app /bin/bash

test:
	$(DOCKER_APP) uv run pytest
