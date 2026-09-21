# Handoff

Updated: 2026-09-21

## Verified state

- T2 is the primary track; ADR-0002 corrects the earlier delivery priority.
- Official T2 and toolkit sources are pinned under `upstream/`.
- A numeric-only T2 forecaster, Linux/amd64 Dockerfile, contract test, official verifier image,
  smoke script and descriptor generator now exist.
- The Linux/amd64 image builds successfully, the container contract test passes, and the offline
  exemplar passes the pinned official verifier with no failure labels.

## Next safe action

Push `ghcr.io/aicreator27/agenthon-t2`, make only that package public, and verify an anonymous pull
by immutable digest before generating and sealing the Development descriptor. Source remains in a
private repository and submission code uses the MIT licence.

## Gate order

1. T2 build, contract test and official exemplar smoke.
2. T2 public-practice admissibility matrix.
3. Registry push, anonymous digest pull and sealed Development package.
4. T2 rolling-origin numeric calibration.
5. Bounded House text adjustments and ablation.
6. Minimum T1 path using only proven shared infrastructure.

## Open decisions

- Public image versus organizer-approved confidential handoff.
- Team ID / Team Number and Team Key required by the official descriptor sealing flow.

## Do not infer

- The research report is not binding competition authority.
- Public-practice success does not imply hidden-task generalization.
- A valid Docker image does not imply agent quality.
