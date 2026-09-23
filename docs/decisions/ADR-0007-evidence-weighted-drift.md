# ADR-0007: Evidence-weighted drift (numeric ensemble v0.3)

Date: 2026-09-22
Status: Accepted; extends ADR-0004
Measurement rules: ADR-0003

## Context

ADR-0004 was calibrated entirely on daily **level** panels and measured 0.8249 against M0 there.
A transfer check afterwards showed it did not generalize: on log_return and monthly macro
populations both v0.1 and v0.2 scored *above* 1.0, i.e. worse than the official text-blind
baseline. The roster contains both, so the gap was real and worth closing.

## Decision

One new default: `drift_evidence_c = 25.0`. The drift applied to the cumulated path is the
trailing mean step **shrunk by how much statistical evidence supports it**:

```
t = mean(step) / (sd(step) / sqrt(n))
weight = t^2 / (t^2 + c),      drift = weight * mean(step)
```

It replaces the fixed `drift_shrink` / `return_drift_shrink` constants and applies to both
target types by one rule. Nothing else changes.

## Why this rule rather than a per-population constant

A submission ships **one** config for every card, so a fix cannot simply special-case monthly
data. It has to key on something observable at run time.

Forcing zero drift on level targets is most of why v0.2's marginal beat M0 on daily panels: the
trailing mean step there carries a t of roughly 0.3 and is almost pure estimation noise. The same
rule is badly wrong on a monthly price index, where the trend is the signal. Measured on a
trailing 300-observation window:

| panel | asset | t of mean step | weight at c=25 |
|---|---|---|---|
| rates_daily | UST_10Y | -0.26 | 0.003 |
| g10_fx_daily | AUD | 0.20 | 0.002 |
| macro_monthly | CPI_ALL | **11.45** | **0.84** |
| macro_monthly | CPI_CORE | **20.50** | **0.94** |
| macro_monthly | NFP | 1.22 | 0.06 |

So the one rule reproduces the calibrated driftless behaviour on daily financial panels and
restores the real trend on monthly price indices, while still declining to invent a trend for
NFP, which does not have one. The diagnostic that pointed here was the horizon pattern: monthly
marginal was fine at h=2 (0.993) and bad at h=9 (1.040), which is the signature of a missing
drift, since a location error grows with the horizon.

## Result on held-out data

The log_return and monthly populations were given their own chronological dev/holdout splits
before any tuning. The daily holdout is reused only as a regression guard; no selection used it.

| population | v0.2 | v0.3 | median | beats M0 |
|---|---|---|---|---|
| daily level (1,168) | 0.8249 | 0.8264 | 0.9139 | 71.9% |
| log_return (411) | 1.0369 | **1.0218** | 0.9651 | 59.6% |
| monthly (81) | 1.0756 | **0.9984** | 0.9905 | 55.6% |

Monthly crosses from worse-than-M0 to parity. The daily cost is +0.0015, which is 3% of that
holdout's bootstrap confidence width and therefore noise. Roster-mix weighted expectation moves
from 0.8668 to 0.8626.

## Rejected, with evidence

**Shortening the bootstrap block on coarse panels. Rejected.** The hypothesis was that a 31-row
block is 2.6 *years* on a monthly panel, so it resamples whole inflation regimes and inflates the
tails. A cadence-aware block length was implemented (`block_length_days`, `block_min`) and
verified to leave daily output bit-identical, then swept over monthly blocks of 1, 2, 3, 4 and 6
rows. The best arm gained 0.007 and a block of 1 *lost* 0.053. Narrowing the block did reduce the
monthly tail ratio (1.33 to 1.19) but cost more on the marginal and joint terms than it saved.
The knobs are retained, defaulting to inert, as recorded negative evidence.

**A fixed `return_drift_shrink` for log_return. Superseded.** It worked (-0.0096 on dev) but the
evidence-weighted rule achieves the same effect on log_return (-0.0100) while also fixing
monthly, so carrying both would be two knobs doing one job.

## Remaining weakness: investigated and closed as irreducible

`log_return a1h21_63` -- one asset, two horizons, return target -- averages 1.195 on the holdout
with a median of 1.038. Its marginal (0.981) and tail (0.965) already beat M0; the whole deficit
is the joint term at 1.062. It was investigated directly and **there is no achievable gain**.

`variogram_score` reads the forecast only through `mean_k |x_ki - x_kj|^p`. On a two-cell grid
that is a **single scalar**, so the complete space of what any forecast can do to this term is
one dimension, and it can be searched exhaustively rather than argued about.

Measured on 187 development units of this shape, scaling our cross-horizon dispersion by `k`:

| k | 0.80 | 0.90 | 0.95 | **1.00** | 1.05 | 1.10 | 1.20 |
|---|---|---|---|---|---|---|---|
| mean score | 1.388 | 1.295 | 1.241 | **1.189** | 1.203 | 1.218 | 1.275 |

`k = 1.00`, what we already do, is the optimum.

The decisive measurement is the oracle. Replacing our prediction with the **mean realized value**
-- the best constant predictor that exists, which no model could beat -- scores **1.517**, far
*worse* than our 1.189. The reason is structural: the score is `VS_ours / VS_M0`, and
`VS_M0 = (r - b)^2` approaches zero whenever M0's predicted dispersion happens to land on the
realized draw. A forecast that sits close to M0 has a numerator that vanishes at the same time
and stays bounded; a forecast that is systematically *more accurate* than M0 does not, and its
ratio explodes on exactly those units. Our prediction sits within 1.5% of M0's here
(0.1867 vs 0.1896, realized mean 0.1818), which is why the shape is merely mediocre rather than
catastrophic.

So on a two-cell single-asset grid the metric rewards proximity to the denominator, not accuracy.
The only lever that would lower this shape's score further is hedging still closer to M0, which
carries no predictive content and which the sweep shows is not available anyway. **Do not
re-attempt this.** Effort is better spent on shapes where the marginal and tail terms carry the
weight.

## Admissibility

Container contract test 1/1, offline exemplar admissible under the pinned official verifier with
no failure labels, public admissibility matrix 36/36 on v0.3.
