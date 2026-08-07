-- Append-only association history
CREATE TABLE IF NOT EXISTS crm_dev.bronze.contact_company_associations (
  `from_object_type` STRING,
  `from_hubspot_id` STRING,
  `to_object_type` STRING,
  `to_hubspot_id` STRING,
  `association_type_id` STRING,
  `raw_json` STRING,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING
) USING DELTA;
