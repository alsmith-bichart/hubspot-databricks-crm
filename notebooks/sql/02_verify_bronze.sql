-- Module 2 verify (run in Databricks SQL after local ingest)
SELECT 'contacts' AS tbl, count(*) AS n FROM crm.bronze.contacts
UNION ALL SELECT 'companies', count(*) FROM crm.bronze.companies
UNION ALL SELECT 'deals', count(*) FROM crm.bronze.deals
UNION ALL SELECT 'owners', count(*) FROM crm.bronze.owners
UNION ALL SELECT 'deal_pipeline_stages', count(*) FROM crm.bronze.deal_pipeline_stages;

SELECT hubspot_id, properties_json, _ingested_at
FROM crm.bronze.deals
LIMIT 5;
