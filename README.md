# HubSpot → Databricks CRM

Bronze ingest (HubSpot → Unity Catalog). Keep it simple: **ingest as code**, schedule/secrets in the UI.

## Branches

| Branch | Catalog | How |
|---|---|---|
| `dev` | `crm_dev` | Merge after CI |
| `main` | `crm` | PR from `dev` + approval |

## As code vs UI

| Git | UI |
|---|---|
| Ingest Python | Warehouse, secrets |
| Thin CI | Job schedule, re-run |
| Deploy syncs Job files | Explore / query |

Details: [docs/operating_model.md](docs/operating_model.md)

## Quick start

```bash
pip install -r requirements.txt
# fill configs/.env (gitignored)
python scripts/apply_uc_ddl.py --catalog crm_dev
python scripts/ingest_bronze.py --catalog crm_dev
```

## Docs

[docs/README.md](docs/README.md)

## Later

dbt for staging / silver / gold — not started.
