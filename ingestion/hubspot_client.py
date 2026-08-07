"""HubSpot CRM API client — paginated fetch for bronze ingest."""

from __future__ import annotations

import time
from typing import Any

import requests

BASE = "https://api.hubapi.com"


class HubSpotError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _request(
    method: str,
    url: str,
    token: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    retries: int = 5,
) -> dict[str, Any]:
    for _ in range(retries):
        r = requests.request(
            method,
            url,
            headers=_headers(token),
            params=params,
            json=json_body,
            timeout=60,
        )
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        if r.status_code >= 400:
            raise HubSpotError(f"{r.status_code}: {r.text[:400]}")
        return r.json() if r.content else {}
    raise HubSpotError("rate limit retries exhausted")


def _paginate(
    token: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    params = dict(params or {})
    params.setdefault("limit", page_size)
    after: str | None = None
    out: list[dict[str, Any]] = []

    while True:
        page_params = dict(params)
        if after:
            page_params["after"] = after
        data = _request("GET", url, token, params=page_params)
        out.extend(data.get("results", []))
        after = ((data.get("paging") or {}).get("next") or {}).get("after")
        if not after:
            break
    return out


# ---------------------------------------------------------------------------
# CRM objects (contacts / companies / deals)
# ---------------------------------------------------------------------------

def get_all_objects(
    token: str,
    object_type: str,
    properties: tuple[str, ...] | list[str],
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    url = f"{BASE}/crm/v3/objects/{object_type}"
    return _paginate(
        token,
        url,
        params={"properties": ",".join(properties)},
        page_size=page_size,
    )


def get_all_contacts(
    token: str,
    properties: tuple[str, ...] | list[str],
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    return get_all_objects(token, "contacts", properties, page_size=page_size)


def get_all_companies(
    token: str,
    properties: tuple[str, ...] | list[str],
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    return get_all_objects(token, "companies", properties, page_size=page_size)


def get_all_deals(
    token: str,
    properties: tuple[str, ...] | list[str],
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    return get_all_objects(token, "deals", properties, page_size=page_size)


# ---------------------------------------------------------------------------
# Owners (append dim)
# ---------------------------------------------------------------------------

def get_all_owners(
    token: str,
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    return _paginate(token, f"{BASE}/crm/v3/owners", page_size=page_size)


# ---------------------------------------------------------------------------
# Deal pipelines + stages (append dim)
# ---------------------------------------------------------------------------

def get_deal_pipelines(token: str) -> list[dict[str, Any]]:
    """Return deal pipelines; each has nested `stages`."""
    data = _request("GET", f"{BASE}/crm/v3/pipelines/deals", token)
    return data.get("results", [])


# ---------------------------------------------------------------------------
# Associations (append history)
# ---------------------------------------------------------------------------

def get_associations(
    token: str,
    from_object: str,
    to_object: str,
    from_ids: list[str],
    *,
    batch_size: int = 100,
) -> list[dict[str, Any]]:
    """Batch-read associations. Returns flat list of edge dicts.

    Each item:
      from_id, to_id, association_type_id, raw (association type payload)
    """
    url = f"{BASE}/crm/v4/associations/{from_object}/{to_object}/batch/read"
    edges: list[dict[str, Any]] = []

    for i in range(0, len(from_ids), batch_size):
        chunk = from_ids[i : i + batch_size]
        data = _request(
            "POST",
            url,
            token,
            json_body={"inputs": [{"id": str(oid)} for oid in chunk]},
        )
        for row in data.get("results", []):
            from_id = str(row.get("from", {}).get("id") or "")
            for assoc in row.get("to") or []:
                to_id = str(assoc.get("toObjectId") or "")
                types = assoc.get("associationTypes") or []
                type_id = ""
                if types:
                    type_id = str(types[0].get("typeId") or types[0].get("category") or "")
                edges.append(
                    {
                        "from_id": from_id,
                        "to_id": to_id,
                        "association_type_id": type_id,
                        "raw": assoc,
                    }
                )
    return edges
