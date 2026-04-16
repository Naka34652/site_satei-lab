"""Post generated draft payloads to WordPress via REST API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib import error, request

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.shared.io import write_json
from scripts.shared.logging_utils import get_logger
from scripts.shared.markup import markdown_to_html


def _load_payload(input_json_path: Path) -> dict:
    return json.loads(Path(input_json_path).read_text(encoding="utf-8"))


def _resolve_auth(username: str | None, app_password: str | None) -> str:
    resolved_username = username or os.getenv("WP_USERNAME", "")
    resolved_app_password = app_password or os.getenv("WP_APP_PASSWORD", "")

    if not resolved_username or not resolved_app_password:
        raise ValueError("WordPress credentials are missing. Set WP_USERNAME / WP_APP_PASSWORD or pass CLI args.")

    token = base64.b64encode(f"{resolved_username}:{resolved_app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _resolve_site_url(site_url: str | None) -> str:
    resolved_site_url = site_url or os.getenv("WP_SITE_URL", "")
    if not resolved_site_url:
        raise ValueError("WordPress site URL is missing. Set WP_SITE_URL or pass --site-url.")
    return resolved_site_url.rstrip("/")


def _build_request_payload(record: dict) -> dict:
    content = record["post_content"]
    if "<h2>" not in content and "<p>" not in content and "<table>" not in content and "<ul>" not in content:
        content = markdown_to_html(content)

    return {
        "title": record["post_title"],
        "slug": record["post_name"],
        "content": content,
        "excerpt": record.get("excerpt", ""),
        "status": "draft",
    }


def _request_json(url: str, auth_header: str, timeout_sec: int, method="GET", payload: dict | None = None) -> dict | list:
    data = None
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    api_request = request.Request(url, data=data, method=method, headers=headers)
    with request.urlopen(api_request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_existing_post_id(post_name: str, site_url: str, auth_header: str, timeout_sec: int) -> int | None:
    lookup_url = f"{site_url}/wp-json/wp/v2/posts?slug={post_name}&status=any&context=edit"
    response_json = _request_json(lookup_url, auth_header, timeout_sec)
    if isinstance(response_json, list) and response_json:
        return response_json[0].get("id")
    return None


def _post_one_record(record: dict, site_url: str, auth_header: str, timeout_sec: int) -> dict:
    request_payload = _build_request_payload(record)
    existing_post_id = _find_existing_post_id(record["post_name"], site_url, auth_header, timeout_sec)
    if existing_post_id:
        endpoint = f"{site_url}/wp-json/wp/v2/posts/{existing_post_id}"
        action = "updated"
    else:
        endpoint = f"{site_url}/wp-json/wp/v2/posts"
        action = "created"

    response_json = _request_json(endpoint, auth_header, timeout_sec, method="POST", payload=request_payload)

    return {
        "success": True,
        "action": action,
        "model_slug": record["model_slug"],
        "post_name": record["post_name"],
        "wp_post_id": response_json.get("id"),
        "wp_status": response_json.get("status"),
        "wp_link": response_json.get("link"),
        "meta_description": record.get("meta_description"),
        "category_candidates": record.get("category_candidates", []),
        "eyecatch_title_candidate": record.get("eyecatch_title_candidate", ""),
    }


def build_result_output_path(input_json_path: Path) -> Path:
    stem = input_json_path.stem
    return repo_root / "output/wordpress_drafts" / f"{stem}_post_results.json"


def post_drafts(input_json_path: Path, site_url: str, auth_header: str, timeout_sec: int, logger) -> dict:
    payload = _load_payload(input_json_path)
    results = []
    failed = []

    for record in payload.get("records", []):
        try:
            result = _post_one_record(
                record=record,
                site_url=site_url,
                auth_header=auth_header,
                timeout_sec=timeout_sec,
            )
            results.append(result)
            logger.info(
                "Draft %s successfully: %s -> wp_post_id=%s",
                result["action"],
                record["post_name"],
                result["wp_post_id"],
            )
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            failed_record = {
                "success": False,
                "model_slug": record["model_slug"],
                "post_name": record["post_name"],
                "error_type": "HTTPError",
                "status_code": exc.code,
                "reason": exc.reason,
                "response_body": error_body,
            }
            failed.append(failed_record)
            logger.error("Draft post failed: %s (HTTP %s %s)", record["post_name"], exc.code, exc.reason)
        except error.URLError as exc:
            failed_record = {
                "success": False,
                "model_slug": record["model_slug"],
                "post_name": record["post_name"],
                "error_type": "URLError",
                "reason": str(exc.reason),
            }
            failed.append(failed_record)
            logger.error("Draft post failed: %s (%s)", record["post_name"], exc.reason)
        except Exception as exc:  # noqa: BLE001
            failed_record = {
                "success": False,
                "model_slug": record["model_slug"],
                "post_name": record["post_name"],
                "error_type": type(exc).__name__,
                "reason": str(exc),
            }
            failed.append(failed_record)
            logger.exception("Draft post failed unexpectedly: %s", record["post_name"])

    return {
        "input_file": str(input_json_path),
        "site_url": site_url,
        "posted_count": len(results),
        "failed_count": len(failed),
        "posted": results,
        "failed": failed,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Post WordPress draft payload JSON to the WP REST API.")
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to a wordpress draft payload JSON file.",
    )
    parser.add_argument(
        "--site-url",
        default=None,
        help="WordPress site URL. Falls back to WP_SITE_URL.",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="WordPress username. Falls back to WP_USERNAME.",
    )
    parser.add_argument(
        "--app-password",
        default=None,
        help="WordPress application password. Falls back to WP_APP_PASSWORD.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=30,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    now_str = datetime.now().strftime("%Y%m%d")
    log_path = repo_root / "data/logs" / f"post_wordpress_drafts_{now_str}.log"
    logger = get_logger("post_wordpress_drafts", log_file_path=log_path)

    input_json_path = Path(args.input_json)
    site_url = _resolve_site_url(args.site_url)
    auth_header = _resolve_auth(args.username, args.app_password)

    result = post_drafts(
        input_json_path=input_json_path,
        site_url=site_url,
        auth_header=auth_header,
        timeout_sec=args.timeout_sec,
        logger=logger,
    )

    output_path = build_result_output_path(input_json_path)
    write_json(output_path, result)
    logger.info("Draft posting result JSON: %s", output_path)
    logger.info("Posted=%s Failed=%s", result["posted_count"], result["failed_count"])


if __name__ == "__main__":
    main()
