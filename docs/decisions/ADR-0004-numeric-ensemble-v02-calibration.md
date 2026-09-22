# ADR-0004: Numeric ensemble v0.2 calibration

Date: 2026-09-22
Status: Accepted; supersedes the v0.1 sampler defaults set by ADR-0002
Measurement rules: ADR-0003

## Decision

Three sampler defaults change:

| knob | v0.1 | v0.2 |
|---|---|---|
| `history_window` | full history at or before the as-of | **300** |
| `block_length` | 5 | **31** |
| `bootstrap_weight` | 0.65 | **0.80** |

Everything else is unchanged, including the driftless level target and the
block-bootstrap / Student-t path mixture.

## Result

On the locked holdout of 1,168 rolling-origin pseudo-units (239 as-of dates from 2017-12-29
onward, never used during tuning):

| arm | mean vs M0 | median | beats M0 | bootstrap p | HAC t |
|---|---|---|---|---|---|
| **v0.2** | **0.8249** | 0.9109 | **72.0%** | **< 0.00005** | **-13.43** |
| v0.1 | 0.9540 | 0.8384 | 66.0% | 0.054 | -- |
| official reference CLI | 1.2173 | 1.0567 | 44.9% | 1.000 | -- |

The bootstrap 95% interval on the mean has width 0.050, so the estimate sits far from the
null value of 1.0. Every unit shape beats M0. v0.1 did not clear significance.

## Why these three, and the mechanism

**`history_window = 300` is the large effect** (-0.066 on its own). The joint variogram term is a
*squared* penalty on predicted pairwise dispersion, so a mis-scaled spread is punished
quadratically there while the marginal CRPS tolerates it. Putting 45% of the covariance weight on
the full 2000-2024 history biased our scale high in calm regimes, because volatility
distributions are right-skewed. The confirming evidence is the `cov_full` arm, which uses only
long-history covariance: it is the worst non-degenerate arm measured, with a joint ratio of 2.04.
Truncating to the recent 300 observations moved the joint ratio from 1.238 to 0.991.

**`block_length = 31`** preserves volatility clustering at roughly the monthly scale. It is not
merely a tuning artifact: see the rejected alternatives below.

**`bootstrap_weight = 0.80`** reduces the parametric Student-t arm, which is largely redundant
tail mass on top of the empirical tails the bootstrap already carries.

## Rejected, with evidence

**Adding drift to level targets. Rejected.** M0 applies the full trailing `s*mu`; we apply none,
and our marginal beats M0 on every shape without it. Scanning `drift_shrink` over
{-0.25, +0.25, +0.50} moved the score by -0.003 / +0.003 / +0.007: zero is optimal within noise.
There is no exploitable drift at these horizons.

**Rescaling dispersion. Rejected.** A scan of a global `dispersion_scale` over
{0.90, 0.95, 1.05, 1.10} was worse at every point. Since CRPS is a proper scoring rule, minimized
at correct calibration, this is positive evidence that the v0.2 spread is already well calibrated.

**Explicit variance-ratio matching. Rejected, and instructive.** The hypothesis was that terminal
dispersion should be `sigma_1(recent) * sqrt(h * VR(long history))` -- volatility level from the
recent regime, term structure from long history, because overlapping h-step estimates on a
300-observation window leave roughly 1.4 effective observations. Every variant scored worse than
doing nothing. The ordering is the informative part: forcing `sigma_1 * sqrt(h)` exactly
(shrink 0) was the *worst* variant, and the score improved monotonically as the estimate was
allowed back toward the untouched sampler. So the block bootstrap's *implicit* horizon scaling is
genuinely informative, and the premise was wrong -- the variance ratio is regime-dependent too,
and the bootstrap already estimates it from the right window. The code is retained with
`variance_ratio=False` as recorded negative evidence.

## Known fragility

Under the official aggregation every score is clipped into `[0, 4]` (`aggregate.py`), and the
v0.2 gain depends on that clip: the unclipped mean raw score is *higher* than v0.1's. The cause
is bounded and understood. All 17 clipped units out of 2,905 are the one-asset two-horizon shape,
where the variogram has exactly one pair, so when M0's predicted dispersion happens to land on
the realized value its denominator approaches zero and *any* submission's ratio explodes. Their
marginal ratios stay between 0.87 and 1.16, so this is a property of the normalization on 2-cell
grids, not a defect in the forecast. The clip is official and applies to every entrant, but a
change in the aggregation rule would move this result.

## Admissibility is preserved

The calibration does not trade admissibility for score: container contract test 1/1, offline
exemplar admissible under the pinned official verifier with no failure labels, and the public
admissibility matrix re-run at **36/36** on the v0.2 model, spanning level and log_return targets,
daily and monthly panels, and families F1 to F4.
