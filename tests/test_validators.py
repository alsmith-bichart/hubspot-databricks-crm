"""Unit tests for bronze row validators."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ingestion.validators import validate_rows


def _good_row(**overrides):
    row = {
        "hubspot_id": "1",
        "raw_json": "{}",
        "_ingested_at": datetime.now(timezone.utc),
        "_ingestion_run_id": "run-a",
        "_source_system": "hubspot",
    }
    row.update(overrides)
    return row


def test_validate_rows_passes_for_good_batch() -> None:
    validate_rows(
        [_good_row(hubspot_id="1"), _good_row(hubspot_id="2")],
        business_keys=("hubspot_id",),
        label="contacts",
    )


def test_missing_hubspot_id_fails() -> None:
    with pytest.raises(ValueError, match="hubspot_id"):
        validate_rows(
            [_good_row(hubspot_id="")],
            business_keys=("hubspot_id",),
            label="contacts",
        )


def test_missing_raw_json_fails() -> None:
    with pytest.raises(ValueError, match="raw_json"):
        validate_rows(
            [_good_row(raw_json="")],
            business_keys=("hubspot_id",),
            label="contacts",
        )


def test_missing_tech_field_fails() -> None:
    row = _good_row()
    del row["_ingestion_run_id"]
    with pytest.raises(ValueError, match="_ingestion_run_id"):
        validate_rows([row], business_keys=("hubspot_id",), label="contacts")


def test_wrong_source_system_fails() -> None:
    with pytest.raises(ValueError, match="_source_system"):
        validate_rows(
            [_good_row(_source_system="salesforce")],
            business_keys=("hubspot_id",),
            label="contacts",
        )


def test_duplicate_business_key_in_batch_fails() -> None:
    with pytest.raises(ValueError, match="duplicate business key"):
        validate_rows(
            [_good_row(hubspot_id="1"), _good_row(hubspot_id="1")],
            business_keys=("hubspot_id",),
            label="contacts",
        )


def test_scd2_requires_valid_from_and_is_current() -> None:
    with pytest.raises(ValueError, match="_valid_from"):
        validate_rows(
            [_good_row()],
            business_keys=("hubspot_id",),
            label="contacts",
            scd2=True,
        )


def test_scd2_passes_with_version_fields() -> None:
    validate_rows(
        [
            _good_row(
                hubspot_id="1",
                _valid_from=datetime.now(timezone.utc),
                _is_current=True,
            )
        ],
        business_keys=("hubspot_id",),
        label="contacts",
        scd2=True,
    )


def test_required_keys_can_be_subset() -> None:
    rows = [
        {
            "contact_id": "c1",
            "company_id": "co1",
            "association_category": None,
            "association_type_id": None,
            "raw_json": "{}",
            "_ingested_at": datetime.now(timezone.utc),
            "_ingestion_run_id": "run-a",
            "_source_system": "hubspot",
        }
    ]
    validate_rows(
        rows,
        business_keys=(
            "contact_id",
            "company_id",
            "association_category",
            "association_type_id",
        ),
        required_keys=("contact_id", "company_id"),
        label="contact_company_associations",
    )
