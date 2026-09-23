#!/usr/bin/env sh
# Restore upstream/ at the exact pins recorded in sources/SOURCE_REGISTRY.md.
#
# upstream/ is deliberately NOT committed: the shared toolkit is CC BY-NC 4.0, so vendoring it
# into this repository would redistribute it under terms we do not hold. Cloning at a pinned
# commit gets the same bytes without that problem.
#
# Nothing in this project builds or runs until this has been done once: the verifier images
# COPY from upstream/, and every smoke, matrix and backtest reads the official units.
# Re-running is safe; a checkout already at its pin is left untouched.
#
# POSIX counterpart of bootstrap_upstream.ps1, for macOS and Linux.

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UP="$ROOT/upstream"
mkdir -p "$UP"
FAILED=""

pin_one() {
    name="$1"; commit="$2"; url="$3"
    dir="$UP/$name"

    if [ -d "$dir/.git" ]; then
        head="$(git -c safe.directory='*' -C "$dir" rev-parse HEAD 2>/dev/null || echo none)"
        if [ "$head" = "$commit" ]; then
            printf 'OK      %s already at pin\n' "$name"
            return 0
        fi
        printf 'MOVING  %s is at %.12s\n' "$name" "$head"
    elif [ -e "$dir" ]; then
        printf 'ERROR   %s exists but is not a git checkout; remove it and rerun\n' "$name"
        FAILED="$FAILED $name"; return 0
    else
        printf 'CLONE   %s\n' "$name"
        git clone --quiet "$url" "$dir" || { FAILED="$FAILED $name"; return 0; }
    fi

    git -c safe.directory='*' -C "$dir" fetch --quiet origin "$commit" 2>/dev/null || true
    git -c safe.directory='*' -C "$dir" checkout --quiet --detach "$commit" \
        || { FAILED="$FAILED $name"; return 0; }

    # Verify rather than trust: a wrong pin silently changes what every gate is measured against.
    head="$(git -c safe.directory='*' -C "$dir" rev-parse HEAD)"
    if [ "$head" != "$commit" ]; then
        printf 'MISMATCH %s: HEAD %s != pin %s\n' "$name" "$head" "$commit"
        FAILED="$FAILED $name"; return 0
    fi
    printf 'PINNED  %s @ %.12s\n' "$name" "$commit"
}

pin_one Agenthon2026-public       03fc89cc666354e999768381bb923e60be5c1cee \
        https://github.com/Agenthon-2026/Agenthon2026-public.git
pin_one track1-coding-public      25975fc743d67019827652b9dfbdefc712229533 \
        https://github.com/Agenthon-2026/track1-coding-public.git
pin_one track2-forecasting-public 4ee40699e81f4ab50056c8835e67583035695692 \
        https://github.com/Agenthon-2026/track2-forecasting-public.git

if [ -n "$FAILED" ]; then
    printf 'Failed to pin:%s\n' "$FAILED" >&2
    exit 1
fi
printf 'BOOTSTRAP_OK all upstream pins match sources/SOURCE_REGISTRY.md\n'
