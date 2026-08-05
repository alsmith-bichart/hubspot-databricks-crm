# Project structure

```text
hubspot-databricks-crm/
├── databricks.yml               # targets: dev→crm_dev, prod→crm
├── resources/jobs/
│   ├── apply_uc_ddl.yml         # serverless DDL Job (--catalog)
│   └── ingest_bronze.yml        # serverless ingest (prod 6am; dev paused)
├── uc/
│   ├── README.md
│   ├── ddl/                     # canonical crm.bronze; rewritten on apply
│   └── ops/                     # destructive SQL (manual / PR only)
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml               # branch→env→target
├── configs/
│   └── .env                     # secrets (gitignored)
├── docs/
│   └── cicd_governance.md
├── ingestion/                   # no CREATE TABLE
├── schemas/
│   └── object_specs.py          # Python column contract (must match uc/ddl)
├── scripts/
│   ├── apply_uc_ddl.py
│   └── ingest_bronze.py
├── transformations/             # future silver/gold
├── orchestration/               # unused — schedule lives in resources/jobs/
├── tests/
│   ├── test_validators.py
│   ├── test_uc_ddl_matches_specs.py
│   ├── test_apply_uc_ddl_rewrite.py
│   ├── test_hubspot_client.py
│   └── test_bronze_quality.py
├── utils/
└── requirements.txt
```

## Folder roles

| Folder | Purpose |
|---|---|
| `uc/` | Unity Catalog DDL source of truth |
| `resources/` + `databricks.yml` | Asset Bundle Jobs (dev paused / prod 6am) |
| `.github/workflows/` | CI + branch-gated deploy (not daily ingest cron) |
| `ingestion/` | Extract HubSpot → SCD2/append load (tables must already exist) |
| `schemas/` | Python contracts aligned with `uc/ddl` |
| `scripts/` | Local/CI entrypoints |
| `docs/` | Architecture, onboarding, governance |

## Entrypoints

| Command | What it runs |
|---|---|
| `python scripts/apply_uc_ddl.py` | Apply `uc/ddl` via SQL warehouse |
| `python scripts/ingest_bronze.py` | Full bronze pipeline (no DDL) |
| `python scripts/test_hubspot_client.py` | HubSpot contacts smoke test |
| `python tests/test_bronze_quality.py` | Sampled quality asserts |
| `pytest tests/test_validators.py tests/test_uc_ddl_matches_specs.py` | Unit + DDL contract |
| `databricks bundle deploy -t prod` | Deploy Jobs/schema (publishes 6am schedule) |
| `databricks bundle run apply_uc_ddl -t prod` | Run DDL Job in workspace |
| `databricks bundle run ingest_bronze -t prod` | One-off cloud ingest (backfill) |
