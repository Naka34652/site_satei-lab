"""Normalize parsed kaitori records into article-ready rows."""

from datetime import datetime
from pathlib import Path

from scripts.shared.io import write_json
from scripts.shared.normalizers import (
    normalize_text,
)


def normalize_price_data(parsed_records, config, model_record, repo_root, logger):
    """Normalize extracted records and save a JSON snapshot."""
    normalized_records = []
    for record in parsed_records:
        price_min_yen = record.get("price_min_yen")
        price_max_yen = record.get("price_max_yen")
        appraisal_price_yen = record.get("price_yen")

        normalized_records.append(
            {
                "record_type": record["record_type"],
                "source_slug": record["source_slug"],
                "source_model_key": record["source_model_key"],
                "source_page_type": record.get("source_page_type", "root"),
                "source_variant_label": record.get("source_variant_label", "root"),
                "source_target_year": record.get("source_target_year", ""),
                "fetch_url": record["fetch_url"],
                "collected_at": record["collected_at"],
                "maker_name": record["maker_name"],
                "model_name": record["model_name"],
                "model_slug": record["model_slug"],
                "generation_label": normalize_text(record.get("generation_label", "")),
                "target_year": record.get("target_year", ""),
                "target_year_label": normalize_text(record.get("target_year_label", "")),
                "grade_name": normalize_text(record.get("grade_name", "")),
                "mileage_band_label": normalize_text(record.get("mileage_band_label", "")),
                "mileage_min_km": record.get("mileage_min_km"),
                "mileage_max_km": record.get("mileage_max_km"),
                "color": normalize_text(record.get("color", "")),
                "prefecture": normalize_text(record.get("prefecture", "")),
                "appraisal_date": normalize_text(record.get("appraisal_date", "")),
                "price_range_text": normalize_text(record.get("price_range_text", "")),
                "price_text": normalize_text(record.get("price_text", "")),
                "price_min_yen": price_min_yen,
                "price_max_yen": price_max_yen,
                "price_yen": appraisal_price_yen,
                "price_min_manen": round(price_min_yen / 10000, 1) if price_min_yen is not None else None,
                "price_max_manen": round(price_max_yen / 10000, 1) if price_max_yen is not None else None,
                "price_manen": round(appraisal_price_yen / 10000, 1) if appraisal_price_yen is not None else None,
            }
        )

    normalized_path = (
        Path(repo_root)
        / config["paths"]["normalized_dir"]
        / model_record["model_slug"]
        / f"{model_record['source_slug']}_{datetime.now().strftime('%Y%m%d')}.json"
    )
    write_json(normalized_path, normalized_records)
    logger.info("Normalized %s records", len(normalized_records))

    return normalized_records
