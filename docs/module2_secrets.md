# Module 2 — HubSpot token (Option B locked)

**Free Edition:** no secret scopes.  
**Module 2 auth:** local `.env` only — HubSpot token never enters Databricks notebooks.

```text
.env (gitignored)
   HUBSPOT_TOKEN
   DATABRICKS_HOST / HTTP_PATH / TOKEN
        │
        ▼
scripts/ingest_hubspot_local.py
        │  HubSpot API
        ▼
crm.bronze.*  via SQL warehouse
```

## Setup

1. Create local `.env` (gitignored) — see README for required keys
2. Fill values (warehouse: Compute → SQL warehouse → Connection details)
3. `python -m venv .venv && source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python scripts/ingest_hubspot_local.py`
6. Verify in Databricks SQL:

```sql
SELECT 'contacts' AS t, count(*) AS n FROM crm.bronze.contacts
UNION ALL SELECT 'companies', count(*) FROM crm.bronze.companies
UNION ALL SELECT 'deals', count(*) FROM crm.bronze.deals;
```

## Pass

- Counts > 0 for contacts / companies / deals  
- Second run idempotent (MERGE on `hubspot_id`)  
- `.env` not committed  

Notebook `02_ingest_hubspot_bronze.py` = optional in-workspace alt (widget). Prefer this script for the course.

Enterprise later: same script, swap `.env` for vault-injected env vars in CI.
