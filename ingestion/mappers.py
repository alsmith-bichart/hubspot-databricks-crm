"""Map HubSpot API payloads → bronze row dicts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from schemas.object_specs import (
    COMPANY_PROPERTIES,
    CONTACT_PROPERTIES,
    DEAL_PROPERTIES,
)


def _dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# SCD2 CRM objects
# ---------------------------------------------------------------------------

def crm_object_to_row(
    obj: dict[str, Any],
    *,
    object_type: str,
    properties: tuple[str, ...] | list[str],
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    props = obj.get("properties") or {}
    selected = {k: props.get(k) for k in properties}
    return {
        "hubspot_id": str(obj["id"]),
        "object_type": object_type,
        "properties_json": _dumps(selected),
        "raw_json": _dumps(obj),
        "hubspot_created_at": obj.get("createdAt"),
        "hubspot_updated_at": obj.get("updatedAt"),
        "archived": bool(obj.get("archived", False)),
        "_ingested_at": ingested_at,
        "_ingestion_run_id": run_id,
        "_source_system": "hubspot",
        "_valid_from": ingested_at,
        "_valid_to": None,
        "_is_current": True,
    }


def contact_to_row(
    obj: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    return crm_object_to_row(
        obj,
        object_type="contacts",
        properties=CONTACT_PROPERTIES,
        ingested_at=ingested_at,
        run_id=run_id,
    )


def company_to_row(
    obj: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    return crm_object_to_row(
        obj,
        object_type="companies",
        properties=COMPANY_PROPERTIES,
        ingested_at=ingested_at,
        run_id=run_id,
    )


def deal_to_row(
    obj: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    return crm_object_to_row(
        obj,
        object_type="deals",
        properties=DEAL_PROPERTIES,
        ingested_at=ingested_at,
        run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Append-only: owners
# ---------------------------------------------------------------------------

def owner_to_row(
    obj: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    return {
        "owner_id": str(obj.get("id") or ""),
        "user_id": str(obj["userId"]) if obj.get("userId") is not None else None,
        "email": obj.get("email"),
        "first_name": obj.get("firstName"),
        "last_name": obj.get("lastName"),
        "teams_json": _dumps(obj.get("teams") or []),
        "raw_json": _dumps(obj),
        "hubspot_created_at": obj.get("createdAt"),
        "hubspot_updated_at": obj.get("updatedAt"),
        "archived": bool(obj.get("archived", False)),
        "_ingested_at": ingested_at,
        "_ingestion_run_id": run_id,
        "_source_system": "hubspot",
    }


# ---------------------------------------------------------------------------
# Append-only: deal pipeline stages (one row per stage)
# ---------------------------------------------------------------------------

def pipeline_to_stage_rows(
    pipeline: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> list[dict[str, Any]]:
    pipeline_id = str(pipeline.get("id") or "")
    pipeline_label = pipeline.get("label")
    rows: list[dict[str, Any]] = []
    for stage in pipeline.get("stages") or []:
        stage_id = str(stage.get("id") or "")
        rows.append(
            {
                "pipeline_id": pipeline_id,
                "pipeline_label": pipeline_label,
                "stage_id": stage_id,
                "stage_label": stage.get("label"),
                "display_order": stage.get("displayOrder"),
                "pipeline_stage_key": f"{pipeline_id}:{stage_id}",
                "raw_json": _dumps({"pipeline": pipeline, "stage": stage}),
                "_ingested_at": ingested_at,
                "_ingestion_run_id": run_id,
                "_source_system": "hubspot",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Append-only: associations
# ---------------------------------------------------------------------------

def association_to_row(
    edge: dict[str, Any],
    *,
    from_object: str,
    to_object: str,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    """Map edge from hubspot_client.get_associations → bronze assoc row."""
    return {
        "from_object_type": from_object,
        "from_hubspot_id": str(edge.get("from_id") or ""),
        "to_object_type": to_object,
        "to_hubspot_id": str(edge.get("to_id") or ""),
        "association_type_id": str(edge.get("association_type_id") or ""),
        "raw_json": _dumps(edge.get("raw") or edge),
        "_ingested_at": ingested_at,
        "_ingestion_run_id": run_id,
        "_source_system": "hubspot",
    }
