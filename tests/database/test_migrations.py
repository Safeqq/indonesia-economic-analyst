from __future__ import annotations

from pathlib import Path

import pytest

from scripts.apply_migrations import discover_migrations, split_sql_statements


def test_migrations_are_ordered_and_have_stable_checksums() -> None:
    migrations = discover_migrations()

    assert [migration.version for migration in migrations] == sorted(
        migration.version for migration in migrations
    )
    assert migrations
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_migration_version_must_be_unique(tmp_path: Path) -> None:
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "001_second.sql").write_text("SELECT 2;", encoding="utf-8")

    with pytest.raises(ValueError, match="Versi migration duplikat"):
        discover_migrations(tmp_path)


def test_controlled_sql_is_split_into_statements() -> None:
    assert split_sql_statements(
        "CREATE TABLE a (id INT);\nCREATE INDEX b ON a(id);"
    ) == (
        "CREATE TABLE a (id INT)",
        "CREATE INDEX b ON a(id)",
    )
