# Project agent instructions

## Executive summary

Deliver a scoreable Agenthon Track 2 submission first. Keep Track 1 limited to genuinely shared
runtime assets until the T2 vertical chain is verified. Do not treat Docker work as the product.

## Authority

Rules/Licensing/Terms outrank the pinned track/toolkit repositories. Machine-readable schemas
outrank prose. `upstream/` is read-only; record upgrades in the source registry and an ADR.

## Verification

- Write long build/test output to `evidence/reports/` or one run directory.
- Keep foreground output to exit status and at most an 80-line tail.
- Run one foreground validation process at a time.
- A green claim requires a saved evidence path.
- Never add a realized answer or sealed-test material.

## Submission boundaries

- The T2 output directory must contain exactly `forecast.parquet`, `forecast_meta.json`, and
  non-empty `forecast_rationale.md`.
- Keep the numeric path functional with `--network=none`.
- House access is optional and must fall back to numeric-only behavior.
- Never store Team Keys, model tokens or registry credentials.

