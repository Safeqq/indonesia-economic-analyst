.PHONY: setup database schema migrate check lint test test-api test-integration
.PHONY: pipeline pipeline-bps pipeline-bi verify-bps verify-bi marts quality eda
.PHONY: advanced-analytics verify-analytics api dashboard frontend-install
.PHONY: frontend-lint frontend-test frontend-build frontend-smoke frontend-check
.PHONY: scheduled-run schedule-dry-run freshness deployment-config deployment-smoke

PYTHON := .venv/bin/python
FRONTEND_NPM := npm --prefix frontend

setup:
	./scripts/setup_project.sh

database:
	./scripts/init_database.sh

schema:
	$(PYTHON) scripts/apply_schema.py
	$(PYTHON) scripts/apply_migrations.py

migrate:
	$(PYTHON) scripts/apply_migrations.py

check:
	$(PYTHON) scripts/check_setup.py

lint:
	$(PYTHON) -m ruff format --check analytics backend pipelines scripts tests
	$(PYTHON) -m ruff check analytics backend pipelines scripts tests
	$(FRONTEND_NPM) run lint
	$(FRONTEND_NPM) run typecheck

test:
	$(PYTHON) -m pytest -q
	$(FRONTEND_NPM) test

test-api:
	$(PYTHON) -m pytest -q tests/api/test_api.py

test-integration:
	RUN_DB_INTEGRATION=1 $(PYTHON) -m pytest -q -m integration

pipeline:
	$(PYTHON) -m pipelines.jobs.run_pipeline

pipeline-bps:
	$(PYTHON) -m pipelines.jobs.run_bps_pipeline

pipeline-bi:
	$(PYTHON) -m pipelines.jobs.run_bank_indonesia_pipeline

verify-bps:
	$(PYTHON) scripts/verify_bps.py

verify-bi:
	$(PYTHON) scripts/verify_bank_indonesia.py

marts:
	$(PYTHON) scripts/build_marts.py

quality:
	$(PYTHON) scripts/check_data_quality.py

freshness:
	$(PYTHON) scripts/check_data_freshness.py

scheduled-run:
	$(PYTHON) -m pipelines.jobs.run_scheduled_pipelines

schedule-dry-run:
	$(PYTHON) -m pipelines.jobs.run_scheduled_pipelines --dry-run

eda:
	MPLCONFIGDIR=data/exports/.matplotlib $(PYTHON) scripts/run_eda_notebooks.py

advanced-analytics:
	MPLCONFIGDIR=data/exports/.matplotlib $(PYTHON) scripts/run_advanced_analytics.py

verify-analytics:
	$(PYTHON) scripts/verify_advanced_analytics.py

api:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

dashboard:
	$(FRONTEND_NPM) run dev

frontend-install:
	$(FRONTEND_NPM) ci

frontend-lint:
	$(FRONTEND_NPM) run lint
	$(FRONTEND_NPM) run typecheck

frontend-test:
	$(FRONTEND_NPM) test

frontend-build:
	$(FRONTEND_NPM) run build

frontend-smoke:
	$(FRONTEND_NPM) run test:smoke

frontend-check: frontend-lint frontend-test frontend-build

deployment-config:
	docker compose --env-file .env -f docker-compose.production.yml config --quiet

deployment-smoke:
	$(PYTHON) scripts/smoke_deployment.py
