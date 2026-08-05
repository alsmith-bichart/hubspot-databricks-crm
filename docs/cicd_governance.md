# CI/CD & Unity Catalog governance

This repo treats **Git as the only path** to change data platform objects.

## Non-negotiables

1. **No direct production DDL in Catalog Explorer**  
   Tables/schemas are created/altered only via `uc/ddl` applied through CI/CD (or local `scripts/apply_uc_ddl.py` against **`crm_dev`** while developing).

2. **No manually edited production metric views**  
   Metric views (when added) must live in Git and deploy via the bundle. UI edits in prod are forbidden.

3. **No manually altered Job definitions**  
   Jobs under `resources/jobs/` are managed by Databricks Asset Bundles. Do **not** edit schedules, tasks, or clusters in the Jobs UI — including the 6:00 America/Chicago prod ingest schedule.

4. **Every change begins with a Git branch and pull request**  
   Prefer: feature → `dev` → PR → `main`. No hotfixes only in the workspace.

## Environments

| Git branch | Bundle `-t` | Catalog | Ingest schedule |
|---|---|---|---|
| `dev` | `dev` | `crm_dev` | **PAUSED** |
| `main` | `prod` | `crm` | **UNPAUSED** 6am CT |

Same Databricks workspace host. Isolation = separate UC catalog.  
Deploy uses **repo-level** Actions secrets (no GitHub Environments required).

## Change flow

```text
work on dev → push → Deploy (-t dev → crm_dev)
         → PR into main → CI
         → merge main → Deploy (-t prod → crm)
         → prod Job ingest_bronze runs daily 6am CT
```

GitHub Actions does **not** cron ingest. Prod daily load is owned by the Databricks Job. Dev Job exists for manual runs only (schedule paused).

## Where things live

| Concern | Location |
|---|---|
| UC table DDL (canonical `crm.bronze`) | [`uc/ddl/`](../uc/ddl/) |
| Destructive ops (manual) | [`uc/ops/`](../uc/ops/) |
| Bundle / Jobs | [`databricks.yml`](../databricks.yml), [`resources/`](../resources/) |
| Ingest schedule | [`resources/jobs/ingest_bronze.yml`](../resources/jobs/ingest_bronze.yml) |
| Python column contract | [`schemas/object_specs.py`](../schemas/object_specs.py) |
| Ingest code (no CREATE TABLE) | [`ingestion/`](../ingestion/) |

## Observability

- Job run history in Databricks Workflows UI  
- Failure email: bundle var `job_failure_email` / GitHub secret `JOB_FAILURE_EMAIL`  

## Required GitHub secrets

Repo → Settings → Secrets and variables → Actions:

| Secret | Used by |
|---|---|
| `DATABRICKS_HOST` | CLI + SQL connector |
| `DATABRICKS_TOKEN` | CLI + SQL connector |
| `DATABRICKS_HTTP_PATH` | `scripts/apply_uc_ddl.py` |
| `DATABRICKS_WAREHOUSE_ID` | Bundle deploy var |
| `HUBSPOT_TOKEN` | Optional for Deploy env file |
| `JOB_FAILURE_EMAIL` | Optional; ingest failure alert |

## Databricks secret scope (Job runtime)

Create scope `hubspot-crm` with keys:

- `HUBSPOT_TOKEN`
- `DATABRICKS_HOST`
- `DATABRICKS_HTTP_PATH`
- `DATABRICKS_TOKEN`

Catalog is **not** a secret — Jobs pass `--catalog` / `--bronze-schema` from the bundle target.
