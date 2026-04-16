"""Export normalized kaitori rows and article-ready summaries."""

from pathlib import Path

from scripts.shared.io import write_csv


def export_model_csv(normalized_records, config, model_record, repo_root, logger):
    """Export one per-model CSV for article input."""
    output_path = Path(repo_root) / config["paths"]["marts_csv_dir"] / f"{model_record['model_slug']}.csv"
    rows = sorted(
        normalized_records,
        key=lambda row: (
            row["record_type"],
            -(int(row["target_year"]) if str(row["target_year"]).isdigit() else 0),
            row["mileage_min_km"] or 99999999,
            row["price_max_yen"] or row["price_yen"] or 999999999,
        ),
    )
    fieldnames = [
        "record_type",
        "source_slug",
        "source_model_key",
        "source_page_type",
        "source_variant_label",
        "source_target_year",
        "fetch_url",
        "collected_at",
        "maker_name",
        "model_name",
        "model_slug",
        "generation_label",
        "target_year",
        "target_year_label",
        "grade_name",
        "mileage_band_label",
        "mileage_min_km",
        "mileage_max_km",
        "color",
        "prefecture",
        "appraisal_date",
        "price_range_text",
        "price_text",
        "price_min_yen",
        "price_max_yen",
        "price_yen",
        "price_min_manen",
        "price_max_manen",
        "price_manen",
    ]
    write_csv(output_path, fieldnames, rows)
    logger.info("Exported CSV: %s", output_path)
    return output_path


def export_summary_csvs(model_dataset, config, model_record, repo_root, logger):
    """Export year, mileage, and overall summary CSVs for article templates."""
    summary_dir = Path(repo_root) / config["paths"]["marts_summary_dir"]
    model_slug = model_record["model_slug"]

    year_path = summary_dir / f"{model_slug}_year_summary.csv"
    year_fields = [
        "model_slug",
        "model_name",
        "generation_label",
        "target_year",
        "target_year_label",
        "source_page_type",
        "source_variant_label",
        "sample_count",
        "price_min",
        "price_max",
        "price_avg",
        "price_median",
        "price_common_min",
        "price_common_max",
        "high_price",
        "high_price_case",
        "high_price_year",
        "high_price_grade",
        "high_price_mileage",
        "high_price_prefecture",
        "price_unit",
    ]
    write_csv(year_path, year_fields, model_dataset["year_summary"])

    mileage_path = summary_dir / f"{model_slug}_mileage_summary.csv"
    mileage_fields = [
        "model_slug",
        "model_name",
        "source_page_type",
        "source_variant_label",
        "mileage_band_label",
        "mileage_min_km",
        "mileage_max_km",
        "sample_count",
        "price_min",
        "price_max",
        "price_avg",
        "price_median",
        "price_common_min",
        "price_common_max",
        "high_price",
        "high_price_case",
        "high_price_year",
        "high_price_grade",
        "high_price_mileage",
        "high_price_prefecture",
        "price_unit",
    ]
    write_csv(mileage_path, mileage_fields, model_dataset["mileage_summary"])

    overall_path = summary_dir / f"{model_slug}_overall_summary.csv"
    overall_fields = [
        "model_slug",
        "model_name",
        "source_page_type",
        "source_variant_label",
        "sample_count",
        "price_min",
        "price_max",
        "price_avg",
        "price_median",
        "price_common_min",
        "price_common_max",
        "high_price",
        "high_price_case",
        "high_price_year",
        "high_price_grade",
        "high_price_mileage",
        "high_price_prefecture",
        "price_unit",
    ]
    write_csv(overall_path, overall_fields, model_dataset["overall_summary"])

    logger.info("Exported summary CSVs: %s, %s, %s", year_path, mileage_path, overall_path)
    return {
        "year_summary_csv": year_path,
        "mileage_summary_csv": mileage_path,
        "overall_summary_csv": overall_path,
    }
