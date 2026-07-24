#!/usr/bin/env python3
"""Copy ForgeMind AI records between SQLAlchemy databases.

Use against an empty target database and create a backup first.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import create_engine, inspect, text
from backend.app.db import Base
import backend.app.models  # noqa: F401


def normalize(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--allow-nonempty", action="store_true")
    args = parser.parse_args()
    source = create_engine(normalize(args.source), pool_pre_ping=True)
    target = create_engine(normalize(args.target), pool_pre_ping=True)
    Base.metadata.create_all(target)

    with source.connect() as src, target.begin() as dst:
        for table in Base.metadata.sorted_tables:
            existing = dst.execute(text(f'SELECT COUNT(*) FROM "{table.name}"')).scalar_one()
            if existing and not args.allow_nonempty:
                raise SystemExit(f"Target table {table.name} is not empty. Aborting.")
            rows = [dict(row._mapping) for row in src.execute(table.select())]
            if rows:
                dst.execute(table.insert(), rows)
            print(f"{table.name}: {len(rows)} rows copied")

        if target.dialect.name == "postgresql":
            for table in Base.metadata.sorted_tables:
                if "id" in table.c and table.c.id.autoincrement:
                    quoted_table = target.dialect.identifier_preparer.quote(table.name)
                    sequence_sql = text(
                        f"SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {quoted_table}), 1), "
                        f"(SELECT COUNT(*) > 0 FROM {quoted_table}))"
                    )
                    dst.execute(sequence_sql, {"table_name": table.name})
    print("Migration completed. Verify row counts and application behavior before switching environments.")


if __name__ == "__main__":
    main()
