"""Bronze load helpers — shared across objects. Contacts SCD2 first."""

from __future__ import annotations

from typing import Any, Sequence

from databricks import sql
from databricks.sql.client import Connection

from configs.config import Settings
from schemas.object_specs import CONTACT_CHANGE_ATTRS, CONTACT_COLUMNS


def connect(settings: Settings) -> Connection:
    return sql.connect(
        server_hostname=settings.databricks_host,
        http_path=settings.databricks_http_path,
        access_token=settings.databricks_token,
    )


def _execute(conn: Connection, statement: str) -> None:
    with conn.cursor() as cur:
        cur.execute(statement)


def assert_contacts_tables(conn: Connection, settings: Settings) -> None:
    with conn.cursor() as cur:
        cur.execute(f"SHOW TABLES IN {settings.catalog}.{settings.bronze_schema}")
        names = {row[1] for row in cur.fetchall()}
    for table in ("contacts", "_stg_contacts"):
        if table not in names:
            raise RuntimeError(
                f"Missing {settings.bronze(table)}. Create DDL in SQL Editor."
            )


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


def scd2_merge_contacts(
    conn: Connection,
    settings: Settings,
    *,
    close_missing: bool = True,
) -> None:
    target = settings.bronze("contacts")
    staging = settings.bronze("_stg_contacts")
    change_pred = " OR ".join(
        f"NOT (t.`{c}` <=> s.`{c}`)" for c in CONTACT_CHANGE_ATTRS
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

    cols = ", ".join(f"`{c}`" for c in CONTACT_COLUMNS)
    _execute(
        conn,
        f"""
        INSERT INTO {target} ({cols})
        SELECT {", ".join(f"s.`{c}`" for c in CONTACT_COLUMNS)}
        FROM {staging} s
        WHERE NOT EXISTS (
          SELECT 1 FROM {target} t
          WHERE t.hubspot_id = s.hubspot_id AND t._is_current = true
        )
        """,
    )


def count_current_contacts(conn: Connection, settings: Settings) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) FROM {settings.bronze('contacts')} WHERE _is_current = true"
        )
        return int(cur.fetchone()[0])


def count_contacts(conn: Connection, settings: Settings) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {settings.bronze('contacts')}")
        return int(cur.fetchone()[0])
