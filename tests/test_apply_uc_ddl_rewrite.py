"""Unit tests for DDL catalog/schema rewrite."""

from ingestion.ddl_rewrite import rewrite_sql


def test_rewrite_table_fqn() -> None:
    sql = "CREATE TABLE IF NOT EXISTS crm.bronze.contacts (id STRING) USING DELTA;"
    out = rewrite_sql(sql, "crm_dev", "bronze")
    assert "crm_dev.bronze.contacts" in out
    assert "crm.bronze.contacts" not in out


def test_rewrite_catalog_create() -> None:
    sql = "CREATE CATALOG IF NOT EXISTS crm;"
    out = rewrite_sql(sql, "crm_dev", "bronze")
    assert out.strip() == "CREATE CATALOG IF NOT EXISTS crm_dev;"


def test_rewrite_prod_noop() -> None:
    sql = "CREATE SCHEMA IF NOT EXISTS crm.bronze;"
    out = rewrite_sql(sql, "crm", "bronze")
    assert out == sql
