"""Build article-ready summary datasets for one model."""

from statistics import median


def _to_manen(value):
    """Convert yen into manen with one decimal place."""
    return round(value / 10000, 1)


def _percentile(sorted_prices, ratio):
    """Return a simple percentile value from a sorted list."""
    if not sorted_prices:
        return None

    index = int(round((len(sorted_prices) - 1) * ratio))
    return sorted_prices[index]


def _build_high_price_case(row):
    """Return article-friendly high price case fields from one appraisal row."""
    parts = []
    if row.get("target_year_label"):
        parts.append(row["target_year_label"])
    if row.get("grade_name"):
        parts.append(row["grade_name"])
    if row.get("mileage_band_label"):
        parts.append(row["mileage_band_label"])
    if row.get("prefecture"):
        parts.append(row["prefecture"])

    return {
        "high_price": _to_manen(row["price_yen"]),
        "high_price_case": " / ".join(parts),
        "high_price_year": row.get("target_year_label", ""),
        "high_price_grade": row.get("grade_name", ""),
        "high_price_mileage": row.get("mileage_band_label", ""),
        "high_price_prefecture": row.get("prefecture", ""),
    }


def _build_price_stats(rows):
    """Return article-ready summary stats."""
    prices_yen = sorted(row["price_yen"] for row in rows)
    high_price_row = max(rows, key=lambda row: row["price_yen"])

    return {
        "sample_count": len(prices_yen),
        "price_min": _to_manen(min(prices_yen)),
        "price_max": _to_manen(max(prices_yen)),
        "price_avg": _to_manen(round(sum(prices_yen) / len(prices_yen))),
        "price_median": _to_manen(round(median(prices_yen))),
        "price_common_min": _to_manen(_percentile(prices_yen, 0.25)),
        "price_common_max": _to_manen(_percentile(prices_yen, 0.75)),
        "price_unit": "manen",
        **_build_high_price_case(high_price_row),
    }


def _group_rows(rows, key_builder):
    grouped = {}
    for row in rows:
        grouped.setdefault(key_builder(row), []).append(row)
    return grouped


def _select_preferred_appraisal_rows(appraisal_rows):
    """Prefer year-variant rows over root rows when both exist for the same target year."""
    years_with_variants = {
        row.get("target_year", "")
        for row in appraisal_rows
        if row.get("source_page_type") == "year_variant" and row.get("target_year")
    }

    preferred_rows = []
    for row in appraisal_rows:
        row_year = row.get("target_year", "")
        if row.get("source_page_type") == "year_variant":
            preferred_rows.append(row)
            continue
        if row_year and row_year in years_with_variants:
            continue
        preferred_rows.append(row)
    return preferred_rows


def _build_source_fields(rows):
    """Return summary metadata showing which source page type was preferred."""
    page_types = {row.get("source_page_type", "root") for row in rows}
    variant_labels = {row.get("source_variant_label", "root") for row in rows if row.get("source_variant_label")}

    if len(page_types) == 1:
        source_page_type = next(iter(page_types))
    else:
        source_page_type = "mixed"

    if len(variant_labels) == 1:
        source_variant_label = next(iter(variant_labels))
    else:
        source_variant_label = "mixed"

    return {
        "source_page_type": source_page_type,
        "source_variant_label": source_variant_label,
    }


def build_model_dataset(normalized_records, config, model_record):
    """Aggregate appraisal records into summary datasets for one model."""
    appraisal_rows = [
        row for row in normalized_records
        if row["record_type"] == "appraisal_record" and row.get("price_yen") is not None
    ]
    preferred_appraisal_rows = _select_preferred_appraisal_rows(appraisal_rows)

    year_groups = _group_rows(
        preferred_appraisal_rows,
        lambda row: (row.get("target_year", ""), row.get("target_year_label", ""), row.get("generation_label", "")),
    )
    year_summary_rows = []
    for (target_year, target_year_label, generation_label), rows in sorted(
        year_groups.items(),
        key=lambda item: int(item[0][0]) if str(item[0][0]).isdigit() else 0,
        reverse=True,
    ):
        year_summary_rows.append(
            {
                "model_slug": model_record["model_slug"],
                "model_name": model_record["model_name"],
                "generation_label": generation_label,
                "target_year": target_year,
                "target_year_label": target_year_label,
                **_build_source_fields(rows),
                **_build_price_stats(rows),
            }
        )

    mileage_groups = _group_rows(
        preferred_appraisal_rows,
        lambda row: (row.get("mileage_band_label", ""), row.get("mileage_min_km"), row.get("mileage_max_km")),
    )
    mileage_summary_rows = []
    for (mileage_band_label, mileage_min_km, mileage_max_km), rows in sorted(
        mileage_groups.items(),
        key=lambda item: item[0][1] if item[0][1] is not None else 999999999,
    ):
        mileage_summary_rows.append(
            {
                "model_slug": model_record["model_slug"],
                "model_name": model_record["model_name"],
                **_build_source_fields(rows),
                "mileage_band_label": mileage_band_label,
                "mileage_min_km": mileage_min_km,
                "mileage_max_km": mileage_max_km,
                **_build_price_stats(rows),
            }
        )

    overall_summary_rows = []
    if preferred_appraisal_rows:
        overall_summary_rows.append(
            {
                "model_slug": model_record["model_slug"],
                "model_name": model_record["model_name"],
                **_build_source_fields(preferred_appraisal_rows),
                **_build_price_stats(preferred_appraisal_rows),
            }
        )

    return {
        "year_summary": year_summary_rows,
        "mileage_summary": mileage_summary_rows,
        "overall_summary": overall_summary_rows,
    }
