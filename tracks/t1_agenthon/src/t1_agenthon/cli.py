"""Official Track 1 submission CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .solver import solve_task


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agenthon Track 1 solver")
    parser.add_argument("verb", choices=["solve"])
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    solve_task(args.task_dir, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
