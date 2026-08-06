from __future__ import annotations

import time
from typing import Any

import requests

BASE = "https://api.hubapi.com"


class HubSpotError(RuntimeError):
    pass


def get_all_contacts(
    token: str,
    properties: tuple[str, ...] | list[str],
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    url = f"{BASE}/crm/v3/objects/contacts"
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, Any] = {
        "limit": page_size,
        "properties": ",".join(properties),
    }
    after = None
    out: list[dict[str, Any]] = []

    while True:
        if after:
            params["after"] = after
        elif "after" in params:
            del params["after"]

        for _ in range(5):
            r = requests.get(url, headers=headers, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code >= 400:
                raise HubSpotError(f"{r.status_code}: {r.text[:400]}")
            data = r.json()
            break
        else:
            raise HubSpotError("rate limit retries exhausted")

        out.extend(data.get("results", []))
        after = ((data.get("paging") or {}).get("next") or {}).get("after")
        if not after:
            break
    return out