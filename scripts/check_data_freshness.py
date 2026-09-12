from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.automation import load_automation_configuration  # noqa: E402
from pipelines.utils.database import get_engine  # noqa: E402
from pipelines.utils.freshness import (  # noqa: E402
    assess_freshness,
    load_freshness_snapshots,
    persist_freshness_report,
)
from pipelines.utils.structured_logging import (  # noqa: E402
    configure_logging,
    log_event,
)

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Periksa freshness data dan hasilkan alert operasional"
    )
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        help="Kode sumber; ulangi untuk beberapa sumber",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Jangan simpan status alert ke MariaDB",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    configure_logging()
    engine = None
    try:
        configuration = load_automation_configuration()
        selected = tuple(args.sources or configuration.sources)
        unknown = sorted(set(selected).difference(configuration.sources))
        if unknown:
            raise ValueError(f"Sumber freshness tidak dikenal: {unknown}")
        if len(selected) != len(set(selected)):
            raise ValueError("Sumber freshness tidak boleh duplikat")
        schedules = {code: configuration.sources[code] for code in selected}
        engine = get_engine()
        snapshots = load_freshness_snapshots(engine, selected)
        report = assess_freshness(snapshots, schedules)
        if not args.no_persist:
            persist_freshness_report(report, engine)
    except Exception as error:
        log_event(
            LOGGER,
            logging.ERROR,
            "freshness_check_failed",
            "Pemeriksaan freshness gagal dijalankan",
            error_type=error.__class__.__name__,
            error=str(error),
        )
        return 2
    finally:
        if engine is not None:
            engine.dispose()

    findings_by_source = {
        source_code: [
            finding for finding in report.findings if finding.source_code == source_code
        ]
        for source_code in selected
    }
    for source_code, findings in findings_by_source.items():
        if not findings:
            log_event(
                LOGGER,
                logging.INFO,
                "data_freshness_passed",
                "Data sumber masih berada dalam ambang freshness",
                source_code=source_code,
            )
        for finding in findings:
            log_event(
                LOGGER,
                logging.WARNING,
                "data_freshness_alert",
                finding.message,
                source_code=finding.source_code,
                alert_type=finding.alert_type,
                severity=finding.severity,
                latest_observation_date=finding.latest_observation_date,
                last_ingested_at=finding.last_ingested_at,
            )
    return 0 if report.is_fresh else 1


if __name__ == "__main__":
    raise SystemExit(main())
