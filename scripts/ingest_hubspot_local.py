#!/usr/bin/env python3
"""Module 2 Option B — HubSpot → crm.bronze via local .env + SQL warehouse.

Token never enters a Databricks notebook.
Usage:
  cp .env.example .env   # fill values
  pip install -r requirements.txt
  python scripts/ingest_hubspot_local.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from databricks import sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

BASE = "https://api.hubapi.com"
PAGE_LIMIT = 100
MAX_PAGES = 200
BATCH_INSERT = 200

CONTACT_PROPS = [
    "email",
    "firstname",
    "lastname",
    "company",
    "jobtitle",
    "lifecyclestage",
    "hs_lead_status",
    "createdate",
    "lastmodifieddate",
    "hubspot_owner_id",
]
COMPANY_PROPS = [
    "name",
    "domain",
    "industry",
    "city",
    "state",
    "country",
    "numberofemployees",
    "createdate",
    "hs_lastmodifieddate",
    "hubspot_owner_id",
]
DEAL_PROPS = [
    "dealname",
    "amount",
    "dealstage",
    "pipeline",
    "closedate",
    "createdate",
    "hs_lastmodifieddate",
    "hubspot_owner_id",
    "hs_is_closed_won",
    "hs_is_closed",
]

DDL = """
CREATE TABLE IF NOT EXISTS crm.bronze.{table} (
  hubspot_id STRING,
  object_type STRING,
  properties_json STRING,
  raw_json STRING,
  hubspot_created_at STRING,
  hubspot_updated_at STRING,
  archived STRING,
  _ingested_at TIMESTAMP,
  _source_system STRING
) USING DELTA
"""


def require_env(*keys: str) -> dict[str, str]:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example → .env and fill values.", file=sys.stderr)
        sys.exit(1)
    return {k: os.environ[k] for k in keys}


def hs_get(token: str, path: str, params: dict[str, Any] | None = None) -> dict:
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(5):
        r = requests.get(url, headers=headers, params=params or {}, timeout=60)
        if r.status_code == 429:
            wait = 2**attempt
            print(f"429 rate limit; sleep {wait}s")
            time.sleep(wait)
            continue
        if not r.ok:
            raise RuntimeError(f"HubSpot {r.status_code} {path}: {r.text[:500]}")
        return r.json()
    raise RuntimeError(f"HubSpot rate limit exhausted: {path}")


def list_objects(token: str, object_type: str, properties: list[str]) -> list[dict]:
    results: list[dict] = []
    after = None
    for page in range(MAX_PAGES):
        params: dict[str, Any] = {
            "limit": PAGE_LIMIT,
            "properties": ",".join(properties),
            "archived": "false",
        }
        if after:
            params["after"] = after
        data = hs_get(token, f"/crm/v3/objects/{object_type}", params)
        batch = data.get("results") or []
        results.extend(batch)
        after = ((data.get("paging") or {}).get("next") or {}).get("after")
        print(f"{object_type}: page {page + 1}, +{len(batch)} (total {len(results)})")
        if not after:
            break
        time.sleep(0.15)
    return results


def list_owners(token: str) -> list[dict]:
    results: list[dict] = []
    after = None
    for page in range(MAX_PAGES):
        params: dict[str, Any] = {"limit": PAGE_LIMIT, "archived": "false"}
        if after:
            params["after"] = after
        data = hs_get(token, "/crm/v3/owners", params)
        batch = data.get("results") or []
        results.extend(batch)
        after = ((data.get("paging") or {}).get("next") or {}).get("after")
        print(f"owners: page {page + 1}, +{len(batch)} (total {len(results)})")
        if not after:
            break
    return results


def list_deal_pipelines(token: str) -> list[dict]:
    data = hs_get(token, "/crm/v3/pipelines/deals")
    return data.get("results") or []


def to_rows(object_type: str, records: list[dict], ingested_at: str) -> list[tuple]:
    rows = []
    for r in records:
        rows.append(
            (
                str(r.get("id")),
                object_type,
                json.dumps(r.get("properties") or {}),
                json.dumps(r),
                r.get("createdAt"),
                r.get("updatedAt"),
                str(r.get("archived")),
                ingested_at,
                "hubspot",
            )
        )
    return rows


def pipeline_stage_rows(pipelines: list[dict], ingested_at: str) -> list[tuple]:
    rows = []
    for p in pipelines:
        pid = str(p.get("id"))
        for st in p.get("stages") or []:
            props = {
                "pipeline_id": pid,
                "pipeline_label": p.get("label"),
                "stage_id": st.get("id"),
                "stage_label": st.get("label"),
                "display_order": st.get("displayOrder"),
                "metadata": st.get("metadata") or {},
            }
            rows.append(
                (
                    f"{pid}:{st.get('id')}",
                    "deal_pipeline_stage",
                    json.dumps(props),
                    json.dumps({"pipeline": p, "stage": st}),
                    p.get("createdAt"),
                    p.get("updatedAt"),
                    str(p.get("archived")),
                    ingested_at,
                    "hubspot",
                )
            )
    return rows


def merge_table(cursor, table: str, rows: list[tuple]) -> None:
    full = f"crm.bronze.{table}"
    stg = f"crm.bronze._stg_{table}"
    cursor.execute(DDL.format(table=table))
    cursor.execute(DDL.format(table=f"_stg_{table}"))
    cursor.execute(f"TRUNCATE TABLE {stg}")
    if not rows:
        print(f"{full}: 0 rows — skip MERGE")
        return
    insert_sql = f"""
        INSERT INTO {stg} (
          hubspot_id, object_type, properties_json, raw_json,
          hubspot_created_at, hubspot_updated_at, archived,
          _ingested_at, _source_system
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for i in range(0, len(rows), BATCH_INSERT):
        chunk = rows[i : i + BATCH_INSERT]
        cursor.executemany(insert_sql, chunk)
        print(f"{stg}: inserted {i + len(chunk)}/{len(rows)}")
    cursor.execute(
        f"""
        MERGE INTO {full} AS t
        USING {stg} AS s
        ON t.hubspot_id = s.hubspot_id
        WHEN MATCHED THEN UPDATE SET
          object_type = s.object_type,
          properties_json = s.properties_json,
          raw_json = s.raw_json,
          hubspot_created_at = s.hubspot_created_at,
          hubspot_updated_at = s.hubspot_updated_at,
          archived = s.archived,
          _ingested_at = s._ingested_at,
          _source_system = s._source_system
        WHEN NOT MATCHED THEN INSERT *
        """
    )
    cursor.execute(f"SELECT count(*) FROM {full}")
    n = cursor.fetchone()[0]
    print(f"{full}: MERGE done; count = {n}")


def main() -> None:
    env = require_env(
        "HUBSPOT_TOKEN",
        "DATABRICKS_HOST",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    )
    host = env["DATABRICKS_HOST"].removeprefix("https://").removeprefix("http://")
    token = env["HUBSPOT_TOKEN"]
    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    print("Fetching HubSpot…")
    contacts = list_objects(token, "contacts", CONTACT_PROPS)
    companies = list_objects(token, "companies", COMPANY_PROPS)
    deals = list_objects(token, "deals", DEAL_PROPS)
    owners = list_owners(token)
    pipelines = list_deal_pipelines(token)
    print(
        f"Fetched contacts={len(contacts)} companies={len(companies)} "
        f"deals={len(deals)} owners={len(owners)} pipelines={len(pipelines)}"
    )

    print(f"Connecting to Databricks SQL warehouse @ {host}…")
    with sql.connect(
        server_hostname=host,
        http_path=env["DATABRICKS_HTTP_PATH"],
        access_token=env["DATABRICKS_TOKEN"],
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS crm.bronze")
            merge_table(cur, "contacts", to_rows("contacts", contacts, ingested_at))
            merge_table(cur, "companies", to_rows("companies", companies, ingested_at))
            merge_table(cur, "deals", to_rows("deals", deals, ingested_at))
            merge_table(cur, "owners", to_rows("owners", owners, ingested_at))
            merge_table(
                cur,
                "deal_pipeline_stages",
                pipeline_stage_rows(pipelines, ingested_at),
            )

    print("Done. Verify counts in Databricks SQL editor.")


if __name__ == "__main__":
    main()
