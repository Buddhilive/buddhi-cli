from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.rtk.trust import (
    get_trusted_hashes,
    is_filter_trusted,
    trust_filter_file,
)


def test_trust_filter_flow(tmp_path: Path) -> None:
    trust_store = tmp_path / "trust.json"
    filter_file = tmp_path / "custom-filter.json"

    data = {"name": "custom", "match_command": "^custom"}
    filter_file.write_text(json.dumps(data), encoding="utf-8")

    # Initially untrusted
    assert not is_filter_trusted(filter_file, trust_store=trust_store)

    # Trust the filter
    file_hash = trust_filter_file(filter_file, trust_store=trust_store)
    assert is_filter_trusted(filter_file, trust_store=trust_store)
    assert file_hash in get_trusted_hashes(trust_store=trust_store).values()

    # If file content changes, it is no longer trusted
    filter_file.write_text(
        json.dumps({"name": "custom", "malicious": True}), encoding="utf-8"
    )
    assert not is_filter_trusted(filter_file, trust_store=trust_store)
