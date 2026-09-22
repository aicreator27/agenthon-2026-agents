# Asset Manifest

Updated: 2026-09-22

| Asset | Role | Authority | Status |
|---|---|---|---|
| `docs/architecture/ASSET_ARCHITECTURE_MAP.md` | Canonical asset and handoff map | Project | Frozen v0.1 |
| `docs/decisions/ADR-0001-architecture-v0.1.md` | Initial architecture decisions | User-approved direction | Frozen v0.1 |
| `docs/handoff/HANDOFF.md` | Current state and next safe action | Project | Current |
| `docs/decisions/ADR-0003-predictive-power-measurement.md` | Definition of predictive power and the iteration/holdout rule | Official `M0-BASELINE.md` | Accepted |
| `docs/decisions/ADR-0004-numeric-ensemble-v02-calibration.md` | Calibrated v0.2 sampler defaults and rejected alternatives | Project | Accepted |
| `sources/deep-research-report-5.md` | Snapshot of the supplied research report | External research | Immutable snapshot |
| `sources/SOURCE_REGISTRY.md` | Source hashes and authority classification | Project | Current |
| `upstream/README.md` | Rules for official repository/toolkit pins | Official upstream | Awaiting pins |
| `core/README.md` | Reusable-core boundary | Project | Scaffold only |
| `tracks/t1_agenthon/README.md` | T1 adapter/solver boundary | Project | Scaffold only |
| `tracks/t2_agenthon/README.md` | T2 adapter/forecaster boundary | Project | Scaffold only |
| `tracks/t2_agenthon/src/t2_agenthon/` | Runnable T2 numeric ensemble and official CLI | Project | Implemented v0.1 |
| `packaging/t1/README.md` | T1 container/submission boundary | Official contract | Scaffold only |
| `packaging/t2/` | T2 image, pinned dependencies and descriptor template | Official contract | Built, verified and pushed by digest |
| `packaging/t2-verifier/` | Local image for pinned official smoke scorer | Official contract | Implemented; Docker run pending |
| `tests/README.md` | Verification asset taxonomy | Project | Scaffold only |
| `tests/contracts/test_t2_submission.py` | Deterministic three-file output contract | Project | Passing |
| `scripts/regression_t2.py` | Public-card producer plus official scorer harness | Project | Representative 6/6 pass |
| `evidence/README.md` | Run-bundle and acceptance evidence contract | Project | Scaffold only |
| `tests/backtests/t2/harness.py` | Rolling-origin pseudo-units and faithful M0 reimplementation | Official `M0-BASELINE.md` §3 | Validated against the documented reference-CLI arm |
| `tests/backtests/t2/units.py` | Pseudo-unit catalogue and locked dev/holdout split | Project | Current |
| `tests/backtests/t2/stage_forecast.py` | Backtest arm producer (submission image) | Project | Current |
| `tests/backtests/t2/stage_score.py` | Official-scorer evaluation and significance test | Official contract | Current |
| `evidence/reports/VERIFICATION_STATUS.md` | Evidence-backed current acceptance state | Project | Current |
| `evidence/manifests/t2-v0.2-verification.json` | Pins, verdicts, digest and holdout result for v0.2 | Project | Current |
| `evidence/runs/t2-calibration-v02-20260922/` | Calibration rounds 0-6 and the single holdout evaluation | Project | Sealed |

Every material asset added later must have a manifest entry, an authority class and a status.
