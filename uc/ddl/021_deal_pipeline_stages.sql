CREATE TABLE IF NOT EXISTS crm.bronze.deal_pipeline_stages (
  `pipeline_stage_key` STRING,
  `pipeline_id` STRING,
  `pipeline_label` STRING,
  `stage_id` STRING,
  `stage_label` STRING,
  `display_order` INT,
  `metadata_json` STRING,
  `pipeline_created_at` STRING,
  `pipeline_updated_at` STRING,
  `pipeline_archived` BOOLEAN,
  `stage_created_at` STRING,
  `stage_updated_at` STRING,
  `stage_archived` BOOLEAN,
  `raw_json` STRING,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING
) USING DELTA;
