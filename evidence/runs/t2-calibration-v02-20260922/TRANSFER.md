# Transfer check: does the calibration hold outside daily level panels?

The calibration in ADR-0004 was measured entirely on **daily level** panels
(`rates_daily`, `g10_fx_daily`, `factors_daily` treated as levels). The published roster also
contains log_return targets and monthly macro panels. This is a check on populations that
influenced **no** tuning decision at any point.

Populations: 1,376 log_return pseudo-units from `factors_daily` (which really is a per-step
return panel; realized = the sum of h returns) and 281 monthly pseudo-units from
`macro_monthly` with horizons in panel steps, i.e. months, as `M0-BASELINE.md` section 3.7 does
for the four monthly cards.

| population | v0.1 | v0.2 | v0.2 median | v0.2 beats M0 |
|---|---|---|---|---|
| log_return (1,376) | 1.1607 | **1.0360** | 0.9930 | 53.3% |
| monthly (281) | 1.3197 | **1.1997** | 1.0434 | 42.0% |
| combined (1,657) | 1.1877 | **1.0638** | 0.9963 | 51.4% |

Paired, v0.2 is 0.1239 better than v0.1 and wins on 57.7% of these units.

## Two separate conclusions, which must not be conflated

**The calibration generalizes.** v0.2 beats v0.1 on a population that had no influence on it, by
a margin comparable to the one measured on the tuned population. The three changed defaults are
not artifacts of the development set.

**The predictive power does not.** Both versions score **above 1.0** here, meaning worse than the
official text-blind baseline, with a one-sided p of 1.0. The 0.8249 holdout result is a statement
about **daily level panels only**. On log_return we are at parity with M0; on monthly we are
clearly behind it.

## Consequence for the roster

The published roster is roughly 81% daily level, about 15% log_return and 4 monthly cards.
Weighting the measured populations by that mix gives an expected roster score near **0.87** for
v0.2 against about **1.00** for v0.1 -- a real improvement, but materially weaker than the 0.8249
headline, which applies to the daily level slice alone.

This is an extrapolation across proxy populations, not a measurement on the official cards, which
carry no realized outcomes and therefore cannot be scored locally at all.

## Leads

- `history_window = 300` is inert on monthly data: the panel holds only 281 observations, so the
  truncation never fires there and the monthly gain comes from `block_length` and
  `bootstrap_weight` alone. A block of 31 *months* is 2.6 years on a 281-month history, which is
  very likely the wrong scale.
- The tail component is the worst on monthly (1.23 to 1.43 against M0) and the marginal is the
  worst on `m1h9` (1.12), so both location and spread are mis-set at long monthly horizons.
