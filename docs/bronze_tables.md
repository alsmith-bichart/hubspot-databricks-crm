# Bronze tables (`crm.bronze`)

CRM objects use **SCD Type 2**. Owners, stages, and associations remain **append-only**.

## CRM objects (SCD2)

Shared shape for `contacts`, `companies`, `deals`:

| Column | Type | Notes |
|---|---|---|
| `hubspot_id` | string | HubSpot record id |
| `object_type` | string | `contacts` / `companies` / `deals` |
| `properties_json` | string | Requested properties as JSON |
| `raw_json` | string | Full API object payload |
| `hubspot_created_at` | string | Source `createdAt` as received |
| `hubspot_updated_at` | string | Source `updatedAt` as received |
| `archived` | boolean | HubSpot archived flag |
| `_ingested_at` | timestamp | Load time (UTC) |
| `_ingestion_run_id` | string | Pipeline run UUID that wrote this version |
| `_source_system` | string | `hubspot` |
| `_valid_from` | timestamp | Version start (UTC) |
| `_valid_to` | timestamp | Version end; NULL if current |
| `_is_current` | boolean | Open version flag |

Grain: `(hubspot_id, _valid_from)`. Current rows: `_is_current = true`.
Staging tables: `crm.bronze._stg_contacts|companies|deals`.

### Properties requested (into `properties_json`)

| Object | Properties |
|---|---|
| contacts | `email`, `firstname`, `lastname` |
| companies | `name`, `domain` |
| deals | `dealname`, `amount`, `dealstage`, `closedate`, `pipeline`, `hubspot_owner_id` |

## Owners

Grain: one row per owner per ingest run.

| Column | Type |
|---|---|
| `owner_id` | string |
| `user_id` | string |
| `email` | string |
| `first_name` | string |
| `last_name` | string |
| `teams_json` | string |
| `raw_json` | string |
| `hubspot_created_at` | string |
| `hubspot_updated_at` | string |
| `archived` | boolean |
| `_ingested_at` | timestamp |
| `_ingestion_run_id` | string |
| `_source_system` | string |

## Deal pipeline stages

Grain: one row per stage within a pipeline (`pipeline_stage_key = pipeline_id\|stage_id`).

| Column | Type |
|---|---|
| `pipeline_stage_key` | string |
| `pipeline_id` | string |
| `pipeline_label` | string |
| `stage_id` | string |
| `stage_label` | string |
| `display_order` | int |
| `metadata_json` | string |
| `pipeline_created_at` | string |
| `pipeline_updated_at` | string |
| `pipeline_archived` | boolean |
| `stage_created_at` | string |
| `stage_updated_at` | string |
| `stage_archived` | boolean |
| `raw_json` | string |
| `_ingested_at` | timestamp |
| `_ingestion_run_id` | string |
| `_source_system` | string |

## Associations

Three tables; same technical suffix columns.

### `contact_company_associations`

| Column | Type |
|---|---|
| `contact_id` | string |
| `company_id` | string |
| `association_category` | string |
| `association_type_id` | bigint |
| `association_label` | string |
| `raw_json` | string |
| `_ingested_at` | timestamp |
| `_ingestion_run_id` | string |
| `_source_system` | string |

### `deal_company_associations`

| Column | Type |
|---|---|
| `deal_id` | string |
| `company_id` | string |
| `association_category` | string |
| `association_type_id` | bigint |
| `association_label` | string |
| `raw_json` | string |
| `_ingested_at` | timestamp |
| `_ingestion_run_id` | string |
| `_source_system` | string |

### `deal_contact_associations`

| Column | Type |
|---|---|
| `deal_id` | string |
| `contact_id` | string |
| `association_category` | string |
| `association_type_id` | bigint |
| `association_label` | string |
| `raw_json` | string |
| `_ingested_at` | timestamp |
| `_ingestion_run_id` | string |
| `_source_system` | string |

## Source of truth in code

Column order and HubSpot property lists: [`schemas/object_specs.py`](../schemas/object_specs.py).

Row construction: [`ingestion/mappers.py`](../ingestion/mappers.py).
