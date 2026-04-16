"""Build WordPress draft payloads from generated markdown articles and metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.shared.io import load_csv, load_models_master, write_json
from scripts.shared.logging_utils import get_logger


def _load_metadata_rows(target_year):
    metadata_path = repo_root / "output/metadata" / f"article_metadata_{target_year}.csv"
    rows = load_csv(metadata_path)
    return {row["model_slug"]: row for row in rows}


def _read_markdown_article(article_path):
    lines = article_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Article file is empty: {article_path}")

    title_line = lines[0].strip()
    if title_line.startswith("# "):
        post_title = title_line[2:]
        post_content = "\n".join(lines[2:]).strip()
    else:
        post_title = title_line
        post_content = "\n".join(lines[1:]).strip()

    return post_title, post_content


def build_draft_records(target_year, model_slugs):
    metadata_map = _load_metadata_rows(target_year)
    articles_dir = repo_root / "output/articles"
    records = []

    for model_slug in model_slugs:
        metadata = metadata_map.get(model_slug)
        if not metadata:
            raise ValueError(f"Metadata not found for model_slug={model_slug}")

        article_path = articles_dir / metadata["article_file"]
        if not article_path.exists():
            raise ValueError(f"Article file not found for model_slug={model_slug}: {article_path}")

        post_title, post_content = _read_markdown_article(article_path)
        records.append(
            {
                "model_slug": model_slug,
                "post_title": post_title,
                "post_name": metadata["post_slug_candidate"],
                "post_content": post_content,
                "meta_description": metadata["meta_description_candidate"],
                "excerpt": metadata["excerpt_candidate"],
                "category_candidates": metadata["category_candidates"].split("|") if metadata["category_candidates"] else [],
                "eyecatch_title_candidate": metadata["eyecatch_title_candidate"],
                "post_status": "draft",
                "article_file": metadata["article_file"],
            }
        )

    return records


def write_payload(target_year, records, output_label):
    output_path = repo_root / "output/wordpress_drafts" / f"wordpress_draft_payload_{target_year}_{output_label}.json"
    payload = {
        "target_year": str(target_year),
        "record_count": len(records),
        "records": records,
    }
    return write_json(output_path, payload)


def _resolve_model_slugs(args):
    if args.all_active:
        models_master_path = repo_root / "data/normalized/reference/models_master.csv"
        model_records = load_models_master(models_master_path)
        return [record["model_slug"] for record in model_records if record.get("active") == "true"]

    if not args.model_slugs:
        raise ValueError("Either --model-slugs or --all-active is required.")

    return [slug.strip() for slug in args.model_slugs.split(",") if slug.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate WordPress draft payload JSON from article markdown and metadata CSV.")
    parser.add_argument("--target-year", required=True, help="Article year, e.g. 2026")
    parser.add_argument(
        "--model-slugs",
        default="",
        help="Comma-separated model slugs, e.g. toyota-prius,honda-jade,honda-nsx",
    )
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="Generate payload for all active models in models_master.csv",
    )
    parser.add_argument(
        "--output-label",
        default="sample",
        help="Output file label, e.g. sample or all",
    )
    return parser.parse_args()


def main():
    logger = get_logger("generate_wordpress_draft_payload")
    args = parse_args()
    model_slugs = _resolve_model_slugs(args)
    records = build_draft_records(args.target_year, model_slugs)
    output_path = write_payload(args.target_year, records, args.output_label)
    logger.info("Generated WordPress draft payload: %s", output_path)
    logger.info("Draft records: %s", len(records))


if __name__ == "__main__":
    main()
