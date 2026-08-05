# Unity Catalog DDL (source of truth)

UC schemas and tables are managed **only** via Git + Databricks Asset Bundles / CI.

## Rules

See [docs/cicd_governance.md](../docs/cicd_governance.md).

- Do **not** create/alter production tables in Catalog Explorer
- Change DDL under `uc/ddl/` on a branch; open a PR
- Column lists should stay aligned with [`schemas/object_specs.py`](../schemas/object_specs.py)

## Layout

| Path | Purpose |
|---|---|
| `ddl/` | Ordered `CREATE SCHEMA` / `CREATE TABLE IF NOT EXISTS` applied by CI/CD |
| `ops/` | Destructive ops (DROP). **Never** auto-run in deploy |

## Apply locally

DDL files are authored against canonical `crm.bronze`. `apply_uc_ddl.py` rewrites
the catalog/schema for the target (`crm` or `crm_dev`).

```bash
# After warehouse creds in configs/.env
python scripts/apply_uc_ddl.py --catalog crm_dev   # isolated
python scripts/apply_uc_ddl.py --catalog crm       # prod

# Or via bundle Job
databricks bundle deploy -t dev --profile bicharttest
databricks bundle run apply_uc_ddl -t dev --profile bicharttest
```

## Grants / ACLs

Not managed in this pass — document intended grants in PRs until `uc/grants/` is added.
