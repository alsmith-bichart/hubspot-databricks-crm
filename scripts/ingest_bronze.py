import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.pipeline import run_bronze_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="HubSpot → bronze ingest")
    parser.add_argument(
        "--catalog",
        default=None,
        help="UC catalog (default: DATABRICKS_CATALOG or crm)",
    )
    parser.add_argument(
        "--bronze-schema",
        default=None,
        help="Bronze schema (default: DATABRICKS_BRONZE_SCHEMA or bronze)",
    )
    args = parser.parse_args()
    if args.catalog:
        os.environ["DATABRICKS_CATALOG"] = args.catalog
    if args.bronze_schema:
        os.environ["DATABRICKS_BRONZE_SCHEMA"] = args.bronze_schema
    run_bronze_pipeline()


if __name__ == "__main__":
    main()
