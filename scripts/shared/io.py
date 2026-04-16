"""I/O helpers for scaffolded pipeline files."""

import csv
import json
from pathlib import Path


def load_models_master(csv_path):
    """Load model records from models_master.csv."""
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        records = list(csv.DictReader(fh))

    for record in records:
        raw_source_model_key = record.get("source_model_key", "")
        try:
            parsed_source_model_key = json.loads(raw_source_model_key)
        except (TypeError, json.JSONDecodeError):
            parsed_source_model_key = {"root": raw_source_model_key, "year_variants": {}}

        if isinstance(parsed_source_model_key, str):
            parsed_source_model_key = {"root": parsed_source_model_key, "year_variants": {}}

        parsed_source_model_key.setdefault("root", "")
        parsed_source_model_key.setdefault("year_variants", {})
        record["source_model_key_map"] = parsed_source_model_key

    return records


def load_csv(csv_path):
    """Load a generic CSV file into a list of dictionaries."""
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def select_model_record(model_records, target_model_slug):
    """Return the first active record that matches the target slug."""
    for record in model_records:
        if record.get("model_slug") == target_model_slug and record.get("active") == "true":
            return record

    raise ValueError(f"Target model slug not found or inactive: {target_model_slug}")


def ensure_parent_dir(file_path):
    """Create the parent directory for a file path when needed."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def write_text(file_path, content):
    """Write UTF-8 text content to disk."""
    file_path = Path(file_path)
    ensure_parent_dir(file_path)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def write_json(file_path, payload):
    """Write JSON payload to disk."""
    file_path = Path(file_path)
    ensure_parent_dir(file_path)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return file_path


def write_csv(file_path, fieldnames, rows):
    """Write CSV rows to disk."""
    file_path = Path(file_path)
    ensure_parent_dir(file_path)
    with file_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return file_path
