"""Fetch one or more raw HTML pages for the configured source and save them to disk."""

from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from scripts.shared.io import write_text


def _build_fetch_targets(model_record):
    """Expand one model record into root/year-variant fetch targets."""
    source_key_map = model_record.get("source_model_key_map", {})
    fetch_targets = [
        {
            "source_page_type": "root",
            "source_variant_label": "root",
            "source_target_year": "",
            "source_model_key": source_key_map.get("root", model_record.get("source_model_key", "")),
        }
    ]

    for target_year, variant_label in sorted(source_key_map.get("year_variants", {}).items(), reverse=True):
        root_key = source_key_map.get("root", model_record.get("source_model_key", ""))
        fetch_targets.append(
            {
                "source_page_type": "year_variant",
                "source_variant_label": variant_label,
                "source_target_year": str(target_year),
                "source_model_key": f"{root_key}/{variant_label}",
            }
        )

    return fetch_targets


def fetch_source_data(config, model_record, repo_root, logger):
    """Fetch raw HTML pages for one model and save them under data/raw/html/."""
    source_slug = model_record["source_slug"]
    source_config = config["sources"][source_slug]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_results = []
    for fetch_target in _build_fetch_targets(model_record):
        fetch_url = urljoin(
            source_config["base_url"],
            source_config["url_template"].format(source_model_key=fetch_target["source_model_key"]),
        )
        request = Request(
            fetch_url,
            headers={"User-Agent": source_config["headers"]["user_agent"]},
        )

        logger.info(
            "Fetching raw HTML from %s (%s)",
            fetch_url,
            fetch_target["source_page_type"],
        )

        try:
            with urlopen(request, timeout=source_config["timeout_sec"]) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.exception("Failed to fetch source HTML: %s", exc)
            raise

        raw_html_path = (
            Path(repo_root)
            / config["paths"]["raw_html_dir"]
            / source_slug
            / model_record["model_slug"]
            / fetch_target["source_variant_label"]
            / f"{timestamp}.html"
        )
        write_text(raw_html_path, html)

        raw_results.append(
            {
                "source_slug": source_slug,
                "source_type": source_config["type"],
                "source_model_key": fetch_target["source_model_key"],
                "source_page_type": fetch_target["source_page_type"],
                "source_variant_label": fetch_target["source_variant_label"],
                "source_target_year": fetch_target["source_target_year"],
                "fetch_url": fetch_url,
                "collected_at": timestamp,
                "raw_html_path": str(raw_html_path),
                "html": html,
            }
        )

    return raw_results
