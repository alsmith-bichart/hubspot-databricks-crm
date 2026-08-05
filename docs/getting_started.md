# Getting started

## Prerequisites

- Python 3.11+
- HubSpot private app token with CRM read scopes
- Databricks SQL warehouse + PAT with access to catalogs `crm` and `crm_dev`
- UC bronze tables applied from Git (`uc/ddl`) — **ingest does not CREATE tables**
- Permission to `CREATE CATALOG` (or pre-create `crm_dev`)

Read [operating_model.md](operating_model.md) for code vs UI and branch flow.

## Install

```bash
pip install -r requirements.txt
```

Optional: [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) for Asset Bundles.

## Configure

Put secrets in `configs/.env` (gitignored):

| Variable | Purpose |
|---|---|
| `HUBSPOT_TOKEN` | HubSpot private app access token |
| `DATABRICKS_HOST` | Workspace host (no `https://`) |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path |
| `DATABRICKS_TOKEN` | Databricks personal access token |

Optional: `DATABRICKS_CATALOG` (default `crm`), `DATABRICKS_BRONZE_SCHEMA` (default `bronze`).  
Use `crm_dev` for isolated local/dev work.

### Databricks Job secrets (UI)

Jobs do **not** use `configs/.env`. Create secret scope `hubspot-crm` with:

| Key | Value |
|---|---|
| `HUBSPOT_TOKEN` | HubSpot token |
| `DATABRICKS_HOST` | Workspace host |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path |
| `DATABRICKS_TOKEN` | PAT used by the connector from the Job |

Catalog is passed by the Job as `--catalog` (prod=`crm`, dev=`crm_dev`).

```bash
databricks secrets create-scope hubspot-crm --profile bicharttest
databricks secrets put-secret hubspot-crm HUBSPOT_TOKEN --profile bicharttest
# ... DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN
```

## Apply UC DDL (required before first ingest)

```bash
# Prod catalog (existing)
python scripts/apply_uc_ddl.py --catalog crm

# Dev catalog (isolated)
python scripts/apply_uc_ddl.py --catalog crm_dev

# Or via bundle Job
databricks bundle deploy -t dev --profile bicharttest
databricks bundle run apply_uc_ddl -t dev --profile bicharttest
```

## Run

### HubSpot smoke test

```bash
python tests/test_hubspot_client.py
```

### Full bronze ingest (local)

```bash
python scripts/ingest_bronze.py --catalog crm       # prod tables
python scripts/ingest_bronze.py --catalog crm_dev   # dev tables
```

1. Creates `run_id`
2. Asserts required bronze tables exist (fails with apply DDL hint if missing)
3. Contacts/companies/deals → SCD2 merge
4. Owners, stages, associations → append
5. Prints counts

### Databricks Job

Job definition synced from Git; **schedule set in Jobs UI**.

- Compute: serverless
- Catalog: `crm` (main) / `crm_dev` (dev) via `--catalog`
- Secrets: scope `hubspot-crm`
- Deploy does not run ingest; re-run from UI or:
  `databricks bundle run ingest_bronze -t prod --profile bicharttest`

### Bronze quality (sampled)

```bash
python tests/test_bronze_quality.py
python tests/test_bronze_quality.py --limit 10
```

### Unit tests (CI)

```bash
pytest tests/test_validators.py tests/test_config_env.py tests/test_apply_uc_ddl_rewrite.py -q
```

## Destructive schema reset (manual)

```bash
# Review uc/ops/drop_scd2_crm_tables.sql, run manually, then:
python scripts/apply_uc_ddl.py
python scripts/ingest_bronze.py
```

## Verify in Databricks

```sql
SHOW TABLES IN crm.bronze;

SELECT COUNT(*) FROM crm.bronze.contacts WHERE _is_current;
SELECT hubspot_id, _valid_from, _valid_to, _is_current
FROM crm.bronze.contacts
ORDER BY hubspot_id, _valid_from DESC
LIMIT 20;
```
