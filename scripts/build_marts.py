from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.database import get_engine  # noqa: E402

MART_SQL_FILES = (
    PROJECT_ROOT / "sql" / "staging" / "stg_world_bank.sql",
    PROJECT_ROOT / "sql" / "marts" / "mart_national_overview.sql",
    PROJECT_ROOT / "sql" / "marts" / "mart_indicator_trends.sql",
    PROJECT_ROOT / "sql" / "marts" / "mart_asean_comparison.sql",
)


def build_marts(engine: Engine | None = None) -> tuple[str, ...]:
    engine = engine or get_engine()
    built_views: list[str] = []
    with engine.begin() as connection:
        for sql_file in MART_SQL_FILES:
            statement = sql_file.read_text(encoding="utf-8")
            try:
                connection.exec_driver_sql(statement)
            except Exception as error:
                message = f"Gagal membangun view dari {sql_file.name}"
                raise RuntimeError(message) from error
            built_views.append(sql_file.stem)
    return tuple(built_views)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    for view_name in build_marts():
        print(f"[OK] View tersedia: {view_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
