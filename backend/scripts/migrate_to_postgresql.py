"""Copy an existing SQLite EMIS database into PostgreSQL.

The source database is only ever read. The target must be empty (or at least
contain no EMIS tables); the script creates the schema from SQLAlchemy
metadata, copies every row in foreign-key-safe order, resets PostgreSQL
sequences and verifies the row counts.

Usage:
    # 1. set the destination in backend/.env (or in the environment)
    DATABASE_URL=postgresql+psycopg2://user:password@host:5432/emis

    # 2. run from the backend directory
    python scripts/migrate_to_postgresql.py

    # optional: override the source
    SOURCE_DATABASE_URL=sqlite:////path/to/emis_dev.db python scripts/migrate_to_postgresql.py
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import models  # noqa: E402,F401 - registers every table in metadata
from app.extensions import db  # noqa: E402

CHUNK_SIZE = 5000


def ordered_tables(metadata):
    """Return tables sorted so referenced tables are copied first."""
    tables = list(metadata.tables.values())
    dependencies = {table.name: set() for table in tables}
    for table in tables:
        for foreign_key in table.foreign_keys:
            parent = foreign_key.column.table.name
            if parent != table.name:
                dependencies[table.name].add(parent)

    ordered = []
    done = set()
    while len(done) < len(tables):
        ready = [
            table for table in tables
            if table.name not in done and dependencies[table.name] <= done
        ]
        if not ready:
            pending = [t.name for t in tables if t.name not in done]
            raise RuntimeError(f"Circular foreign-key dependency among: {pending}")
        for table in ready:
            ordered.append(table)
            done.add(table.name)
    return ordered


def reset_sequences(connection, metadata):
    """PostgreSQL sequences must be advanced after explicit primary keys."""
    for table in metadata.tables.values():
        for column in table.primary_key.columns:
            if not column.autoincrement or column.type.python_type not in (int,):
                continue
            sequence = connection.exec_driver_sql(
                "SELECT pg_get_serial_sequence(%s, %s)",
                (table.name, column.name),
            ).scalar()
            if sequence:
                connection.exec_driver_sql(
                    f"SELECT setval('{sequence}', "
                    f"COALESCE((SELECT MAX({column.name}) FROM {table.name}), 1), "
                    "true)"
                )


def main():
    source_url = os.getenv(
        "SOURCE_DATABASE_URL", f"sqlite:///{BASE_DIR / 'emis_dev.db'}"
    )
    target_url = os.getenv("DATABASE_URL", "").strip()
    if not target_url:
        raise SystemExit(
            "DATABASE_URL is not set. Set it to the PostgreSQL destination "
            "in backend/.env or in the environment."
        )
    if "postgres" not in target_url.lower():
        raise SystemExit(
            f"DATABASE_URL must point to PostgreSQL, got: {target_url.split('://')[0]}"
        )
    if source_url == target_url:
        raise SystemExit("Source and target are the same database.")

    source = create_engine(source_url)
    target = create_engine(target_url)
    metadata = db.metadata

    if inspect(source).get_table_names() == []:
        raise SystemExit(f"No tables found in source database: {source_url}")
    existing = inspect(target).get_table_names()
    overlapping = sorted(set(metadata.tables) & set(existing))
    if overlapping:
        raise SystemExit(
            "Target already contains EMIS tables (refusing to overwrite): "
            + ", ".join(overlapping)
        )

    tables = ordered_tables(metadata)
    counts = {}

    with source.begin() as src, target.begin() as dst:
        metadata.create_all(dst)

        for table in tables:
            result = src.execution_options(stream_results=True).execute(table.select())
            keys = list(result.keys())
            moved = 0
            while True:
                rows = result.fetchmany(CHUNK_SIZE)
                if not rows:
                    break
                dst.execute(
                    table.insert(), [dict(zip(keys, row)) for row in rows]
                )
                moved += len(rows)
            counts[table.name] = moved
            print(f"  {table.name:<28} {moved:>8} rows")

        reset_sequences(dst, metadata)

    # Verify counts in a fresh transaction.
    with source.connect() as src, target.connect() as dst:
        problems = []
        for name, expected in counts.items():
            actual = dst.execute(
                f'SELECT COUNT(*) FROM "{name}"'
            ).scalar_one()
            if actual != expected:
                problems.append(f"{name}: source={expected} target={actual}")
        if problems:
            raise SystemExit("Count verification failed:\n  " + "\n  ".join(problems))

    print(f"\nMigration complete. {sum(counts.values())} rows copied and verified.")


if __name__ == "__main__":
    main()
