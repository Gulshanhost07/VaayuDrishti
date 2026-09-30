.DEFAULT_GOAL := help

COMPOSE ?= docker compose
PY ?= python

.PHONY: help env up up-full down psql logs migrate seed test lint fmt typecheck loadtest demo pdf spark-rollups spark-stream spark-up webapp webapp-install webapp-dev

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example (if missing)
	@test -f .env || cp .env.example .env
	@echo ".env ready"

up: env ## Start core stack (storage + kafka + api + workers)
	$(COMPOSE) up -d --build

up-full: env ## Start everything incl. Spark + tools
	$(COMPOSE) --profile full --profile tools up -d --build

down: ## Stop stack (keeps volumes)
	$(COMPOSE) down

clean: ## Stop stack and delete volumes
	$(COMPOSE) down -v

logs: ## Tail all logs
	$(COMPOSE) logs -f --tail=100

logs-api: ## Tail api logs
	$(COMPOSE) logs -f --tail=100 api

psql: ## Open psql shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-vaayu} -d $${POSTGRES_DB:-vaayu}

migrate: env ## Apply schema + seeds (create_all path)
	$(COMPOSE) run --rm seed

seed: migrate ## Alias of migrate

test: ## Run backend tests
	cd backend && $(PY) -m pytest -q

lint: ## Ruff lint
	cd backend && $(PY) -m ruff check .

fmt: ## Ruff format
	cd backend && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

typecheck: ## Mypy
	cd backend && $(PY) -m mypy shared api ingest pipeline ml

loadtest: ## Blast 10k synthetic posts through the pipeline
	cd backend && $(PY) -m scripts.load_test --count 10000

spark-rollups: ## Run Spark hourly/daily rollup job (needs --profile full stack)
	$(COMPOSE) --profile full run --rm spark-jobs

spark-stream: ## Start Spark structured-streaming ingest (raw.posts -> reports)
	$(COMPOSE) --profile full up -d spark-stream

spark-up: ## Start the whole Spark layer (master + workers + stream)
	$(COMPOSE) --profile full up -d spark-master spark-worker spark-stream

pdf: ## Regenerate docs/VaayuDrishti_Full_Workflow.pdf
	$(PY) docs/generate_pdf.py

demo: ## Print the 10-minute judge demo script
	@cat scripts/demo.sh

webapp-install: ## Install webapp npm dependencies
	cd webapp && npm install

webapp: ## Build the React frontend into frontend/ (served by the API)
	cd webapp && npm run build

webapp-dev: ## Start the Vite dev server on :5173 (proxies /api to :8000)
	cd webapp && npm run dev
