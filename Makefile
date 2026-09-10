.PHONY: setup database check lint test test-integration pipeline marts quality api

PYTHON := .venv/bin/python

setup:
	./scripts/setup_project.sh

database:
	./scripts/init_database.sh

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

marts:
	$(PYTHON) scripts/build_marts.py

quality:
	$(PYTHON) scripts/check_data_quality.py

api:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
