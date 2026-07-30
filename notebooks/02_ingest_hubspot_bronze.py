# Databricks notebook source
# MAGIC %md
# MAGIC # Module 2 — HubSpot → `crm.bronze` (custom notebook)
# MAGIC
# MAGIC **Prereq:** Module 1 schemas exist. HubSpot Private App token ready.
# MAGIC
# MAGIC ### Auth (Free Edition — no secret scopes)
# MAGIC 1. Set widget **HubSpot token** at the top
# MAGIC 2. Run All
# MAGIC 3. Clear widget when finished
# MAGIC
# MAGIC Optional local `.env` path (token never in Databricks): see `docs/module2_secrets.md`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0) Config + auth

# COMMAND ----------

from datetime import datetime, timezone
import json
import time
import urllib.parse
import urllib.request
import urllib.error

from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    TimestampType,
)

CATALOG = "crm"
BRONZE = f"{CATALOG}.bronze"
BASE = "https://api.hubapi.com"
PAGE_LIMIT = 100
MAX_PAGES = 200  # safety cap for learning portal

# Free Edition: no secret scopes — widget is the auth path
dbutils.widgets.text("hs_token", "", "HubSpot token")

def get_token() -> str:
    # Optional: if a paid workspace adds scopes later, this still works
    try:
        t = dbutils.secrets.get(scope="hubspot", key="token")
        if t:
            print("Auth: secret scope hubspot/token")
            return t
    except Exception:
        pass
    t = dbutils.widgets.get("hs_token").strip()
    if not t:
        raise ValueError(
            "Free Edition has no secret scopes. Set the HubSpot token widget, "
            "or use local .env ingest (docs/module2_secrets.md)."
        )
    print("Auth: widget (clear after run)")
    return t

TOKEN = get_token()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) HubSpot HTTP helpers

# COMMAND ----------

def hs_get(path: str, params: dict | None = None) -> dict:
    """GET HubSpot API with Bearer token. Retries on 429."""
    q = urllib.parse.urlencode(params or {})
    url = f"{BASE}{path}" + (f"?{q}" if q else "")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="GET",
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                wait = 2 ** attempt
                print(f"429 rate limit; sleep {wait}s")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HubSpot {e.code} {path}: {body[:500]}") from e
    raise RuntimeError(f"HubSpot rate limit exhausted: {path}")


def list_all_objects(object_type: str, properties: list[str]) -> list[dict]:
    """Paginate GET /crm/v3/objects/{type}."""
    results = []
    after = None
    props = ",".join(properties)
    for page in range(MAX_PAGES):
        params = {"limit": PAGE_LIMIT, "properties": props, "archived": "false"}
        if after:
            params["after"] = after
        data = hs_get(f"/crm/v3/objects/{object_type}", params)
        batch = data.get("results") or []
        results.extend(batch)
        paging = (data.get("paging") or {}).get("next") or {}
        after = paging.get("after")
        print(f"{object_type}: page {page + 1}, +{len(batch)} (total {len(results)})")
        if not after:
            break
        time.sleep(0.15)  # gentle on rate limits
    return results


def list_owners() -> list[dict]:
    results = []
    after = None
    for page in range(MAX_PAGES):
        params = {"limit": PAGE_LIMIT, "archived": "false"}
        if after:
            params["after"] = after
        data = hs_get("/crm/v3/owners", params)
        batch = data.get("results") or []
        results.extend(batch)
        paging = (data.get("paging") or {}).get("next") or {}
        after = paging.get("after")
        print(f"owners: page {page + 1}, +{len(batch)} (total {len(results)})")
        if not after:
            break
    return results


def list_deal_pipelines() -> list[dict]:
    data = hs_get("/crm/v3/pipelines/deals")
    return data.get("results") or []

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Flatten → Delta MERGE into bronze

# COMMAND ----------

BRONZE_SCHEMA = StructType(
    [
        StructField("hubspot_id", StringType(), False),
        StructField("object_type", StringType(), False),
        StructField("properties_json", StringType(), True),
        StructField("raw_json", StringType(), True),
        StructField("hubspot_created_at", StringType(), True),
        StructField("hubspot_updated_at", StringType(), True),
        StructField("archived", StringType(), True),
        StructField("_ingested_at", TimestampType(), False),
        StructField("_source_system", StringType(), False),
    ]
)


def records_to_rows(object_type: str, records: list[dict], ingested_at: datetime) -> list[dict]:
    rows = []
    for r in records:
        rows.append(
            {
                "hubspot_id": str(r.get("id")),
                "object_type": object_type,
                "properties_json": json.dumps(r.get("properties") or {}),
                "raw_json": json.dumps(r),
                "hubspot_created_at": r.get("createdAt"),
                "hubspot_updated_at": r.get("updatedAt"),
                "archived": str(r.get("archived")),
                "_ingested_at": ingested_at,
                "_source_system": "hubspot",
            }
        )
    return rows


def merge_bronze(table_name: str, rows: list[dict]) -> None:
    full = f"{BRONZE}.{table_name}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRONZE}")
    if not rows:
        print(f"{full}: 0 rows — skip")
        return
    df = spark.createDataFrame(rows, schema=BRONZE_SCHEMA)
    df.createOrReplaceTempView("staging_bronze")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {full} (
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
    )
    spark.sql(
        f"""
        MERGE INTO {full} AS t
        USING staging_bronze AS s
        ON t.hubspot_id = s.hubspot_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
        """
    )
    n = spark.table(full).count()
    print(f"{full}: MERGE done; table count = {n}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Pull objects

# COMMAND ----------

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

ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)

contacts = list_all_objects("contacts", CONTACT_PROPS)
companies = list_all_objects("companies", COMPANY_PROPS)
deals = list_all_objects("deals", DEAL_PROPS)
owners = list_owners()
pipelines = list_deal_pipelines()

print(
    f"Fetched contacts={len(contacts)} companies={len(companies)} "
    f"deals={len(deals)} owners={len(owners)} pipelines={len(pipelines)}"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Land bronze tables + pipeline stages (nested → flat)

# COMMAND ----------

merge_bronze("contacts", records_to_rows("contacts", contacts, ingested_at))
merge_bronze("companies", records_to_rows("companies", companies, ingested_at))
merge_bronze("deals", records_to_rows("deals", deals, ingested_at))
merge_bronze("owners", records_to_rows("owners", owners, ingested_at))

# Pipelines: one row per stage (useful for gold dim_deal_stage)
stage_rows = []
for p in pipelines:
    pid = str(p.get("id"))
    for st in p.get("stages") or []:
        stage_rows.append(
            {
                "hubspot_id": f"{pid}:{st.get('id')}",
                "object_type": "deal_pipeline_stage",
                "properties_json": json.dumps(
                    {
                        "pipeline_id": pid,
                        "pipeline_label": p.get("label"),
                        "stage_id": st.get("id"),
                        "stage_label": st.get("label"),
                        "display_order": st.get("displayOrder"),
                        "metadata": st.get("metadata") or {},
                    }
                ),
                "raw_json": json.dumps({"pipeline": p, "stage": st}),
                "hubspot_created_at": p.get("createdAt"),
                "hubspot_updated_at": p.get("updatedAt"),
                "archived": str(p.get("archived")),
                "_ingested_at": ingested_at,
                "_source_system": "hubspot",
            }
        )

merge_bronze("deal_pipeline_stages", stage_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5) Verify (pass criteria)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'contacts' AS tbl, count(*) AS n FROM crm.bronze.contacts
# MAGIC UNION ALL SELECT 'companies', count(*) FROM crm.bronze.companies
# MAGIC UNION ALL SELECT 'deals', count(*) FROM crm.bronze.deals
# MAGIC UNION ALL SELECT 'owners', count(*) FROM crm.bronze.owners
# MAGIC UNION ALL SELECT 'deal_pipeline_stages', count(*) FROM crm.bronze.deal_pipeline_stages;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Spot-check one deal payload
# MAGIC SELECT hubspot_id, properties_json, _ingested_at
# MAGIC FROM crm.bronze.deals
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pass
# MAGIC - Counts > 0 for contacts / companies / deals (portal-dependent for others)
# MAGIC - Re-run this notebook → counts stay stable (MERGE, no duplicates)
# MAGIC - Token not printed in cell outputs
