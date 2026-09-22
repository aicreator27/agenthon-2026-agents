"""Official Track 2 `forecast` command for the runnable numeric-only MVP."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tomllib
from typing import Any

import numpy as np
import pandas as pd

from agenthon_core.reproducibility import configured_seed, unit_seed

from .forecaster import monthly_steps, read_panels, simulate_joint
from .limits import OutputLimits

DEFAULT_DRAWS = 1000
RATIONALE_NAME = "forecast_rationale.md"


def _find_card(panels: pathlib.Path, explicit: pathlib.Path | None) -> pathlib.Path:
    candidates = [explicit] if explicit is not None else [
        panels / "card.toml",
        panels.parent / "card.toml",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise ValueError(f"card.toml not found beside {panels}")


def _draw_count(requested: int | None, card: dict[str, Any]) -> int:
    card_floor = int(card.get("scoring", {}).get("params", {}).get("n_draws_min", 0) or 0)
    environment_default = int(os.getenv("T2_N_DRAWS", str(DEFAULT_DRAWS)))
    value = max(requested or environment_default, card_floor, OutputLimits().min_draws)
    if value > OutputLimits().max_draws:
        raise ValueError(f"n_draws {value} exceeds {OutputLimits().max_draws}")
    return value


def _write_forecast(
    path: pathlib.Path, samples: np.ndarray, assets: list[str], horizons: list[int]
) -> None:
    n_draws = samples.shape[0]
    cells = len(assets) * len(horizons)
    frame = pd.DataFrame(
        {
            "draw": np.repeat(np.arange(n_draws, dtype=np.int32), cells),
            "asset": np.tile(np.repeat(np.asarray(assets, dtype=object), len(horizons)), n_draws),
            "horizon": np.tile(
                np.tile(np.asarray(horizons, dtype=np.int32), len(assets)), n_draws
            ),
            "value": samples.reshape(-1).astype(np.float64),
        }
    )
    frame.to_parquet(path, index=False)


def _rationale(
    *,
    unit_id: str,
    asof: str,
    assets: list[str],
    horizons: list[int],
    n_draws: int,
    stats: dict[str, Any],
    text_dir: pathlib.Path,
) -> str:
    documents = sum(1 for path in text_dir.rglob("*") if path.is_file()) if text_dir.is_dir() else 0
    anchors = "\n".join(
        f"| {asset} | {stats['anchors'][asset]:.8g} | {stats['step_sd'][asset]:.8g} |"
        for asset in assets
    )
    return f"""# Forecast rationale — {unit_id}

## Executive summary

This numeric-only admissible baseline produced {n_draws} joint draws as of {asof} for
{len(assets)} asset(s) and horizon key(s) {horizons}. It uses one simulated path per draw,
so assets and longer horizons retain dependence.

## Numeric construction

Method: {stats['method']}.

- Step unit: {stats['step_unit']}
- Historical rows inspected: {stats['history_rows']}
- Complete joint rows: {stats['complete_history_rows']}
- Block-bootstrap mixture weight: {stats['bootstrap_weight']:.2f}
- Shrinkage Student-t mixture weight: {stats['student_t_weight']:.2f}
- Block length: {stats['block_length']}
- Target type: {stats['target_type']}

| asset | anchor | calibrated step sd |
|---|---:|---:|
{anchors}

## Text contribution

The corpus contained {documents} file(s). This v0.1 submission intentionally made no text
adjustment. It is the stable numeric reference that later House-conditioned mean, volatility,
correlation and tail knobs must beat in rolling-origin tests.

## Adjustment ledger

Text mean shift: 0. Text volatility multiplier: 1. Correlation adjustment: 0.
Tail scenario adjustment: 0. Future versions must list every non-zero adjustment here.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forecast")
    parser.add_argument("--panels", required=True, type=pathlib.Path)
    parser.add_argument("--text", required=True, type=pathlib.Path)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--card", type=pathlib.Path, default=None)
    parser.add_argument("--n-draws", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        card_path = _find_card(arguments.panels, arguments.card)
        card = tomllib.loads(card_path.read_text(encoding="utf-8"))
        targets = card["targets"]
        assets = [str(asset) for asset in targets["asset_ids"]]
        horizons = [int(horizon) for horizon in targets["horizons"]]
        unit_id = str(card["task"]["id"])
        n_draws = _draw_count(arguments.n_draws, card)
        seed = unit_seed(configured_seed(arguments.seed), unit_id)

        panels = read_panels(arguments.panels)
        steps = monthly_steps(panels, card, card_path, arguments.asof)
        result = simulate_joint(
            panels,
            assets,
            horizons,
            arguments.asof,
            n_draws,
            seed,
            target_type=str(targets.get("target_type", "level")),
            panel_steps=steps,
        )

        output_dir = arguments.out.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_forecast(arguments.out, result.samples, assets, horizons)
        metadata = {
            "unit_id": unit_id,
            "asof": arguments.asof,
            "representation": "samples",
            "asset_ids": assets,
            "horizons": horizons,
            "n_draws": n_draws,
            "target": targets.get("target_type", "level"),
            "rationale": {
                "file": RATIONALE_NAME,
                "method": result.stats["method"] + "; text-disabled-v0.2-calibrated",
            },
        }
        (output_dir / "forecast_meta.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        (output_dir / RATIONALE_NAME).write_text(
            _rationale(
                unit_id=unit_id,
                asof=arguments.asof,
                assets=assets,
                horizons=horizons,
                n_draws=n_draws,
                stats=result.stats,
                text_dir=arguments.text,
            ),
            encoding="utf-8",
        )
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"forecast failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"wrote {arguments.out.name}, forecast_meta.json and {RATIONALE_NAME}: "
        f"{len(assets)} asset(s) x {len(horizons)} horizon(s) x {n_draws} draws"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

