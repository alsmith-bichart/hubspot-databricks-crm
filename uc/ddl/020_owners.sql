-- Append-only history (no SCD2)
CREATE TABLE IF NOT EXISTS crm_dev.bronze.owners (
  `owner_id` STRING,
  `user_id` STRING,
  `email` STRING,
  `first_name` STRING,
  `last_name` STRING,
  `teams_json` STRING,
  `raw_json` STRING,
  `hubspot_created_at` STRING,
  `hubspot_updated_at` STRING,
  `archived` BOOLEAN,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING
) USING DELTA;
