from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.structured_logging import (  # noqa: E402
    configure_logging,
    log_event,
)
from scripts.apply_migrations import apply_migrations  # noqa: E402
from scripts.apply_schema import apply_schema  # noqa: E402
from scripts.build_marts import build_marts  # noqa: E402

LOGGER = logging.getLogger(__name__)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    configure_logging()
    try:
        schema_files = apply_schema()
        migrations = apply_migrations()
        views = build_marts()
    except Exception as error:
        log_event(
            LOGGER,
            logging.ERROR,
            "database_preparation_failed",
            "Persiapan database produksi gagal",
            error_type=error.__class__.__name__,
            error=str(error),
        )
        return 1
    log_event(
        LOGGER,
        logging.INFO,
        "database_preparation_complete",
        "Database produksi siap digunakan",
        schema_file_count=len(schema_files),
        migrations_applied=len(migrations.applied),
        migrations_skipped=len(migrations.skipped),
        view_count=len(views),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
