from pathlib import Path

import pytest

import pipelines.jobs.run_pipeline as pipeline_job
from pipelines.utils.config import IndicatorDefinition


def test_pipeline_failure_is_recorded(monkeypatch, tmp_path):
    definition = IndicatorDefinition(
        code="NY.GDP.MKTP.KD.ZG",
        name="GDP growth",
        unit="percent",
        frequency="annual",
        source="world_bank",
    )
    engine = object()
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        pipeline_job,
        "load_indicator_definitions",
        lambda: {definition.code: definition},
    )
    monkeypatch.setattr(
        pipeline_job,
        "start_pipeline_run",
        lambda source_code, supplied_engine: (supplied_engine, 42),
    )

    def fail_extraction(*args, **kwargs):
        raise RuntimeError("sumber tidak tersedia")

    def record_failure(run_id, error, supplied_engine):
        recorded.update(run_id=run_id, error=str(error), engine=supplied_engine)

    monkeypatch.setattr(pipeline_job, "extract_indicator", fail_extraction)
    monkeypatch.setattr(pipeline_job, "fail_pipeline_run", record_failure)

    with pytest.raises(RuntimeError, match="sumber tidak tersedia"):
        pipeline_job.execute_pipeline(
            "IDN",
            [definition.code],
            2020,
            2023,
            raw_directory=Path(tmp_path),
            engine=engine,
        )

    assert recorded == {
        "run_id": 42,
        "error": "sumber tidak tersedia",
        "engine": engine,
    }
