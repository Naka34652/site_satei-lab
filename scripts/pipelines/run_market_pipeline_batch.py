"""Run the full market pipeline for all active models and generate articles."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.generators.generate_market_article import generate_market_article
from scripts.pipelines.run_single_model_pipeline import run_model_pipeline
from scripts.shared.config import load_config
from scripts.shared.io import load_models_master
from scripts.shared.logging_utils import get_logger


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run market pipeline and article generation for active models.")
    parser.add_argument("--target-year", default="2025", help="Preferred target year for article generation.")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(repo_root / "config.yaml")
    log_file_path = repo_root / "data/logs" / f"run_market_pipeline_batch_{datetime.now().strftime('%Y%m%d')}.log"
    logger = get_logger(
        "run_market_pipeline_batch",
        level=config["logging"].get("level", "INFO"),
        log_file_path=log_file_path,
    )

    model_records = load_models_master(repo_root / config["paths"]["models_master_csv"])
    active_models = [record for record in model_records if record.get("active") == "true"]

    logger.info("Batch market pipeline started for %s active models", len(active_models))
    failed_models = []

    for model_record in active_models:
        model_slug = model_record["model_slug"]
        try:
            run_model_pipeline(model_slug, config, repo_root, logger)
            generate_market_article(model_slug, args.target_year, logger=logger)
        except Exception as exc:
            failed_models.append(model_slug)
            logger.exception("Failed to process model_slug=%s: %s", model_slug, exc)
            continue

    if failed_models:
        logger.warning("Batch finished with failures: %s", ", ".join(failed_models))
    else:
        logger.info("Batch finished successfully with no failures.")


if __name__ == "__main__":
    main()
