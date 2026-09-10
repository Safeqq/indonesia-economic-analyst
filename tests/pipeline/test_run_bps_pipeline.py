import pytest

import pipelines.jobs.run_bps_pipeline as bps_job
from tests.pipeline.bps_fixtures import configuration, province_configuration


def test_bps_pipeline_failure_is_recorded(monkeypatch, tmp_path):
    engine = object()
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        bps_job,
        "load_bps_provinces",
        province_configuration,
    )
    monkeypatch.setattr(
        bps_job,
        "start_pipeline_run",
        lambda source_code, supplied_engine: (supplied_engine, 81),
    )

    def fail_extraction(*args, **kwargs):
        raise RuntimeError("sumber BPS tidak tersedia")

    def record_failure(run_id, error, supplied_engine):
        recorded.update(run_id=run_id, error=str(error), engine=supplied_engine)

    monkeypatch.setattr(bps_job, "extract_bps", fail_extraction)
    monkeypatch.setattr(bps_job, "fail_pipeline_run", record_failure)

    with pytest.raises(RuntimeError, match="sumber BPS tidak tersedia"):
        bps_job.execute_bps_pipeline(
            raw_directory=tmp_path,
            engine=engine,
            client=object(),
            configuration=configuration(),
        )

    assert recorded == {
        "run_id": 81,
        "error": "sumber BPS tidak tersedia",
        "engine": engine,
    }
