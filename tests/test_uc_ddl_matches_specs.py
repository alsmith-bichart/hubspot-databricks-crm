"""Ensure uc/ddl CREATE TABLE column lists match schemas/object_specs.py."""

from __future__ import annotations

import re
from pathlib import Path

from schemas.object_specs import (
    ASSOCIATION_SPECS,
    CRM_OBJECT_COLUMNS,
    DEAL_PIPELINE_STAGE_COLUMNS,
    OWNER_COLUMNS,
    column_names,
    staging_table_name,
)

ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = ROOT / "uc" / "ddl"

CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"
    r"(?P<fqn>`?[\w.]+`?)\s*\((?P<body>.*?)\)\s*USING\s+DELTA",
    re.IGNORECASE | re.DOTALL,
)
COL_RE = re.compile(r"`([^`]+)`\s+[A-Z]+", re.IGNORECASE)


def _expected() -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {
        "crm.bronze.contacts": column_names(CRM_OBJECT_COLUMNS),
        "crm.bronze.companies": column_names(CRM_OBJECT_COLUMNS),
        "crm.bronze.deals": column_names(CRM_OBJECT_COLUMNS),
        f"crm.bronze.{staging_table_name('contacts')}": column_names(
            CRM_OBJECT_COLUMNS
        ),
        f"crm.bronze.{staging_table_name('companies')}": column_names(
            CRM_OBJECT_COLUMNS
        ),
        f"crm.bronze.{staging_table_name('deals')}": column_names(
            CRM_OBJECT_COLUMNS
        ),
        "crm.bronze.owners": column_names(OWNER_COLUMNS),
        "crm.bronze.deal_pipeline_stages": column_names(
            DEAL_PIPELINE_STAGE_COLUMNS
        ),
    }
    for assoc in ASSOCIATION_SPECS:
        expected[f"crm.bronze.{assoc.table_name}"] = column_names(assoc.columns)
    return expected


def _parse_ddl_tables() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(DDL_DIR.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for match in CREATE_RE.finditer(text):
            fqn = match.group("fqn").replace("`", "")
            cols = COL_RE.findall(match.group("body"))
            found[fqn] = cols
    return found


def test_all_expected_tables_have_ddl() -> None:
    found = _parse_ddl_tables()
    expected = _expected()
    missing = sorted(set(expected) - set(found))
    assert not missing, f"DDL missing for tables: {missing}"


def test_ddl_columns_match_object_specs() -> None:
    found = _parse_ddl_tables()
    expected = _expected()
    for fqn, cols in expected.items():
        assert fqn in found, f"missing DDL for {fqn}"
        assert found[fqn] == cols, (
            f"column mismatch for {fqn}\n"
            f"  specs: {cols}\n"
            f"  ddl:   {found[fqn]}"
        )
