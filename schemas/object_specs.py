"""Contacts property list + bronze column order."""
CONTACT_PROPERTIES = ("email", "firstname", "lastname")

CONTACT_COLUMNS = (
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
CONTACT_CHANGE_ATTRS = (
    "properties_json",
    "archived",
    "hubspot_updated_at",
    "hubspot_created_at",
)