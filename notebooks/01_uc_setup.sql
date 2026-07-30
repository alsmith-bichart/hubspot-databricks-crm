-- Module 1 — Unity Catalog foundations
-- Run in Databricks SQL editor or a SQL notebook (warehouse attached).
-- Free Edition: you should already see at least one catalog (often `workspace` or `main`).

-- 1) Inspect what you have
SHOW CATALOGS;
SHOW CURRENT CATALOG;

-- 2) Create project catalog + medallion schemas
CREATE CATALOG IF NOT EXISTS crm
COMMENT 'HubSpot CRM Funnel Lakehouse — crash course';

CREATE SCHEMA IF NOT EXISTS crm.bronze
COMMENT 'Raw HubSpot landings (append / MERGE snapshots)';

CREATE SCHEMA IF NOT EXISTS crm.silver
COMMENT 'Cleaned, typed, deduped CRM entities';

CREATE SCHEMA IF NOT EXISTS crm.gold
COMMENT 'Dims, facts, funnel marts — AI/BI safe zone';

-- 3) Verify
SHOW SCHEMAS IN crm;
DESCRIBE CATALOG EXTENDED crm;

-- 4) Tiny managed Delta table (proves write path + lineage later)
CREATE TABLE IF NOT EXISTS crm.bronze._uc_smoke (
  id INT,
  note STRING,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'Module 1 smoke table — safe to drop after Module 2';

INSERT INTO crm.bronze._uc_smoke VALUES
  (1, 'uc_ok', current_timestamp());

SELECT * FROM crm.bronze._uc_smoke;

-- 5) View for Catalog Explorer lineage demo
CREATE OR REPLACE VIEW crm.gold._uc_smoke_v AS
SELECT id, note, created_at
FROM crm.bronze._uc_smoke;

SELECT * FROM crm.gold._uc_smoke_v;

-- 6) Privileges on gold (adjust principal if needed)
-- Free Edition / owner: SHOW GRANTS often returns EMPTY — that is normal.
-- You own the object; no explicit GRANT rows until you grant others.
-- Module 8 will add an analyst principal + selective grants.
SHOW GRANTS ON SCHEMA crm.gold;
SHOW GRANTS ON TABLE crm.bronze._uc_smoke;
-- Also useful:
-- DESCRIBE EXTENDED crm.bronze._uc_smoke;  -- look for Owner

-- Optional: if you created a group later for "analysts"
-- GRANT USE CATALOG ON CATALOG crm TO `account users`;
-- GRANT USE SCHEMA ON SCHEMA crm.gold TO `account users`;
-- GRANT SELECT ON SCHEMA crm.gold TO `account users`;
-- (Do NOT grant bronze/silver SELECT to analysts — Module 8.)

-- Pass criteria:
--   SHOW SCHEMAS IN crm  → bronze, silver, gold
--   SELECT from crm.bronze._uc_smoke works
--   Catalog Explorer → crm.gold._uc_smoke_v → Lineage shows bronze source
