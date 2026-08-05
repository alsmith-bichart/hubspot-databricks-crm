# CI/CD (simple)

See [operating_model.md](operating_model.md) first.

## Flow

1. Work on a feature branch (or directly on `dev` for small fixes)
2. CI must pass (unit tests)
3. Merge to **`dev`** → deploy syncs code to `crm_dev`
4. Open PR **`dev` → `main`**
5. **Alec approves** → merge → deploy syncs to `crm`

## GitHub settings (manual, once)

On `main`:

- Require pull request before merge
- Require 1 approving review (you)
- Require status check `CI / test`

## What Git does not own

- Job schedule (Jobs UI)
- Warehouse / secret values (UI)
- Ad-hoc SQL (SQL Editor)

## Secrets (repo Actions)

`DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_HTTP_PATH`, `HUBSPOT_TOKEN`, `JOB_FAILURE_EMAIL`

Job runtime: Databricks scope `hubspot-crm` (same four keys as ingest needs).
