"""Run the T2 producer and pinned official admissibility scorer over public units."""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time
import tomllib
from typing import Any


def _asof(card: dict[str, Any]) -> str:
    candidates = (
        card.get("provenance", {}).get("data_cutoff"),
        card.get("text", {}).get("cutoff"),
        card.get("metadata", {}).get("asof"),
    )
    for value in candidates:
        if value:
            return str(value)[:10]
    raise ValueError("card does not declare an as-of/data cutoff")


def _run(command: list[str], *, env: dict[str, str], log: pathlib.Path) -> int:
    completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    return completed.returncode


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--project", required=True, type=pathlib.Path)
    result.add_argument("--run-dir", required=True, type=pathlib.Path)
    result.add_argument("--python", default=sys.executable)
    result.add_argument("--n-draws", type=int, default=200)
    result.add_argument("--seed", type=int, default=0)
    result.add_argument("--unit", action="append", default=[])
    result.add_argument("--offset", type=int, default=0)
    result.add_argument("--limit", type=int, default=None)
    return result


def main() -> int:
    args = parser().parse_args()
    project = args.project.resolve()
    units_root = project / "upstream" / "track2-forecasting-public" / "units"
    scorer = project / "upstream" / "track2-forecasting-public" / "scoring" / "scoring.py"
    pydeps = os.environ.get("AGENTHON_VALIDATION_DEPS", "")

    selected = sorted(path for path in units_root.iterdir() if (path / "card.toml").is_file())
    if args.unit:
        names = set(args.unit)
        selected = [path for path in selected if path.name in names]
    selected = selected[args.offset :]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        raise SystemExit("no matching units")

    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    producer_path = os.pathsep.join(
        filter(
            None,
            [pydeps, str(project / "core" / "src"), str(project / "tracks" / "t2_agenthon" / "src")],
        )
    )
    scorer_path = os.pathsep.join(
        filter(
            None,
            [
                pydeps,
                str(project / "upstream" / "Agenthon2026-public" / "common"),
                str(project / "upstream" / "track2-forecasting-public"),
            ],
        )
    )
    rows: list[dict[str, Any]] = []
    for index, unit in enumerate(selected, 1):
        started = time.perf_counter()
        card = tomllib.loads((unit / "card.toml").read_text(encoding="utf-8"))
        unit_run = run_dir / unit.name
        output = unit_run / "output"
        output.mkdir(parents=True)
        producer_env = dict(os.environ, PYTHONPATH=producer_path)
        producer_command = [
            args.python,
            "-m",
            "t2_agenthon.cli",
            "--panels",
            str(unit / "panels"),
            "--text",
            str(unit / "text"),
            "--asof",
            _asof(card),
            "--out",
            str(output / "forecast.parquet"),
            "--n-draws",
            str(args.n_draws),
            "--seed",
            str(args.seed),
        ]
        producer_code = _run(producer_command, env=producer_env, log=unit_run / "producer.log")
        admissible = False
        gates: dict[str, Any] = {}
        scorer_code: int | None = None
        if producer_code == 0:
            scorer_env = dict(os.environ, PYTHONPATH=scorer_path)
            scorer_command = [
                args.python,
                str(scorer),
                "score",
                "--card",
                str(unit / "card.toml"),
                "--forecast",
                str(output / "forecast.parquet"),
            ]
            scorer_code = _run(scorer_command, env=scorer_env, log=unit_run / "scorer.log")
            try:
                verdict = json.loads((unit_run / "scorer.log").read_text(encoding="utf-8"))
                admissible = bool(verdict.get("admissible"))
                gates = dict(verdict.get("gates", {}))
            except (json.JSONDecodeError, OSError, TypeError):
                pass
        row = {
            "unit": unit.name,
            "family": card.get("metadata", {}).get("category", ""),
            "target_type": card.get("targets", {}).get("target_type", ""),
            "target_frequency": card.get("targets", {}).get("target_frequency", ""),
            "producer_exit": producer_code,
            "scorer_exit": scorer_code,
            "admissible": admissible,
            "g0": gates.get("g0_integrity", ""),
            "g1": gates.get("g1_schema", ""),
            "g2": gates.get("g2_cutoff_resource", ""),
            "g3": gates.get("g3_domain_semantics", ""),
            "seconds": round(time.perf_counter() - started, 3),
        }
        rows.append(row)
        print(f"[{index}/{len(selected)}] {unit.name}: {'PASS' if admissible else 'FAIL'}", flush=True)

    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "units": len(rows),
        "admissible": sum(bool(row["admissible"]) for row in rows),
        "failed": sum(not bool(row["admissible"]) for row in rows),
        "n_draws": args.n_draws,
        "seed": args.seed,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
