from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import inspect, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def check_python() -> None:
    if sys.version_info < (3, 11):  # noqa: UP036 - pemeriksaan runtime disengaja
        raise RuntimeError("Python minimal 3.11")
    print(f"[OK] Python {sys.version.split()[0]}")


def check_environment() -> None:
    required = [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Environment variable belum diisi: {', '.join(missing)}")
    if os.environ["MYSQL_PASSWORD"] == "change_me":
        raise RuntimeError("MYSQL_PASSWORD masih menggunakan nilai default")
    print("[OK] Konfigurasi .env")


def check_database() -> None:
    from pipelines.utils.database import get_engine

    engine = get_engine()
    with engine.connect() as connection:
        version = connection.execute(text("SELECT VERSION()"))
        print(f"[OK] Database terhubung: {version.scalar_one()}")

    required_tables = {
        "dim_source",
        "dim_indicator",
        "dim_region",
        "dim_date",
        "fact_economic_indicator",
        "fact_pipeline_run",
        "dim_indicator_metadata_history",
        "fact_forecast_run",
        "fact_forecast",
        "fact_anomaly_event",
        "schema_migration",
        "data_freshness_alert",
        "pipeline_schedule_run",
    }
    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(f"Tabel belum tersedia: {sorted(missing_tables)}")
    print("[OK] Seluruh tabel wajib tersedia")


def main() -> None:
    check_python()
    check_environment()
    check_database()
    print("Setup project siap digunakan.")


if __name__ == "__main__":
    main()
