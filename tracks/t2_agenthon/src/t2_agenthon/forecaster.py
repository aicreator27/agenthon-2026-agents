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
class EnsembleConfig:
    """Tunable knobs of the numeric ensemble.

    The defaults are the v0.3 calibration: they scored 0.8249 against the official M0
    text-blind baseline on a locked holdout of 1,168 rolling-origin pseudo-units
    (block-bootstrap p < 0.00005, HAC t = -13.4), where the v0.1 defaults scored 0.9540 at
    p = 0.054. The evidence and the rejected alternatives are in ADR-0004; the harness that
    produced them is `tests/backtests/t2/`.
    """

    history_window: int | None = 300  # calibrated: regime-appropriate dispersion (ADR-0004)
    recent_window: int = 252
    recent_weight: float = 0.55
    full_weight: float = 0.45
    blend_weight: float = 0.85
    diagonal_shrinkage: float = 0.15
    vol_halflife: float | None = None  # None -> scale from the blended covariance alone
    dispersion_scale: float = 1.0  # global multiplier on simulated spread
    drift_shrink: float = 0.0  # fraction of the trailing mean step applied to level targets
    variance_ratio: bool = False  # match terminal dispersion to the empirical h-step spread
    variance_ratio_window: int | None = None  # None -> the full history at or before the as-of
    variance_ratio_shrink: float = 1.0  # 0 -> keep sqrt(h); 1 -> the raw empirical ratio
    variance_ratio_floor: float = 0.5
    variance_ratio_cap: float = 2.0
    bootstrap_weight: float = 0.80
    block_length: int = 31
    block_length_days: float | None = None  # express the block as a duration, not a row count
    block_min: int = 1  # floor in rows; binds only on panels too coarse to carry the duration
    return_drift_shrink: float = 1.0  # fraction of the trailing mean return kept on log_return
    drift_evidence_c: float | None = 25.0  # evidence-weighted drift (ADR-0007)
    degrees_freedom: float = 6.0


DEFAULT_CONFIG = EnsembleConfig()


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


def _median_spacing_days(history: pd.Series) -> float:
    """Calendar days between observations, so a block can be stated as a duration.

    Volatility clustering and macro persistence live on calendar timescales, but a block
    length counted in rows means something completely different on a daily panel than on a
    monthly one: 31 rows is six weeks of dailies and 2.6 years of monthlies. One submission
    ships one config, so the conversion has to happen at run time from the panel itself.
    """
    try:
        stamps = pd.to_datetime(pd.Series([str(value) for value in history.index]), errors="coerce")
    except Exception:  # pragma: no cover - an index we cannot date is treated as daily
        return 1.0
    gaps = stamps.diff().dt.days.dropna()
    gaps = gaps[gaps > 0]
    return float(gaps.median()) if len(gaps) else 1.0


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


def _variance_ratios(
    history: pd.Series, horizons: list[int], target_type: str, config: EnsembleConfig
) -> dict[int, float]:
    """Empirical Var(h-step) / (h * Var(1-step)), estimated on LONG history.

    A cumulated random walk implies a terminal spread of sigma_1 * sqrt(h); real yield and FX
    series do not obey that at one to six months. The level of volatility is a regime property
    and is taken from the short recent window, but this ratio is a structural one, so it is
    estimated over as much history as exists. That split matters: on a 300-observation window,
    overlapping 126-step changes leave roughly 1.4 effective observations, which is noise.
    """
    series = history if config.variance_ratio_window is None else history.iloc[
        -config.variance_ratio_window :
    ]
    values = np.asarray(series, dtype=float)
    cumulative = np.cumsum(values) if target_type == "log_return" else values
    single = np.diff(cumulative)
    single = single[np.isfinite(single)]
    ratios: dict[int, float] = {}
    if single.size < 30:
        return {h: 1.0 for h in horizons}
    base = float(np.var(single, ddof=1))
    for horizon in sorted(set(horizons)):
        if base <= 0 or cumulative.size <= horizon + 10:
            ratios[horizon] = 1.0
            continue
        spread = cumulative[horizon:] - cumulative[:-horizon]
        spread = spread[np.isfinite(spread)]
        # Overlapping windows: usable for a ratio, but the effective sample is n/h, so the
        # estimate is shrunk toward 1.0 and bounded rather than trusted outright.
        if spread.size < max(3 * horizon, 30):
            ratios[horizon] = 1.0
            continue
        raw = float(np.var(spread, ddof=1)) / (horizon * base)
        pulled = 1.0 + config.variance_ratio_shrink * (raw - 1.0)
        ratios[horizon] = float(
            np.clip(pulled, config.variance_ratio_floor, config.variance_ratio_cap)
        )
    return ratios


def _nearest_psd(matrix: np.ndarray) -> np.ndarray:
    symmetric = (matrix + matrix.T) / 2.0
    values, vectors = np.linalg.eigh(symmetric)
    floor = max(float(np.max(values)) * 1e-10, 1e-12)
    return vectors @ np.diag(np.clip(values, floor, None)) @ vectors.T


def _step_frame(
    histories: dict[str, pd.Series],
    *,
    target_type: str,
    monthly: bool,
    config: EnsembleConfig,
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
    if config.drift_evidence_c is not None:
        # Evidence-weighted drift, applied to both target types by one rule.
        #
        # Forcing zero drift on level targets is what put our marginal ahead of M0 on daily
        # panels, where the trailing mean step carries a t of about 0.3 and is therefore noise.
        # The same rule is wrong on a monthly price index: CPI_CORE's mean step has a t above
        # 20, and suppressing it is a location error that grows with the horizon -- which is
        # exactly the pattern in the monthly diagnostics (marginal fine at h=2, bad at h=9).
        #
        # So the drift is shrunk by how much evidence there is for it rather than by a constant:
        # w = t^2 / (t^2 + c). Daily financial panels land near 0 and keep the calibrated
        # behaviour; a trending macro series lands near 1 and keeps its trend.
        mean_step = frame.mean(skipna=True)
        counts = frame.count().clip(lower=1)
        spread = frame.std(skipna=True)
        error = (spread / np.sqrt(counts)).replace(0.0, np.nan)
        tstat = (mean_step / error).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        weight = (tstat**2) / (tstat**2 + config.drift_evidence_c)
        drift = (weight * mean_step.fillna(0.0)).fillna(0.0).to_numpy(dtype=float)
    elif target_type == "log_return":
        # The same argument that made a driftless level target beat M0: the trailing mean is
        # mostly estimation noise at these horizons. On log_return we currently copy M0's full
        # mean, which is why we sit at parity there rather than ahead of it.
        drift = config.return_drift_shrink * frame.mean(skipna=True).fillna(0.0).to_numpy(
            dtype=float
        )
    else:
        # M0 applies the full trailing mean step to a level target and we apply none, which is
        # most of why our marginal already beats it: an estimated drift is mostly noise at these
        # horizons. `drift_shrink` scans the space between the two rather than assuming either
        # end is right.
        drift = config.drift_shrink * frame.mean(skipna=True).fillna(0.0).to_numpy(dtype=float)
    return frame, drift


def _covariance(
    frame: pd.DataFrame, drift: np.ndarray, config: EnsembleConfig
) -> tuple[np.ndarray, np.ndarray]:
    residual = frame - drift
    full_std = residual.std(skipna=True).fillna(0.0).to_numpy(dtype=float)
    positive = full_std[full_std > 0]
    fallback = float(np.median(positive)) if positive.size else 1e-4
    full_std = np.where(full_std > 0, full_std, fallback)
    diagonal = np.diag(full_std**2)
    full_cov = residual.cov(min_periods=5).to_numpy(dtype=float)
    recent_cov = (
        residual.tail(min(config.recent_window, len(residual)))
        .cov(min_periods=5)
        .to_numpy(dtype=float)
    )
    full_cov = np.where(np.isfinite(full_cov), full_cov, diagonal)
    recent_cov = np.where(np.isfinite(recent_cov), recent_cov, full_cov)
    # The two weights of each pair are stored explicitly rather than derived as 1 - w:
    # 1.0 - 0.55 is not bit-identical to 0.45, and the v0.1 evidence is hash-exact.
    blended = config.recent_weight * recent_cov + config.full_weight * full_cov
    shrunk = config.blend_weight * blended + config.diagonal_shrinkage * np.diag(np.diag(blended))
    if config.vol_halflife:
        # A trailing window weights a step from 300 days ago exactly like yesterday's. The
        # variogram is a squared penalty on predicted dispersion, so a stale scale is punished
        # quadratically there while the marginal CRPS barely notices. An exponentially weighted
        # scale tracks the current regime without discarding the correlation structure.
        decay = 0.5 ** (1.0 / float(config.vol_halflife))
        squared = residual.to_numpy(dtype=float) ** 2
        weight = decay ** np.arange(len(squared) - 1, -1, -1.0)
        mask = np.isfinite(squared)
        weighted = np.where(mask, squared, 0.0) * weight[:, None]
        mass = np.where(mask, 1.0, 0.0) * weight[:, None]
        totals = mass.sum(axis=0)
        ew_std = np.sqrt(np.divide(weighted.sum(axis=0), np.where(totals > 0, totals, 1.0)))
        ew_std = np.where(ew_std > 0, ew_std, np.sqrt(np.maximum(np.diag(shrunk), 1e-12)))
        current = np.sqrt(np.maximum(np.diag(shrunk), 1e-12))
        rescale = ew_std / current
        shrunk = shrunk * np.outer(rescale, rescale)
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
    config: EnsembleConfig = DEFAULT_CONFIG,
) -> ForecastResult:
    bootstrap_weight = config.bootstrap_weight
    block_length = config.block_length
    rng = np.random.default_rng(seed)
    histories = {asset: asset_series(panels, asset, asof) for asset in assets}
    full_histories = histories
    if config.history_window is not None:
        histories = {a: h.iloc[-config.history_window :] for a, h in histories.items()}
    monthly = panel_steps is not None
    if monthly:
        histories = {asset: _monthly_series(history) for asset, history in histories.items()}
    if config.block_length_days:
        spacing = float(
            np.median([_median_spacing_days(history) for history in histories.values()])
        )
        # Daily panels have a median spacing of exactly 1 day, so a 31-day duration reproduces
        # the calibrated 31-row block unchanged. A monthly panel maps to 1 row, which is where
        # the floor does its work: it is the only knob that moves coarse panels without
        # touching the daily calibration at all.
        block_length = int(
            max(config.block_min, round(config.block_length_days / max(spacing, 1e-9)))
        )
    step_frame, drift = _step_frame(
        histories, target_type=target_type, monthly=monthly, config=config
    )
    covariance, target_std = _covariance(step_frame, drift, config)
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
        increments[~use_bootstrap] = _student_paths(
            rng, covariance, t_count, n_steps, degrees_freedom=config.degrees_freedom
        )
    if config.dispersion_scale != 1.0:
        # CRPS is a proper scoring rule, so it is minimized at correct calibration; a scan over
        # a single multiplier is the direct test of whether our spread is systematically off.
        increments *= config.dispersion_scale
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
    ratios_used: dict[str, dict[int, float]] = {}
    if config.variance_ratio and not monthly:
        # Terminal dispersion is set explicitly to sigma_1 * sqrt(h * VR) rather than left to
        # whatever serial correlation the block bootstrap happened to inherit from a short
        # window. Only the spread of each cell moves; its centre and every correlation with
        # other cells are untouched, so the joint structure is preserved.
        for asset_index, asset in enumerate(assets):
            ratios = _variance_ratios(full_histories[asset], horizons, target_type, config)
            ratios_used[asset] = ratios
            for horizon_index, horizon in enumerate(horizons):
                column = output[:, asset_index, horizon_index]
                current = float(column.std(ddof=1))
                if not np.isfinite(current) or current <= 0.0:
                    continue
                wanted = float(target_std[asset_index]) * np.sqrt(horizon * ratios[horizon])
                if not np.isfinite(wanted) or wanted <= 0.0:
                    continue
                centre = float(column.mean())
                output[:, asset_index, horizon_index] = centre + (column - centre) * (
                    wanted / current
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
            "history_window": config.history_window,
            "degrees_freedom": config.degrees_freedom,
            "vol_halflife": config.vol_halflife,
            "dispersion_scale": config.dispersion_scale,
            "drift_shrink": config.drift_shrink,
            "return_drift_shrink": config.return_drift_shrink,
            "drift_evidence_c": config.drift_evidence_c,
            "block_length_days": config.block_length_days,
            "effective_block_length": block_length,
            "variance_ratio": config.variance_ratio,
            "variance_ratios": {a: dict(r) for a, r in ratios_used.items()},
            "history_rows": int(len(step_frame)),
            "complete_history_rows": int(len(complete)),
            "target_type": target_type,
            "step_unit": "month" if monthly else "business_day",
            "anchors": {asset: float(anchor[i]) for i, asset in enumerate(assets)},
            "step_sd": {asset: float(target_std[i]) for i, asset in enumerate(assets)},
        },
    )

