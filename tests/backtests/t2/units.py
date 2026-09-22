"""Deterministic rolling-origin pseudo-unit construction.

Shapes mirror the published roster, which matters because the scorer treats them
differently: 1-cell units get the variogram weight redistributed, multi-cell units do not.
The roster is dominated by single-asset cards, so a backtest made only of wide units would
measure the wrong thing.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

from harness import PseudoUnit, anchor_index, load_panel

SHAPES: tuple[tuple[str, int, tuple[int, ...]], ...] = (
    ("a1h21", 1, (21,)),
    ("a1h63", 1, (63,)),
    ("a1h21_63", 1, (21, 63)),
    ("a4h21", 4, (21,)),
    ("a4h63_126", 4, (63, 126)),
)

MIN_HISTORY = 320  # a full M0 trailing window (300) plus room for the gap rule


def deepest_panels(units_root: pathlib.Path) -> dict[str, pathlib.Path]:
    """One panel file per family: the deepest published copy of it."""
    best: dict[str, tuple[int, pathlib.Path]] = {}
    for path in sorted(units_root.rglob("*.parquet")):
        family = path.stem
        size = path.stat().st_size
        if family not in best or size > best[family][0]:
            best[family] = (size, path)
    return {family: path for family, (_, path) in best.items()}


def build_units(
    panel_key: str,
    panel_path: pathlib.Path,
    *,
    target_type: str = "level",
    stride: int = 21,
    shapes: tuple[tuple[str, int, tuple[int, ...]], ...] = SHAPES,
    min_history: int = MIN_HISTORY,
) -> list[PseudoUnit]:
    panel = load_panel(panel_path)
    assets = sorted(panel)
    grid = panel[assets[0]][0]
    for asset in assets[1:]:
        grid = np.intersect1d(grid, panel[asset][0])

    units: list[PseudoUnit] = []
    for order, position in enumerate(range(min_history, len(grid), stride)):
        asof = str(grid[position])
        for shape, n_assets, horizons in shapes:
            if n_assets == 1:
                chosen = (assets[order % len(assets)],)
            else:
                if len(assets) < n_assets:
                    continue
                chosen = tuple(assets[:n_assets])
            longest = max(horizons)
            if any(
                anchor_index(panel[a][0], asof) + longest >= len(panel[a][0]) for a in chosen
            ):
                continue
            if any(anchor_index(panel[a][0], asof) + 1 < min_history for a in chosen):
                continue
            units.append(
                PseudoUnit(
                    unit_id=f"pu-{panel_key}-{asof}-{shape}",
                    panel=str(panel_path),
                    asof=asof,
                    assets=chosen,
                    horizons=horizons,
                    target_type=target_type,
                    shape=shape,
                )
            )
    return units


def split(units: list[PseudoUnit], *, holdout_fraction: float = 0.3, embargo_days: int = 200):
    """Chronological dev / holdout split with an embargo.

    Iterating five times against the same pseudo-units and then quoting a p-value from them
    measures the iteration, not the model. Development uses the early period; the holdout is
    opened once, at the end. The embargo drops units whose forecast window would straddle the
    boundary, so no development target date sits inside the holdout period.
    """
    ordered = sorted(units, key=lambda u: (u.asof, u.unit_id))
    asofs = sorted({u.asof for u in ordered})
    cut = asofs[int(len(asofs) * (1.0 - holdout_fraction))]
    boundary = np.datetime64(cut, "D")
    dev, holdout = [], []
    for unit in ordered:
        when = np.datetime64(unit.asof, "D")
        if when < boundary - np.timedelta64(embargo_days, "D"):
            dev.append(unit)
        elif when >= boundary:
            holdout.append(unit)
    return dev, holdout, cut


def write(units: list[PseudoUnit], path: pathlib.Path) -> None:
    path.write_text(
        json.dumps([u.as_dict() for u in units], indent=1), encoding="utf-8"
    )


def read(path: pathlib.Path) -> list[PseudoUnit]:
    return [
        PseudoUnit(
            unit_id=r["unit_id"],
            panel=r["panel"],
            asof=r["asof"],
            assets=tuple(r["assets"]),
            horizons=tuple(r["horizons"]),
            target_type=r["target_type"],
            shape=r["shape"],
        )
        for r in json.loads(path.read_text(encoding="utf-8"))
    ]
