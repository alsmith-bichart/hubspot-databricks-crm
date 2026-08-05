from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectSpec:
    name: str
    hubspot_object: str
    properties: tuple[str, ...]
    table_name: str
    business_keys: tuple[str, ...] = ("hubspot_id",)


@dataclass(frozen=True)
class AssociationSpec:
    """Maps a HubSpot association batch to a bronze association table."""

    table_name: str
    from_object_type: str  # HubSpot API from type
    to_object_type: str  # HubSpot API to type
    from_id_column: str  # bronze column for from id
    to_id_column: str  # bronze column for to id
    columns: tuple[tuple[str, str], ...]
    business_keys: tuple[str, ...]


CONTACT_SPEC = ObjectSpec(
    name="contacts",
    hubspot_object="contacts",
    properties=("email", "firstname", "lastname"),
    table_name="contacts",
    business_keys=("hubspot_id",),
)

COMPANY_SPEC = ObjectSpec(
    name="companies",
    hubspot_object="companies",
    properties=("name", "domain"),
    table_name="companies",
    business_keys=("hubspot_id",),
)

DEAL_SPEC = ObjectSpec(
    name="deals",
    hubspot_object="deals",
    properties=(
        "dealname",
        "amount",
        "dealstage",
        "closedate",
        "pipeline",
        "hubspot_owner_id",
    ),
    table_name="deals",
    business_keys=("hubspot_id",),
)

CRM_OBJECT_SPECS: tuple[ObjectSpec, ...] = (
    CONTACT_SPEC,
    COMPANY_SPEC,
    DEAL_SPEC,
)

# Must match crm.bronze.contacts|companies|deals column order exactly.
# SCD Type 2: versioned by (hubspot_id, _valid_from); current row has _is_current=true.
CRM_OBJECT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("hubspot_id", "STRING"),
    ("object_type", "STRING"),
    ("properties_json", "STRING"),
    ("raw_json", "STRING"),
    ("hubspot_created_at", "STRING"),
    ("hubspot_updated_at", "STRING"),
    ("archived", "BOOLEAN"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
    ("_valid_from", "TIMESTAMP"),
    ("_valid_to", "TIMESTAMP"),
    ("_is_current", "BOOLEAN"),
)

# Compared to current version to decide whether to open a new SCD2 version.
SCD2_CHANGE_ATTRIBUTES: tuple[str, ...] = (
    "properties_json",
    "archived",
    "hubspot_updated_at",
    "hubspot_created_at",
)

# Must match crm.bronze.owners
OWNER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("owner_id", "STRING"),
    ("user_id", "STRING"),
    ("email", "STRING"),
    ("first_name", "STRING"),
    ("last_name", "STRING"),
    ("teams_json", "STRING"),
    ("raw_json", "STRING"),
    ("hubspot_created_at", "STRING"),
    ("hubspot_updated_at", "STRING"),
    ("archived", "BOOLEAN"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
)

# Must match crm.bronze.deal_pipeline_stages
DEAL_PIPELINE_STAGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("pipeline_stage_key", "STRING"),
    ("pipeline_id", "STRING"),
    ("pipeline_label", "STRING"),
    ("stage_id", "STRING"),
    ("stage_label", "STRING"),
    ("display_order", "INT"),
    ("metadata_json", "STRING"),
    ("pipeline_created_at", "STRING"),
    ("pipeline_updated_at", "STRING"),
    ("pipeline_archived", "BOOLEAN"),
    ("stage_created_at", "STRING"),
    ("stage_updated_at", "STRING"),
    ("stage_archived", "BOOLEAN"),
    ("raw_json", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
)

CONTACT_COMPANY_ASSOCIATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("contact_id", "STRING"),
    ("company_id", "STRING"),
    ("association_category", "STRING"),
    ("association_type_id", "BIGINT"),
    ("association_label", "STRING"),
    ("raw_json", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
)

DEAL_COMPANY_ASSOCIATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("deal_id", "STRING"),
    ("company_id", "STRING"),
    ("association_category", "STRING"),
    ("association_type_id", "BIGINT"),
    ("association_label", "STRING"),
    ("raw_json", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
)

DEAL_CONTACT_ASSOCIATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("deal_id", "STRING"),
    ("contact_id", "STRING"),
    ("association_category", "STRING"),
    ("association_type_id", "BIGINT"),
    ("association_label", "STRING"),
    ("raw_json", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_ingestion_run_id", "STRING"),
    ("_source_system", "STRING"),
)

ASSOCIATION_SPECS: tuple[AssociationSpec, ...] = (
    AssociationSpec(
        table_name="contact_company_associations",
        from_object_type="contacts",
        to_object_type="companies",
        from_id_column="contact_id",
        to_id_column="company_id",
        columns=CONTACT_COMPANY_ASSOCIATION_COLUMNS,
        business_keys=(
            "contact_id",
            "company_id",
            "association_category",
            "association_type_id",
        ),
    ),
    AssociationSpec(
        table_name="deal_company_associations",
        from_object_type="deals",
        to_object_type="companies",
        from_id_column="deal_id",
        to_id_column="company_id",
        columns=DEAL_COMPANY_ASSOCIATION_COLUMNS,
        business_keys=(
            "deal_id",
            "company_id",
            "association_category",
            "association_type_id",
        ),
    ),
    AssociationSpec(
        table_name="deal_contact_associations",
        from_object_type="deals",
        to_object_type="contacts",
        from_id_column="deal_id",
        to_id_column="contact_id",
        columns=DEAL_CONTACT_ASSOCIATION_COLUMNS,
        business_keys=(
            "deal_id",
            "contact_id",
            "association_category",
            "association_type_id",
        ),
    ),
)

OWNER_BUSINESS_KEYS: tuple[str, ...] = ("owner_id",)
PIPELINE_STAGE_BUSINESS_KEYS: tuple[str, ...] = ("pipeline_stage_key",)
TECH_FIELDS: tuple[str, ...] = (
    "_ingested_at",
    "_ingestion_run_id",
    "_source_system",
)

SCD2_FIELDS: tuple[str, ...] = (
    "_valid_from",
    "_valid_to",
    "_is_current",
)


def history_keys(business_keys: tuple[str, ...]) -> tuple[str, ...]:
    """Append-only tables: unique grain per ingest run."""
    return business_keys + ("_ingestion_run_id",)


def scd2_version_keys(business_keys: tuple[str, ...] = ("hubspot_id",)) -> tuple[str, ...]:
    """SCD2 tables: unique grain per version."""
    return business_keys + ("_valid_from",)


def staging_table_name(table_name: str) -> str:
    return f"_stg_{table_name}"


def object_columns(spec: ObjectSpec) -> list[tuple[str, str]]:
    _ = spec
    return list(CRM_OBJECT_COLUMNS)


def column_names(columns: tuple[tuple[str, str], ...]) -> list[str]:
    return [name for name, _ in columns]
