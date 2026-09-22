"""Stage B -- official scoring of our samples against M0, plus the significance test.

Runs inside the verifier image, which carries the pinned official scorer, so the composite
is computed by organizer code rather than a local re-derivation.

The normalization is per COMPONENT, not per composite (M0-BASELINE.md section 5 and
scoring._composite): the score is w_m*(our_marginal/M0_marginal) + w_j*(...) + w_t*(...).
Scoring M0 against itself therefore gives exactly 1.0, which is what makes 1.0 mean
"no better than a forecast that never read the text".
"""

from __future__ import annotations

import argparse
import csv
import math
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import units as unit_io  # noqa: E402
from harness import TAIL_LEVELS, load_panel, m0_samples, realized, weights_for  # noqa: E402

from qfbench2_track_forecasting.cli import _draw as reference_draw  # noqa: E402
from qfbench2_track_forecasting.scoring import _composite  # noqa: E402

SCORE_CLIP = (0.0, 4.0)  # aggregate.py -- every real score is clipped into [0.0, 4.0]


def reference_samples(unit, raw_panel, draws: int) -> np.ndarray:
    """The shipped official reference CLI at its default seed.

    M0-BASELINE.md section 7 measures this arm at mean 1.29 / median 1.05 against M0 over the
    released cards. It is the only external calibration available for a local M0
    reimplementation: if our M0 were too weak, this arm would land below 1.0 instead.
    """
    samples, _ = reference_draw(
        raw_panel, sorted(unit.assets), sorted(unit.horizons), unit.asof, draws, 0,
        target_type=unit.target_type, panel_steps=None,
    )
    return samples.reshape(draws, -1).astype(np.float64)


def score_arms(unit, panel, arms: dict[str, np.ndarray]) -> dict[str, dict[str, float]]:
    """Score every arm against the same M0 draws and the same realized outcome."""
    y = realized(unit, panel)
    m0 = m0_samples(unit, panel)
    weights = weights_for(unit.cell_count)
    common = dict(
        weights=weights, tail_levels=TAIL_LEVELS, joint="variogram", tail_metric="pinball"
    )
    base = _composite(m0, y, ref_scale=None, **common)
    # M0-BASELINE.md section 5: a component that comes out zero or negative is stored as 1.0,
    # i.e. that component is simply not normalized.
    ref = {
        k: (v if v > 0.0 else 1.0) for k, v in base.items() if k in ("marginal", "joint", "tail")
    }
    out = {}
    for name, samples in arms.items():
        got = _composite(samples, y, ref_scale=ref, **common)
        out[name] = {
            "score": float(np.clip(got["composite"], *SCORE_CLIP)),
            "raw_score": float(got["composite"]),
            "marginal_ratio": float(got["marginal"] / ref["marginal"]),
            "joint_ratio": float(got["joint"] / ref["joint"]),
            "tail_ratio": float(got["tail"] / ref["tail"]),
        }
    return out


def block_bootstrap_pvalue(
    by_date: dict[str, list[float]], *, block: int, draws: int = 20000, seed: int = 20260922
) -> tuple[float, float, float]:
    """One-sided p-value for H0: mean score >= 1.0, against H1: mean score < 1.0.

    Resampling moves contiguous BLOCKS OF AS-OF DATES and carries every unit at a date
    together. That is deliberate: overlapping forecast windows make neighbouring dates
    serially dependent, and units sharing a date are cross-sectionally dependent. A naive
    i.i.d. bootstrap over units would ignore both and report a p-value far too small.
    """
    dates = sorted(by_date)
    per_date = [np.asarray(by_date[d], dtype=float) for d in dates]
    n = len(dates)
    # A block at least as long as the sample makes every replicate identical and the
    # p-value meaningless, so cap it and say so rather than reporting a zero-width interval.
    block = max(1, min(block, n // 4))
    observed = float(np.mean(np.concatenate(per_date)))
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block))
    starts = rng.integers(0, max(n - block + 1, 1), size=(draws, n_blocks))
    replicates = np.empty(draws, dtype=float)
    offsets = np.arange(block)
    for b in range(draws):
        picked = (starts[b][:, None] + offsets[None, :]).ravel()[:n]
        picked = picked[picked < n]
        replicates[b] = float(np.mean(np.concatenate([per_date[i] for i in picked])))
    # Shift the replicate distribution to sit under H0 (mean 1.0) and ask how often it
    # reaches a value at least as favourable as what we observed.
    p = (1.0 + float(np.sum(replicates <= 2.0 * observed - 1.0))) / (draws + 1.0)
    lo, hi = np.quantile(replicates, [0.025, 0.975])
    return observed, p, float(hi - lo)


def newey_west_t(by_date: dict[str, list[float]], *, lag: int) -> float:
    """DM-style t statistic on the per-date mean score against 1.0, HAC-corrected."""
    dates = sorted(by_date)
    x = np.array([np.mean(by_date[d]) for d in dates], dtype=float) - 1.0
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    gamma0 = float(e @ e) / n
    total = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        gamma = float(e[k:] @ e[:-k]) / n
        total += 2.0 * (1.0 - k / (lag + 1.0)) * gamma
    if total <= 0:
        return float("nan")
    return float(x.mean() / math.sqrt(total / n))


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--units", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="dev")
    parser.add_argument("--block", type=int, default=8)
    parser.add_argument("--hac-lag", type=int, default=6)
    parser.add_argument("--boot-draws", type=int, default=20000)
    parser.add_argument("--calibrate", action="store_true",
                        help="also score the official reference CLI arm")
    args = parser.parse_args()

    catalogue = {u.unit_id: u for u in unit_io.read(pathlib.Path(args.units))}
    store = np.load(args.samples)
    panels: dict[str, dict] = {}
    raw_panels: dict[str, dict] = {}

    grouped: dict[str, dict[str, np.ndarray]] = {}
    for key in store.files:
        arm_name, _, unit_id = key.partition("||")
        if not unit_id:
            arm_name, unit_id = "ours", key
        grouped.setdefault(unit_id, {})[arm_name] = store[key]

    rows = []
    for unit_id, produced in grouped.items():
        unit = catalogue[unit_id]
        if unit.panel not in panels:
            panels[unit.panel] = load_panel(unit.panel)
        arms = dict(produced)
        if args.calibrate:
            if unit.panel not in raw_panels:
                raw_panels[unit.panel] = {
                    pathlib.Path(unit.panel).stem: pd.read_parquet(unit.panel)
                }
            try:
                arms["reference_cli"] = reference_samples(
                    unit, raw_panels[unit.panel], next(iter(produced.values())).shape[0]
                )
            except Exception as exc:
                print(f"  REF-SKIP {unit_id}: {type(exc).__name__}: {exc}")
        try:
            scored = score_arms(unit, panels[unit.panel], arms)
        except Exception as exc:
            print(f"  SKIP {unit_id}: {type(exc).__name__}: {exc}")
            continue
        for arm, result in scored.items():
            rows.append({"unit_id": unit_id, "asof": unit.asof, "shape": unit.shape,
                         "cells": unit.cell_count, "arm": arm, **result})

    out = pathlib.Path(args.out)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    arm_names = sorted({r["arm"] for r in rows})
    if len(arm_names) > 2:
        # A one-factor sweep: rank the arms and show the paired move against the baseline,
        # which is far more precise than each arm's own absolute confidence interval.
        base = {r["unit_id"]: r["score"] for r in rows if r["arm"] == "baseline"}
        print("")
        print(f"=== {args.label}: {len(arm_names)} arms, paired against 'baseline' ===")
        head = (f"  {'arm':14} {'mean':>8} {'vs base':>9} {'median':>8} {'<1.0':>7} "
                f"{'joint':>8} {'boot p':>9}")
        print(head)
        table = []
        for arm in arm_names:
            sub = [r for r in rows if r["arm"] == arm]
            s = np.array([r["score"] for r in sub], dtype=float)
            paired = np.array(
                [r["score"] - base[r["unit_id"]] for r in sub if r["unit_id"] in base]
            )
            multi = [r for r in sub if int(r["cells"]) > 1]
            joint = float(np.mean([r["joint_ratio"] for r in multi])) if multi else float("nan")
            per_date: dict[str, list[float]] = {}
            for r in sub:
                per_date.setdefault(r["asof"], []).append(r["score"])
            _, pval, _ = block_bootstrap_pvalue(per_date, block=args.block, draws=args.boot_draws)
            table.append((float(s.mean()), arm, float(np.median(s)),
                          float(np.mean(s < 1.0)) * 100, joint, float(paired.mean()), pval))
        for mean, arm, med, win, joint, delta, pval in sorted(table):
            mark = "  <-- baseline" if arm == "baseline" else ""
            print(f"  {arm:14} {mean:>8.4f} {delta:>+9.4f} {med:>8.4f} {win:>6.1f}% "
                  f"{joint:>8.4f} {pval:>9.5f}{mark}")
        print("")
        print("  per-shape mean score")
        shapes = sorted({r["shape"] for r in rows})
        print("  " + f"{'arm':12}" + "".join(f"{s:>12}" for s in shapes))
        for _, arm, *_rest in sorted(table):
            cells = []
            for shape in shapes:
                sub = [r["score"] for r in rows if r["arm"] == arm and r["shape"] == shape]
                cells.append(f"{np.mean(sub):>12.4f}")
            print(f"  {arm:12}" + "".join(cells))
        return 0

    for arm in sorted({r["arm"] for r in rows}, key=lambda a: a != "ours"):
        subset = [r for r in rows if r["arm"] == arm]
        scores = np.array([r["score"] for r in subset], dtype=float)
        by_date: dict[str, list[float]] = {}
        for r in subset:
            by_date.setdefault(r["asof"], []).append(r["score"])
        mean, p, width = block_bootstrap_pvalue(by_date, block=args.block, draws=args.boot_draws)
        t_stat = newey_west_t(by_date, lag=args.hac_lag)
        print("")
        print(f"=== {args.label} | arm={arm} | {len(subset)} units, {len(by_date)} as-of dates ===")
        print(f"mean score vs M0      : {mean:.4f}   (1.0 = text-blind baseline, lower is better)")
        print(f"median score          : {float(np.median(scores)):.4f}")
        print(f"units beating M0      : {float(np.mean(scores < 1.0)) * 100:.1f}%")
        print(f"block-bootstrap p     : {p:.5f}   (H0: mean >= 1.0, one-sided)")
        print(f"HAC t / implied p     : {t_stat:.3f} / {normal_cdf(t_stat):.5f}")
        print(f"bootstrap 95% width   : {width:.4f}")
        print("per shape:")
        print(f"  {'shape':12} {'n':>5} {'mean':>8} {'<1.0':>7} {'marg':>8} {'joint':>8} {'tail':>8}")
        for shape in sorted({r["shape"] for r in subset}):
            sub = [r for r in subset if r["shape"] == shape]
            s = np.array([r["score"] for r in sub])
            print(
                f"  {shape:12} {len(sub):>5} {s.mean():>8.4f} {np.mean(s < 1.0) * 100:>6.1f}% "
                f"{np.mean([r['marginal_ratio'] for r in sub]):>8.4f} "
                f"{np.mean([r['joint_ratio'] for r in sub]):>8.4f} "
                f"{np.mean([r['tail_ratio'] for r in sub]):>8.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
