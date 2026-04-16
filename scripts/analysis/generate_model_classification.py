"""Build content classification data for active models.

This script reads the active models from models_master.csv and combines them
with the generated summary CSVs to produce a lightweight classification table
that article templates can reference later.
"""

from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path("/Users/user/Documents/Site/satei-lab")
MODELS_MASTER_CSV = REPO_ROOT / "data/normalized/reference/models_master.csv"
SUMMARY_DIR = REPO_ROOT / "data/marts/summary"
OUTPUT_CSV = REPO_ROOT / "data/normalized/reference/model_classification.csv"


# Expensive / enthusiast-oriented models deserve a slightly different tone.
SPORTS_OR_PREMIUM_SLUGS = {
    "daihatsu-copen",
    "honda-beat",
    "honda-civic-type-r",
    "honda-cr-x",
    "honda-integra",
    "honda-nsx",
    "honda-prelude",
    "honda-s2000",
    "honda-s660",
    "nissan-fairlady-z",
    "nissan-gt-r",
    "nissan-silvia",
    "mazda-roadster",
    "mazda-roadster-rf",
    "mazda-rx-7",
    "mazda-rx-8",
    "mazda-savanna-rx-7",
    "mitsubishi-lancer-evolution",
    "mitsubishi-lancer-evolution-wagon",
    "subaru-brz",
    "subaru-impreza-wrx",
    "toyota-gr86",
    "toyota-gr-corolla",
    "toyota-gr-yaris",
    "toyota-supra",
}

# Optional support tags for finer template tuning.
SUPPORT_TAGS = {
    "軽自動車": {
        "daihatsu-cast",
        "daihatsu-copen",
        "daihatsu-esse",
        "daihatsu-max",
        "daihatsu-mira",
        "daihatsu-mira-avi",
        "daihatsu-mira-cocoa",
        "daihatsu-mira-es",
        "daihatsu-mira-gino",
        "daihatsu-mira-gino-1000",
        "daihatsu-mira-tocot",
        "daihatsu-move",
        "daihatsu-move-canbus",
        "daihatsu-move-conte",
        "daihatsu-move-custom",
        "daihatsu-move-latte",
        "daihatsu-sonica",
        "daihatsu-taft",
        "daihatsu-tanto",
        "daihatsu-tanto-custom",
        "daihatsu-tanto-exe",
        "honda-beat",
        "honda-n-box",
        "honda-n-one",
        "honda-n-van",
        "honda-n-wgn",
        "honda-s660",
        "mazda-az-offroad",
        "mazda-az-wagon",
        "mazda-carol",
        "mazda-carol-eco",
        "mazda-flare",
        "mazda-flare-crossover",
        "mazda-flare-wagon",
        "mazda-scrum-wagon",
        "mazda-spiano",
        "mitsubishi-delica-mini",
        "mitsubishi-ek-cross",
        "mitsubishi-ek-cross-ev",
        "mitsubishi-ek-wagon",
        "mitsubishi-minica",
        "mitsubishi-pajero-mini",
        "mitsubishi-town-box",
        "subaru-chiffon",
        "subaru-pleo",
        "subaru-pleo-nesta",
        "subaru-pleo-plus",
        "subaru-r1",
        "subaru-r2",
        "subaru-stella",
        "subaru-vivio",
        "subaru-vivio-bistro",
        "subaru-vivio-targa-top",
        "suzuki-alto",
        "suzuki-alto-eco",
        "suzuki-alto-lapin",
        "suzuki-alto-lapin-chocolat",
        "suzuki-alto-works",
        "suzuki-cervo",
        "suzuki-cervo-mode",
        "suzuki-every-wagon",
        "suzuki-hustler",
        "suzuki-jimny",
        "suzuki-mr-wagon",
        "suzuki-palette",
        "suzuki-spacia",
        "suzuki-spacia-custom",
        "suzuki-spacia-gear",
        "suzuki-twin",
        "suzuki-wagon-r-custom-z",
        "suzuki-wagon-r-rr",
        "suzuki-wagon-r-smile",
        "suzuki-wagon-r-stingray",
        "nissan-dayz",
        "nissan-roox",
        "nissan-sakura",
    },
    "ミニバン": {
        "daihatsu-atrai7",
        "daihatsu-thor",
        "honda-freed",
        "honda-odyssey",
        "honda-step-wgn",
        "mazda-biante",
        "mazda-mpv",
        "mitsubishi-delica-d5",
        "mitsubishi-delica-space-gear",
        "mitsubishi-dion",
        "mitsubishi-grandis",
        "subaru-exiga",
        "subaru-exiga-crossover-7",
        "suzuki-solio",
        "suzuki-solio-bandit",
        "suzuki-wagon-r-solio",
        "nissan-elgrand",
        "nissan-lafesta",
        "nissan-presage",
        "nissan-serena",
        "toyota-alphard",
        "toyota-noah",
        "toyota-sienta",
        "toyota-vellfire",
        "toyota-voxy",
    },
    "商用車": {
        "daihatsu-hijet-cargo",
        "daihatsu-hijet-deck-van",
        "daihatsu-hijet-truck",
        "honda-n-van",
        "mazda-scrum-truck",
        "mazda-scrum-van",
        "mitsubishi-delica-van",
        "mitsubishi-mini-cab-truck",
        "subaru-sambar-truck",
        "subaru-sambar-van",
        "suzuki-every",
        "suzuki-every-wagon",
        "nissan-caravan",
        "nissan-nv200-vanette",
    },
    "EV・FCV": {
        "mitsubishi-ek-cross-ev",
        "mitsubishi-outlander-phev",
        "mazda-mx-30",
        "mazda-mx-30-rotary-ev",
        "nissan-ariya",
        "nissan-leaf",
        "nissan-sakura",
        "subaru-solterra",
        "toyota-bz4x",
        "toyota-mirai",
    },
}


def _load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _load_active_models() -> list[dict[str, str]]:
    return [row for row in _load_csv_rows(MODELS_MASTER_CSV) if row["active"].lower() == "true"]


def _load_latest_year(model_slug: str) -> int:
    rows = _load_csv_rows(SUMMARY_DIR / f"{model_slug}_year_summary.csv")
    return max(int(row["target_year"]) for row in rows if row.get("target_year"))


def _load_overall_summary(model_slug: str) -> dict[str, str]:
    rows = _load_csv_rows(SUMMARY_DIR / f"{model_slug}_overall_summary.csv")
    return rows[0]


def _has_required_summary_files(model_slug: str) -> bool:
    required_paths = [
        SUMMARY_DIR / f"{model_slug}_year_summary.csv",
        SUMMARY_DIR / f"{model_slug}_mileage_summary.csv",
        SUMMARY_DIR / f"{model_slug}_overall_summary.csv",
    ]
    return all(path.exists() for path in required_paths)


def _build_support_tags(model_slug: str) -> list[str]:
    tags = []
    for tag_name, slugs in SUPPORT_TAGS.items():
        if model_slug in slugs:
            tags.append(tag_name)
    return tags


def _classify_model(model_slug: str, latest_year: int, price_median: float, high_price: float) -> tuple[str, str]:
    reasons = []

    if model_slug in SPORTS_OR_PREMIUM_SLUGS:
        reasons.append("sports_or_premium_list")
    if price_median >= 220:
        reasons.append("overall_price_median>=220")
    if high_price >= 500:
        reasons.append("high_price>=500")

    if reasons:
        return "高額・スポーツ系車種", " / ".join(reasons)

    if latest_year <= 2022:
        return "古い年式中心の車種", "latest_available_year<=2022"

    return "通常車種", "default"


def build_classification_rows() -> list[dict[str, str]]:
    rows = []

    for model in _load_active_models():
        model_slug = model["model_slug"]
        if not _has_required_summary_files(model_slug):
            continue
        latest_year = _load_latest_year(model_slug)
        overall = _load_overall_summary(model_slug)
        price_median = float(overall["price_median"])
        high_price = float(overall["high_price"])
        primary_class, classification_reason = _classify_model(
            model_slug=model_slug,
            latest_year=latest_year,
            price_median=price_median,
            high_price=high_price,
        )

        rows.append(
            {
                "model_slug": model_slug,
                "maker_name": model["maker_name"],
                "model_name": model["model_name"],
                "primary_class": primary_class,
                "support_tags": "|".join(_build_support_tags(model_slug)),
                "latest_available_year": str(latest_year),
                "overall_price_median": overall["price_median"],
                "overall_high_price": overall["high_price"],
                "classification_reason": classification_reason,
            }
        )

    return sorted(rows, key=lambda row: (row["primary_class"], row["maker_name"], row["model_slug"]))


def write_output(rows: list[dict[str, str]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model_slug",
        "maker_name",
        "model_name",
        "primary_class",
        "support_tags",
        "latest_available_year",
        "overall_price_median",
        "overall_high_price",
        "classification_reason",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    write_output(build_classification_rows())


if __name__ == "__main__":
    main()
