"""Bronze load helpers — SCD2 for CRM objects, append for dims/assocs."""

from __future__ import annotations

from typing import Any, Sequence

from databricks import sql
from databricks.sql.client import Connection

from configs.config import Settings
from schemas.object_specs import (
    CRM_CHANGE_ATTRS,
    CRM_OBJECT_COLUMNS,
    staging_table_name,
)

REQUIRED_BRONZE_TABLES = (
    "contacts",
    "_stg_contacts",
    "companies",
    "_stg_companies",
    "deals",
    "_stg_deals",
    "owners",
    "deal_pipeline_stages",
    "contact_company_associations",
    "deal_company_associations",
    "deal_contact_associations",
)


def connect(settings: Settings) -> Connection:
    return sql.connect(
        server_hostname=settings.databricks_host,
        http_path=settings.databricks_http_path,
        access_token=settings.databricks_token,
    )


def _execute(conn: Connection, statement: str) -> None:
    with conn.cursor() as cur:
        cur.execute(statement)


def list_bronze_tables(conn: Connection, settings: Settings) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(f"SHOW TABLES IN {settings.catalog}.{settings.bronze_schema}")
        return {row[1] for row in cur.fetchall()}


def assert_tables(
    conn: Connection,
    settings: Settings,
    tables: Sequence[str],
) -> None:
    names = list_bronze_tables(conn, settings)
    missing = [t for t in tables if t not in names]
    if missing:
        raise RuntimeError(
            "Missing bronze tables: "
            + ", ".join(settings.bronze(t) for t in missing)
            + ". Run uc/ddl/*.sql in SQL Editor."
        )


def assert_bronze_tables(conn: Connection, settings: Settings) -> None:
    assert_tables(conn, settings, REQUIRED_BRONZE_TABLES)


def assert_contacts_tables(conn: Connection, settings: Settings) -> None:
    assert_tables(conn, settings, ("contacts", "_stg_contacts"))


def truncate_table(conn: Connection, table_fqn: str) -> None:
    _execute(conn, f"TRUNCATE TABLE {table_fqn}")


def insert_rows(
    conn: Connection,
    table_fqn: str,
    columns: Sequence[str],
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0
    col_sql = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(["?"] * len(columns))
    sql_text = f"INSERT INTO {table_fqn} ({col_sql}) VALUES ({placeholders})"
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(sql_text, [row[c] for c in columns])
    return len(rows)


def append_rows(
    conn: Connection,
    settings: Settings,
    table_name: str,
    columns: Sequence[str],
    rows: list[dict[str, Any]],
) -> int:
    """Insert into an append-only bronze table (owners, stages, assocs)."""
    return insert_rows(conn, settings.bronze(table_name), columns, rows)


def scd2_merge(
    conn: Connection,
    settings: Settings,
    object_type: str,
    *,
    close_missing: bool = True,
) -> None:
    """Close changed/missing current rows, then insert new current versions.

    object_type: contacts | companies | deals
    """
    target = settings.bronze(object_type)
    staging = settings.bronze(staging_table_name(object_type))
    change_pred = " OR ".join(
        f"NOT (t.`{c}` <=> s.`{c}`)" for c in CRM_CHANGE_ATTRS
    )

    _execute(
        conn,
        f"""
        MERGE INTO {target} AS t
        USING {staging} AS s
        ON t.hubspot_id = s.hubspot_id AND t._is_current = true
        WHEN MATCHED AND ({change_pred}) THEN UPDATE SET
          t._valid_to = s._valid_from,
          t._is_current = false
        """,
    )

    if close_missing:
        _execute(
            conn,
            f"""
            UPDATE {target} AS t
            SET _valid_to = current_timestamp(), _is_current = false
            WHERE t._is_current = true
              AND NOT EXISTS (
                SELECT 1 FROM {staging} s WHERE s.hubspot_id = t.hubspot_id
              )
            """,
        )

    cols = ", ".join(f"`{c}`" for c in CRM_OBJECT_COLUMNS)
    _execute(
        conn,
        f"""
        INSERT INTO {target} ({cols})
        SELECT {", ".join(f"s.`{c}`" for c in CRM_OBJECT_COLUMNS)}
        FROM {staging} s
        WHERE NOT EXISTS (
          SELECT 1 FROM {target} t
          WHERE t.hubspot_id = s.hubspot_id AND t._is_current = true
        )
        """,
    )


def scd2_merge_contacts(
    conn: Connection,
    settings: Settings,
    *,
    close_missing: bool = True,
) -> None:
    scd2_merge(conn, settings, "contacts", close_missing=close_missing)


def count_rows(conn: Connection, table_fqn: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_fqn}")
        return int(cur.fetchone()[0])


def count_current(conn: Connection, settings: Settings, object_type: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) FROM {settings.bronze(object_type)} "
            f"WHERE _is_current = true"
        )
        return int(cur.fetchone()[0])


def count_current_contacts(conn: Connection, settings: Settings) -> int:
    return count_current(conn, settings, "contacts")


def count_contacts(conn: Connection, settings: Settings) -> int:
    return count_rows(conn, settings.bronze("contacts"))
