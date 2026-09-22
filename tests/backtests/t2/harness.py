"""Rolling-origin backtest harness for T2.

Nothing here touches sealed material. A pseudo-unit is cut from a published panel this
repository already holds: the history is truncated at an as-of, and the "realized" value
of a cell is simply the later observation that the truncation hides from the forecaster.

`m0_samples` is a faithful reimplementation of the official text-blind baseline specified
in `upstream/track2-forecasting-public/docs/M0-BASELINE.md` section 3. M0 is the scoring
denominator: a composite ratio of 1.0 means "no better than a forecast that never read
the text", so beating M0 is what predictive power means on this track.

The module is imported by both the submission image (pandas 2.2) and the verifier image
(pandas 3.0), so it stays on numpy and avoids version-sensitive pandas APIs.
"""

from __future__ import annotations

import binascii
import dataclasses
import pathlib

import numpy as np
import pandas as pd

M0_DRAWS = 500
M0_WINDOW = 300  # M0-BASELINE.md 3.1 -- the trailing window is the whole of M0's memory
TAIL_LEVELS = (0.01, 0.05, 0.95, 0.99)
BASE_WEIGHTS = (0.5, 0.3, 0.2)
_ASSET_COLUMNS = ("asset", "asset_id")


@dataclasses.dataclass(frozen=True)
class PseudoUnit:
    unit_id: str
    panel: str
    asof: str
    assets: tuple[str, ...]
    horizons: tuple[int, ...]
    target_type: str = "level"
    shape: str = ""

    def cells(self) -> list[tuple[str, int]]:
        """Canonical cell order: sorted by asset id, then horizon ascending (M0 3.9)."""
        return [(a, h) for a in sorted(self.assets) for h in sorted(self.horizons)]

    @property
    def cell_count(self) -> int:
        return len(self.assets) * len(self.horizons)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def weights_for(cell_count: int) -> tuple[float, float, float]:
    """Single-cell renormalization (scoring.py, track-lead ruling 2026-08-24).

    On a one-cell grid the variogram is 0 by construction, so its weight is redistributed
    over the components that structurally exist: (0.5, 0.3, 0.2) -> (0.714286, 0, 0.285714).
    """
    w_m, w_j, w_t = BASE_WEIGHTS
    if cell_count == 1:
        live = w_m + w_t
        return (w_m / live, 0.0, w_t / live)
    return (w_m, w_j, w_t)


def load_panel(path: str | pathlib.Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """asset -> (dates[datetime64[D]] ascending and unique, values[float])."""
    frame = pd.read_parquet(path)
    column = next(name for name in _ASSET_COLUMNS if name in frame.columns)
    panel: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for asset, group in frame.groupby(column, sort=True):
        dates = pd.to_datetime(group["date"]).to_numpy().astype("datetime64[D]")
        values = np.asarray(group["value"], dtype=float)
        order = np.argsort(dates, kind="stable")
        dates, values = dates[order], values[order]
        keep = np.append(dates[1:] != dates[:-1], True)  # last wins on a duplicated date
        panel[str(asset)] = (dates[keep], values[keep])
    return panel


def anchor_index(dates: np.ndarray, asof: str) -> int:
    """Position of the last observation at or before the as-of (M0 3.6)."""
    return int(np.searchsorted(dates, np.datetime64(asof, "D"), side="right") - 1)


def _steps(dates: np.ndarray, values: np.ndarray, target_type: str) -> tuple[np.ndarray, np.ndarray]:
    """M0 3.2 + 3.3 -- steps carrying the date of the row they end on, holes set to NaN."""
    spacing = (dates[1:] - dates[:-1]).astype("timedelta64[D]").astype(float)
    if target_type == "log_return":
        # A per-step return at row i IS row i; row 0 has no preceding interval to test.
        step = values[1:].astype(float).copy()
    else:
        step = np.diff(values.astype(float))
    threshold = max(10.0 * float(np.median(spacing)), 5.0)
    step[spacing > threshold] = np.nan
    return dates[1:], step


def realized(unit: PseudoUnit, panel: dict[str, tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    """The outcome the truncation hid, in canonical cell order."""
    out = []
    for asset, horizon in unit.cells():
        dates, values = panel[asset]
        i = anchor_index(dates, unit.asof)
        if unit.target_type == "log_return":
            out.append(float(np.sum(values[i + 1 : i + 1 + horizon])))
        else:
            out.append(float(values[i + horizon]))
    return np.asarray(out, dtype=float)


def m0_samples(unit: PseudoUnit, panel: dict[str, tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    """The official text-blind joint Gaussian random walk (M0-BASELINE.md section 3)."""
    assets = sorted(unit.assets)
    window: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for asset in assets:
        dates, values = panel[asset]
        i = anchor_index(dates, unit.asof)
        window[asset] = (dates[: i + 1][-M0_WINDOW:], values[: i + 1][-M0_WINDOW:])

    # 3.4 -- the step frame is the intersection of dates present for every asset.
    by_asset: dict[str, dict[int, float]] = {}
    common: set[int] | None = None
    for asset in assets:
        dates, values = window[asset]
        step_dates, step = _steps(dates, values, unit.target_type)
        finite = np.isfinite(step)
        keys = step_dates[finite].astype("datetime64[D]").astype(np.int64)
        by_asset[asset] = dict(zip(keys.tolist(), step[finite].tolist()))
        common = set(by_asset[asset]) if common is None else common & set(by_asset[asset])
    if not common:
        raise ValueError(f"{unit.unit_id}: no date-aligned steps across assets")
    index = sorted(common)
    frame = np.column_stack([[by_asset[a][k] for k in index] for a in assets])

    mu = frame.mean(axis=0)  # 3.5 -- no shrinkage, no winsorizing; M0 is the floor
    sigma = np.atleast_2d(np.cov(frame, rowvar=False))

    if unit.target_type == "log_return":
        anchor = {a: 0.0 for a in assets}
    else:
        anchor = {a: float(window[a][1][-1]) for a in assets}

    cells = unit.cells()
    position = {a: k for k, a in enumerate(assets)}
    mean = np.array([anchor[a] + h * mu[position[a]] for a, h in cells], dtype=float)
    size = len(cells)
    cov = np.empty((size, size), dtype=float)
    for p, (asset_p, horizon_p) in enumerate(cells):
        for q, (asset_q, horizon_q) in enumerate(cells):
            # 3.8 -- min(s_i, s_j) is what makes the draws a path rather than a bundle.
            cov[p, q] = min(horizon_p, horizon_q) * sigma[position[asset_p], position[asset_q]]
    cov[np.diag_indices(size)] += 1e-10
    jittered = cov + 1e-9 * np.eye(size)
    try:
        factor = np.linalg.cholesky(jittered)
    except np.linalg.LinAlgError:
        factor = np.linalg.cholesky(np.diag(np.diag(jittered)))

    seed = binascii.crc32(unit.unit_id.encode()) & 0x7FFFFFFF  # 3.9
    draws = np.random.default_rng(seed).standard_normal((M0_DRAWS, size))
    return mean + draws @ factor.T


def unit_seed(unit: PseudoUnit) -> int:
    return binascii.crc32(unit.unit_id.encode()) & 0x7FFFFFFF
