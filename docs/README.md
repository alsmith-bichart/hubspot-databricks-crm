# Docs

| Doc | Contents |
|---|---|
| [operating_model.md](operating_model.md) | Code vs UI, branches, debug |
| [cicd_governance.md](cicd_governance.md) | CI → dev → approved PR → main |
| [getting_started.md](getting_started.md) | Setup, local ingest |
| [architecture.md](architecture.md) | Bronze pipeline |
| [bronze_tables.md](bronze_tables.md) | Table shapes |
| [project_structure.md](project_structure.md) | Folders |

## Quick start

```bash
pip install -r requirements.txt
python scripts/apply_uc_ddl.py --catalog crm_dev
python tests/test_hubspot_client.py
python scripts/ingest_bronze.py --catalog crm_dev
```
