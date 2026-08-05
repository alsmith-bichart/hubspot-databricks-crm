-- DESTRUCTIVE — not run by CI/CD.
-- Reset contacts/companies/deals (+ staging) for schema recreate.
-- Owners / stages / associations are NOT dropped.
-- Apply via PR review + manual run only. Then: python scripts/apply_uc_ddl.py

DROP TABLE IF EXISTS crm.bronze.contacts;
DROP TABLE IF EXISTS crm.bronze.companies;
DROP TABLE IF EXISTS crm.bronze.deals;
DROP TABLE IF EXISTS crm.bronze._stg_contacts;
DROP TABLE IF EXISTS crm.bronze._stg_companies;
DROP TABLE IF EXISTS crm.bronze._stg_deals;
