"""Configuration helpers for the data pipeline scaffold."""

import json
from pathlib import Path


def load_config(config_path):
    """Load the project config from disk.

    The scaffold keeps using a .yaml filename, but the file content is stored
    as JSON so the pipeline can run on the standard library alone.
    """
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
