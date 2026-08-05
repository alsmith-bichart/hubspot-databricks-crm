# Getting started

## Prerequisites

- Python 3.11+
- HubSpot private app token with CRM read scopes
- Databricks SQL warehouse + PAT with access to catalogs `crm` and `crm_dev`
- UC bronze tables applied from Git (`uc/ddl`) — **ingest does not CREATE tables**
- Permission to `CREATE CATALOG` (or pre-create `crm_dev`)

Read [cicd_governance.md](cicd_governance.md) before changing production UC/Jobs.

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

### Databricks Job secrets (scheduled ingest)

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

### Scheduled ingest (Databricks Job)

Job [`resources/jobs/ingest_bronze.yml`](../resources/jobs/ingest_bronze.yml):

- **Compute:** serverless
- **Prod (`main`):** daily **6:00 America/Chicago**, catalog `crm`
- **Dev (`dev` branch):** schedule **PAUSED**, catalog `crm_dev`
- **Secrets:** scope `hubspot-crm` via dbutils; catalog via Job `--catalog`
- **Deploy:** push to `dev` or merge to `main` (GitHub Actions) — does **not** auto-run ingest
- **Manual:** `databricks bundle run ingest_bronze -t prod --profile bicharttest`
- **Do not** change schedule in Jobs UI — edit YAML + PR

### Bronze quality (sampled)

```bash
python tests/test_bronze_quality.py
python tests/test_bronze_quality.py --limit 10
```

### Unit / contract tests

```bash
pytest tests/test_validators.py tests/test_uc_ddl_matches_specs.py -q
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
