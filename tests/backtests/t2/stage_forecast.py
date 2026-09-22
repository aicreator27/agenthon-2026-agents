"""Stage A -- produce our forecaster's samples for every pseudo-unit.

Runs inside the submission image so the model is exercised on exactly the pinned stack it
ships with (numpy 2.1.3 / pandas 2.2.3), not on the verifier's newer one.

`--configs` names one or more EnsembleConfig variants; each becomes a scoring arm, and every
arm sees the same units, the same seeds and the same M0 draws, so the comparison is paired.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import units as unit_io  # noqa: E402
from harness import unit_seed  # noqa: E402

from t2_agenthon.forecaster import EnsembleConfig, simulate_joint  # noqa: E402

_CACHE: dict[str, dict[str, pd.DataFrame]] = {}


def panels_for(path: str) -> dict[str, pd.DataFrame]:
    if path not in _CACHE:
        _CACHE[path] = {pathlib.Path(path).stem: pd.read_parquet(path)}
    return _CACHE[path]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--units", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument(
        "--configs",
        help='JSON file mapping arm name -> EnsembleConfig overrides; default {"ours": {}}',
    )
    args = parser.parse_args()

    spec = (
        json.loads(pathlib.Path(args.configs).read_text(encoding="utf-8"))
        if args.configs
        else {"ours": {}}
    )
    # "draws" is not an EnsembleConfig field: it is pulled out so an arm can be run at a
    # matched draw count. CRPS is downward-biased in the number of samples, so an arm drawing
    # more than M0's 500 gains a little for free; the control arm isolates that from skill.
    arms: dict[str, tuple[EnsembleConfig, int]] = {}
    for name, overrides in spec.items():
        overrides = dict(overrides)
        draws = int(overrides.pop("draws", args.draws))
        arms[name] = (EnsembleConfig(**overrides), draws)

    catalogue = unit_io.read(pathlib.Path(args.units))
    store: dict[str, np.ndarray] = {}
    failures: list[str] = []
    started = time.time()
    for index, unit in enumerate(catalogue, 1):
        assets, horizons = sorted(unit.assets), sorted(unit.horizons)
        for name, (config, draws) in arms.items():
            try:
                result = simulate_joint(
                    panels_for(unit.panel),
                    assets,
                    horizons,
                    unit.asof,
                    draws,
                    unit_seed(unit),
                    target_type=unit.target_type,
                    panel_steps=None,
                    config=config,
                )
            except Exception as exc:  # an arm that cannot serve a unit is a result, not a crash
                failures.append(f"{name}||{unit.unit_id}  {type(exc).__name__}: {exc}")
                continue
            store[f"{name}||{unit.unit_id}"] = result.samples.reshape(
                draws, -1
            ).astype(np.float64)
        if index % 250 == 0:
            print(f"  {index}/{len(catalogue)}  {time.time() - started:.0f}s", flush=True)

    np.savez_compressed(args.out, **store)
    print(
        f"FORECAST_OK arms={len(arms)} units={len(catalogue)} "
        f"series={len(store)} failed={len(failures)} secs={time.time() - started:.0f}"
    )
    if failures:
        pathlib.Path(args.out).with_suffix(".failures.txt").write_text(
            "\n".join(failures), encoding="utf-8"
        )
        for line in failures[:5]:
            print("  FAIL", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
