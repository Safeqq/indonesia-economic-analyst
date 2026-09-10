.PHONY: setup database schema check lint test test-integration pipeline pipeline-bps pipeline-bi verify-bps verify-bi marts quality api

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
	$(PYTHON) -m ruff check backend pipelines scripts tests

test:
	$(PYTHON) -m pytest -q

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

api:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
