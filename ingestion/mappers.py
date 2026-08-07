"""Map HubSpot contact API payload → bronze row dict."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from schemas.object_specs import CONTACT_PROPERTIES


def contact_to_row(
    obj: dict[str, Any],
    *,
    ingested_at: datetime,
    run_id: str,
) -> dict[str, Any]:
    props = obj.get("properties") or {}
    selected = {k: props.get(k) for k in CONTACT_PROPERTIES}
    return {
        "hubspot_id": str(obj["id"]),
        "object_type": "contacts",
        "properties_json": json.dumps(selected, separators=(",", ":"), sort_keys=True),
        "raw_json": json.dumps(obj, separators=(",", ":"), sort_keys=True),
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