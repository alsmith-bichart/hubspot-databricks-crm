-- Append-only history (no SCD2)
CREATE TABLE IF NOT EXISTS crm_dev.bronze.deal_pipeline_stages (
  `pipeline_id` STRING,
  `pipeline_label` STRING,
  `stage_id` STRING,
  `stage_label` STRING,
  `display_order` INT,
  `pipeline_stage_key` STRING,
  `raw_json` STRING,
  `_ingested_at` TIMESTAMP,
  `_ingestion_run_id` STRING,
  `_source_system` STRING
) USING DELTA;
