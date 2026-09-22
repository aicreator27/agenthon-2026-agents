# Handoff

Updated: 2026-09-22

## Verified state

- T2 is the primary track; ADR-0002 corrects the earlier delivery priority.
- Official T2 and toolkit sources are pinned under `upstream/`.
- The Linux/amd64 submission image builds, passes the container contract test, and passes the
  pinned official verifier on the offline exemplar with no failure labels.
- The base image is pinned by digest and build attestations are disabled, so the pushed artifact
  is a single linux/amd64 OCI manifest rather than an index carrying an `unknown/unknown` entry.
- The image is pushed and carries the calibrated v0.2 model:
  `ghcr.io/aicreator27/agenthon-t2@sha256:f464a19e510c9e53e03b01d9acd95058597de1e5972e832f52bd90461ad3db0d`
- A rolling-origin backtest exists under `tests/backtests/t2/`. It reimplements the official M0
  text-blind baseline and scores with the pinned official composite. Its fidelity is established
  externally: the shipped official reference CLI measures 1.2173 mean / 1.0552 median through it,
  where `M0-BASELINE.md` section 7 documents 1.29 / 1.05.
- **The model has statistically significant predictive power on daily level panels.** On the
  locked holdout of 1,168 pseudo-units the v0.2 defaults score 0.8249 against M0 (p < 0.00005,
  HAC t = -13.4, 72.0% of units beating M0), where v0.1 scored 0.9540 at p = 0.054. See ADR-0004.
- **It does not transfer.** On log_return (1,376 units) and monthly (281 units) populations that
  influenced no tuning decision, v0.2 scores 1.0360 and 1.1997 -- worse than the text-blind
  baseline. The calibration generalizes (v0.2 still beats v0.1 by 0.124 paired there), the
  predictive power does not. Roster-mix expectation is near 0.87, not 0.8249.
  See `evidence/runs/t2-calibration-v02-20260922/TRANSFER.md`.
- Admissibility survived the calibration: contract test 1/1, offline exemplar admissible with no
  failure labels, public matrix 36/36.

## Next safe action

Upload `packaging/t2/submission.zip` on the Track 2 CodaBench page from the team's single
designated account. Everything upstream of that is verified: the image is public and anonymously
pullable by digest, that exact digest was pulled credential-free and passed the pinned official
verifier, and the zip passes 14/14 pre-upload checks.

Track 2 allows 5 uploads per team per day and 20 in total during Development, and a held or
cancelled upload still consumes an attempt.

Note: the Team Key was exposed in plaintext in a chat transcript on 2026-09-22 and should be
rotated with the organizers. If it is rotated, the derived `team_id` changes and the descriptor
must be repacked before the next upload.

## Gate order

1. T2 build, contract test and official exemplar smoke. **Done.**
2. T2 public-practice admissibility matrix. **Done (representative 6/6).**
3. Registry push, public visibility, anonymous digest pull and sealed package. **Done.** Upload: open.
4. T2 rolling-origin numeric calibration. **Done for daily level panels; log_return and
   monthly are measured and are worse than M0, so this gate is only partly closed.**
5. Bounded House text adjustments and ablation.
6. Minimum T1 path using only proven shared infrastructure.

## Measured model state

Locked holdout, 1,168 pseudo-units over 239 as-of dates from 2017-12-29, never used for tuning:

| arm | mean vs M0 | median | beats M0 | one-sided p |
|---|---|---|---|---|
| v0.2 (current defaults) | **0.8249** | 0.9109 | 72.0% | **< 0.00005** |
| v0.1 | 0.9540 | 0.8384 | 66.0% | 0.054 |
| official reference CLI | 1.2173 | 1.0567 | 44.9% | 1.000 |

Rejected during calibration, with evidence in ADR-0004: adding drift to level targets, rescaling
dispersion, and explicit variance-ratio matching. The known fragility is that the gain depends on
the official `[0, 4]` clip; all 17 clipped units are the one-asset two-horizon shape, where M0's
variogram denominator can approach zero by coincidence.

## Open decisions

- Public image versus organizer-approved confidential handoff.
- Team Number and Team Key, required only by `qfbench2 submission pack`. They are not needed for
  any local measurement.

## Do not infer

- The research report is not binding competition authority.
- Public-practice success does not imply hidden-task generalization.
- A valid Docker image does not imply agent quality.
- The holdout has now been opened. It cannot be reused: any further tuning needs a fresh split,
  or its p-value measures the tuning.
- The calibration is measured on daily level panels only. log_return and monthly-panel score
  behaviour is unmeasured, though both are covered for admissibility.
