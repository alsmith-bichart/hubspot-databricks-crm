# Project structure

```text
hubspot-databricks-crm/
├── databricks.yml               # sync ingest + Job (no schedule)
├── resources/jobs/
│   ├── apply_uc_ddl.yml
│   └── ingest_bronze.yml        # serverless task; schedule in UI
├── uc/ddl/                      # bronze CREATE TABLE (frozen / rare)
├── .github/workflows/
│   ├── ci.yml                   # thin unit tests
│   └── deploy.yml               # sync to crm_dev / crm
├── configs/.env                 # local secrets (gitignored)
├── docs/
│   └── operating_model.md       # start here
├── ingestion/                   # bronze ingest
├── schemas/object_specs.py
├── scripts/
│   ├── apply_uc_ddl.py
│   └── ingest_bronze.py
├── transformations/             # dbt later
├── tests/
└── requirements.txt
```

## Folder roles

| Folder | Purpose |
|---|---|
| `ingestion/` | HubSpot → bronze |
| `uc/ddl` | Bronze table DDL (apply when needed) |
| `resources/` + `databricks.yml` | Job task sync |
| `.github/workflows/` | Thin CI + deploy |
| `transformations/` | Future dbt — empty for now |
