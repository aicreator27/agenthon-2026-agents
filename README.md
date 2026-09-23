# Agenthon 2026 Agents

Source, decisions, tests, packaging and acceptance evidence for Agenthon 2026 **Track 1 (coding)**
and **Track 2 (forecasting)**.

## Joining the project? Read this first

**[docs/handoff/TEAM_HANDOFF.md](docs/handoff/TEAM_HANDOFF.md)**
(中文單檔版：[docs/handoff/handoff.html](docs/handoff/handoff.html)，下載後用瀏覽器開啟) — current state of both tracks,
the open blockers, how to get from a fresh clone to a first scored run, what has already been
tried and rejected, and the traps that have cost time. Everything below is a summary of it.

## First run, from a fresh clone

`upstream/` is **not committed** — the shared toolkit is CC BY-NC 4.0, so vendoring it here would
redistribute it under terms we do not hold. Restore it at its pinned commits first; nothing builds
or runs until you do, because the verifier images `COPY` from `upstream/` and every gate reads the
official units from it.

```powershell
.\scripts\bootstrap_upstream.ps1
.\scripts\build_t2.ps1 ; .\scripts\test_t2.ps1 ; .\scripts\smoke_t2.ps1
.\scripts\build_t1.ps1 ; .\scripts\test_t1.ps1 ; .\scripts\smoke_t1.ps1
```

On macOS or Linux use `sh scripts/bootstrap_upstream.sh` for the first line. Docker Desktop must
be running. Green means T2 `admissible=True labels=[]` and T1 `reward=1.0 passed=14`.

## Current state

| | Track 1 | Track 2 |
|---|---|---|
| Image | `ghcr.io/aicreator27/agenthon-t1` | `ghcr.io/aicreator27/agenthon-t2` |
| Package | public, anonymously pullable | public, anonymously pullable |
| Gates | 10/10 contract, 87/87 conformance, exemplar reward 1.0 | 1/1 contract, exemplar admissible, matrix 36/36 |
| Uploaded | no | no |

Track 2 scores **0.826** against the official text-blind M0 baseline on held-out daily level
panels (p < 0.00005), where 1.0 means "no better than a forecast that never read the text".
Track 1 has a legal, runnable universal agent but has only earned reward on the worked exemplar.
Both claims and their limits are stated precisely in the handoff.

## Layout

```
core/                 shared, Agenthon-unaware helpers
tracks/t1_agenthon/   T1 adapter + universal solver
tracks/t2_agenthon/   T2 adapter + forecasting ensemble
packaging/t1|t2/      Dockerfiles, lockfiles, descriptors — no agent intelligence
tests/backtests/t2/   rolling-origin harness + local M0 reimplementation
evidence/             manifests, run bundles, acceptance reports
docs/decisions/       ADRs 0001-0007
upstream/             pinned official repos, restored by bootstrap. READ ONLY
```

Docker is the runtime envelope. Agent intelligence stays in `core/` and `tracks/`; `packaging/`
carries container and submission concerns only.

## Ground rules

- Tune on development data; a holdout is opened **once** (ADR-0003). All three T2 holdouts have
  been spent — further tuning needs a fresh split.
- Never commit a Team Key, model token or registry credential.
- `upstream/` is read-only. Upgrade pins through an ADR and `sources/SOURCE_REGISTRY.md`.
- Every new top-level asset gets an entry in [ASSET_MANIFEST.md](ASSET_MANIFEST.md).
