CREATE TABLE IF NOT EXISTS crm_dev.bronze._stg_companies (
  `hubspot_id` STRING,
  `object_type` STRING,
  `properties_json` STRING,
  `raw_json` STRING,
  `hubspot_created_at` STRING,
  `hubspot_updated_at` STRING,
  `archived` BOOLEAN,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING,
  `_valid_from` TIMESTAMP,
  `_valid_to` TIMESTAMP,
  `_is_current` BOOLEAN
) USING DELTA;
