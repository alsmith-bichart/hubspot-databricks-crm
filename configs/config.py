from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

CONFIGS_DIR = Path(__file__).resolve().parent
ENV_PATH = CONFIGS_DIR / ".env"
ROOT = CONFIGS_DIR.parent


@dataclass(frozen=True)
class Settings:
    hubspot_token: str
    databricks_host: str
    databricks_http_path: str
    databricks_token: str
    catalog: str = "crm_dev"
    bronze_schema: str = "bronze"

    def bronze(self, table: str) -> str:
        return f"{self.catalog}.{self.bronze_schema}.{table}"


def load_settings() -> Settings:
    load_dotenv(ENV_PATH, override=False)

    http_path = (
        os.getenv("DATABRICKS_HTTP_PATH") or os.getenv("HTTP_PATH") or ""
    ).strip()
    missing = [
        k
        for k in ("HUBSPOT_TOKEN", "DATABRICKS_HOST", "DATABRICKS_TOKEN")
        if not os.getenv(k)
    ]
    if not http_path:
        missing.append("HTTP_PATH or DATABRICKS_HTTP_PATH")
    if missing:
        raise RuntimeError(f"Missing env: {', '.join(missing)}")

    host = os.environ["DATABRICKS_HOST"].strip()
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")

    return Settings(
        hubspot_token=os.environ["HUBSPOT_TOKEN"].strip(),
        databricks_host=host,
        databricks_http_path=http_path,
        databricks_token=os.environ["DATABRICKS_TOKEN"].strip(),
    )
