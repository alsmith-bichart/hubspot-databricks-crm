CREATE TABLE IF NOT EXISTS crm.bronze.deal_contact_associations (
  `deal_id` STRING,
  `contact_id` STRING,
  `association_category` STRING,
  `association_type_id` BIGINT,
  `association_label` STRING,
  `raw_json` STRING,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING
) USING DELTA;
