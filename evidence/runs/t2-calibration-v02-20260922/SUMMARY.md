# T2 numeric-ensemble calibration -- rounds 0 to 6 and the locked holdout

Measurement rules: ADR-0003. Decision and rejected alternatives: ADR-0004.
Nothing here touches sealed material; pseudo-units are cut from published panels.

## Harness fidelity

`M0-BASELINE.md` section 7 measures the shipped official reference CLI at mean 1.29 /
median 1.05 against the real M0 on the organizers' sealed cards. Re-measured through this
harness on independent rolling-origin pseudo-units: **1.2573 / 1.0552** on the development
subset and **1.2173 / 1.0567** on the holdout. That agreement is what licenses the numbers below.

## Round by round (development set)

| round | question | outcome |
|---|---|---|
| 0 | baseline | 0.9872, p = 0.241. Not significant. Loss localized to the joint term. |
| 1 | which factor drives the joint loss? | `history_window = 300` wins (-0.066); joint 1.238 -> 0.991. `cov_full` worst at joint 2.04, confirming the dispersion-regime mechanism. |
| 2 | combinations, window size, EWMA, matched draws | best 0.8950. Matched-draws control: 500 draws scores 0.9137 vs 0.9213 at 1000, so the edge is not a draw-count artifact. |
| 3 | fine tuning | flat region: top group 0.888-0.904. Stopped tuning rather than chase the argmax. |
| 4 | full development set (2,905 units) | 0.8176, p = 0.00005. Diagnosed the clip: 17/2905 units clipped, all one shape. |
| 5 | explicit variance-ratio matching | **rejected**; every variant worse. Forcing sqrt(h) was worst, so the bootstrap's implicit scaling is informative. |
| 6 | dispersion scale and drift | **rejected**; 1.0 and 0.0 already optimal. Scalar tuning exhausted. |

## Locked holdout -- opened once

1,168 units, 239 as-of dates, 2017-12-29 onward, never used for any tuning decision.

| arm | mean vs M0 | median | beats M0 | bootstrap p | HAC t |
|---|---|---|---|---|---|
| **v0.2** | **0.8249** | 0.9109 | **72.0%** | **< 0.00005** | **-13.43** |
| v0.1 | 0.9540 | 0.8384 | 66.0% | 0.054 | -- |
| official reference CLI | 1.2173 | 1.0567 | 44.9% | 1.000 | -- |

Per shape, v0.2: a1h21 0.8209, a1h21_63 0.9370, a1h63 0.8062, a4h21 0.8030, a4h63_126 0.7556.
Every shape beats M0. Bootstrap 95% interval width on the mean: 0.050.

## Files

`scores-r*.csv` are per-unit per-arm scores for each round; `configs-r*.json` are the exact arm
definitions; `units-dev.json` / `units-holdout.json` are the frozen split;
`scores-holdout*.csv` is the single holdout evaluation; `admissibility-36-*` is the post-change
official admissibility matrix.
