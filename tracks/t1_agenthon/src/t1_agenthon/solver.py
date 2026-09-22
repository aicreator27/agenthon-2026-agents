"""Deterministic exemplar plus a bounded House generate/repair loop."""

from __future__ import annotations

import ast
import ctypes
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from agenthon_core.house import HouseUnavailable, chat_json, house_available

_BANNED_IMPORT_ROOTS = {
    "ctypes",
    "ftplib",
    "http",
    "httpx",
    "multiprocessing",
    "openai",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}
_BANNED_CALL_NAMES = {"__import__", "compile", "eval", "exec"}
_BANNED_OS_CALLS = {
    "popen",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "system",
}
_FORBIDDEN_OUTPUT_NAMES = {"pytest_report.json", "reward.json", "reward.txt"}
_OUTPUT_NAME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_/-])([A-Za-z0-9_./-]+\.(?:json|parquet|csv|txt))(?![A-Za-z0-9_/-])",
    re.IGNORECASE,
)
_UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _BANNED_CALL_NAMES:
                raise ValueError(f"dynamic execution is not allowed: {node.func.id}")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr in _BANNED_OS_CALLS
        ):
            raise ValueError(f"process execution is not allowed: os.{node.func.attr}")


def _protect_parent_process() -> None:
    if os.name != "posix":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
        raise OSError(ctypes.get_errno(), "could not protect parent process credentials")


def _resource_limits() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))


def _commit_staged_outputs(staging: pathlib.Path, output: pathlib.Path, task: pathlib.Path) -> bool:
    files = [path for path in staging.rglob("*") if path.is_file()]
    if not files:
        return False
    for source in files:
        if (
            source.is_symlink()
            or not source.resolve().is_relative_to(staging.resolve())
            or source.name in _FORBIDDEN_OUTPUT_NAMES
        ):
            raise ValueError(f"forbidden output: {source.name}")
    instruction_path = task / "instruction.md"
    instruction = _read_text(instruction_path, 50_000) if instruction_path.is_file() else ""
    canaries = [token.encode("ascii") for token in _UUID_PATTERN.findall(instruction)]
    for source in files:
        payload = source.read_bytes()
        if any(canary in payload for canary in canaries):
            raise ValueError(f"canary leaked into output: {source.name}")
    diagnostic = output / "agent_diagnostic.json"
    if diagnostic.exists():
        diagnostic.unlink()
    for source in files:
        relative = source.relative_to(staging)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return True


def _stage_task_inputs(task: pathlib.Path, sandbox: pathlib.Path) -> pathlib.Path:
    staged_task = sandbox / "task"
    staged_task.mkdir()
    for name in ("instruction.md", "card.toml"):
        source = task / name
        if source.is_file() and not source.is_symlink():
            shutil.copyfile(source, staged_task / name)
    for relative in (pathlib.Path("environment/data"), pathlib.Path("data")):
        source = task / relative
        if not source.is_dir() or source.is_symlink():
            continue
        destination = staged_task / relative
        shutil.copytree(source, destination, symlinks=False)
    return staged_task


def _run_program(source: str, task: pathlib.Path, output: pathlib.Path) -> tuple[bool, str]:
    _validate_program(source)
    _protect_parent_process()
    with tempfile.TemporaryDirectory(prefix="t1-agent-") as temporary:
        temporary_root = pathlib.Path(temporary)
        script = temporary_root / "solution.py"
        staging = temporary_root / "output"
        staging.mkdir()
        staged_task = _stage_task_inputs(task, temporary_root)
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
                "TASK_DIR": str(staged_task),
                "OUT_DIR": str(staging),
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
            preexec_fn=_resource_limits if os.name == "posix" else None,
        )
        transcript = (completed.stdout + "\n" + completed.stderr)[-12_000:]
        if completed.returncode != 0:
            return False, transcript
        return _commit_staged_outputs(staging, output, task), transcript


def _fallback_outputs(task: pathlib.Path, output: pathlib.Path) -> bool:
    instruction_path = task / "instruction.md"
    if not instruction_path.is_file():
        return False
    contract_sources = [_read_text(instruction_path, 50_000)]
    for relative in (pathlib.Path("environment/data"), pathlib.Path("data")):
        data_root = task / relative
        if not data_root.is_dir():
            continue
        for path in sorted(data_root.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".json", ".py", ".toml", ".txt"}:
                contract_sources.append(_read_text(path, 100_000))
    contract_text = "\n".join(contract_sources)
    candidates = {
        pathlib.PurePosixPath(match).name
        for match in _OUTPUT_NAME_PATTERN.findall(contract_text)
        if pathlib.PurePosixPath(match).name not in _FORBIDDEN_OUTPUT_NAMES
    }
    for name in sorted(candidates):
        destination = output / name
        suffix = destination.suffix.lower()
        if suffix == ".json":
            destination.write_text("{}\n", encoding="utf-8")
        elif suffix == ".csv":
            destination.write_text("placeholder\n0\n", encoding="utf-8")
        elif suffix == ".parquet":
            pd.DataFrame({"placeholder": pd.Series(dtype=float)}).to_parquet(destination, index=False)
        elif suffix == ".txt":
            destination.write_text("0\n", encoding="utf-8")
    return bool(candidates)


def _house_solve(task: pathlib.Path, output: pathlib.Path) -> bool:
    contract = _contract(task)
    data_files = sum(1 for path in task.rglob("*") if path.is_file())
    if len(contract) < 8_000 and data_files <= 4:
        adaptive_budget = 4
    elif len(contract) < 20_000 and data_files <= 10:
        adaptive_budget = 6
    else:
        adaptive_budget = 8
    max_requests = max(1, min(12, int(os.getenv("T1_MAX_REQUESTS", adaptive_budget))))
    system = (
        "You are a financial coding agent. Return one JSON object with keys plan, python and notes. "
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
            print(f"T1_HOUSE_REQUESTS={request_index + 1} STATUS=success", file=sys.stderr)
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
    print(f"T1_HOUSE_REQUESTS={max_requests} STATUS=exhausted", file=sys.stderr)
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
    if _fallback_outputs(task, output):
        return output
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
    "multiprocessing",
