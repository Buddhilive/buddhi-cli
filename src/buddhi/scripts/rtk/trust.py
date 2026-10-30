"""Project filter trust and SHA-256 integrity management for RTK.

Project-local filters defined in `.buddhi/rtk/filters/*.json` require explicit user trust
to prevent unverified or malicious filter configurations from muting critical output.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from buddhi.scripts.rtk.filters import FilterSpec, load_filter_from_file

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_FILTERS_DIR = Path(".buddhi/rtk/filters")
DEFAULT_TRUST_STORE = Path(".buddhi/rtk/trust.json")


def compute_filter_hash(path: Path) -> str:
    """Compute the SHA-256 hash of a filter file."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def get_trusted_hashes(trust_store: Path = DEFAULT_TRUST_STORE) -> dict[str, str]:
    """Load the map of trusted filter filenames to SHA-256 hashes."""
    if not trust_store.is_file():
        return {}
    try:
        data = json.loads(trust_store.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to read trust store from %s: %s", trust_store, err)
    return {}


def is_filter_trusted(path: Path, trust_store: Path = DEFAULT_TRUST_STORE) -> bool:
    """Check if the given filter file matches its trusted SHA-256 hash."""
    if not path.is_file():
        return False
    trusted = get_trusted_hashes(trust_store)
    file_name = path.name
    if file_name not in trusted:
        return False
    current_hash = compute_filter_hash(path)
    return current_hash == trusted[file_name]


def trust_filter_file(path: Path, trust_store: Path = DEFAULT_TRUST_STORE) -> str:
    """Record the current SHA-256 hash of a filter file into the trust store."""
    if not path.is_file():
        raise FileNotFoundError(f"Filter file not found: {path}")

    current_hash = compute_filter_hash(path)
    trusted = get_trusted_hashes(trust_store)
    trusted[path.name] = current_hash

    trust_store.parent.mkdir(parents=True, exist_ok=True)
    trust_store.write_text(json.dumps(trusted, indent=2), encoding="utf-8")
    return current_hash


def load_project_filters(
    project_filters_dir: Path = DEFAULT_PROJECT_FILTERS_DIR,
    trust_store: Path = DEFAULT_TRUST_STORE,
) -> tuple[list[FilterSpec], list[str]]:
    """Load all trusted project filters from the directory.

    Returns:
        (trusted_filters, untrusted_warning_messages)
    """
    if not project_filters_dir.is_dir():
        return [], []

    filters: list[FilterSpec] = []
    warnings: list[str] = []

    for file_path in sorted(project_filters_dir.glob("*.json")):
        if is_filter_trusted(file_path, trust_store=trust_store):
            try:
                filters.append(load_filter_from_file(file_path))
            except Exception as err:  # noqa: BLE001
                warnings.append(
                    f"Failed to load trusted filter {file_path.name}: {err}"
                )
        else:
            warnings.append(
                f"Untrusted filter skipped: {file_path.name}. Run 'buddhi scripts rtk trust {file_path}' to approve."
            )

    return filters, warnings
