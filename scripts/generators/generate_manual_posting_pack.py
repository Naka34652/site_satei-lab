"""Generate manual WordPress posting packs from article markdown and metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.shared.io import load_csv, load_models_master, write_csv, write_text
from scripts.shared.logging_utils import get_logger
from scripts.shared.markup import markdown_to_html


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_block(key: str, value: str) -> str:
    lines = value.splitlines() or [""]
    block = [f"{key}: |-"]
    for line in lines:
        block.append(f"  {line}")
    return "\n".join(block)


def _write_yaml_pack(output_path: Path, payload: dict) -> Path:
    categories = payload.get("category_candidates", [])
    lines = [
        f"post_title: {_yaml_quote(payload['post_title'])}",
        f"post_name: {_yaml_quote(payload['post_name'])}",
        _yaml_block("excerpt", payload["excerpt"]),
        _yaml_block("meta_description", payload["meta_description"]),
        "category_candidates:",
    ]

    if categories:
        for category in categories:
            lines.append(f"  - {_yaml_quote(category)}")
    else:
        lines.append("  []")

    lines.extend(
        [
            f"eyecatch_title_candidate: {_yaml_quote(payload['eyecatch_title_candidate'])}",
            f"post_status: {_yaml_quote(payload['post_status'])}",
            _yaml_block("post_content", payload["post_content"]),
            "",
        ]
    )
    return write_text(output_path, "\n".join(lines))


def _read_article_parts(article_path: Path) -> tuple[str, str]:
    lines = article_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Article file is empty: {article_path}")

    title_line = lines[0].strip()
    post_title = title_line[2:] if title_line.startswith("# ") else title_line
    markdown_body = "\n".join(lines[2:]).strip()
    return post_title, markdown_body


def build_manual_pack_rows(target_year: str, model_slugs: list[str]):
    metadata_path = repo_root / "output/metadata" / f"article_metadata_{target_year}.csv"
    metadata_rows = {row["model_slug"]: row for row in load_csv(metadata_path)}
    articles_dir = repo_root / "output/articles"

    pack_rows = []
    for model_slug in model_slugs:
        metadata = metadata_rows.get(model_slug)
        if not metadata:
            raise ValueError(f"Metadata not found for model_slug={model_slug}")

        article_path = articles_dir / metadata["article_file"]
        post_title, markdown_body = _read_article_parts(article_path)
        post_content_html = markdown_to_html(markdown_body)
        pack_rows.append(
            {
                "model_slug": model_slug,
                "post_title": post_title,
                "post_name": metadata["post_slug_candidate"],
                "excerpt": metadata["excerpt_candidate"],
                "meta_description": metadata["meta_description_candidate"],
                "category_candidates": metadata["category_candidates"].split("|") if metadata["category_candidates"] else [],
                "eyecatch_title_candidate": metadata["eyecatch_title_candidate"],
                "post_status": "draft",
                "post_content": post_content_html,
                "article_file": metadata["article_file"],
            }
        )
    return pack_rows


def write_manual_packs(target_year: str, pack_rows: list[dict], output_label: str) -> tuple[Path, list[Path]]:
    output_dir = repo_root / "output/manual_posting" / f"{target_year}_{output_label}"
    index_rows = []
    pack_paths = []

    for row in pack_rows:
        pack_path = output_dir / f"{row['model_slug']}.yaml"
        _write_yaml_pack(pack_path, row)
        pack_paths.append(pack_path)
        index_rows.append(
            {
                "model_slug": row["model_slug"],
                "post_title": row["post_title"],
                "post_name": row["post_name"],
                "pack_file": pack_path.name,
                "article_file": row["article_file"],
            }
        )

    index_path = output_dir / "manual_posting_index.csv"
    write_csv(index_path, ["model_slug", "post_title", "post_name", "pack_file", "article_file"], index_rows)
    return index_path, pack_paths


def _resolve_model_slugs(args) -> list[str]:
    if args.all_active:
        models_master_path = repo_root / "data/normalized/reference/models_master.csv"
        model_records = load_models_master(models_master_path)
        return [record["model_slug"] for record in model_records if record.get("active") == "true"]

    if not args.model_slugs:
        raise ValueError("Either --model-slugs or --all-active is required.")

    return [slug.strip() for slug in args.model_slugs.split(",") if slug.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate manual WordPress posting packs from articles and metadata.")
    parser.add_argument("--target-year", required=True, help="Article year, e.g. 2026")
    parser.add_argument(
        "--model-slugs",
        default="",
        help="Comma-separated model slugs, e.g. toyota-prius,honda-jade,honda-nsx",
    )
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="Generate packs for all active models in models_master.csv",
    )
    parser.add_argument(
        "--output-label",
        default="sample",
        help="Output directory label, e.g. sample or all",
    )
    return parser.parse_args()


def main():
    logger = get_logger("generate_manual_posting_pack")
    args = parse_args()
    model_slugs = _resolve_model_slugs(args)
    pack_rows = build_manual_pack_rows(args.target_year, model_slugs)
    index_path, pack_paths = write_manual_packs(args.target_year, pack_rows, args.output_label)
    logger.info("Generated manual posting index: %s", index_path)
    logger.info("Generated manual posting packs: %s", len(pack_paths))


if __name__ == "__main__":
    main()
