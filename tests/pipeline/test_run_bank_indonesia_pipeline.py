from datetime import date

import pytest

import pipelines.jobs.run_bank_indonesia_pipeline as bi_job
from pipelines.utils.bank_indonesia_config import (
    load_bank_indonesia_configuration,
)


def test_bank_indonesia_pipeline_failure_is_recorded(monkeypatch, tmp_path):
    engine = object()
    recorded: dict[str, object] = {}
    configuration = load_bank_indonesia_configuration()

    monkeypatch.setattr(
        bi_job,
        "start_pipeline_run",
        lambda source_code, supplied_engine: (supplied_engine, 91),
    )

    def fail_extraction(*args, **kwargs):
        raise RuntimeError("sumber BI tidak tersedia")

    def record_failure(run_id, error, supplied_engine):
        recorded.update(run_id=run_id, error=str(error), engine=supplied_engine)

    monkeypatch.setattr(bi_job, "extract_bank_indonesia", fail_extraction)
    monkeypatch.setattr(bi_job, "fail_pipeline_run", record_failure)

    with pytest.raises(RuntimeError, match="sumber BI tidak tersedia"):
        bi_job.execute_bank_indonesia_pipeline(
            date(2026, 1, 1),
            date(2026, 2, 28),
            raw_directory=tmp_path,
            engine=engine,
            configuration=configuration,
        )

    assert recorded == {
        "run_id": 91,
        "error": "sumber BI tidak tersedia",
        "engine": engine,
    }


def test_previous_complete_month_end_is_deterministic():
    assert bi_job.previous_complete_month_end(date(2026, 9, 10)) == date(2026, 8, 31)
    assert bi_job.previous_complete_month_end(date(2026, 1, 1)) == date(2025, 12, 31)
