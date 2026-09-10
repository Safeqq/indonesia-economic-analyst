from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.database import get_engine  # noqa: E402

SCHEMA_FILES = (
    PROJECT_ROOT / "database" / "schema" / "02_create_dimensions.sql",
    PROJECT_ROOT / "database" / "schema" / "03_create_facts.sql",
    PROJECT_ROOT / "database" / "schema" / "05_create_metadata_history.sql",
    PROJECT_ROOT / "database" / "schema" / "06_create_advanced_analytics.sql",
    PROJECT_ROOT / "database" / "schema" / "04_create_indexes.sql",
)


def apply_schema(engine: Engine | None = None) -> tuple[str, ...]:
    engine = engine or get_engine()
    applied: list[str] = []
    with engine.begin() as connection:
        for schema_file in SCHEMA_FILES:
            statements = [
                statement.strip()
                for statement in schema_file.read_text(encoding="utf-8").split(";")
                if statement.strip()
            ]
            for statement in statements:
                connection.exec_driver_sql(statement)
            applied.append(schema_file.name)
    return tuple(applied)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    for filename in apply_schema():
        print(f"[OK] Schema diterapkan: {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
