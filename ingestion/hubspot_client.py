from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://api.hubspot.com"
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_STATUSES = {429, 500, 502, 503, 504}
ASSOC_BATCH_SIZE = 100


class HubSpotError(RuntimeError):
    """Non-retryable HubSpot API failure."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    url: str,
    *,
    token: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(
                method,
                url,
                headers=_headers(token),
                params=params,
                json=json_body,
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2**attempt)
            continue

        if response.status_code in RETRY_STATUSES:
            retry_after = response.headers.get("Retry-After")
            sleep_s = float(retry_after) if retry_after else 2**attempt
            time.sleep(sleep_s)
            last_error = HubSpotError(
                f"{response.status_code} for {url}: {response.text[:300]}"
            )
            continue

        if not response.ok:
            raise HubSpotError(
                f"{response.status_code} {response.reason} for {url}: "
                f"{response.text[:500]}"
            )

        if not response.content:
            return {}
        return response.json()

    raise HubSpotError(f"HubSpot request failed after retries: {last_error}")


def get_page(
    token: str,
    object_type: str,
    properties: list[str] | tuple[str, ...],
    after: str | None = None,
    associations: list[str] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}/crm/v3/objects/{object_type}"
    params: dict[str, Any] = {
        "limit": 100,
        "properties": ",".join(properties),
    }
    if after:
        params["after"] = after
    if associations:
        params["associations"] = ",".join(associations)
    return _request("GET", url, token=token, params=params)


def get_all_objects(
    token: str,
    object_type: str,
    properties: list[str] | tuple[str, ...],
    associations: list[str] | None = None,
    *,
    limit: int | None = None,
) -> list[dict]:
    objects: list[dict] = []
    after: str | None = None

    while True:
        data = get_page(
            token,
            object_type,
            properties,
            after=after,
            associations=associations,
        )
        objects.extend(data.get("results", []))
        if limit is not None and len(objects) >= limit:
            return objects[:limit]
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    return objects


def get_all_owners(token: str, *, limit: int | None = None) -> list[dict]:
    owners: list[dict] = []
    after: str | None = None
    url = f"{BASE_URL}/crm/v3/owners"

    while True:
        params: dict[str, Any] = {"limit": 100}
        if after:
            params["after"] = after
        data = _request("GET", url, token=token, params=params)
        owners.extend(data.get("results", []))
        if limit is not None and len(owners) >= limit:
            return owners[:limit]
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    return owners


def get_deal_pipelines(token: str) -> list[dict]:
    url = f"{BASE_URL}/crm/v3/pipelines/deals"
    data = _request("GET", url, token=token)
    return data.get("results", [])


def get_associations_batch(
    token: str,
    from_object_type: str,
    to_object_type: str,
    from_ids: list[str],
) -> list[dict]:
    """Return raw v4 batch association results for from→to."""
    if not from_ids:
        return []

    url = (
        f"{BASE_URL}/crm/v4/associations/"
        f"{from_object_type}/{to_object_type}/batch/read"
    )
    results: list[dict] = []

    for i in range(0, len(from_ids), ASSOC_BATCH_SIZE):
        chunk = from_ids[i : i + ASSOC_BATCH_SIZE]
        body = {"inputs": [{"id": str(object_id)} for object_id in chunk]}
        data = _request("POST", url, token=token, json_body=body)
        results.extend(data.get("results", []))

    return results
