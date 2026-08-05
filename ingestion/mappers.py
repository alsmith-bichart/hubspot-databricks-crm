from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from schemas.object_specs import AssociationSpec, ObjectSpec


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _props(obj: dict[str, Any]) -> dict[str, Any]:
    return obj.get("properties") or {}


def object_to_row(
    obj: dict[str, Any],
    *,
    run_id: str,
    spec: ObjectSpec,
    ingested_at: datetime | None = None,
) -> dict[str, Any]:
    """crm.bronze.contacts|companies|deals column order."""
    ts = ingested_at or _utc_now()
    return {
        "hubspot_id": str(obj["id"]),
        "object_type": spec.hubspot_object,
        "properties_json": json.dumps(_props(obj), default=str),
        "raw_json": json.dumps(obj, default=str),
        "hubspot_created_at": obj.get("createdAt"),
        "hubspot_updated_at": obj.get("updatedAt"),
        "archived": bool(obj.get("archived", False)),
        "_ingested_at": ts,
        "_ingestion_run_id": run_id,
        "_source_system": "hubspot",
        "_valid_from": ts,
        "_valid_to": None,
        "_is_current": True,
    }


def owner_to_row(
    owner: dict[str, Any],
    *,
    run_id: str,
    ingested_at: datetime | None = None,
) -> dict[str, Any]:
    """crm.bronze.owners column order."""
    ts = ingested_at or _utc_now()
    user_id = owner.get("userId")
    return {
        "owner_id": str(owner["id"]),
        "user_id": str(user_id) if user_id is not None else None,
        "email": owner.get("email"),
        "first_name": owner.get("firstName"),
        "last_name": owner.get("lastName"),
        "teams_json": json.dumps(owner.get("teams") or [], default=str),
        "raw_json": json.dumps(owner, default=str),
        "hubspot_created_at": owner.get("createdAt"),
        "hubspot_updated_at": owner.get("updatedAt"),
        "archived": bool(owner.get("archived", False)),
        "_ingested_at": ts,
        "_ingestion_run_id": run_id,
        "_source_system": "hubspot",
    }


def pipeline_stage_to_rows(
    pipeline: dict[str, Any],
    *,
    run_id: str,
    ingested_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """crm.bronze.deal_pipeline_stages column order."""
    ts = ingested_at or _utc_now()
    pipeline_id = str(pipeline.get("id", ""))
    rows: list[dict[str, Any]] = []

    for stage in pipeline.get("stages", []):
        stage_id = str(stage.get("id", ""))
        rows.append(
            {
                "pipeline_stage_key": f"{pipeline_id}|{stage_id}",
                "pipeline_id": pipeline_id,
                "pipeline_label": pipeline.get("label"),
                "stage_id": stage_id,
                "stage_label": stage.get("label"),
                "display_order": stage.get("displayOrder"),
                "metadata_json": json.dumps(stage.get("metadata") or {}, default=str),
                "pipeline_created_at": pipeline.get("createdAt"),
                "pipeline_updated_at": pipeline.get("updatedAt"),
                "pipeline_archived": bool(pipeline.get("archived", False)),
                "stage_created_at": stage.get("createdAt"),
                "stage_updated_at": stage.get("updatedAt"),
                "stage_archived": bool(stage.get("archived", False)),
                "raw_json": json.dumps(
                    {"pipeline": pipeline, "stage": stage},
                    default=str,
                ),
                "_ingested_at": ts,
                "_ingestion_run_id": run_id,
                "_source_system": "hubspot",
            }
        )
    return rows


def association_to_rows(
    batch_result: dict[str, Any],
    *,
    spec: AssociationSpec,
    run_id: str,
    ingested_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Flatten one v4 batch result into a typed association bronze table."""
    ts = ingested_at or _utc_now()
    from_id = str(batch_result.get("from", {}).get("id", ""))
    rows: list[dict[str, Any]] = []

    for to_item in batch_result.get("to", []):
        to_id = str(to_item.get("toObjectId") or to_item.get("id") or "")
        if not from_id or not to_id:
            continue

        type_ids = to_item.get("associationTypes") or []
        # One bronze row per association type on the edge
        type_entries = type_ids or [{}]
        for assoc_type in type_entries:
            type_id = assoc_type.get("typeId")
            rows.append(
                {
                    spec.from_id_column: from_id,
                    spec.to_id_column: to_id,
                    "association_category": assoc_type.get("category"),
                    "association_type_id": int(type_id) if type_id is not None else None,
                    "association_label": assoc_type.get("label"),
                    "raw_json": json.dumps(
                        {
                            "from": batch_result.get("from"),
                            "to": to_item,
                        },
                        default=str,
                    ),
                    "_ingested_at": ts,
                    "_ingestion_run_id": run_id,
                    "_source_system": "hubspot",
                }
            )
    return rows
