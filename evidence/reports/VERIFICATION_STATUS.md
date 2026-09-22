# Verification status

Updated: 2026-09-22
Model: `text-disabled-v0.2-calibrated` (ADR-0004)

## Verified

- Container contract test: 1/1 pass, including exact three-file output and deterministic rerun.
- Official worked exemplar: producer exit 0 with 1,000 draws.
- Pinned official scorer verdict on the exemplar: `admissible: true`; g0, g1, g2 and g3 all pass,
  no failure labels, under `--network=none`.
- Public admissibility matrix on the v0.2 model: **36/36 admissible**, spanning level and
  log_return targets, daily and monthly panels, and families F1 to F4.
- Linux/amd64 image: base pinned by digest, build attestations disabled, pushed as a single OCI
  manifest (not an index).
- Registry push by immutable digest:
  `ghcr.io/aicreator27/agenthon-t2@sha256:f464a19e510c9e53e03b01d9acd95058597de1e5972e832f52bd90461ad3db0d`
- **Anonymous pullability: pass.** A credential-free GHCR token was issued, the manifest resolved
  by digest with HTTP 200, and the config blob plus all ten layers returned HTTP 206 without any
  workstation credential.
- **Registry-digest rehearsal: pass.** The image was pulled by digest with an isolated empty
  Docker config (no credentials), then run offline against the pinned official verifier:
  `admissible`, no failure labels, and all three deliverable hashes byte-identical to the
  locally verified build. The registry artifact is the artifact that was verified.
- **Submission zip: 14/14 pre-upload checks pass** (`team-d97f76905fee06ab78eb89d72e5e19f4`,
  site team 497). The claim binds the exact `submission.json` bytes, and no `team_key` appears
  anywhere in the archive.
- Descriptor packing dry run: pass. `qfbench2 submission pack` produced a well-formed
  `submission.zip` (12-key `submission.json` + schema-2.0 `team-claim.json` carrying a proof and
  no `team_key`) using a throwaway key, since deleted.

## Predictive power

Measured under ADR-0003 against a local reimplementation of the official M0 text-blind baseline,
on rolling-origin pseudo-units cut from published panels. No sealed material is involved.

Harness fidelity, which gates everything below: the shipped official reference CLI measures
**1.2173 mean / 1.0567 median** through this harness, where `M0-BASELINE.md` section 7 documents
**1.29 / 1.05** on the organizers' own sealed cards.

Locked holdout (1,168 units, 239 as-of dates from 2017-12-29, never used for tuning):

| arm | mean vs M0 | median | beats M0 | one-sided p | HAC t |
|---|---|---|---|---|---|
| **v0.2** | **0.8249** | 0.9109 | **72.0%** | **< 0.00005** | **-13.43** |
| v0.1 | 0.9540 | 0.8384 | 66.0% | 0.054 | -- |
| official reference CLI | 1.2173 | 1.0567 | 44.9% | 1.000 | -- |

1.0 is the text-blind baseline and lower is better, so v0.2 is 17.5% better than a forecast that
never read the text, significant at the 0.00005 level, on data held out from every tuning
decision. v0.1 was not significant.

**That result applies to daily level panels only, and does not generalize.** On populations that
influenced no tuning decision -- 1,376 log_return pseudo-units and 281 monthly ones -- both
versions score *above* 1.0, i.e. worse than the text-blind baseline:

| population | v0.1 | v0.2 | v0.2 beats M0 |
|---|---|---|---|
| daily level (holdout) | 0.9540 | **0.8249** | 72.0% |
| log_return | 1.1607 | 1.0360 | 53.3% |
| monthly macro | 1.3197 | 1.1997 | 42.0% |

The calibration itself does generalize -- v0.2 beats v0.1 by 0.124 paired on the untouched
populations -- but the *predictive power* is specific to daily level panels. Weighting by the
roster mix (roughly 81% daily level, 15% log_return, 4 monthly cards) gives an expected roster
score near **0.87**, not 0.8249. Details: `evidence/runs/t2-calibration-v02-20260922/TRANSFER.md`.

## Not yet verified

- CodaBench execution, which needs the Team Number and a Team Key entered by the operator at the
  toolkit's hidden prompt. No Team Key is stored in this repository or in any tooling here.
- The full 104-directory public sweep. The 36-unit bounded batch is the current evidence, and the
  regression script supports `--offset` / `--limit` for further batches.
- log_return pseudo-units and monthly-panel pseudo-units are not in the backtest population; the
  calibration is measured on daily level panels. Admissibility on both is covered by the 36-unit
  matrix, but their *score* behaviour is not measured.
