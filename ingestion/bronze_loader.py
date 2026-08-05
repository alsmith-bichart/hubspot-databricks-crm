from __future__ import annotations

from typing import Any, Sequence

from databricks import sql
from databricks.sql.client import Connection

from ingestion.config import Settings
from schemas.object_specs import (
    ASSOCIATION_SPECS,
    CRM_OBJECT_SPECS,
    DEAL_PIPELINE_STAGE_COLUMNS,
    OWNER_COLUMNS,
    SCD2_CHANGE_ATTRIBUTES,
    ObjectSpec,
    column_names,
    object_columns,
    staging_table_name,
)

REQUIRED_BRONZE_TABLES: tuple[str, ...] = tuple(
    [spec.table_name for spec in CRM_OBJECT_SPECS]
    + [staging_table_name(spec.table_name) for spec in CRM_OBJECT_SPECS]
    + ["owners", "deal_pipeline_stages"]
    + [assoc.table_name for assoc in ASSOCIATION_SPECS]
)

INSERT_BATCH_SIZE = 200


def connect(settings: Settings) -> Connection:
    try:
        return sql.connect(
            server_hostname=settings.databricks_host,
            http_path=settings.databricks_http_path,
            access_token=settings.databricks_token,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to connect to Databricks SQL warehouse. "
            "Check DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN "
            f"in configs/.env ({exc})"
        ) from exc


def _execute(conn: Connection, statement: str) -> None:
    with conn.cursor() as cur:
        cur.execute(statement)


def _fetchone(
    conn: Connection,
    statement: str,
    parameters: Sequence[Any] | None = None,
) -> Any:
    with conn.cursor() as cur:
        if parameters is None:
            cur.execute(statement)
        else:
            cur.execute(statement, parameters)
        return cur.fetchone()


def assert_bronze_tables_exist(conn: Connection, settings: Settings) -> None:
    """Fail clearly if UC tables are missing. DDL is owned by CI/CD (uc/ddl)."""
    missing: list[str] = []
    for table in REQUIRED_BRONZE_TABLES:
        fqn = settings.bronze(table)
        try:
            _fetchone(conn, f"DESCRIBE TABLE {fqn}")
        except Exception:
            missing.append(fqn)
    if missing:
        raise RuntimeError(
            "Required bronze tables missing (apply UC DDL via CI/CD first): "
            + ", ".join(missing)
            + ". Run: python scripts/apply_uc_ddl.py "
            "or databricks bundle run apply_uc_ddl -t dev"
        )


def _quote_ident(name: str) -> str:
    return f"`{name}`"


def insert_rows(
    conn: Connection,
    table_fqn: str,
    rows: list[dict[str, Any]],
    columns: Sequence[str],
) -> int:
    if not rows:
        return 0

    col_sql = ", ".join(_quote_ident(c) for c in columns)
    placeholders = ", ".join(["?"] * len(columns))
    statement = f"INSERT INTO {table_fqn} ({col_sql}) VALUES ({placeholders})"

    inserted = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), INSERT_BATCH_SIZE):
            batch = rows[i : i + INSERT_BATCH_SIZE]
            values = [tuple(row.get(col) for col in columns) for row in batch]
            cur.executemany(statement, values)
            inserted += len(batch)
    return inserted


def append_bronze(
    conn: Connection,
    table_fqn: str,
    rows: list[dict[str, Any]],
    columns: Sequence[str],
) -> int:
    """Append-only load — keeps full history across runs."""
    return insert_rows(conn, table_fqn, rows, columns)


def _change_predicate(alias_t: str = "t", alias_s: str = "s") -> str:
    parts = []
    for col in SCD2_CHANGE_ATTRIBUTES:
        t = f"{alias_t}.{_quote_ident(col)}"
        s = f"{alias_s}.{_quote_ident(col)}"
        parts.append(
            f"COALESCE(CAST({t} AS STRING), '') <> COALESCE(CAST({s} AS STRING), '')"
        )
    return " OR ".join(parts)


def load_staging(
    conn: Connection,
    staging_fqn: str,
    rows: list[dict[str, Any]],
    columns: Sequence[str],
) -> int:
    _execute(conn, f"TRUNCATE TABLE {staging_fqn}")
    return insert_rows(conn, staging_fqn, rows, columns)


def merge_scd2_crm_object(
    conn: Connection,
    target_fqn: str,
    staging_fqn: str,
    columns: Sequence[str],
    *,
    close_missing: bool = True,
) -> None:
    """SCD2 merge for contacts/companies/deals.

    - Close current rows that changed vs staging
    - Optionally close currents missing from staging (full extract)
    - Insert staging rows that have no open current (new + changed)
    """
    changed = _change_predicate("t", "s")

    # Warehouse SQL does not support UPDATE...FROM; use EXISTS + scalar subquery.
    _execute(
        conn,
        f"""
        UPDATE {target_fqn} AS t
        SET `_is_current` = false,
            `_valid_to` = (
                SELECT MAX(s.`_valid_from`)
                FROM {staging_fqn} AS s
                WHERE s.`hubspot_id` = t.`hubspot_id`
            )
        WHERE t.`_is_current` = true
          AND EXISTS (
              SELECT 1
              FROM {staging_fqn} AS s
              WHERE s.`hubspot_id` = t.`hubspot_id`
                AND ({changed})
          )
        """,
    )

    if close_missing:
        _execute(
            conn,
            f"""
            UPDATE {target_fqn} AS t
            SET `_is_current` = false,
                `_valid_to` = (
                    SELECT MAX(s.`_valid_from`) FROM {staging_fqn} AS s
                )
            WHERE t.`_is_current` = true
              AND NOT EXISTS (
                  SELECT 1 FROM {staging_fqn} AS s
                  WHERE s.`hubspot_id` = t.`hubspot_id`
              )
            """,
        )

    col_list = ", ".join(_quote_ident(c) for c in columns)
    select_list = ", ".join(f"s.{_quote_ident(c)}" for c in columns)
    _execute(
        conn,
        f"""
        INSERT INTO {target_fqn} ({col_list})
        SELECT {select_list}
        FROM {staging_fqn} AS s
        WHERE NOT EXISTS (
            SELECT 1 FROM {target_fqn} AS t
            WHERE t.`hubspot_id` = s.`hubspot_id`
              AND t.`_is_current` = true
        )
        """,
    )


def upsert_scd2(
    conn: Connection,
    settings: Settings,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    columns: Sequence[str],
    close_missing: bool = True,
) -> int:
    """Stage rows then SCD2-merge into bronze CRM object table."""
    target = settings.bronze(table_name)
    staging = settings.bronze(staging_table_name(table_name))
    staged = load_staging(conn, staging, rows, columns)
    merge_scd2_crm_object(
        conn, target, staging, columns, close_missing=close_missing
    )
    return staged


def assert_one_current_per_business_key(
    conn: Connection,
    table_fqn: str,
    business_key: str = "hubspot_id",
    *,
    label: str,
) -> None:
    """Fail if any business key has more than one _is_current=true row."""
    key = _quote_ident(business_key)
    row = _fetchone(
        conn,
        f"""
        SELECT COUNT(*) FROM (
            SELECT {key}
            FROM {table_fqn}
            WHERE `_is_current` = true
            GROUP BY {key}
            HAVING COUNT(*) > 1
        ) d
        """,
    )
    bad = int(row[0]) if row else 0
    if bad:
        raise ValueError(
            f"{label}: {bad} {business_key} values have multiple current rows "
            f"in {table_fqn}"
        )


def assert_required_columns_non_null_current(
    conn: Connection,
    table_fqn: str,
    columns: Sequence[str],
    *,
    label: str,
) -> None:
    """Fail if any required column is null/blank on current SCD2 rows."""
    for col in columns:
        ident = _quote_ident(col)
        row = _fetchone(
            conn,
            f"SELECT COUNT(*) FROM {table_fqn} "
            f"WHERE `_is_current` = true "
            f"AND ({ident} IS NULL OR TRIM(CAST({ident} AS STRING)) = '')",
        )
        bad = int(row[0]) if row else 0
        if bad:
            raise ValueError(
                f"{label}: {bad} current rows in {table_fqn} have null/blank {col}"
            )


def count_current(conn: Connection, table_fqn: str) -> int:
    row = _fetchone(
        conn,
        f"SELECT COUNT(*) FROM {table_fqn} WHERE `_is_current` = true",
    )
    return int(row[0]) if row else 0


def count_table(
    conn: Connection,
    table_fqn: str,
    *,
    run_id: str | None = None,
) -> int:
    if run_id is None:
        row = _fetchone(conn, f"SELECT COUNT(*) FROM {table_fqn}")
    else:
        row = _fetchone(
            conn,
            f"SELECT COUNT(*) FROM {table_fqn} "
            f"WHERE `_ingestion_run_id` = ?",
            (run_id,),
        )
    return int(row[0]) if row else 0


def assert_unique_keys(
    conn: Connection,
    table_fqn: str,
    key_columns: Sequence[str],
    *,
    label: str,
    run_id: str | None = None,
) -> None:
    """Fail if history/business key columns are not unique."""
    if not key_columns:
        raise ValueError(f"{label}: key_columns required")

    cols = ", ".join(_quote_ident(c) for c in key_columns)
    if run_id is None:
        total = count_table(conn, table_fqn)
        distinct_row = _fetchone(
            conn,
            f"SELECT COUNT(*) FROM (SELECT DISTINCT {cols} FROM {table_fqn}) d",
        )
    else:
        total = count_table(conn, table_fqn, run_id=run_id)
        distinct_row = _fetchone(
            conn,
            f"SELECT COUNT(*) FROM ("
            f"SELECT DISTINCT {cols} FROM {table_fqn} "
            f"WHERE `_ingestion_run_id` = ?"
            f") d",
            (run_id,),
        )
    distinct = int(distinct_row[0]) if distinct_row else 0
    if total != distinct:
        raise ValueError(
            f"{label}: key uniqueness failed on {table_fqn} "
            f"keys={list(key_columns)} total={total} distinct={distinct}"
        )


def assert_required_columns_non_null(
    conn: Connection,
    table_fqn: str,
    columns: Sequence[str],
    *,
    label: str,
    run_id: str | None = None,
) -> None:
    """Fail if any required column has null/blank values."""
    for col in columns:
        ident = _quote_ident(col)
        if run_id is None:
            row = _fetchone(
                conn,
                f"SELECT COUNT(*) FROM {table_fqn} "
                f"WHERE {ident} IS NULL OR TRIM(CAST({ident} AS STRING)) = ''",
            )
        else:
            row = _fetchone(
                conn,
                f"SELECT COUNT(*) FROM {table_fqn} "
                f"WHERE `_ingestion_run_id` = ? "
                f"AND ({ident} IS NULL OR TRIM(CAST({ident} AS STRING)) = '')",
                (run_id,),
            )
        bad = int(row[0]) if row else 0
        if bad:
            raise ValueError(
                f"{label}: {bad} rows in {table_fqn} have null/blank {col}"
            )


def object_column_names(spec: ObjectSpec) -> list[str]:
    return column_names(tuple(object_columns(spec)))


def owner_column_names() -> list[str]:
    return column_names(OWNER_COLUMNS)


def pipeline_stage_column_names() -> list[str]:
    return column_names(DEAL_PIPELINE_STAGE_COLUMNS)


def association_column_names(columns: tuple[tuple[str, str], ...]) -> list[str]:
    return column_names(columns)
