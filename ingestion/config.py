from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "configs" / ".env"

REQUIRED_VARS = (
    "HUBSPOT_TOKEN",
    "DATABRICKS_HOST",
    "DATABRICKS_HTTP_PATH",
    "DATABRICKS_TOKEN",
)

SECRET_SCOPE = "hubspot-crm"


def _hydrate_secrets_from_dbutils() -> None:
    """Fill missing env vars from Databricks secret scope (serverless Jobs)."""
    if all(os.getenv(name) for name in REQUIRED_VARS):
        return
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
    except Exception:
        return

    scope = os.getenv("HUBSPOT_SECRET_SCOPE", SECRET_SCOPE)
    for name in REQUIRED_VARS:
        if not os.getenv(name):
            os.environ[name] = dbutils.secrets.get(scope=scope, key=name)


@dataclass(frozen=True)
class Settings:
    hubspot_token: str
    databricks_host: str
    databricks_http_path: str
    databricks_token: str
    catalog: str = "crm"
    bronze_schema: str = "bronze"

    def fqn(self, schema: str, table: str) -> str:
        return f"{self.catalog}.{schema}.{table}"

    def bronze(self, table: str) -> str:
        return self.fqn(self.bronze_schema, table)

    def bronze_staging(self, table: str) -> str:
        return self.bronze(f"_stg_{table}")


def load_settings() -> Settings:
    """Load settings from process env; optionally overlay configs/.env if present.

    Databricks serverless Jobs read secrets from scope hubspot-crm via dbutils.
    Local/dev may use configs/.env.
    """
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH, override=False)
    else:
        load_dotenv(override=False)

    _hydrate_secrets_from_dbutils()

    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in {ENV_PATH} locally, or in Databricks secret scope "
            f"{SECRET_SCOPE} for Jobs."
        )

    host = os.environ["DATABRICKS_HOST"].strip()
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")

    return Settings(
        hubspot_token=os.environ["HUBSPOT_TOKEN"].strip(),
        databricks_host=host,
        databricks_http_path=os.environ["DATABRICKS_HTTP_PATH"].strip(),
        databricks_token=os.environ["DATABRICKS_TOKEN"].strip(),
        catalog=os.getenv("DATABRICKS_CATALOG", "crm").strip() or "crm",
        bronze_schema=os.getenv("DATABRICKS_BRONZE_SCHEMA", "bronze").strip()
        or "bronze",
    )
