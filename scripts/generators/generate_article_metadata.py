"""Generate posting metadata candidates for generated market articles."""

from __future__ import annotations

import argparse
from pathlib import Path

import sys

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.shared.io import load_csv, load_models_master, write_csv
from scripts.shared.logging_utils import get_logger


def _to_int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _is_low_sample(row, threshold=3):
    return _to_int(row.get("sample_count")) < threshold


def _format_common_range_text(row):
    low = row.get("price_common_min")
    high = row.get("price_common_max")
    if not low and not high:
        return "参考値"
    if low == high:
        return f"{low}万円前後"
    return f"{low}万円〜{high}万円"


def _pick_latest_year_row(year_rows):
    candidates = [row for row in year_rows if str(row.get("target_year", "")).isdigit()]
    if not candidates:
        return None
    return max(candidates, key=lambda row: _to_int(row.get("target_year")))


def _load_classification_map():
    rows = load_csv(repo_root / "data/normalized/reference/model_classification.csv")
    return {row["model_slug"]: row for row in rows}


def _build_category_candidates(maker_name, primary_class, support_tags):
    categories = ["車買取相場", maker_name]

    if primary_class == "古い年式中心の車種":
        categories.append("旧型・生産終了車")
    elif primary_class == "高額・スポーツ系車種":
        categories.append("高額・スポーツ車")

    for tag in filter(None, support_tags.split("|")):
        categories.append(tag)

    # Keep ordering stable while removing duplicates.
    seen = set()
    ordered = []
    for category in categories:
        if category not in seen:
            seen.add(category)
            ordered.append(category)
    return ordered


def _build_meta_description(model_name, article_year, latest_year_row, primary_class):
    latest_year_label = latest_year_row.get("target_year_label", "最新年式")
    median_price = latest_year_row.get("price_median")
    range_text = _format_common_range_text(latest_year_row)
    low_sample = _is_low_sample(latest_year_row)

    if primary_class == "古い年式中心の車種":
        return (
            f"{model_name}の買取相場を{article_year}年版として整理。"
            f"公開データで確認できた最新は{latest_year_label}で、中央値は{median_price}万円。"
            f"{'事例ベースの参考値として' if low_sample else ''}年式別・走行距離別の査定目安をまとめています。"
        )

    if primary_class == "高額・スポーツ系車種":
        return (
            f"{model_name}の買取相場を{article_year}年版で解説。"
            f"{latest_year_label}の中央値は{median_price}万円、目安は{range_text}。"
            f"{'サンプルは少なめのため参考値中心で' if low_sample else '高値事例も含めて'}振れ幅を確認できます。"
        )

    return (
        f"{model_name}の買取相場を{article_year}年版で整理。"
        f"{latest_year_label}の中央値は{median_price}万円、目安は{range_text}。"
        f"{'参考値ベースで' if low_sample else ''}年式別・走行距離別の査定目安を確認できます。"
    )


def _build_excerpt(model_name, article_year, latest_year_row, primary_class):
    latest_year_label = latest_year_row.get("target_year_label", "最新年式")
    median_price = latest_year_row.get("price_median")
    range_text = _format_common_range_text(latest_year_row)
    high_price = latest_year_row.get("high_price")
    low_sample = _is_low_sample(latest_year_row)

    if primary_class == "古い年式中心の車種":
        second_sentence = (
            f"公開データ上で確認できた最新は{latest_year_label}で、中央値は{median_price}万円、目安は{range_text}です。"
        )
        caution = "比較的新しい年式の公開データが限られるため、相場感をつかむ入口として使いやすい内容にまとめています。"
        return f"{model_name}の買取相場を{article_year}年版として整理しました。{second_sentence}{caution}"

    if primary_class == "高額・スポーツ系車種":
        caution = (
            "グレード差や修復歴、走行距離差で振れ幅が出やすい車種なので、"
            "中央値と高値事例をあわせて見たいときの入口に向いています。"
        )
        if low_sample:
            caution = (
                "サンプル数が少ない場合は事例ベースの参考値として見ながら、"
                "複数査定で条件差を確認しやすいように整理しています。"
            )
        return (
            f"{model_name}の買取相場を{article_year}年版で整理しました。"
            f"{latest_year_label}の中央値は{median_price}万円、目安は{range_text}、高値事例は{high_price}万円です。"
            f"{caution}"
        )

    caution = "年式別・走行距離別の目安をひと目で確認したいときに使いやすい構成です。"
    if low_sample:
        caution = "サンプル数が少ない場合は参考値として見ながら、事例ベースで相場感をつかみやすいように整理しています。"
    return (
        f"{model_name}の買取相場を{article_year}年版で整理しました。"
        f"{latest_year_label}の中央値は{median_price}万円、目安は{range_text}です。"
        f"{caution}"
    )


def _build_eyecatch_title(model_name, article_year, primary_class):
    if primary_class == "高額・スポーツ系車種":
        return f"{model_name} 買取相場 {article_year} 高値事例"
    if primary_class == "古い年式中心の車種":
        return f"{model_name} 買取相場 {article_year}年版"
    return f"{model_name} 買取相場 {article_year}"


def _build_slug_candidate(model_slug, article_year):
    return f"{model_slug}-kaitori-soba-{article_year}"


def build_metadata_rows(target_year):
    models = load_models_master(repo_root / "data/normalized/reference/models_master.csv")
    classification_map = _load_classification_map()
    summary_dir = repo_root / "data/marts/summary"
    output_dir = repo_root / "output/articles"

    rows = []
    for model in models:
        if model.get("active") != "true":
            continue

        model_slug = model["model_slug"]
        article_path = output_dir / f"{model_slug}-kaitori-soba-{target_year}.md"
        if not article_path.exists():
            continue

        year_rows = load_csv(summary_dir / f"{model_slug}_year_summary.csv")
        latest_year_row = _pick_latest_year_row(year_rows)
        classification_row = classification_map.get(
            model_slug,
            {
                "primary_class": "通常車種",
                "support_tags": "",
            },
        )

        category_candidates = _build_category_candidates(
            maker_name=model["maker_name"],
            primary_class=classification_row["primary_class"],
            support_tags=classification_row.get("support_tags", ""),
        )

        rows.append(
            {
                "model_slug": model_slug,
                "model_name": model["model_name"],
                "maker_name": model["maker_name"],
                "article_year": str(target_year),
                "article_file": article_path.name,
                "post_slug_candidate": _build_slug_candidate(model_slug, target_year),
                "meta_description_candidate": _build_meta_description(
                    model_name=model["model_name"],
                    article_year=str(target_year),
                    latest_year_row=latest_year_row,
                    primary_class=classification_row["primary_class"],
                ),
                "excerpt_candidate": _build_excerpt(
                    model_name=model["model_name"],
                    article_year=str(target_year),
                    latest_year_row=latest_year_row,
                    primary_class=classification_row["primary_class"],
                ),
                "primary_category_candidate": category_candidates[0] if category_candidates else "",
                "category_candidates": "|".join(category_candidates),
                "eyecatch_title_candidate": _build_eyecatch_title(
                    model_name=model["model_name"],
                    article_year=str(target_year),
                    primary_class=classification_row["primary_class"],
                ),
                "primary_class": classification_row["primary_class"],
                "support_tags": classification_row.get("support_tags", ""),
                "latest_available_year": classification_row.get("latest_available_year", ""),
            }
        )

    return rows


def write_metadata_csv(target_year, rows):
    output_path = repo_root / "output/metadata" / f"article_metadata_{target_year}.csv"
    fieldnames = [
        "model_slug",
        "model_name",
        "maker_name",
        "article_year",
        "article_file",
        "post_slug_candidate",
        "meta_description_candidate",
        "excerpt_candidate",
        "primary_category_candidate",
        "category_candidates",
        "eyecatch_title_candidate",
        "primary_class",
        "support_tags",
        "latest_available_year",
    ]
    return write_csv(output_path, fieldnames, rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate article metadata candidates from generated markdown files.")
    parser.add_argument("--target-year", required=True, help="Article year, e.g. 2026")
    return parser.parse_args()


def main():
    logger = get_logger("generate_article_metadata")
    args = parse_args()
    rows = build_metadata_rows(args.target_year)
    output_path = write_metadata_csv(args.target_year, rows)
    logger.info("Generated article metadata CSV: %s", output_path)
    logger.info("Metadata rows: %s", len(rows))


if __name__ == "__main__":
    main()
