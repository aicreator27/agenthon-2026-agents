# Handoff — Track 2 operational state

> Joining the project? Start at [TEAM_HANDOFF.md](TEAM_HANDOFF.md), which covers
> both tracks and the current blockers. This file is the T2 detail.

Updated: 2026-09-22

## Verified state

- T2 is the primary track; ADR-0002 corrects the earlier delivery priority.
- Official T2 and toolkit sources are pinned under `upstream/`.
- The Linux/amd64 submission image builds, passes the container contract test, and passes the
  pinned official verifier on the offline exemplar with no failure labels.
- The base image is pinned by digest and build attestations are disabled, so the pushed artifact
  is a single linux/amd64 OCI manifest rather than an index carrying an `unknown/unknown` entry.
- The image is pushed and carries the calibrated v0.3 model:
  `ghcr.io/aicreator27/agenthon-t2@sha256:e3991ed0cad9097e5b00e1a2560b5642e72f31b181de77271b65b6479866b066`
  (anonymous manifest check: HTTP 200; single OCI manifest, linux/amd64)
- A rolling-origin backtest exists under `tests/backtests/t2/`. It reimplements the official M0
  text-blind baseline and scores with the pinned official composite. Its fidelity is established
  externally: the shipped official reference CLI measures 1.2173 mean / 1.0552 median through it,
  where `M0-BASELINE.md` section 7 documents 1.29 / 1.05.
- **Predictive power, v0.3 (ADR-0007), on held-out data:**

| population | v0.2 | v0.3 | beats M0 |
|---|---|---|---|
| daily level (1,168) | 0.8249 | 0.8264 | 71.9% |
| log_return (411) | 1.0369 | **1.0218** | 59.6% |
| monthly (81) | 1.0756 | **0.9984** | 55.6% |

  The daily result remains significant (p < 0.00005, HAC t = -13.4 as measured for v0.2; v0.3
  differs by +0.0015, which is 3% of that holdout's bootstrap width). Monthly has crossed from
  worse-than-M0 to parity. Roster-mix expectation moves from 0.8668 to 0.8626.
- **`log_return a1h21_63` (1.195) investigated and closed as irreducible.** The variogram reads
  a two-cell forecast through one scalar, so the space was searched exhaustively: our current
  dispersion is the optimum, and even an oracle using the mean realized value scores *worse*
  (1.517), because the ratio's denominator vanishes wherever M0 is lucky. The metric rewards
  proximity to M0 on this shape, not accuracy. See ADR-0007; do not re-attempt. Every other
  shape is below 1.0.
- Admissibility survived the calibration: contract test 1/1, offline exemplar admissible with no
  failure labels, public matrix 36/36.

## Next safe action

`packaging/t2/submission.json` has been regenerated against the v0.3 digest, so **the existing
`submission.zip` is stale and must be repacked** before uploading:

```
docker run --rm -it -v "<repo>/packaging/t2:/out" --entrypoint qfbench2 agenthon-t2-verifier:dev   submission pack --descriptor /out/submission.json --team-number 497 --out /out/submission.zip
```

`--team-key-file` is not usable from a Windows bind mount: the toolkit refuses a key file that is
readable by group or others, and a bind mount cannot present mode 600. Use the hidden prompt.

The Team Key was exposed in plaintext in a chat transcript on 2026-09-22 and should be rotated
with the organizers. Rotating changes the derived `team_id`, so repack after any rotation.

## Gate order

1. T2 build, contract test and official exemplar smoke. **Done.**
2. T2 public-practice admissibility matrix. **Done (representative 6/6).**
3. Registry push, public visibility, anonymous digest pull and sealed package. **Done.** Upload: open.
4. T2 rolling-origin numeric calibration. **Done.** Daily level 0.8264, monthly at parity,
   log_return 1.0218. The one shape still above 1.0 is `log_return a1h21_63`.
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
- Numeric-only tuning is exhausted. The remaining gate-5 lever is bounded House text
  adjustments, which is a different kind of change, not another parameter.
- The daily, log_return and monthly holdouts have each now been opened. Further tuning needs a
  fresh split, or its p-value measures the tuning.
- Track 1 is being developed in this same repository by a separate effort (ADR-0005, ADR-0006).
  `scripts/test_t2.ps1` scopes discovery to `test_t2_*.py` because the T2 image deliberately does
  not contain `t1_agenthon`; do not widen that pattern.
