import argparse
import os
import sys
from pathlib import Path

# Databricks spark_python_task may exec() this file without defining __file__.
try:
    _SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    _SCRIPT_DIR = None

if _SCRIPT_DIR is not None:
    ROOT = _SCRIPT_DIR.parent
else:
    cwd = Path.cwd().resolve()
    ROOT = None
    for candidate in (cwd, *cwd.parents):
        if (candidate / "ingestion" / "__init__.py").is_file():
            ROOT = candidate
            break
    if ROOT is None:
        for arg in sys.argv:
            p = Path(arg)
            try:
                p = p.resolve()
            except OSError:
                continue
            if p.suffix == ".py" and p.parent.name == "scripts":
                ROOT = p.parent.parent
                break
    if ROOT is None:
        raise RuntimeError(
            f"Cannot resolve repo root (cwd={cwd}, argv={list(sys.argv)!r})"
        )

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


# Databricks may exec() without __file__ and with a non-__main__ __name__.
try:
    _has_file = bool(__file__)
except NameError:
    _has_file = False

if __name__ == "__main__" or not _has_file:
    main()
