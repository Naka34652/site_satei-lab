"""Parse one Kurumaerabi kaitori page from its embedded Next.js JSON."""

import json
import re
from datetime import datetime


NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    flags=re.DOTALL,
)


def _extract_page_props(raw_html):
    match = NEXT_DATA_PATTERN.search(raw_html)
    if not match:
        return {}

    payload = json.loads(match.group(1))
    return payload["props"]["pageProps"]["json"]["pageProps"]


def _generation_label(full_between):
    if not full_between:
        return ""

    generation = full_between[0].get("model_generation")
    full_end_date = full_between[0].get("full_end_date")
    if full_end_date == "9999-12":
        return "現行モデル"
    if generation:
        return f"{generation}代目モデル"
    return ""


def _format_year_label(year_value):
    return f"{year_value}年式" if year_value else ""


def _format_mileage_label(mileage_kiro):
    mileage_kiro = int(mileage_kiro)
    if mileage_kiro % 10000 == 0:
        return f"{mileage_kiro // 10000}万km"
    return f"{mileage_kiro:,}km"


def parse_source_data(raw_result, config, model_record):
    """Parse one Kurumaerabi model page into year, mileage, and appraisal rows."""
    page_props = _extract_page_props(raw_result["html"])
    if not page_props:
        return []

    records = []

    for row in page_props.get("modelYearPriceList", []):
        records.append(
            {
                "record_type": "year_market",
                "generation_label": _generation_label(row.get("fullBetween", [])),
                "target_year": str(row.get("modelYear", "")),
                "target_year_label": _format_year_label(row.get("modelYear", "")),
                "price_min_yen": int(row["minPrice"]) if row.get("minPrice") else None,
                "price_max_yen": int(row["maxPrice"]) if row.get("maxPrice") else None,
                "source_slug": raw_result["source_slug"],
                "source_model_key": raw_result["source_model_key"],
                "source_page_type": raw_result.get("source_page_type", "root"),
                "source_variant_label": raw_result.get("source_variant_label", "root"),
                "source_target_year": raw_result.get("source_target_year", ""),
                "fetch_url": raw_result["fetch_url"],
                "collected_at": raw_result["collected_at"],
                "model_slug": model_record["model_slug"],
                "maker_name": model_record["maker_name"],
                "model_name": model_record["model_name"],
            }
        )

    for row in page_props.get("mileagePriceList", []):
        mileage_kiro = int(row["mileageKiro"]) if row.get("mileageKiro") else None
        records.append(
            {
                "record_type": "mileage_market",
                "mileage_band_label": _format_mileage_label(mileage_kiro) if mileage_kiro is not None else "",
                "mileage_min_km": mileage_kiro,
                "mileage_max_km": mileage_kiro + 9999 if mileage_kiro is not None else None,
                "price_min_yen": int(row["minPrice"]) if row.get("minPrice") else None,
                "price_max_yen": int(row["maxPrice"]) if row.get("maxPrice") else None,
                "source_slug": raw_result["source_slug"],
                "source_model_key": raw_result["source_model_key"],
                "source_page_type": raw_result.get("source_page_type", "root"),
                "source_variant_label": raw_result.get("source_variant_label", "root"),
                "source_target_year": raw_result.get("source_target_year", ""),
                "fetch_url": raw_result["fetch_url"],
                "collected_at": raw_result["collected_at"],
                "model_slug": model_record["model_slug"],
                "maker_name": model_record["maker_name"],
                "model_name": model_record["model_name"],
            }
        )

    for row in page_props.get("carslist", []):
        first_registration_date = row.get("firstRegistrationDate", "")
        stock_date = row.get("stockDateYm") or row.get("stockDate") or ""

        target_year = ""
        if first_registration_date:
            target_year = first_registration_date[:4]

        appraisal_date = ""
        if stock_date:
            appraisal_date = datetime.fromisoformat(stock_date.replace("Z", "+00:00")).strftime("%Y-%m")

        mileage_kiro = int(row["mileageKiro"]) if row.get("mileageKiro") else None
        records.append(
            {
                "record_type": "appraisal_record",
                "grade_name": row.get("carGradeName", ""),
                "target_year": target_year,
                "target_year_label": _format_year_label(target_year),
                "mileage_band_label": _format_mileage_label(mileage_kiro) if mileage_kiro is not None else "",
                "mileage_min_km": mileage_kiro,
                "mileage_max_km": mileage_kiro,
                "prefecture": row.get("address1", ""),
                "appraisal_date": appraisal_date,
                "price_yen": int(row["purchaseAmount"]) if row.get("purchaseAmount") else None,
                "source_slug": raw_result["source_slug"],
                "source_model_key": raw_result["source_model_key"],
                "source_page_type": raw_result.get("source_page_type", "root"),
                "source_variant_label": raw_result.get("source_variant_label", "root"),
                "source_target_year": raw_result.get("source_target_year", ""),
                "fetch_url": raw_result["fetch_url"],
                "collected_at": raw_result["collected_at"],
                "model_slug": model_record["model_slug"],
                "maker_name": model_record["maker_name"],
                "model_name": model_record["model_name"],
            }
        )

    for row in page_props.get("sortedRelateCars", []):
        records.append(
            {
                "record_type": "related_year_market",
                "generation_label": "",
                "target_year": str(row.get("modelYear", "")),
                "target_year_label": _format_year_label(row.get("modelYear", "")),
                "price_min_yen": int(row["priceMin"]) if row.get("priceMin") else None,
                "price_max_yen": int(row["priceMax"]) if row.get("priceMax") else None,
                "source_slug": raw_result["source_slug"],
                "source_model_key": raw_result["source_model_key"],
                "source_page_type": raw_result.get("source_page_type", "root"),
                "source_variant_label": raw_result.get("source_variant_label", "root"),
                "source_target_year": raw_result.get("source_target_year", ""),
                "fetch_url": raw_result["fetch_url"],
                "collected_at": raw_result["collected_at"],
                "model_slug": model_record["model_slug"],
                "maker_name": model_record["maker_name"],
                "model_name": model_record["model_name"],
            }
        )

    return records
