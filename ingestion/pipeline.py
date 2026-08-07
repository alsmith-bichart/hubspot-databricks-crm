"""Bronze ingest orchestration — SCD2 CRM objects + append dims/assocs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from configs.config import Settings, load_settings
from ingestion import bronze_loader as loader
from ingestion.hubspot_client import (
    get_all_companies,
    get_all_contacts,
    get_all_deals,
    get_all_owners,
    get_associations,
    get_deal_pipelines,
)
from ingestion.mappers import (
    association_to_row,
    company_to_row,
    contact_to_row,
    deal_to_row,
    owner_to_row,
    pipeline_to_stage_rows,
)
from schemas.object_specs import (
    ASSOCIATION_COLUMNS,
    ASSOCIATION_SPECS,
    COMPANY_PROPERTIES,
    CONTACT_PROPERTIES,
    CRM_OBJECT_COLUMNS,
    DEAL_PIPELINE_STAGE_COLUMNS,
    DEAL_PROPERTIES,
    OWNER_COLUMNS,
    staging_table_name,
)


def _maybe_limit(
    rows: list[dict[str, Any]], sample_limit: int | None
) -> list[dict[str, Any]]:
    if sample_limit is None:
        return rows
    return rows[:sample_limit]


def _load_scd2(
    conn: Any,
    settings: Settings,
    object_type: str,
    raw: list[dict[str, Any]],
    to_row: Callable[..., dict[str, Any]],
    *,
    ingested_at: datetime,
    run_id: str,
    close_missing: bool,
) -> None:
    rows = [to_row(o, ingested_at=ingested_at, run_id=run_id) for o in raw]
    stg = staging_table_name(object_type)
    print(f"{object_type} fetched={len(rows)}")
    loader.truncate_table(conn, settings.bronze(stg))
    n = loader.insert_rows(conn, settings.bronze(stg), CRM_OBJECT_COLUMNS, rows)
    print(f"{object_type} staged={n}")
    loader.scd2_merge(conn, settings, object_type, close_missing=close_missing)
    print(
        f"{object_type} current={loader.count_current(conn, settings, object_type)} "
        f"versions={loader.count_rows(conn, settings.bronze(object_type))}"
    )


def run_bronze_pipeline(*, sample_limit: int | None = None) -> None:
    settings = load_settings()
    token = settings.hubspot_token
    run_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc)
    close_missing = sample_limit is None
    print(f"run_id={run_id} catalog={settings.catalog} close_missing={close_missing}")

    # --- fetch HubSpot ---
    contacts_raw = _maybe_limit(
        get_all_contacts(token, CONTACT_PROPERTIES), sample_limit
    )
    companies_raw = _maybe_limit(
        get_all_companies(token, COMPANY_PROPERTIES), sample_limit
    )
    deals_raw = _maybe_limit(get_all_deals(token, DEAL_PROPERTIES), sample_limit)
    owners_raw = get_all_owners(token)
    pipelines_raw = get_deal_pipelines(token)

    contact_ids = [str(o["id"]) for o in contacts_raw]
    company_ids = [str(o["id"]) for o in companies_raw]
    deal_ids = [str(o["id"]) for o in deals_raw]

    assoc_from_ids = {
        "contacts": contact_ids,
        "companies": company_ids,
        "deals": deal_ids,
    }

    with loader.connect(settings) as conn:
        loader.assert_bronze_tables(conn, settings)

        # --- SCD2 CRM objects ---
        _load_scd2(
            conn,
            settings,
            "contacts",
            contacts_raw,
            contact_to_row,
            ingested_at=ingested_at,
            run_id=run_id,
            close_missing=close_missing,
        )
        _load_scd2(
            conn,
            settings,
            "companies",
            companies_raw,
            company_to_row,
            ingested_at=ingested_at,
            run_id=run_id,
            close_missing=close_missing,
        )
        _load_scd2(
            conn,
            settings,
            "deals",
            deals_raw,
            deal_to_row,
            ingested_at=ingested_at,
            run_id=run_id,
            close_missing=close_missing,
        )

        # --- append: owners ---
        owner_rows = [
            owner_to_row(o, ingested_at=ingested_at, run_id=run_id)
            for o in owners_raw
        ]
        n = loader.append_rows(
            conn, settings, "owners", OWNER_COLUMNS, owner_rows
        )
        print(f"owners appended={n} total={loader.count_rows(conn, settings.bronze('owners'))}")

        # --- append: deal pipeline stages ---
        stage_rows: list[dict[str, Any]] = []
        for pipeline in pipelines_raw:
            stage_rows.extend(
                pipeline_to_stage_rows(
                    pipeline, ingested_at=ingested_at, run_id=run_id
                )
            )
        n = loader.append_rows(
            conn,
            settings,
            "deal_pipeline_stages",
            DEAL_PIPELINE_STAGE_COLUMNS,
            stage_rows,
        )
        print(
            f"deal_pipeline_stages appended={n} "
            f"total={loader.count_rows(conn, settings.bronze('deal_pipeline_stages'))}"
        )

        # --- append: associations ---
        for spec in ASSOCIATION_SPECS:
            from_object = spec["from_object"]
            to_object = spec["to_object"]
            table_name = spec["table_name"]
            from_ids = assoc_from_ids[from_object]
            edges = get_associations(token, from_object, to_object, from_ids)
            rows = [
                association_to_row(
                    e,
                    from_object=from_object,
                    to_object=to_object,
                    ingested_at=ingested_at,
                    run_id=run_id,
                )
                for e in edges
            ]
            n = loader.append_rows(
                conn, settings, table_name, ASSOCIATION_COLUMNS, rows
            )
            print(
                f"{table_name} appended={n} "
                f"total={loader.count_rows(conn, settings.bronze(table_name))}"
            )

    print("bronze pipeline complete")
