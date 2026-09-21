"""Participant-side output bounds mirrored from the pinned Track 2 scorer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutputLimits:
    min_draws: int = 200
    max_draws: int = 20_000

