# Agenthon 2026 Agents — Asset Architecture Map

Status: `baseline-v0.1`  
Purpose: define where every project asset belongs before implementation begins.

## Authority and asset flow

```mermaid
flowchart TB
    subgraph AUTH[External authority — never edited here]
        A1[Rules / Licensing / Terms]
        A2[Track README + pinned toolkit]
        A3[Task card / schema / instruction]
    end

    subgraph GOV[Governance and provenance]
        G1[ADR decisions]
        G2[Source registry + pinned versions]
        G3[Asset manifest]
        G4[Handoff state]
    end

    subgraph CORE[Reusable core — Agenthon unaware]
        C1[House client + request budget]
        C2[Execution + diagnostics]
        C3[Executable finance registry]
        C4[Logging / provenance / seed / schemas]
    end

    subgraph T1[T1 Agenthon adapter + solver]
        T1A[solve CLI + task contract adapter]
        T1B[Contract → Plan → Implement]
        T1C[Execute → Diagnose → Repair]
        T1D[Hard / soft final validator]
    end

    subgraph T2[T2 Agenthon adapter + forecaster]
        T2A[forecast CLI + card adapter]
        T2B[Numeric baseline ensemble]
        T2C[House text → bounded knobs]
        T2D[Calibrated joint scenario sampler]
    end

    subgraph VERIFY[Verification assets]
        V1[Contract + unit tests]
        V2[T1 public regression matrix]
        V3[T2 rolling-origin pseudo-units]
        V4[Docker smoke / g0–g3 / offline checks]
    end

    subgraph RELEASE[Packaging and evidence]
        R1[T1 linux/amd64 image]
        R2[T2 linux/amd64 image]
        R3[Digest-pinned descriptors]
        R4[Run bundles: hashes / metrics / failure labels]
    end

    A1 --> G2
    A2 --> G2
    A3 --> T1A
    A3 --> T2A
    G1 --> CORE
    G2 --> T1A
    G2 --> T2A
    G3 --> G4
    CORE --> T1
    CORE --> T2
    T1 --> VERIFY
    T2 --> VERIFY
    VERIFY --> R1
    VERIFY --> R2
    R1 --> R3
    R2 --> R3
    VERIFY --> R4
    R3 --> G4
    R4 --> G4
```

## Canonical directory ownership

```text
agenthon-2026-agents/
├── README.md                         Project entrypoint and current phase
├── ASSET_MANIFEST.md                 Canonical inventory and ownership
├── sources/                          Immutable research/source snapshots
├── upstream/                         Pinned official repos and toolkit
├── docs/
│   ├── architecture/                 Architecture maps and boundaries
│   ├── decisions/                    Versioned ADRs
│   └── handoff/                      Current state, next action, open risks
├── core/                             Reusable code with no Agenthon imports
├── tracks/
│   ├── t1_agenthon/                  T1 adapter and universal solver
│   └── t2_agenthon/                  T2 adapter and forecasting pipeline
├── packaging/
│   ├── t1/                           T1 Docker and submission descriptor
│   └── t2/                           T2 Docker and submission descriptor
├── tests/
│   ├── contracts/                    CLI/schema/policy tests
│   ├── integration/                  Exemplars, smoke and offline checks
│   ├── regression/t1/                Public-practice regression matrix
│   └── backtests/t2/                 Rolling-origin pseudo-units and metrics
└── evidence/
    ├── manifests/                    Version, image and input/output hashes
    ├── runs/                         One bounded evidence bundle per run
    └── reports/                      Human-readable acceptance summaries
```

## Runtime boundaries

- `core/` must not import Agenthon track packages or know official CLI paths.
- `upstream/` contains pinned official material only; local implementation never edits it.
- `tracks/` translates official contracts into core interfaces and translates results back.
- `packaging/` contains container/submission concerns only; it must not contain agent intelligence.
- `sources/` is append-only. Derived implementation does not overwrite source snapshots.
- `evidence/runs/` records metadata and concise diagnostics, never credentials or House tokens.
- Every new top-level asset must be registered in `ASSET_MANIFEST.md` and assigned an owner/status.

## Handoff invariant

A successor should be able to determine, without reading chat history:

1. which official versions and policies govern the build;
2. which ADRs are frozen or still experimental;
3. where T1/T2 source, tests, packaging and evidence live;
4. the latest verified gate for each track;
5. the next safe action and unresolved risks.
