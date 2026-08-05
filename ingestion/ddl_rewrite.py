"""Rewrite canonical crm.bronze DDL onto a target catalog/schema."""

from __future__ import annotations

import re

CANONICAL_CATALOG = "crm"
CANONICAL_SCHEMA = "bronze"
CANONICAL_FQN = f"{CANONICAL_CATALOG}.{CANONICAL_SCHEMA}"


def rewrite_sql(sql_text: str, catalog: str, bronze_schema: str) -> str:
    """Map canonical crm.bronze DDL onto the target catalog/schema."""
    target_fqn = f"{catalog}.{bronze_schema}"
    out = sql_text.replace(CANONICAL_FQN, target_fqn)
    out = re.sub(
        rf"\bCREATE\s+CATALOG\s+IF\s+NOT\s+EXISTS\s+{re.escape(CANONICAL_CATALOG)}\b",
        f"CREATE CATALOG IF NOT EXISTS {catalog}",
        out,
        flags=re.IGNORECASE,
    )
    return out
