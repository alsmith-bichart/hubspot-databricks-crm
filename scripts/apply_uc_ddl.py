"""Apply uc/ddl/*.sql in lexical order via Databricks SQL warehouse.

UC DDL is owned by CI/CD — ingest does not CREATE tables.
Canonical FQNs use catalog `crm` / schema `bronze`; rewritten from Settings
(or --catalog / --bronze-schema) so the same files apply to crm_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.bronze_loader import connect, _execute
from ingestion.config import load_settings
from ingestion.ddl_rewrite import rewrite_sql

DDL_DIR = ROOT / "uc" / "ddl"


def _split_statements(sql_text: str) -> list[str]:
    lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    parts = [p.strip() for p in text.split(";")]
    return [p for p in parts if p]


def apply_ddl(catalog: str | None = None, bronze_schema: str | None = None) -> None:
    if catalog:
        os.environ["DATABRICKS_CATALOG"] = catalog
    if bronze_schema:
        os.environ["DATABRICKS_BRONZE_SCHEMA"] = bronze_schema

    settings = load_settings()
    files = sorted(DDL_DIR.glob("*.sql"))
    if not files:
        raise SystemExit(f"No DDL files in {DDL_DIR}")

    print(
        f"Applying {len(files)} DDL files → "
        f"{settings.catalog}.{settings.bronze_schema}"
    )
    with connect(settings) as conn:
        for path in files:
            print(f"  {path.name}")
            raw = path.read_text(encoding="utf-8")
            text = rewrite_sql(raw, settings.catalog, settings.bronze_schema)
            for stmt in _split_statements(text):
                _execute(conn, stmt)
    print("UC DDL apply complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply uc/ddl to a UC catalog")
    parser.add_argument(
        "--catalog",
        default=None,
        help="UC catalog (default: DATABRICKS_CATALOG or crm)",
    )
    parser.add_argument(
        "--bronze-schema",
        default=None,
        help="Bronze schema (default: DATABRICKS_BRONZE_SCHEMA or bronze)",
    )
    args = parser.parse_args()
    apply_ddl(catalog=args.catalog, bronze_schema=args.bronze_schema)


if __name__ == "__main__":
    main()
