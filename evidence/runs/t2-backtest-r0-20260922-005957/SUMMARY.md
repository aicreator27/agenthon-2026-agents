# T2 rolling-origin backtest -- round 0 (baseline, no model change)

Pseudo-units are cut from published panels only; no sealed material is involved.
Scoring is the pinned official `_composite`, normalized per component against a local
reimplementation of the official M0 text-blind baseline (M0-BASELINE.md section 3).

## Harness validation

The official doc measures the shipped reference CLI at **mean 1.29 / median 1.05** against M0
over the 103 released cards. Re-measured here on independent rolling-origin pseudo-units:

| arm | mean | median |
|---|---|---|
| official reference CLI | **1.2573** | **1.0552** |
| documented target | 1.29 | 1.05 |

That agreement is the evidence that the local M0, the per-component normalization, the
single-cell weight renormalization and the [0,4] clip are all wired correctly.

## Round 0 result

| arm | mean | median | beats M0 | bootstrap p |
|---|---|---|---|---|
| ours | **0.9872** | 0.9408 | 61.4% | 0.241 |
| official reference CLI | 1.2573 | 1.0552 | 42.1% | 0.998 |

**Not significant.** We are clearly better than the shipped reference CLI, and not yet
distinguishable from M0.
