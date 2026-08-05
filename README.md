# HubSpot → Databricks CRM

Bronze ingest (HubSpot → Unity Catalog) with Git-managed UC DDL and Databricks Jobs.

## Branches & environments

| Branch | Bundle target | UC catalog |
|---|---|---|
| `dev` | `dev` | `crm_dev.bronze` |
| `main` | `prod` | `crm.bronze` |

Same Databricks workspace; catalogs isolate data. Only `main` deploys to prod (`crm`).  
Secrets: repo-level Actions secrets (no GitHub Environments).

## Docs

See [docs/README.md](docs/README.md).

## Quick start

```bash
pip install -r requirements.txt
# fill configs/.env (gitignored)

# Prod catalog
python scripts/apply_uc_ddl.py --catalog crm
python scripts/ingest_bronze.py --catalog crm

# Dev catalog (isolated)
python scripts/apply_uc_ddl.py --catalog crm_dev
python scripts/ingest_bronze.py --catalog crm_dev
```
