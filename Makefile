.PHONY: setup database check lint test test-integration pipeline api

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
	RUN_DB_INTEGRATION=1 $(PYTHON) -m pytest -q \
		tests/pipeline/test_load_integration.py

pipeline:
	$(PYTHON) -m pipelines.jobs.run_pipeline

api:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
