# Verification Assets

- `contracts/`: CLI, schema, policy and path behavior.
- `integration/`: exemplar, offline and g0–g3 checks.
- `regression/t1/`: public-practice outcomes and failure taxonomy.
- `backtests/t2/`: rolling-origin pseudo-units, text ablations and forecast metrics.

Long outputs belong in external run logs; foreground reports keep only exit status and concise tails.

`scripts/regression_t2.py` runs the producer and pinned official scorer over selected or all public
units and stores one bounded evidence directory per unit plus a CSV/JSON summary.
