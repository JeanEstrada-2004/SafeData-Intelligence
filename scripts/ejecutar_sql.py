"""Run a .sql file using the existing SQLAlchemy engine (no psql needed).

Usage examples:
  python scripts/run_sql.py sql/migration_auth.sql
  python scripts/run_sql.py db_migration_map.sql

It uses app.database.engine which reads your .env (DATABASE_URL or parts),
so make sure the .env is configured.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.database import engine  # uses .env
from sqlalchemy import text


def iter_statements(sql: str):
    """Very simple SQL splitter for our migration files (no functions).

    Splits on ';' line endings, skips empty statements and '--' comments.
    """
    buf: list[str] = []
    for raw_line in sql.splitlines():
        line = raw_line.strip()
        # strip inline comments that start a line
        if line.startswith("--") or not line:
            continue
        buf.append(raw_line)
        if line.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                yield stmt
            buf = []
    # tail
    tail = "\n".join(buf).strip()
    if tail:
        yield tail


def main(path: str) -> None:
    sql_path = Path(path)
    if not sql_path.exists():
        raise SystemExit(f"SQL file not found: {sql_path}")

    sql_text = sql_path.read_text(encoding="utf-8")
    stmts = list(iter_statements(sql_text))
    print(f"Executing {len(stmts)} statements from {sql_path}...")

    with engine.begin() as conn:
        for i, stmt in enumerate(stmts, 1):
            conn.exec_driver_sql(stmt)
            print(f"  ok {i}")
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_sql.py <file.sql>")
        raise SystemExit(2)
    main(sys.argv[1])

