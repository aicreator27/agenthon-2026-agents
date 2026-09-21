# Asset Manifest

Updated: 2026-09-21

| Asset | Role | Authority | Status |
|---|---|---|---|
| `docs/architecture/ASSET_ARCHITECTURE_MAP.md` | Canonical asset and handoff map | Project | Frozen v0.1 |
| `docs/decisions/ADR-0001-architecture-v0.1.md` | Initial architecture decisions | User-approved direction | Frozen v0.1 |
| `docs/handoff/HANDOFF.md` | Current state and next safe action | Project | Current |
| `sources/deep-research-report-5.md` | Snapshot of the supplied research report | External research | Immutable snapshot |
| `sources/SOURCE_REGISTRY.md` | Source hashes and authority classification | Project | Current |
| `upstream/README.md` | Rules for official repository/toolkit pins | Official upstream | Awaiting pins |
| `core/README.md` | Reusable-core boundary | Project | Scaffold only |
| `tracks/t1_agenthon/README.md` | T1 adapter/solver boundary | Project | Scaffold only |
| `tracks/t2_agenthon/README.md` | T2 adapter/forecaster boundary | Project | Scaffold only |
| `tracks/t2_agenthon/src/t2_agenthon/` | Runnable T2 numeric ensemble and official CLI | Project | Implemented v0.1 |
| `packaging/t1/README.md` | T1 container/submission boundary | Official contract | Scaffold only |
| `packaging/t2/` | T2 image, pinned dependencies and descriptor template | Official contract | Implemented; Docker run pending |
| `packaging/t2-verifier/` | Local image for pinned official smoke scorer | Official contract | Implemented; Docker run pending |
| `tests/README.md` | Verification asset taxonomy | Project | Scaffold only |
| `tests/contracts/test_t2_submission.py` | Deterministic three-file output contract | Project | Passing |
| `scripts/regression_t2.py` | Public-card producer plus official scorer harness | Project | Representative 6/6 pass |
| `evidence/README.md` | Run-bundle and acceptance evidence contract | Project | Scaffold only |
| `evidence/reports/VERIFICATION_STATUS.md` | Evidence-backed current acceptance state | Project | Current |

Every material asset added later must have a manifest entry, an authority class and a status.
