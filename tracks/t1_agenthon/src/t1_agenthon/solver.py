"""Deterministic exemplar plus a bounded House generate/repair loop."""

from __future__ import annotations

import ast
import json
import math
import os
import pathlib
import subprocess
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from agenthon_core.house import HouseUnavailable, chat_json, house_available

_BANNED_IMPORT_ROOTS = {
    "ftplib",
    "http",
    "httpx",
    "openai",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}
_MAX_PROFILE_CHARS = 24_000


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    erf = np.vectorize(math.erf, otypes=[float])
    return 0.5 * (1.0 + erf(values / math.sqrt(2.0)))


def _find_options(task: pathlib.Path) -> pathlib.Path | None:
    for relative in ("environment/data/options.parquet", "data/options.parquet"):
        candidate = task / relative
        if candidate.is_file():
            return candidate
    return None


def _solve_black_scholes(task: pathlib.Path, output: pathlib.Path) -> bool:
    source = _find_options(task)
    if source is None:
        return False
    options = pd.read_parquet(source)
    required = {"option_id", "S", "K", "T", "r", "sigma", "option_type"}
    if not required.issubset(options.columns):
        return False

    spot = options["S"].to_numpy(dtype=float)
    strike = options["K"].to_numpy(dtype=float)
    maturity = options["T"].to_numpy(dtype=float)
    rate = options["r"].to_numpy(dtype=float)
    volatility = options["sigma"].to_numpy(dtype=float)
    is_call = options["option_type"].astype(str).to_numpy() == "call"
    sqrt_t = np.sqrt(maturity)
    d1 = (np.log(spot / strike) + (rate + 0.5 * volatility**2) * maturity) / (
        volatility * sqrt_t
    )
    d2 = d1 - volatility * sqrt_t
    discount = np.exp(-rate * maturity)
    density = np.exp(-0.5 * d1**2) / np.sqrt(2.0 * np.pi)
    cdf_d1 = _normal_cdf(d1)
    cdf_d2 = _normal_cdf(d2)
    cdf_minus_d1 = _normal_cdf(-d1)
    cdf_minus_d2 = _normal_cdf(-d2)
    call_theta = -spot * density * volatility / (2.0 * sqrt_t) - rate * strike * discount * cdf_d2
    put_theta = -spot * density * volatility / (2.0 * sqrt_t) + rate * strike * discount * cdf_minus_d2

    result = pd.DataFrame(
        {
            "option_id": options["option_id"],
            "price": np.where(
                is_call,
                spot * cdf_d1 - strike * discount * cdf_d2,
                strike * discount * cdf_minus_d2 - spot * cdf_minus_d1,
            ),
            "delta": np.where(is_call, cdf_d1, cdf_d1 - 1.0),
            "gamma": density / (spot * volatility * sqrt_t),
            "vega": spot * density * sqrt_t,
            "theta": np.where(is_call, call_theta, put_theta) / 365.0,
        }
    )
    result.to_parquet(output / "results.parquet", index=False)
    return True


def _read_text(path: pathlib.Path, limit: int = 12_000) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _data_profile(task: pathlib.Path) -> str:
    data_root = task / "environment" / "data"
    if not data_root.is_dir():
        data_root = task / "data"
    if not data_root.is_dir():
        return "No data directory was present."
    records: list[str] = []
    for path in sorted(data_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(task).as_posix()
        try:
            if path.suffix.lower() == ".parquet":
                frame = pd.read_parquet(path)
                sample = frame.head(3).to_json(orient="records", date_format="iso")
                detail = (
                    f"rows={len(frame)} columns={list(frame.columns)} "
                    f"dtypes={frame.dtypes.astype(str).to_dict()} sample={sample}"
                )
            elif path.suffix.lower() in {".csv", ".json", ".txt"}:
                detail = _read_text(path, 4_000)
            else:
                detail = f"binary/unsupported preview; bytes={path.stat().st_size}"
        except Exception as exc:
            detail = f"preview failed: {type(exc).__name__}"
        records.append(f"## {relative}\n{detail}")
        if sum(map(len, records)) >= _MAX_PROFILE_CHARS:
            break
    return "\n\n".join(records)[:_MAX_PROFILE_CHARS]


def _contract(task: pathlib.Path) -> str:
    instruction = _read_text(task / "instruction.md") if (task / "instruction.md").is_file() else ""
    card = _read_text(task / "card.toml", 8_000) if (task / "card.toml").is_file() else ""
    return f"INSTRUCTION\n{instruction}\n\nCARD\n{card}\n\nDATA PROFILE\n{_data_profile(task)}"


def _validate_program(source: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        roots: set[str] = set()
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots = {node.module.split(".", 1)[0]}
        forbidden = roots & _BANNED_IMPORT_ROOTS
        if forbidden:
            raise ValueError(f"network/process import is not allowed: {sorted(forbidden)}")


def _run_program(source: str, task: pathlib.Path, output: pathlib.Path) -> tuple[bool, str]:
    _validate_program(source)
    with tempfile.TemporaryDirectory(prefix="t1-agent-") as temporary:
        script = pathlib.Path(temporary) / "solution.py"
        script.write_text(source, encoding="utf-8")
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            not in {
                "ALL_PROXY",
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "MODEL_ENDPOINT",
                "MODEL_NAME",
                "MODEL_TOKEN",
                "NO_PROXY",
            }
        }
        env.update(
            {
                "TASK_DIR": str(task),
                "OUT_DIR": str(output),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        completed = subprocess.run(
            ["python3", "-I", str(script)],
            cwd=temporary,
            env=env,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
    transcript = (completed.stdout + "\n" + completed.stderr)[-12_000:]
    deliverables = [path for path in output.iterdir() if path.is_file()]
    return completed.returncode == 0 and bool(deliverables), transcript


def _house_solve(task: pathlib.Path, output: pathlib.Path) -> bool:
    contract = _contract(task)
    max_requests = max(1, min(6, int(os.getenv("T1_MAX_REQUESTS", "4"))))
    system = (
        "You are a financial coding agent. Return one JSON object with keys python and notes. "
        "The python value must be a complete standalone program. It must read TASK_DIR, write only "
        "the requested deliverables into OUT_DIR, use only local data, never inspect checks or write "
        "reward files, never use network/process APIs, and finish deterministically."
    )
    payload: dict[str, Any] = chat_json(
        system=system,
        user=f"Implement this task.\n\n{contract}",
        max_tokens=4000,
    )
    source = str(payload.get("python", ""))
    for request_index in range(max_requests):
        try:
            ok, transcript = _run_program(source, task, output)
        except (SyntaxError, ValueError, subprocess.TimeoutExpired) as exc:
            ok, transcript = False, f"{type(exc).__name__}: {exc}"
        if ok:
            return True
        if request_index + 1 >= max_requests:
            break
        payload = chat_json(
            system=system,
            user=(
                "Repair the program using the execution feedback. Return the full replacement.\n\n"
                f"TASK\n{contract}\n\nPROGRAM\n{source[-18_000:]}\n\nFEEDBACK\n{transcript}"
            ),
            max_tokens=4000,
        )
        source = str(payload.get("python", ""))
    return False


def solve_task(task_dir: str | pathlib.Path, out: str | pathlib.Path) -> pathlib.Path:
    task = pathlib.Path(task_dir).resolve()
    output = pathlib.Path(out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if _solve_black_scholes(task, output):
        return output
    if house_available():
        try:
            if _house_solve(task, output):
                return output
        except HouseUnavailable:
            pass
    (output / "agent_diagnostic.json").write_text(
        json.dumps(
            {
                "status": "unsupported_without_house",
                "message": "No deterministic handler matched and the House route did not produce a deliverable.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output
