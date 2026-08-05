from __future__ import annotations

from typing import Any, Sequence


TECH_FIELDS = ("_ingested_at", "_ingestion_run_id", "_source_system")


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _require_tech_and_raw(row: dict[str, Any], index: int, errors: list[str]) -> None:
    if _missing(row.get("raw_json")):
        errors.append(f"row[{index}]: raw_json missing or empty")
    for field in TECH_FIELDS:
        if field not in row or row.get(field) is None:
            errors.append(f"row[{index}]: {field} missing")
        elif field == "_source_system" and row.get(field) != "hubspot":
            errors.append(
                f"row[{index}]: _source_system must be 'hubspot', got {row.get(field)!r}"
            )
        elif field == "_ingestion_run_id" and _missing(row.get(field)):
            errors.append(f"row[{index}]: _ingestion_run_id missing or empty")


def _require_business_keys(
    row: dict[str, Any],
    index: int,
    business_keys: Sequence[str],
    errors: list[str],
) -> None:
    for key in business_keys:
        if _missing(row.get(key)):
            errors.append(f"row[{index}]: required id {key} missing or empty")


def _assert_unique_business_keys(
    rows: list[dict[str, Any]],
    business_keys: Sequence[str],
    errors: list[str],
) -> None:
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        key = tuple(row.get(k) for k in business_keys)
        if key in seen:
            errors.append(
                f"duplicate business key in batch at row[{index}]: "
                + ", ".join(f"{k}={row.get(k)!r}" for k in business_keys)
            )
        seen.add(key)


def _require_scd2(row: dict[str, Any], index: int, errors: list[str]) -> None:
    if row.get("_valid_from") is None:
        errors.append(f"row[{index}]: _valid_from missing")
    if row.get("_is_current") is None:
        errors.append(f"row[{index}]: _is_current missing")
    elif row.get("_is_current") is not True:
        errors.append(
            f"row[{index}]: staging SCD2 row must have _is_current=True, "
            f"got {row.get('_is_current')!r}"
        )


def validate_rows(
    rows: list[dict[str, Any]],
    *,
    business_keys: Sequence[str],
    label: str,
    required_keys: Sequence[str] | None = None,
    scd2: bool = False,
) -> None:
    """Enforce bronze row quality before load.

    - Required HubSpot / business IDs exist (required_keys, default business_keys)
    - raw_json retained
    - Technical ingestion fields exist
    - Business keys unique within this run's batch
    - Optional SCD2 staging fields (_valid_from, _is_current=True)
    """
    must_have = required_keys if required_keys is not None else business_keys
    errors: list[str] = []
    for index, row in enumerate(rows):
        _require_business_keys(row, index, must_have, errors)
        _require_tech_and_raw(row, index, errors)
        if scd2:
            _require_scd2(row, index, errors)
    _assert_unique_business_keys(rows, business_keys, errors)

    if errors:
        preview = "; ".join(errors[:10])
        more = f" (+{len(errors) - 10} more)" if len(errors) > 10 else ""
        raise ValueError(
            f"{label} validation failed ({len(errors)} issues): {preview}{more}"
        )
