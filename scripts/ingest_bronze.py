import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.pipeline import run_bronze_pipeline


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    run_bronze_pipeline(sample_limit=args.limit)


if __name__ == "__main__":
    main()