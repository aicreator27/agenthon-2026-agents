# ADR-0003: How predictive power is measured and when it may be claimed

Date: 2026-09-22
Status: Accepted; governs gate 4 of the handoff gate order

## Context

"The model is good" is not a checkable statement on this track, and the obvious local proxies
are all wrong. The 104 published units ship no realized outcome, so nothing can be scored
against them directly. Raw CRPS is in the units of whatever is being forecast, so it cannot be
averaged across cards. And the organizers do not publish per-card scales, so the denominator of
the official score is not available either.

What *is* available is the procedure behind that denominator. `M0-BASELINE.md` specifies the
official text-blind baseline completely enough to rebuild, and states the consequence plainly:
the score is a ratio against M0, and **1.0 means no better than a forecast that never read the
text**.

## Decision

Predictive power is defined as **a composite score significantly below 1.0 against a local
reimplementation of M0**, measured on rolling-origin pseudo-units cut from published panels.

Four things are fixed by this decision.

**1. The denominator is M0, rebuilt locally.** `tests/backtests/t2/harness.py` implements
`M0-BASELINE.md` section 3: trailing 300 observations, the gap rule, date-aligned covariance,
`mean[i] = anchor + s*mu`, `cov[i,j] = min(s_i,s_j)*Sigma`, 500 draws seeded by
`crc32(unit_id) & 0x7FFFFFFF`, cells ordered by asset id then ascending horizon.

**2. Normalization is per component, not per composite.** The official score is
`w_m*(our_marginal/M0_marginal) + w_j*(...) + w_t*(...)`, not a ratio of composites. A one-cell
grid redistributes the variogram weight to `(0.714286, 0, 0.285714)`, and scores are clipped
into `[0, 4]`. Scoring is performed by the pinned official `_composite`, not a local rewrite.

**3. The harness must be externally calibrated before any result from it is believed.**
A local M0 that is accidentally too weak would make every arm look good. The only external check
available is `M0-BASELINE.md` section 7, which measures the shipped official reference CLI at
mean 1.29 / median 1.05 against the real M0. Re-measured through this harness on independent
pseudo-units it gives **1.2573 / 1.0552**. That agreement is the licence to trust the numbers,
and it is re-checked whenever the harness changes.

**4. Iteration is separated from evidence.** Pseudo-units are split chronologically into a
development set and a holdout, with a 200-day embargo across the boundary. All tuning happens on
development. The holdout is opened **once**, at the end, and the reported p-value is the holdout
one. A p-value computed on the set that was tuned against measures the tuning, not the model.

## Significance test

The statistic is the mean score against the null value 1.0, tested one-sided. Dependence runs in
two directions at once: overlapping forecast windows make neighbouring as-of dates serially
dependent, and units sharing an as-of date are cross-sectionally dependent. A moving-block
bootstrap over **blocks of as-of dates**, carrying every unit at a date together, handles both.
A Newey-West corrected t statistic on the per-date mean is reported alongside as a cross-check.
An i.i.d. bootstrap over units is not acceptable here; it would ignore both and report a p-value
far too small.

## Consequences

- A development-set improvement is a hypothesis, not a result. Only the holdout figure may be
  quoted as predictive power, and only once.
- Changes to the sampler must keep the official exemplar gates green; the backtest does not
  replace the admissibility evidence, it sits beside it.
- The parameterization added to `forecaster.py` defaults bit-exactly to the v0.1 baseline, so the
  existing hash-level evidence remains valid until a default is deliberately changed.
- Nothing in this ADR requires a Team Number, a Team Key, a registry or a network. Measurement is
  fully local and does not depend on the submission path.
