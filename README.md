# HubSpot CRM Funnel Lakehouse

Crash course project: HubSpot → Databricks (Unity Catalog medallion) with custom notebook ingest, gold funnel mart, data contracts, and Jobs.

## Layout

```text
notebooks/     Databricks SQL / Python labs
contracts/     ODCS data contracts
dags/          Optional Airflow (Module 7)
docs/          Metric dictionary
```

## UC target

```text
crm.bronze   # raw HubSpot land
crm.silver   # cleaned entities
crm.gold     # dims / facts / funnel mart
```

## Modules

| Module | Focus |
|--------|--------|
| 0 | Free Edition + HubSpot token |
| 1 | UC catalog/schemas |
| 2 | Custom HubSpot API → bronze |
| 3 | Silver entities |
| 4 | Gold star + funnel |
| 5 | Data contracts |
| 6 | Databricks Jobs |
| 7 | Optional Airflow |
| 8 | Metrics / DQ / gold-only grants |

## Quick start (Module 2 — Option B)

1. Create local `.env` (gitignored) with:
   - `HUBSPOT_TOKEN`
   - `DATABRICKS_HOST`
   - `DATABRICKS_HTTP_PATH`
   - `DATABRICKS_TOKEN`
2. `pip install -r requirements.txt`
3. `python scripts/ingest_hubspot_local.py`
4. Run verify SQL in [`notebooks/sql/02_verify_bronze.sql`](notebooks/sql/02_verify_bronze.sql)

Token stays on laptop — never commit `.env`.
