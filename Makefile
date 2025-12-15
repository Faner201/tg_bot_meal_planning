UV ?= uv
COMPOSE ?= docker compose
ENV_FILE ?= infra/.env
ENV_EXAMPLE ?= infra/env.example
APP_PORT ?= 8000

.PHONY: help install lint test run build up down logs shell env compose-test

help:
	@echo "Available targets:"
	@echo "  install       Install dependencies with uv"
	@echo "  lint          Quick syntax check via compileall"
	@echo "  test          Run pytest"
	@echo "  run           Run dev HTTP server (http.server)"
	@echo "  build         Build docker images"
	@echo "  up            Start docker-compose stack"
	@echo "  down          Stop docker-compose stack"
	@echo "  logs          Tail app logs from docker-compose"
	@echo "  shell         Open bash in app container"
	@echo "  compose-test  Run pytest inside the app container"

env:
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "Created $(ENV_FILE) from template"; \
	else \
		echo "$(ENV_FILE) already exists"; \
	fi

install:
	$(UV) pip install -e .

lint:
	$(UV) run python -m compileall src tests

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

test: env
	$(COMPOSE) run --rm app uv run pytest
