from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ingestion import bronze_loader as loader
from ingestion.config import load_settings
from ingestion.hubspot_client import (
    get_all_objects,
    get_all_owners,
    get_associations_batch,
    get_deal_pipelines,
)
from ingestion.mappers import (
    association_to_rows,
    object_to_row,
    owner_to_row,
    pipeline_stage_to_rows,
)
from ingestion.validators import validate_rows
from schemas.object_specs import (
    ASSOCIATION_SPECS,
    CRM_OBJECT_SPECS,
    OWNER_BUSINESS_KEYS,
    PIPELINE_STAGE_BUSINESS_KEYS,
    TECH_FIELDS,
    history_keys,
)


def _post_load_checks_append(
    conn,
    *,
    table_fqn: str,
    business_keys: tuple[str, ...],
    label: str,
    required_keys: tuple[str, ...] | None = None,
) -> None:
    must_have = required_keys if required_keys is not None else business_keys
    required = tuple(must_have) + ("raw_json",) + TECH_FIELDS
    loader.assert_required_columns_non_null(
        conn, table_fqn, required, label=label
    )
    loader.assert_unique_keys(
        conn, table_fqn, history_keys(business_keys), label=label
    )


def _post_load_checks_scd2(
    conn,
    *,
    table_fqn: str,
    label: str,
) -> None:
    required = ("hubspot_id", "raw_json", "_valid_from", "_is_current") + TECH_FIELDS
    loader.assert_required_columns_non_null_current(
        conn, table_fqn, required, label=label
    )
    loader.assert_one_current_per_business_key(
        conn, table_fqn, "hubspot_id", label=label
    )


def run_bronze_pipeline(
    *, sample_limit: int | None = None
) -> tuple[str, dict[str, int]]:
    run_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc)
    settings = load_settings()
    token = settings.hubspot_token
    # Sampled runs must not soft-close IDs absent from the sample.
    close_missing = sample_limit is None

    print(f"Starting bronze pipeline run_id={run_id}")
    if sample_limit is not None:
        print(f"sample_limit={sample_limit} (SCD2 close_missing=False)")

    id_sets: dict[str, list[str]] = {}
    counts: dict[str, int] = {}

    with loader.connect(settings) as conn:
        loader.assert_bronze_tables_exist(conn, settings)

        for spec in CRM_OBJECT_SPECS:
            print(f"Fetching {spec.name}...")
            objects = get_all_objects(
                token,
                spec.hubspot_object,
                list(spec.properties),
                limit=sample_limit,
            )
            id_sets[spec.name] = [str(obj["id"]) for obj in objects]
            rows = [
                object_to_row(
                    obj, run_id=run_id, spec=spec, ingested_at=ingested_at
                )
                for obj in objects
            ]
            validate_rows(
                rows,
                business_keys=spec.business_keys,
                label=spec.name,
                scd2=True,
            )

            bronze = settings.bronze(spec.table_name)
            columns = loader.object_column_names(spec)
            print(f"SCD2 loading {bronze} ({len(rows)} staged rows)...")
            loader.upsert_scd2(
                conn,
                settings,
                table_name=spec.table_name,
                rows=rows,
                columns=columns,
                close_missing=close_missing,
            )
            _post_load_checks_scd2(conn, table_fqn=bronze, label=spec.name)
            counts[spec.name] = loader.count_current(conn, bronze)
            print(f"  current {bronze}={counts[spec.name]}")

        print("Fetching owners...")
        owners = get_all_owners(token, limit=sample_limit)
        owner_rows = [
            owner_to_row(owner, run_id=run_id, ingested_at=ingested_at)
            for owner in owners
        ]
        validate_rows(
            owner_rows, business_keys=OWNER_BUSINESS_KEYS, label="owners"
        )
        owner_bronze = settings.bronze("owners")
        loader.append_bronze(
            conn, owner_bronze, owner_rows, loader.owner_column_names()
        )
        _post_load_checks_append(
            conn,
            table_fqn=owner_bronze,
            business_keys=OWNER_BUSINESS_KEYS,
            label="owners",
        )
        counts["owners"] = loader.count_table(conn, owner_bronze)
        print(f"  loaded {owner_bronze}={counts['owners']}")

        print("Fetching deal pipeline stages...")
        pipelines = get_deal_pipelines(token)
        stage_rows = []
        for pipeline in pipelines:
            stage_rows.extend(
                pipeline_stage_to_rows(
                    pipeline, run_id=run_id, ingested_at=ingested_at
                )
            )
        validate_rows(
            stage_rows,
            business_keys=PIPELINE_STAGE_BUSINESS_KEYS,
            label="deal_pipeline_stages",
        )
        stage_bronze = settings.bronze("deal_pipeline_stages")
        loader.append_bronze(
            conn,
            stage_bronze,
            stage_rows,
            loader.pipeline_stage_column_names(),
        )
        _post_load_checks_append(
            conn,
            table_fqn=stage_bronze,
            business_keys=PIPELINE_STAGE_BUSINESS_KEYS,
            label="deal_pipeline_stages",
        )
        counts["deal_pipeline_stages"] = loader.count_table(conn, stage_bronze)
        print(f"  loaded {stage_bronze}={counts['deal_pipeline_stages']}")

        print("Fetching associations...")
        for assoc_spec in ASSOCIATION_SPECS:
            batch_results = get_associations_batch(
                token,
                assoc_spec.from_object_type,
                assoc_spec.to_object_type,
                id_sets.get(assoc_spec.from_object_type, []),
            )
            assoc_rows = []
            for result in batch_results:
                assoc_rows.extend(
                    association_to_rows(
                        result,
                        spec=assoc_spec,
                        run_id=run_id,
                        ingested_at=ingested_at,
                    )
                )
            validate_rows(
                assoc_rows,
                business_keys=assoc_spec.business_keys,
                required_keys=(
                    assoc_spec.from_id_column,
                    assoc_spec.to_id_column,
                ),
                label=assoc_spec.table_name,
            )

            assoc_bronze = settings.bronze(assoc_spec.table_name)
            columns = loader.association_column_names(assoc_spec.columns)
            loader.append_bronze(conn, assoc_bronze, assoc_rows, columns)
            _post_load_checks_append(
                conn,
                table_fqn=assoc_bronze,
                business_keys=assoc_spec.business_keys,
                required_keys=(
                    assoc_spec.from_id_column,
                    assoc_spec.to_id_column,
                ),
                label=assoc_spec.table_name,
            )
            counts[assoc_spec.table_name] = loader.count_table(
                conn, assoc_bronze
            )
            print(f"  loaded {assoc_bronze}={counts[assoc_spec.table_name]}")

        print("Final bronze counts (CRM=current SCD2; others=table total):")
        for name, count in counts.items():
            print(f"  {name}: {count}")

    print(f"Bronze pipeline completed successfully run_id={run_id}")
    return run_id, counts
