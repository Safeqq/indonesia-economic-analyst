from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logging  # noqa: E402

from pipelines.utils.automation import named_database_lock  # noqa: E402
from pipelines.utils.database import get_engine  # noqa: E402
from pipelines.utils.structured_logging import (  # noqa: E402
    configure_logging,
    log_event,
)

MIGRATION_DIRECTORY = PROJECT_ROOT / "database" / "migrations"
MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{3,})_(?P<name>[a-z0-9_]+)\.sql$")
MIGRATION_LOCK_NAME = "indonesia_economic_intelligence_migrations"
LOGGER = logging.getLogger(__name__)

CREATE_LEDGER = """
CREATE TABLE IF NOT EXISTS schema_migration (
    version VARCHAR(20) PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL,
    checksum CHAR(64) NOT NULL,
    applied_at DATETIME NOT NULL
)
"""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    checksum: str


@dataclass(frozen=True)
class MigrationResult:
    applied: tuple[str, ...]
    skipped: tuple[str, ...]


def split_sql_statements(sql: str) -> tuple[str, ...]:
    return tuple(statement.strip() for statement in sql.split(";") if statement.strip())


def discover_migrations(directory: Path = MIGRATION_DIRECTORY) -> tuple[Migration, ...]:
    migrations: list[Migration] = []
    versions: set[str] = set()
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_PATTERN.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Nama migration tidak valid: {path.name}")
        version = match.group("version")
        if version in versions:
            raise ValueError(f"Versi migration duplikat: {version}")
        versions.add(version)
        migrations.append(
            Migration(
                version=version,
                name=match.group("name"),
                path=path,
                checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return tuple(migrations)


def apply_migrations(
    engine: Engine | None = None,
    *,
    directory: Path = MIGRATION_DIRECTORY,
) -> MigrationResult:
    owns_engine = engine is None
    active_engine = engine or get_engine()
    applied: list[str] = []
    skipped: list[str] = []
    try:
        with named_database_lock(active_engine, MIGRATION_LOCK_NAME, 30):
            with active_engine.begin() as connection:
                connection.exec_driver_sql(CREATE_LEDGER)
                known = {
                    str(row["version"]): str(row["checksum"])
                    for row in connection.execute(
                        text("SELECT version, checksum FROM schema_migration")
                    ).mappings()
                }

            for migration in discover_migrations(directory):
                existing_checksum = known.get(migration.version)
                if existing_checksum is not None:
                    if existing_checksum != migration.checksum:
                        raise RuntimeError(
                            f"Checksum migration {migration.version} berubah; "
                            "buat migration baru alih-alih mengubah riwayat"
                        )
                    skipped.append(migration.version)
                    continue

                with active_engine.begin() as connection:
                    sql = migration.path.read_text(encoding="utf-8")
                    for statement in split_sql_statements(sql):
                        connection.exec_driver_sql(statement)
                    connection.execute(
                        text(
                            """
                            INSERT INTO schema_migration
                                (version, migration_name, checksum, applied_at)
                            VALUES
                                (:version, :name, :checksum, :applied_at)
                            """
                        ),
                        {
                            "version": migration.version,
                            "name": migration.name,
                            "checksum": migration.checksum,
                            "applied_at": datetime.now(UTC).replace(tzinfo=None),
                        },
                    )
                applied.append(migration.version)
                known[migration.version] = migration.checksum
    finally:
        if owns_engine:
            active_engine.dispose()
    return MigrationResult(applied=tuple(applied), skipped=tuple(skipped))


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    configure_logging()
    try:
        result = apply_migrations()
    except Exception as error:
        log_event(
            LOGGER,
            logging.ERROR,
            "database_migration_failed",
            "Migration database gagal",
            error_type=error.__class__.__name__,
            error=str(error),
        )
        return 1
    for version in result.applied:
        log_event(
            LOGGER,
            logging.INFO,
            "database_migration_applied",
            "Migration database diterapkan",
            version=version,
        )
    log_event(
        LOGGER,
        logging.INFO,
        "database_migrations_complete",
        "Migration database selesai",
        applied_count=len(result.applied),
        skipped_count=len(result.skipped),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
