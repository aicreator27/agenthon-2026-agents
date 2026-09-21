"""Deterministic seed handling shared by track adapters."""

from __future__ import annotations

import hashlib
import os


def configured_seed(explicit: int | None, *, default: int = 0) -> int:
    if explicit is not None:
        return explicit
    raw = os.getenv("QFBENCH_SEED")
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError("QFBENCH_SEED must be an integer") from exc


def unit_seed(base_seed: int, unit_id: str) -> int:
    payload = f"agenthon-t2:{base_seed}:{unit_id}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)

