# Operating model (simple)

## As code (Git)

- Bronze **ingest** (`ingestion/`, `scripts/ingest_bronze.py`)
- Thin CI (unit tests)
- Job **task definition** (serverless entrypoint) — synced by deploy
- Later: **dbt** models (not started)

## UI / manual (not Git)

- SQL warehouse
- Secret values (scope `hubspot-crm`)
- Explore / query tables
- **Re-run** Jobs
- **Schedule** (cron / pause) on the ingest Job

## Branches

```text
feature → CI green → merge to dev     (crm_dev)
dev → PR → main                       (crm)
         → Alec approves → merge
```

Protect `main`: require PR + your review + CI. Prefer no direct pushes to `main`.

## Debug order (no LLM first)

1. Jobs UI → failed run → error text
2. SQL: `SELECT COUNT(*), MAX(_ingested_at) FROM crm.bronze.deals` (or `crm_dev`)
3. Secrets: scope `hubspot-crm` has `HUBSPOT_TOKEN`, `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN`
4. Local: `python tests/test_hubspot_client.py`
5. Then code / ask for help with the run URL

## Catalogs

| Branch | Catalog |
|---|---|
| `dev` | `crm_dev` |
| `main` | `crm` |
