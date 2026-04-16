"""Batch-generate markdown market articles for active models."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.generators.generate_market_article import generate_market_article
from scripts.shared.io import load_models_master
from scripts.shared.logging_utils import get_logger


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate markdown market articles for all active models.")
    parser.add_argument("--target-year", required=True, help="Target year, e.g. 2025")
    return parser.parse_args()


def main():
    args = parse_args()
    log_file_path = repo_root / "data/logs" / f"generate_market_article_batch_{datetime.now().strftime('%Y%m%d')}.log"
    logger = get_logger(
        "generate_market_article_batch",
        level="INFO",
        log_file_path=log_file_path,
    )

    models_master_path = repo_root / "data/normalized/reference/models_master.csv"
    model_records = load_models_master(models_master_path)
    active_models = [record for record in model_records if record.get("active") == "true"]

    logger.info("Batch article generation started for %s active models", len(active_models))

    failed_models = []
    for model_record in active_models:
        model_slug = model_record["model_slug"]
        try:
            generate_market_article(model_slug, args.target_year, logger=logger)
        except Exception as exc:
            failed_models.append(model_slug)
            logger.exception("Failed to generate article for model_slug=%s: %s", model_slug, exc)
            continue

    if failed_models:
        logger.warning("Batch finished with failures: %s", ", ".join(failed_models))
    else:
        logger.info("Batch finished successfully with no failures.")


if __name__ == "__main__":
    main()
