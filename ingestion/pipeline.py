"""Bronze ingest orchestration — contacts first; more objects later."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from configs.config import load_settings
from ingestion import bronze_loader as loader
from ingestion.hubspot_client import get_all_contacts
from ingestion.mappers import contact_to_row
from schemas.object_specs import CONTACT_COLUMNS, CONTACT_PROPERTIES


def run_bronze_pipeline(*, sample_limit: int | None = None) -> None:
    settings = load_settings()
    run_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc)
    print(f"run_id={run_id} catalog={settings.catalog}")

    # --- contacts ---
    raw = get_all_contacts(settings.hubspot_token, CONTACT_PROPERTIES)
    if sample_limit is not None:
        raw = raw[:sample_limit]
    rows = [
        contact_to_row(o, ingested_at=ingested_at, run_id=run_id) for o in raw
    ]
    print(f"contacts fetched={len(rows)}")

    with loader.connect(settings) as conn:
        loader.assert_contacts_tables(conn, settings)
        loader.truncate_table(conn, settings.bronze("_stg_contacts"))
        n = loader.insert_rows(
            conn, settings.bronze("_stg_contacts"), CONTACT_COLUMNS, rows
        )
        print(f"contacts staged={n}")

        # --limit must NOT close everyone else as "missing"
        loader.scd2_merge_contacts(
            conn, settings, close_missing=(sample_limit is None)
        )
        print(
            f"contacts current={loader.count_current_contacts(conn, settings)} "
            f"versions={loader.count_contacts(conn, settings)}"
        )

    # later: companies, deals (same pattern)
