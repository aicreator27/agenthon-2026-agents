# Agenthon 2026 Agents

Independent project root for all Agenthon T1/T2 source, decisions, tests, packaging and acceptance evidence.

## Current state

- Phase: `runnable-t2-baseline`
- Architecture: `ADR-0001 v0.1`, delivery priority corrected by `ADR-0002`
- Implementation: T2 numeric-only submission source, Docker packaging, tests and smoke scripts
- First asset: [Asset Architecture Map](docs/architecture/ASSET_ARCHITECTURE_MAP.md)
- Current handoff: [HANDOFF.md](docs/handoff/HANDOFF.md)

## Construction order

1. Build and smoke the numeric-only T2 image against the official exemplar.
2. Push by immutable digest and prepare the sealed Development descriptor.
3. Establish a public-practice T2 admissibility matrix.
4. Add rolling-origin evaluation and calibrate the numeric ensemble.
5. Add bounded House text knobs only after the numeric baseline is reproducible.
6. Reuse the proven shell for a minimum T1 path without slowing T2.

## Working rule

Docker is the runtime envelope. Agent intelligence stays in `core/` and track-specific orchestration stays in `tracks/`.

## T2 commands

```powershell
.\scripts\build_t2.ps1
.\scripts\test_t2.ps1
.\scripts\smoke_t2.ps1
```

Docker Desktop must be running. The smoke script saves its evidence under `evidence/runs/`.
