"""Windows-safe equivalent of the official Track 1 conformance sweep."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import tempfile


FILE_LITERAL = re.compile(r"['\"]([A-Za-z0-9_./{}-]+\.(?:json|parquet|csv|txt))['\"]")
EXCLUDED_CONTEXT = re.compile(
    r"(data|input|ref|reference|log)_(dir|path)|input_(json|csv|parquet|text)|"
    r"/app/data|/input|/tests/reference|/logs|[^a-z0-9_](data|ref) */",
    re.IGNORECASE,
)


def expected_names(unit: pathlib.Path) -> set[str]:
    names: set[str] = set()
    for checker in sorted((unit / "checks").glob("*.py")):
        for line in checker.read_text(encoding="utf-8", errors="replace").splitlines():
            if EXCLUDED_CONTEXT.search(line):
                continue
            for match in FILE_LITERAL.finditer(line):
                value = match.group(1)
                if ("{" in value or "}" in value) and not value.startswith("{OUTPUT_DIR}/"):
                    continue
                if "/" not in value or value.startswith(("/output/", "/app/output/", "{OUTPUT_DIR}/")):
                    names.add(pathlib.PurePosixPath(value).name)
    return names


def run(image: str, kit: pathlib.Path, log_path: pathlib.Path) -> int:
    units = sorted(path for path in (kit / "units").glob("t1-*") if path.is_dir())
    evidence_root = log_path.parent.parent
    evidence_root.mkdir(parents=True, exist_ok=True)
    passed = crashed = missing = unchecked = 0
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="t1-conformance-", dir=evidence_root) as temporary:
        work = pathlib.Path(temporary)
        for unit in units:
            output = work / unit.name
            output.mkdir()
            command = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--mount",
                f"type=bind,source={unit.resolve()},target=/input,readonly",
                "--mount",
                f"type=bind,source={output.resolve()},target=/output",
                "--mount",
                f"type=bind,source={output.resolve()},target=/app/output",
                image,
                "solve",
                "--task-dir",
                "/input",
                "--out",
                "/app/output",
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            wanted = expected_names(unit)
            if completed.returncode != 0:
                crashed += 1
                tail = (completed.stderr.strip().splitlines() or [""])[-1][:100]
                lines.append(f"{unit.name:<46} CRASH exit={completed.returncode} {tail}")
            elif not wanted:
                unchecked += 1
                lines.append(f"{unit.name:<46} UNCHECKED")
            elif any((output / name).is_file() for name in wanted):
                passed += 1
                lines.append(f"{unit.name:<46} OK")
            else:
                missing += 1
                lines.append(f"{unit.name:<46} MISSING {' '.join(sorted(wanted))}")
    lines.append("")
    lines.append(
        f"units {len(units)}   ok {passed}   crashed {crashed}   "
        f"wrote-nothing-expected {missing}   unchecked {unchecked}"
    )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines[-1])
    return 0 if units and crashed == 0 and missing == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("kit", type=pathlib.Path)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    args = parser.parse_args()
    return run(args.image, args.kit.resolve(), args.log.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
