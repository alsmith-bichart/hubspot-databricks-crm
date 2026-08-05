"""Bronze quality checks against live HubSpot + Databricks (sampled).

Rules:
1. Required HubSpot IDs exist
2. Raw JSON retained
3. Technical ingestion fields exist
4. Keys unique after loading
   - CRM objects (SCD2): one current row per hubspot_id
   - Append tables: history key (business key + run_id) unique for this run

One sampled ingest (default 25). SCD2 close_missing disabled while sampling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion import bronze_loader as loader
from ingestion.config import load_settings
from ingestion.pipeline import run_bronze_pipeline
from schemas.object_specs import (
    ASSOCIATION_SPECS,
    CRM_OBJECT_SPECS,
    OWNER_BUSINESS_KEYS,
    PIPELINE_STAGE_BUSINESS_KEYS,
    TECH_FIELDS,
    history_keys,
)

DEFAULT_SAMPLE_LIMIT = 25


def _append_tables(settings):
    tables = [
        (
            "owners",
            settings.bronze("owners"),
            OWNER_BUSINESS_KEYS,
            OWNER_BUSINESS_KEYS,
            True,
        ),
        (
            "deal_pipeline_stages",
            settings.bronze("deal_pipeline_stages"),
            PIPELINE_STAGE_BUSINESS_KEYS,
            PIPELINE_STAGE_BUSINESS_KEYS,
            False,
        ),
    ]
    for assoc in ASSOCIATION_SPECS:
        tables.append(
            (
                assoc.table_name,
                settings.bronze(assoc.table_name),
                assoc.business_keys,
                (assoc.from_id_column, assoc.to_id_column),
                False,
            )
        )
    return tables


def _assert_quality(
    conn,
    settings,
    *,
    run_id: str,
    sample_limit: int,
    label: str,
) -> None:
    for spec in CRM_OBJECT_SPECS:
        table_fqn = settings.bronze(spec.table_name)
        required = ("hubspot_id", "raw_json", "_valid_from", "_is_current") + TECH_FIELDS
        loader.assert_required_columns_non_null_current(
            conn,
            table_fqn,
            required,
            label=f"{label}:{table_fqn}",
        )
        loader.assert_one_current_per_business_key(
            conn,
            table_fqn,
            "hubspot_id",
            label=f"{label}:{table_fqn}",
        )
        current_n = loader.count_current(conn, table_fqn)
        if current_n <= 0:
            raise SystemExit(
                f"FAIL: {spec.name} expected >0 current SCD2 rows"
            )

    for name, table_fqn, business_keys, required_ids, capped in _append_tables(
        settings
    ):
        required = tuple(required_ids) + ("raw_json",) + TECH_FIELDS
        loader.assert_required_columns_non_null(
            conn,
            table_fqn,
            required,
            label=f"{label}:{table_fqn}",
            run_id=run_id,
        )
        loader.assert_unique_keys(
            conn,
            table_fqn,
            history_keys(business_keys),
            label=f"{label}:{table_fqn}",
            run_id=run_id,
        )
        run_count = loader.count_table(conn, table_fqn, run_id=run_id)
        if capped:
            if run_count <= 0:
                raise SystemExit(
                    f"FAIL: {name} expected >0 rows for run_id={run_id}"
                )
            if run_count > sample_limit:
                raise SystemExit(
                    f"FAIL: {name} expected <= {sample_limit} rows for "
                    f"run_id={run_id}, got {run_count}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sampled bronze quality check")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SAMPLE_LIMIT,
        help=f"HubSpot sample size (default {DEFAULT_SAMPLE_LIMIT})",
    )
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be > 0")

    settings = load_settings()
    sample_limit = args.limit

    print(f"=== Sampled bronze quality (limit={sample_limit}) ===")
    run_id, counts = run_bronze_pipeline(sample_limit=sample_limit)
    print(f"run_id={run_id}")
    print(f"counts={counts}")

    with loader.connect(settings) as conn:
        _assert_quality(
            conn,
            settings,
            run_id=run_id,
            sample_limit=sample_limit,
            label="after_sample_ingest",
        )
        print("CRM current counts / append run counts:")
        for spec in CRM_OBJECT_SPECS:
            n = loader.count_current(conn, settings.bronze(spec.table_name))
            print(f"  {spec.name} (current): {n}")
        for name, table_fqn, *_ in _append_tables(settings):
            n = loader.count_table(conn, table_fqn, run_id=run_id)
            print(f"  {name} (run): {n}")

    print("PASS: bronze quality rules satisfied (sampled one ingest)")


if __name__ == "__main__":
    main()
