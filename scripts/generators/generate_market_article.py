"""Generate a markdown market-price article from summary CSVs."""

import argparse
import sys
from pathlib import Path
from statistics import median

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.shared.io import load_csv, write_text
from scripts.shared.logging_utils import get_logger
from scripts.shared.io import load_models_master, select_model_record


def _to_int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _to_float(value):
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _format_price_range(min_value, max_value):
    return f"{min_value}万円〜{max_value}万円"


def _format_price_single(value):
    return f"{value}万円"


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


def _bucket_label(lower_km, upper_km):
    if lower_km is None or upper_km is None:
        return "不明"

    if lower_km < 10000:
        return "1万km未満"

    if lower_km >= 100000:
        return "10万km以上"

    lower_man = int(lower_km / 10000)
    return f"{lower_man}万km台"


def _pick_latest_year_row(year_rows):
    """Return the latest available vehicle model year row."""
    candidates = [row for row in year_rows if str(row.get("target_year", "")).isdigit()]
    if not candidates:
        return None
    return max(candidates, key=lambda row: _to_int(row.get("target_year")))


def _load_classification_map():
    classification_path = repo_root / "data/normalized/reference/model_classification.csv"
    rows = load_csv(classification_path)
    return {row["model_slug"]: row for row in rows}


def _build_output_path(output_dir, model_slug, target_year):
    return output_dir / f"{model_slug}-kaitori-soba-{target_year}.md"


def _top_year_rows(year_rows, limit=8):
    sorted_rows = sorted(
        year_rows,
        key=lambda row: _to_int(row.get("target_year")),
        reverse=True,
    )
    return sorted_rows[:limit]


def _find_best_year(year_rows):
    candidates = [row for row in year_rows if _to_int(row.get("sample_count")) > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda row: _to_float(row.get("price_median")))


def _format_high_price_case(row):
    high_price = row.get("high_price")
    high_case = row.get("high_price_case")
    if not high_price:
        return "高値事例は確認できませんでした。"
    if high_case:
        return f"{high_price}万円（{high_case}）"
    return f"{high_price}万円"


def _describe_source_basis(row):
    """Return a short explanation of which source population was used."""
    if row.get("source_page_type") == "year_variant":
        variant_label = row.get("source_variant_label", "")
        return f"年式/落ち年ページ（{variant_label}）を基準にした"
    return "車種トップページを基準にした"


def _describe_source_basis_for_sentence(row):
    """Return a sentence-friendly explanation of the source population."""
    if row.get("source_page_type") == "year_variant":
        variant_label = row.get("source_variant_label", "")
        return f"年式/落ち年ページ（{variant_label}）の公開データ"
    return "車種トップページの公開データ"


def _aggregate_mileage_rows(mileage_rows):
    grouped = {}
    for row in mileage_rows:
        lower = _to_int(row.get("mileage_min_km"))
        sample_count = _to_int(row.get("sample_count"))
        if sample_count <= 0:
            continue

        if lower >= 100000:
            bucket_min = 100000
            bucket_max = 999999
        else:
            bucket_min = (lower // 10000) * 10000
            bucket_max = bucket_min + 9999

        key = (bucket_min, bucket_max)
        grouped.setdefault(key, []).append(row)

    aggregated = []
    for (bucket_min, bucket_max), rows in sorted(grouped.items(), key=lambda item: item[0][0]):
        sample_count = sum(_to_int(row.get("sample_count")) for row in rows)
        price_min = min(_to_float(row.get("price_min")) for row in rows)
        price_max = max(_to_float(row.get("price_max")) for row in rows)
        weighted_medians = []
        weighted_common_lows = []
        weighted_common_highs = []
        weighted_avg_total = 0.0
        high_price = 0.0
        high_price_case = ""

        for row in rows:
            row_sample_count = _to_int(row.get("sample_count"))
            weighted_avg_total += _to_float(row.get("price_avg")) * row_sample_count
            weighted_medians.extend([_to_float(row.get("price_median"))] * row_sample_count)
            weighted_common_lows.extend([_to_float(row.get("price_common_min"))] * row_sample_count)
            weighted_common_highs.extend([_to_float(row.get("price_common_max"))] * row_sample_count)

            row_high_price = _to_float(row.get("high_price"))
            if row_high_price >= high_price:
                high_price = row_high_price
                high_price_case = row.get("high_price_case", "")

        price_avg = round(weighted_avg_total / sample_count, 1) if sample_count else 0.0
        price_median = round(median(weighted_medians), 1) if weighted_medians else 0.0
        price_common_min = round(median(weighted_common_lows), 1) if weighted_common_lows else 0.0
        price_common_max = round(median(weighted_common_highs), 1) if weighted_common_highs else 0.0

        aggregated.append(
            {
                "mileage_bucket_label": _bucket_label(bucket_min, bucket_max),
                "mileage_min_km": bucket_min,
                "mileage_max_km": bucket_max,
                "sample_count": sample_count,
                "price_min": f"{price_min:.1f}",
                "price_max": f"{price_max:.1f}",
                "price_avg": f"{price_avg:.1f}",
                "price_median": f"{price_median:.1f}",
                "price_common_min": f"{price_common_min:.1f}",
                "price_common_max": f"{price_common_max:.1f}",
                "high_price": f"{high_price:.1f}",
                "high_price_case": high_price_case,
                "source_page_type": rows[0].get("source_page_type", "root"),
                "source_variant_label": rows[0].get("source_variant_label", "root"),
            }
        )

    return aggregated


def _find_best_mileage(aggregated_mileage_rows):
    candidates = [row for row in aggregated_mileage_rows if _to_int(row.get("sample_count")) > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda row: _to_float(row.get("price_median")))


def _build_support_note(model_name, support_tags):
    if not support_tags:
        return ""

    tag_set = set(filter(None, support_tags.split("|")))

    support_notes = {
        "軽自動車": (
            f"{model_name}は軽自動車カテゴリでも見られるため、年式や走行距離だけでなく、"
            " 日常使いしやすさや内外装の傷、使用感でも査定差が出やすい傾向があります。"
        ),
        "ミニバン": (
            f"{model_name}はミニバン需要も意識されやすく、乗車人数や装備、"
            " ファミリー利用での使用感が査定で見られやすい車種です。"
        ),
        "商用車": (
            f"{model_name}は商用利用も想定されやすいため、走行距離に加えて、"
            " 荷室の状態や整備履歴、使用歴の分かりやすさも確認されやすくなります。"
        ),
        "EV・FCV": (
            f"{model_name}はEV・FCV系の見られ方もあるため、一般的な年式や走行距離に加えて、"
            " バッテリーやインフラ条件、装備内容による差も意識しておくと相場を読みやすくなります。"
        ),
    }

    ordered_tags = ["軽自動車", "ミニバン", "商用車", "EV・FCV"]
    notes = [support_notes[tag] for tag in ordered_tags if tag in tag_set]
    return " ".join(notes)


def _build_summary_lines(model_name, article_year, latest_year_label, latest_year_row, primary_class):
    lines = []
    low_sample = _is_low_sample(latest_year_row)
    common_range_text = _format_common_range_text(latest_year_row)

    if primary_class == "古い年式中心の車種":
        lines.append(
            f"- この記事は **{article_year}年版** としてまとめていますが、公開データ上で確認できた最新の年式は **{latest_year_label}** です。"
        )
        lines.append(
            f"- {model_name}は比較的新しい年式の公開データが限られるため、まずは **{latest_year_label}** を基準に相場感をつかむ見方が現実的です。"
        )
    else:
        lines.append(
            f"- この記事は **{article_year}年版** としてまとめていますが、公開データ上で確認できた最新の年式は **{latest_year_label}** です。"
        )

    if low_sample:
        lines.append(
            f"- {latest_year_label}は査定サンプルが **{_to_int(latest_year_row.get('sample_count'))}件** と少なく、中央値 **{latest_year_row.get('price_median')}万円** と **{common_range_text}** は参考値として見るのが自然です。"
        )
        lines.append(f"- 直近で確認できた事例ベースでは **{_format_high_price_case(latest_year_row)}** でした。")
    else:
        lines.append(
            f"- {latest_year_label}の中央値は **{latest_year_row.get('price_median')}万円**、よくあるレンジの目安は **{common_range_text}** でした。"
        )
        lines.append(f"- 高値事例としては **{_format_high_price_case(latest_year_row)}** があり、条件次第で上振れも狙えます。")

    if primary_class == "高額・スポーツ系車種":
        if low_sample:
            lines.append(
                f"- {model_name}はグレード差や修復歴、走行距離の違いで振れ幅が出やすく、特にサンプルが少ないうちは断定せず、事例ベースで相場感をつかむのが安全です。"
            )
        else:
            lines.append(
                f"- {model_name}はグレード差や修復歴、走行距離の違いで振れ幅が出やすく、高値事例と中央値をセットで見るのが大切です。"
            )
    lines.append(f"- 数字は、**{_describe_source_basis_for_sentence(latest_year_row)}** をもとに整理しています。")

    lines.append("- 実際の売却額はグレードや状態で変わるため、相場を把握したうえで複数社比較に進むのが安全です。")
    return lines


def _build_caution_lines(article_year, latest_year_label, latest_year_row, primary_class):
    low_sample = _is_low_sample(latest_year_row)
    lines = [
        f"- この記事は {article_year}年版ですが、集計に使っている公開データでは {latest_year_label} が最新確認年式です。",
        "- この記事の数値は集計時点の参考値で、将来の査定額を保証するものではありません。",
    ]

    if primary_class == "高額・スポーツ系車種":
        lines.append("- 高額帯やスポーツ寄りの車種は、グレード、修復歴、走行距離、装備差で金額の振れ幅が大きくなりやすいです。")
    elif primary_class == "古い年式中心の車種":
        lines.append("- 最新年式の公開データが古めの車種では、サンプル数や流通状況によって相場の見え方がぶれやすくなります。")
    else:
        lines.append("- 個体差、地域差、修復歴、内外装の状態、装備差で価格は上下します。")

    if low_sample:
        lines.append("- 最新確認年式のサンプル数が少ないため、中央値やレンジは事例ベースの参考値として見るのが安全です。")

    lines.extend(
        [
            "- 高値事例は実在の参考ケースですが、同じ金額になることを示すものではありません。",
            "- サンプル数が少ない年式や距離帯では、レンジが実態より広く見えることがあります。",
        ]
    )
    return lines


def _build_faq_blocks(model_name, article_year, latest_year_label, latest_year_row, overall_row, primary_class):
    low_sample = _is_low_sample(latest_year_row)
    common_range_text = _format_common_range_text(latest_year_row)
    blocks = [
        (
            f"{article_year}年版の記事なのに、なぜ {latest_year_label} のデータが中心なのですか？",
            f"この記事の {article_year}年版 という表記は更新年を示しています。実際の金額目安は、公開データ上で確認できた最新年式である {latest_year_label} を中心に整理しており、中央値は {latest_year_row.get('price_median')}万円、よくあるレンジの目安は {common_range_text} でした。"
            + (" ただしサンプル数が少ない場合は、参考値として見るのが自然です。" if low_sample else ""),
        ),
    ]

    if primary_class == "高額・スポーツ系車種":
        blocks.append(
            (
                f"{model_name}はグレードや修復歴でどれくらい査定差が出ますか？",
                f"{model_name}は高値事例が目立ちやすい一方で、グレードや修復歴、走行距離の違いで金額差が広がりやすい車種です。"
                + (" 今回のようにサンプル数が少ない場合は、個別事例ベースで見ながら断定を避けるのが安全です。" if low_sample else " 中央値と高値事例をあわせて見ながら、実車条件に近い比較先を探すのが安全です。"),
            )
        )
    elif primary_class == "古い年式中心の車種":
        blocks.append(
            (
                f"{model_name}は古い年式でも査定対象になりますか？",
                f"なります。{model_name}のように公開データ上の最新確認年式が古めの車種でも、状態や走行距離、需要次第で査定がつくケースはあります。まずは少なめのサンプルでも中央値と高値事例の両方を見るのがおすすめです。",
            )
        )
    else:
        blocks.append(
            (
                f"{model_name}は10万kmを超えても値段はつきますか？",
                f"今回の全体集計では、{model_name}全体で {overall_row.get('price_min')}万円〜{overall_row.get('price_max')}万円 の幅がありました。10万km超でも査定自体は十分ありえますが、年式や状態で差が出ます。",
            )
        )

    blocks.extend(
        [
            (
                f"{model_name}は装備差で査定が変わりますか？",
                f"変わる可能性があります。{model_name}はグレードや安全装備、ナビ、駆動方式の違いで比較されやすいため、同じ年式でも査定差が出ます。",
            ),
            (
                f"すぐ売らなくても{model_name}の査定だけ取る意味はありますか？",
                "あります。いまの相場感を知っておくと、売り時や乗り換え時期を判断しやすくなります。",
            ),
        ]
    )
    return blocks


def _build_quick_table(model_name, latest_year_row, overall_row):
    latest_year_label = latest_year_row.get("target_year_label", "最新確認年式")
    common_range_text = _format_common_range_text(latest_year_row)
    if _is_low_sample(latest_year_row):
        common_range_text = f"{common_range_text}（参考値）"
    lines = [
        "| 指標 | 数値 |",
        "| --- | --- |",
        f"| 記事内で主に参照した年式 | {latest_year_label} |",
        f"| {latest_year_label}の査定サンプル数 | {_to_int(latest_year_row.get('sample_count'))}件 |",
        f"| {latest_year_label}の中央値 | {_format_price_single(latest_year_row.get('price_median'))} |",
        f"| {latest_year_label}のよくあるレンジ | {common_range_text} |",
        f"| {latest_year_label}の高値事例 | {_format_high_price_case(latest_year_row)} |",
        f"| {latest_year_label}の参照母集団 | {_describe_source_basis(latest_year_row)} |",
        f"| {model_name}全体の中央値 | {_format_price_single(overall_row.get('price_median'))} |",
        f"| {model_name}全体の高値事例 | {_format_high_price_case(overall_row)} |",
    ]
    return "\n".join(lines)


def _build_year_section(year_rows):
    lines = [
        "| 年式 | サンプル数 | 中央値 | よくあるレンジ | 高値事例 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in _top_year_rows(year_rows):
        lines.append(
            f"| {row.get('target_year_label')} | {_to_int(row.get('sample_count'))} | "
            f"{row.get('price_median')}万円 | "
            f"{_format_common_range_text(row)} | "
            f"{_format_high_price_case(row)} |"
        )
    return "\n".join(lines)


def _build_mileage_section(mileage_rows):
    aggregated_rows = _aggregate_mileage_rows(mileage_rows)
    lines = [
        "| 走行距離帯 | サンプル数 | 中央値 | よくあるレンジ | 高値事例 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in aggregated_rows[:8]:
        lines.append(
            f"| {row.get('mileage_bucket_label')} | {_to_int(row.get('sample_count'))} | "
            f"{row.get('price_median')}万円 | "
            f"{_format_common_range_text(row)} | "
            f"{_format_high_price_case(row)} |"
        )
    return "\n".join(lines)


def build_article_markdown(model_name, article_year, overall_row, latest_year_row, year_rows, mileage_rows, classification_row):
    aggregated_mileage_rows = _aggregate_mileage_rows(mileage_rows)
    best_year = _find_best_year(year_rows)
    best_mileage = _find_best_mileage(aggregated_mileage_rows)
    latest_year_label = latest_year_row.get("target_year_label", "最新確認年式")
    primary_class = classification_row.get("primary_class", "通常車種")
    support_note = _build_support_note(model_name, classification_row.get("support_tags", ""))
    summary_lines = _build_summary_lines(model_name, article_year, latest_year_label, latest_year_row, primary_class)
    caution_lines = _build_caution_lines(article_year, latest_year_label, latest_year_row, primary_class)
    faq_blocks = _build_faq_blocks(model_name, article_year, latest_year_label, latest_year_row, overall_row, primary_class)

    title = f"# {model_name}の買取相場【{article_year}年版】年式別・走行距離別の査定目安\n"

    year_hint = "年式別の数字は参考になりますが、個体差があるため金額をそのまま当てはめない方が安全です。"
    if best_year:
        year_hint = (
            f"年式別では {best_year.get('target_year_label')} の中央値が {best_year.get('price_median')}万円で高めでした。"
            " ただしサンプル数と条件差をあわせて見るのが前提です。"
        )

    mileage_hint = "走行距離の傾向は見えますが、グレードや地域差を無視して断定するのは避けた方が無難です。"
    if best_mileage:
        mileage_hint = (
            f"走行距離帯では {best_mileage.get('mileage_bucket_label')} の中央値が {best_mileage.get('price_median')}万円で高めでした。"
            " 低走行ほど有利な傾向はありますが、例外もあります。"
        )

    sections = [
        title,
        "## 結論サマリー",
        *summary_lines,
        "",
        "## 買取相場早見表",
        _build_quick_table(model_name, latest_year_row, overall_row),
        "",
        "## まず押さえたいポイント",
        f"- この記事は {article_year}年版として更新していますが、本文中の金額目安は主に {latest_year_label} の公開データをもとにしています。",
        f"- {year_hint}",
        f"- {mileage_hint}",
        "- 新しい年式でも、装備や状態、売却タイミングで金額は大きく動きます。",
        "- この記事の数値は査定目安として使い、最終判断は実査定で確認するのが現実的です。",
        "",
        "## 補足",
        support_note if support_note else f"{model_name}は年式や走行距離の数字だけでなく、装備や使われ方によっても査定の見え方が変わります。本文の数字は相場感をつかむ入口として使うのが自然です。",
        "",
        "## 年式別相場",
        _build_year_section(year_rows),
        "",
        f"{article_year}年版の時点で、公開データから確認できた最新の年式は {latest_year_label} でした。"
        f" {model_name}は年式が近くても中央値に差があり、"
        " 古い年式ほど価格レンジが広がりやすいため、下限と上限よりも中央値を基準に見ると使いやすいです。",
        "",
        "## 走行距離別相場",
        _build_mileage_section(mileage_rows),
        "",
        "走行距離別は細かい1,000km単位の数字ではブレやすいため、記事では距離帯でまとめています。"
        " 低走行ほど有利な傾向は見えますが、サンプル数が少ない帯は参考値として扱うのが無難です。",
        "",
        "## 高く売るコツ",
        "- 相場を1社だけで判断せず、複数の査定先を比較する。",
        f"- {model_name}の年式・走行距離・グレードを整理して、査定時に伝えやすくしておく。",
        "- 純正ナビや安全装備、4WDなど評価されやすい仕様は見落とさず伝える。",
        "- 相場が動く前提で、売るか迷っていても早めに査定目安を確認しておく。",
        "",
        "## 注意点",
        *caution_lines,
        "",
        "## よくある質問",
        *[item for question, answer in faq_blocks for item in (f"### {question}", answer, "")],
        "## まとめ",
        f"{article_year}年版の{model_name}相場記事では、公開データ上で確認できた最新年式である {latest_year_label} を基準に、中央値 {latest_year_row.get('price_median')}万円、"
        f"価格帯は {latest_year_row.get('price_min')}万円〜{latest_year_row.get('price_max')}万円 と整理しました。"
        " ただし実際の売却額は条件差で変わるため、この記事の数字は相場把握の入口として使い、最終的には比較査定で確認するのが安全です。",
        "",
    ]
    return "\n".join(sections)


def generate_market_article(model_slug, target_year, logger=None):
    """Generate one markdown article from summary CSVs and return the output path."""
    if logger is None:
        logger = get_logger("generate_market_article")

    summary_dir = repo_root / "data/marts/summary"
    output_dir = repo_root / "output/articles"
    models_master_path = repo_root / "data/normalized/reference/models_master.csv"
    classification_map = _load_classification_map()

    model_records = load_models_master(models_master_path)
    model_record = select_model_record(model_records, model_slug)
    model_name = model_record["model_name"]
    classification_row = classification_map.get(
        model_slug,
        {"primary_class": "通常車種", "support_tags": ""},
    )

    year_rows = load_csv(summary_dir / f"{model_slug}_year_summary.csv")
    mileage_rows = load_csv(summary_dir / f"{model_slug}_mileage_summary.csv")
    overall_rows = load_csv(summary_dir / f"{model_slug}_overall_summary.csv")

    overall_row = overall_rows[0]
    article_year = str(target_year)
    latest_year_row = _pick_latest_year_row(year_rows)
    if not latest_year_row:
        raise ValueError(f"No available year summary rows found for model_slug={model_slug}")

    markdown = build_article_markdown(
        model_name=model_name,
        article_year=article_year,
        overall_row=overall_row,
        latest_year_row=latest_year_row,
        year_rows=year_rows,
        mileage_rows=mileage_rows,
        classification_row=classification_row,
    )

    output_path = _build_output_path(output_dir, model_slug, article_year)
    write_text(output_path, markdown)
    logger.info("Generated article draft: %s", output_path)
    return output_path


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate a markdown market article from summary CSVs.")
    parser.add_argument("--model-slug", required=True, help="Target model slug, e.g. toyota-prius")
    parser.add_argument("--target-year", required=True, help="Target year, e.g. 2025")
    return parser.parse_args()


def main():
    logger = get_logger("generate_market_article")
    args = parse_args()
    generate_market_article(args.model_slug, args.target_year, logger=logger)


if __name__ == "__main__":
    main()
