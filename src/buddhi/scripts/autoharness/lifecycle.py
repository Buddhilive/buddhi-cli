"""Pure-function lifecycle evaluator: probation, graduation, and capacity eviction."""

from __future__ import annotations

import hashlib

from buddhi.scripts.autoharness.config import CAPACITY, MATURITY_THRESHOLD
from buddhi.scripts.autoharness.models import LifecycleDecision, SidecarData


def evaluate_lifecycle(
    skills: dict[str, SidecarData],
    current_request_count: int,
    layer: str = "project",
    capacity_limit: int | None = None,
    maturity_limit: int | None = None,
) -> LifecycleDecision:
    """Evaluate skill pool and determine which skills to keep and which to archive."""
    maturity = maturity_limit or MATURITY_THRESHOLD.get(layer, 100)
    capacity = capacity_limit or CAPACITY.get(layer, 50)

    keep: list[str] = []
    to_archive: list[str] = []

    # 1. Graduation review: mature skills with use == 0 and view == 0 get archived
    graduates: list[tuple[str, float]] = []

    for name, sidecar in skills.items():
        tenure = max(0, current_request_count - sidecar.anchor)

        # Still in probation
        if tenure < maturity:
            keep.append(name)
            continue

        # Mature: check usage
        if sidecar.use == 0 and sidecar.view == 0:
            to_archive.append(name)
        else:
            denom = max(1, tenure)
            rate = sidecar.use / denom
            graduates.append((name, rate))

    # 2. Capacity eviction among active graduates
    if len(graduates) > capacity:
        # Sort by rate ascending, tie-break by deterministic sha256 of name
        graduates.sort(
            key=lambda item: (
                item[1],
                hashlib.sha256(item[0].encode("utf-8")).hexdigest(),
            )
        )
        excess = len(graduates) - capacity
        evicted = [g[0] for g in graduates[:excess]]
        retained = [g[0] for g in graduates[excess:]]
        to_archive.extend(evicted)
        keep.extend(retained)
    else:
        keep.extend([g[0] for g in graduates])

    return LifecycleDecision(keep=sorted(keep), archive=sorted(to_archive))
