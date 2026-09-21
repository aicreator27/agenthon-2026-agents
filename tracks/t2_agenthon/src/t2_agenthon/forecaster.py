"""Cutoff-safe numeric ensemble that emits joint multi-horizon sample paths."""

from __future__ import annotations

import json
import pathlib
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .horizons import HorizonMetadataError, monthly_horizon_steps
from .targets import log_return_steps


@dataclass(frozen=True, slots=True)
class ForecastResult:
    samples: np.ndarray
    stats: dict[str, Any]


_ASSET_COLUMNS = ("asset", "asset_id")


def read_panels(panels_dir: pathlib.Path) -> dict[str, pd.DataFrame]:
    found = sorted(panels_dir.glob("*.parquet"))
    if not found and panels_dir.parent.is_dir():
        found = sorted(panels_dir.parent.glob("*.parquet"))
    if not found:
        raise ValueError(f"no .parquet found under {panels_dir} or its parent")
    return {path.stem: pd.read_parquet(path) for path in found}


def _asset_column(frame: pd.DataFrame) -> str | None:
    return next((name for name in _ASSET_COLUMNS if name in frame.columns), None)


def asset_series(panels: dict[str, pd.DataFrame], asset: str, asof: str) -> pd.Series:
    for frame in panels.values():
        column = _asset_column(frame)
        if column is None or "date" not in frame or "value" not in frame:
            continue
        selected = frame[frame[column].astype(str) == asset].copy()
        if selected.empty:
            continue
        selected["date"] = selected["date"].astype(str).str.slice(0, 10)
        selected = selected[selected["date"] <= asof].sort_values("date")
        if not selected.empty:
            values = selected.set_index("date")["value"].astype(float)
            return values[~values.index.duplicated(keep="last")]
    raise ValueError(f"asset {asset!r} is absent at or before {asof}")


def _diff_without_gaps(series: pd.Series) -> pd.Series:
    differences = series.diff()
    dates = pd.to_datetime(pd.Series(series.index, index=series.index), errors="coerce")
    spacing = dates.diff().dt.days
    if spacing.notna().sum() == 0:
        return differences
    threshold = max(float(spacing.median()) * 10.0, 5.0)
    return differences.where(spacing <= threshold)


def _monthly_series(series: pd.Series) -> pd.Series:
    monthly = series.copy()
    monthly.index = pd.to_datetime(monthly.index).to_period("M")
    if monthly.index.has_duplicates or len(monthly) < 3:
        raise HorizonMetadataError("monthly targets require unique monthly observations")
    if not np.isfinite(monthly.to_numpy()).all():
        raise HorizonMetadataError("monthly target history contains non-finite values")
    if np.median(np.diff(monthly.index.asi8)) != 1:
        raise HorizonMetadataError("selected target history does not have monthly cadence")
    return monthly


def _daily_cadence(series: pd.Series) -> bool:
    dates = pd.DatetimeIndex(pd.to_datetime(series.index))
    if len(dates) < 30 or dates.has_duplicates:
        return False
    gaps = np.diff(dates.to_numpy()).astype("timedelta64[D]").astype(float)
    per_month = pd.Series(1, index=dates.to_period("M")).groupby(level=0).sum()
    return bool(0 < np.median(gaps) <= 3 and per_month.median() >= 8)


def _explicit_monthly_periods(source: dict[str, Any]) -> bool:
    targets = source.get("targets", {})
    questions = source.get("questions", [])
    return (isinstance(targets, dict) and "observation_periods" in targets) or (
        isinstance(questions, list)
        and any(isinstance(row, dict) and "observation_period" in row for row in questions)
    )


def monthly_steps(
    panels: dict[str, pd.DataFrame],
    card: dict[str, Any],
    card_path: pathlib.Path,
    asof: str,
) -> np.ndarray | None:
    targets = card["targets"]
    frequency = targets.get("target_frequency", card.get("metadata", {}).get("target_frequency"))
    if frequency != "monthly":
        return None
    histories = {asset: asset_series(panels, asset, asof) for asset in targets["asset_ids"]}
    spec_path = card_path.parent / "forecast_spec.json"
    spec: dict[str, Any] | None = None
    if spec_path.exists():
        loaded = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise HorizonMetadataError("forecast_spec.json must contain an object")
        spec = loaded
    if all(_daily_cadence(history) for history in histories.values()):
        if _explicit_monthly_periods(card) or _explicit_monthly_periods(spec or {}):
            raise HorizonMetadataError("monthly metadata conflicts with daily observations")
        warnings.warn("monthly declaration has daily observations; using daily steps", stacklevel=2)
        return None
    if targets.get("target_type", "level") != "level":
        raise HorizonMetadataError("monthly sampler supports level targets only")
    last = {}
    for asset, history in histories.items():
        _monthly_series(history)
        last[asset] = str(history.index[-1])[:10]
    return monthly_horizon_steps(
        targets["asset_ids"],
        targets["horizons"],
        last,
        asof=asof,
        card=card,
        forecast_spec=spec,
    )


def _nearest_psd(matrix: np.ndarray) -> np.ndarray:
    symmetric = (matrix + matrix.T) / 2.0
    values, vectors = np.linalg.eigh(symmetric)
    floor = max(float(np.max(values)) * 1e-10, 1e-12)
    return vectors @ np.diag(np.clip(values, floor, None)) @ vectors.T


def _step_frame(
    histories: dict[str, pd.Series], *, target_type: str, monthly: bool
) -> tuple[pd.DataFrame, np.ndarray]:
    columns: dict[str, pd.Series] = {}
    for asset, history in histories.items():
        if target_type == "log_return":
            columns[asset] = pd.Series(log_return_steps(history), index=history.index)
        elif monthly:
            diff = history.diff()
            diff = diff.where(np.r_[False, np.diff(history.index.asi8) == 1])
            columns[asset] = diff
        else:
            columns[asset] = _diff_without_gaps(history)
    frame = pd.DataFrame(columns).replace([np.inf, -np.inf], np.nan)
    drift = (
        frame.mean(skipna=True).fillna(0.0).to_numpy(dtype=float)
        if target_type == "log_return"
        else np.zeros(len(histories), dtype=float)
    )
    return frame, drift


def _covariance(frame: pd.DataFrame, drift: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    residual = frame - drift
    full_std = residual.std(skipna=True).fillna(0.0).to_numpy(dtype=float)
    positive = full_std[full_std > 0]
    fallback = float(np.median(positive)) if positive.size else 1e-4
    full_std = np.where(full_std > 0, full_std, fallback)
    diagonal = np.diag(full_std**2)
    full_cov = residual.cov(min_periods=5).to_numpy(dtype=float)
    recent_cov = residual.tail(min(252, len(residual))).cov(min_periods=5).to_numpy(dtype=float)
    full_cov = np.where(np.isfinite(full_cov), full_cov, diagonal)
    recent_cov = np.where(np.isfinite(recent_cov), recent_cov, full_cov)
    blended = 0.55 * recent_cov + 0.45 * full_cov
    shrunk = 0.85 * blended + 0.15 * np.diag(np.diag(blended))
    covariance = _nearest_psd(shrunk)
    return covariance, np.sqrt(np.maximum(np.diag(covariance), 1e-12))


def _bootstrap_paths(
    rng: np.random.Generator,
    residual: np.ndarray,
    n_draws: int,
    n_steps: int,
    target_std: np.ndarray,
    block_length: int,
) -> np.ndarray:
    n_rows, n_assets = residual.shape
    pool_std = np.std(residual, axis=0, ddof=1)
    scale = target_std / np.where(pool_std > 0, pool_std, 1.0)
    output = np.empty((n_draws, n_steps, n_assets), dtype=float)
    for draw in range(n_draws):
        position = 0
        while position < n_steps:
            start = int(rng.integers(0, n_rows))
            length = min(block_length, n_steps - position)
            indices = (start + np.arange(length)) % n_rows
            output[draw, position : position + length] = residual[indices] * scale
            position += length
    return output


def _student_paths(
    rng: np.random.Generator,
    covariance: np.ndarray,
    n_draws: int,
    n_steps: int,
    *,
    degrees_freedom: float = 6.0,
) -> np.ndarray:
    scale = covariance * ((degrees_freedom - 2.0) / degrees_freedom)
    chol = np.linalg.cholesky(_nearest_psd(scale))
    normals = rng.standard_normal((n_draws, n_steps, covariance.shape[0])) @ chol.T
    denominator = np.sqrt(
        rng.chisquare(degrees_freedom, size=(n_draws, n_steps, 1)) / degrees_freedom
    )
    return normals / denominator


def simulate_joint(
    panels: dict[str, pd.DataFrame],
    assets: list[str],
    horizons: list[int],
    asof: str,
    n_draws: int,
    seed: int,
    *,
    target_type: str,
    panel_steps: np.ndarray | None,
    bootstrap_weight: float = 0.65,
    block_length: int = 5,
) -> ForecastResult:
    rng = np.random.default_rng(seed)
    histories = {asset: asset_series(panels, asset, asof) for asset in assets}
    monthly = panel_steps is not None
    if monthly:
        histories = {asset: _monthly_series(history) for asset, history in histories.items()}
    step_frame, drift = _step_frame(histories, target_type=target_type, monthly=monthly)
    covariance, target_std = _covariance(step_frame, drift)
    residual_frame = step_frame - drift
    complete = residual_frame.dropna()
    if len(complete) >= max(block_length * 2, 10):
        pool = complete.to_numpy(dtype=float)
    else:
        pool = residual_frame.fillna(0.0).to_numpy(dtype=float)
        pool = pool[np.any(np.isfinite(pool) & (pool != 0), axis=1)]
    if len(pool) < 2:
        pool = np.vstack([np.zeros(len(assets)), target_std])

    if monthly:
        steps = np.asarray(panel_steps, dtype=int)
        if steps.shape != (len(assets), len(horizons)) or np.any(steps <= 0):
            raise HorizonMetadataError("invalid monthly step grid")
        n_steps = int(steps.max())
    else:
        if any(horizon <= 0 for horizon in horizons):
            raise ValueError("horizons must be positive")
        steps = None
        n_steps = max(horizons)

    use_bootstrap = rng.random(n_draws) < bootstrap_weight
    increments = np.empty((n_draws, n_steps, len(assets)), dtype=float)
    boot_count = int(use_bootstrap.sum())
    if boot_count:
        increments[use_bootstrap] = _bootstrap_paths(
            rng, pool, boot_count, n_steps, target_std, block_length
        )
    t_count = n_draws - boot_count
    if t_count:
        increments[~use_bootstrap] = _student_paths(rng, covariance, t_count, n_steps)
    increments += drift[None, None, :]
    cumulative = increments.cumsum(axis=1)
    anchor = (
        np.zeros(len(assets), dtype=float)
        if target_type == "log_return"
        else np.array([histories[asset].iloc[-1] for asset in assets], dtype=float)
    )
    output = np.empty((n_draws, len(assets), len(horizons)), dtype=float)
    for asset_index in range(len(assets)):
        for horizon_index, horizon in enumerate(horizons):
            endpoint = int(steps[asset_index, horizon_index] if steps is not None else horizon)
            output[:, asset_index, horizon_index] = (
                anchor[asset_index] + cumulative[:, endpoint - 1, asset_index]
            )
    if not np.isfinite(output).all():
        raise ValueError("numeric ensemble produced non-finite output")
    return ForecastResult(
        samples=output,
        stats={
            "method": "joint block bootstrap + shrinkage Student-t path ensemble",
            "bootstrap_weight": bootstrap_weight,
            "student_t_weight": 1.0 - bootstrap_weight,
            "block_length": block_length,
            "history_rows": int(len(step_frame)),
            "complete_history_rows": int(len(complete)),
            "target_type": target_type,
            "step_unit": "month" if monthly else "business_day",
            "anchors": {asset: float(anchor[i]) for i, asset in enumerate(assets)},
            "step_sd": {asset: float(target_std[i]) for i, asset in enumerate(assets)},
        },
    )

