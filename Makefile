.PHONY: setup database schema check lint test test-api test-integration pipeline pipeline-bps pipeline-bi verify-bps verify-bi marts quality eda advanced-analytics verify-analytics api

PYTHON := .venv/bin/python

setup:
	./scripts/setup_project.sh

database:
	./scripts/init_database.sh

schema:
	$(PYTHON) scripts/apply_schema.py

check:
	$(PYTHON) scripts/check_setup.py

lint:
	$(PYTHON) -m ruff format --check analytics backend pipelines scripts tests
	$(PYTHON) -m ruff check analytics backend pipelines scripts tests

test:
	$(PYTHON) -m pytest -q

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

eda:
	MPLCONFIGDIR=data/exports/.matplotlib $(PYTHON) scripts/run_eda_notebooks.py

advanced-analytics:
	MPLCONFIGDIR=data/exports/.matplotlib $(PYTHON) scripts/run_advanced_analytics.py

verify-analytics:
	$(PYTHON) scripts/verify_advanced_analytics.py

api:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
