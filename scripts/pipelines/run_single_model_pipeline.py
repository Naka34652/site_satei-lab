"""Entry point for the single-model pipeline scaffold."""

import sys
from datetime import datetime
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.collectors.fetch_source_data import fetch_source_data
from scripts.exporters.export_model_csv import export_model_csv, export_summary_csvs
from scripts.parsers.parse_source_data import parse_source_data
from scripts.shared.config import load_config
from scripts.shared.io import load_models_master, select_model_record
from scripts.shared.logging_utils import get_logger
from scripts.transformers.build_model_dataset import build_model_dataset
from scripts.transformers.normalize_price_data import normalize_price_data


def run_model_pipeline(model_slug, config, repo_root, logger):
    """Run fetch -> parse -> normalize -> export for one model slug."""
    models_master_path = repo_root / config["paths"]["models_master_csv"]
    model_records = load_models_master(models_master_path)
    model_record = select_model_record(model_records, model_slug)

    logger.info("Target model: %s", model_record["model_slug"])
    logger.info("Source: %s", model_record["source_slug"])

    raw_results = fetch_source_data(config, model_record, repo_root, logger)
    parsed_records = []
    for raw_result in raw_results:
        parsed_records.extend(parse_source_data(raw_result, config, model_record))
    logger.info("Parsed %s candidate records", len(parsed_records))

    normalized_records = normalize_price_data(
        parsed_records,
        config,
        model_record,
        repo_root,
        logger,
    )
    export_model_csv(normalized_records, config, model_record, repo_root, logger)
    model_dataset = build_model_dataset(normalized_records, config, model_record)
    export_summary_csvs(model_dataset, config, model_record, repo_root, logger)
    return model_record


def main():
    config_path = repo_root / "config.yaml"
    config = load_config(config_path)
    log_file_path = None
    if config["logging"].get("save_file"):
        log_file_path = (
            repo_root
            / config["paths"]["logs_dir"]
            / f"single_model_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        )
    logger = get_logger(
        "single_model_pipeline",
        level=config["logging"].get("level", "INFO"),
        log_file_path=log_file_path,
    )

    try:
        logger.info("Pipeline started.")
        logger.info("Config loaded from %s", config_path)

        target_model_slug = config["pipeline"]["target_model_slug"]
        run_model_pipeline(target_model_slug, config, repo_root, logger)
        logger.info("Pipeline finished successfully.")
    except Exception:
        logger.exception("Pipeline failed.")
        raise


if __name__ == "__main__":
    main()
