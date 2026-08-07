"""Bronze object contracts: HubSpot properties + column order per table.

SCD2 CRM objects share the same column shape. Dims/associations are append-only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SCD2 CRM objects (contacts / companies / deals)
# ---------------------------------------------------------------------------

CRM_OBJECT_COLUMNS = (
    "hubspot_id",
    "object_type",
    "properties_json",
    "raw_json",
    "hubspot_created_at",
    "hubspot_updated_at",
    "archived",
    "_ingested_at",
    "_ingestion_run_id",
    "_source_system",
    "_valid_from",
    "_valid_to",
    "_is_current",
)

# Columns compared to decide if a new SCD2 version is needed
CRM_CHANGE_ATTRS = (
    "properties_json",
    "archived",
    "hubspot_updated_at",
    "hubspot_created_at",
)

CONTACT_PROPERTIES = ("email", "firstname", "lastname")
COMPANY_PROPERTIES = ("name", "domain")
DEAL_PROPERTIES = (
    "dealname",
    "amount",
    "dealstage",
    "closedate",
    "pipeline",
    "hubspot_owner_id",
)

# Back-compat aliases used by contacts code today
CONTACT_COLUMNS = CRM_OBJECT_COLUMNS
CONTACT_CHANGE_ATTRS = CRM_CHANGE_ATTRS
COMPANY_COLUMNS = CRM_OBJECT_COLUMNS
COMPANY_CHANGE_ATTRS = CRM_CHANGE_ATTRS
DEAL_COLUMNS = CRM_OBJECT_COLUMNS
DEAL_CHANGE_ATTRS = CRM_CHANGE_ATTRS

STAGING_TABLE = {
    "contacts": "_stg_contacts",
    "companies": "_stg_companies",
    "deals": "_stg_deals",
}


def staging_table_name(object_type: str) -> str:
    return STAGING_TABLE[object_type]


# ---------------------------------------------------------------------------
# Append-only: owners
# ---------------------------------------------------------------------------

OWNER_COLUMNS = (
    "owner_id",
    "user_id",
    "email",
    "first_name",
    "last_name",
    "teams_json",
    "raw_json",
    "hubspot_created_at",
    "hubspot_updated_at",
    "archived",
    "_ingested_at",
    "_ingestion_run_id",
    "_source_system",
)

# ---------------------------------------------------------------------------
# Append-only: deal pipeline stages
# ---------------------------------------------------------------------------

DEAL_PIPELINE_STAGE_COLUMNS = (
    "pipeline_id",
    "pipeline_label",
    "stage_id",
    "stage_label",
    "display_order",
    "pipeline_stage_key",
    "raw_json",
    "_ingested_at",
    "_ingestion_run_id",
    "_source_system",
)

# ---------------------------------------------------------------------------
# Append-only: associations
# ---------------------------------------------------------------------------

ASSOCIATION_COLUMNS = (
    "from_object_type",
    "from_hubspot_id",
    "to_object_type",
    "to_hubspot_id",
    "association_type_id",
    "raw_json",
    "_ingested_at",
    "_ingestion_run_id",
    "_source_system",
)

# (table_name, from_object, to_object) — HubSpot association pair names
ASSOCIATION_SPECS = (
    {
        "table_name": "contact_company_associations",
        "from_object": "contacts",
        "to_object": "companies",
    },
    {
        "table_name": "deal_company_associations",
        "from_object": "deals",
        "to_object": "companies",
    },
    {
        "table_name": "deal_contact_associations",
        "from_object": "deals",
        "to_object": "contacts",
    },
)
