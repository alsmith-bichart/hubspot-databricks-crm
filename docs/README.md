# HubSpot → Databricks CRM

Python ingest into Unity Catalog bronze. UC tables and Jobs are managed via **Databricks Asset Bundles + GitHub Actions** (not Catalog Explorer).

## Docs

| Doc | Contents |
|---|---|
| [getting_started.md](getting_started.md) | Setup, apply DDL, run ingest |
| [cicd_governance.md](cicd_governance.md) | Branches, envs, PR-only rules |
| [architecture.md](architecture.md) | Pipeline + SCD2 / append patterns |
| [bronze_tables.md](bronze_tables.md) | Table grains and columns |
| [project_structure.md](project_structure.md) | Folder layout |
| [data_contract_hubspot_crm_bronze.yaml](data_contract_hubspot_crm_bronze.yaml) | Consumer data contract |

## Quick start

```bash
pip install -r requirements.txt
# fill configs/.env (gitignored)
python scripts/apply_uc_ddl.py --catalog crm_dev
python tests/test_hubspot_client.py
python scripts/ingest_bronze.py --catalog crm_dev
```

## Branches

| Branch | Deploy target | Catalog |
|---|---|---|
| `dev` | `-t dev` | `crm_dev` |
| `main` | `-t prod` | `crm` |

## Status

- Bronze ingest: SCD2 (CRM objects) + append (owners/stages/assocs)
- UC DDL + Jobs: Asset Bundles under `uc/` + `resources/`
- Prod schedule: Job `ingest_bronze` daily **6:00 America/Chicago** (Git-managed)
- Dev schedule: paused (manual runs only)
- CI/CD: GitHub Actions by branch/environment
- Silver / gold: not built yet
