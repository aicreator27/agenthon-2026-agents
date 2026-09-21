# ADR-0001: Architecture Baseline v0.1

Date: 2026-09-21  
Status: Accepted baseline  
Scope: Agenthon 2026 T1 Coding and T2 Forecasting

## Context

The project needs two minimum legal submissions before model optimization. The architecture must keep reusable intelligence separate from competition adapters, preserve official authority order and produce durable handoff evidence.

## Decisions

1. Build minimum legal T1 and T2 submissions first. Then prioritize T1, returning to T2 optimization after the T1 regression loop is measurable.
2. Keep `core/` unaware of Agenthon. Put official CLI, paths and schemas under `tracks/t1_agenthon/` and `tracks/t2_agenthon/`.
3. Use one monorepo and two independent images/dependency sets. Share only House client, logging, provenance, seed and schema utilities.
4. Authority order is: Rules/Licensing/Terms → current track README plus pinned toolkit → machine-readable task/card/schema → instruction → project assumptions.
5. T1 may execute model-generated Python with a pragmatic first-stage boundary: isolated working directory, read-only inputs, timeout/resource limits, no network or sensitive paths, compile check and staged output validation. AST checks block only clear violations.
6. T1 uses a fixed state machine with a dynamic request budget: contract → plan → implement → execute → diagnose → repair → final validate. Request use escalates by task difficulty and preserves repair reserve; no fixed ten-call assumption.
7. Validators distinguish hard and soft findings. Explicit instruction/schema requirements and unambiguous mathematical identities are hard; convention-sensitive checks are soft. The best candidate survives soft failures.
8. Build a universal solver first. Add domain packs according to public-practice failures; derivatives, fixed income, risk, backtest and FX are initial priorities, not a fixed taxonomy.
9. Financial knowledge lives in a versioned executable registry containing formulas, conventions, units, edge cases, invariants and tests. The LLM selects tools; it does not recreate the registry.
10. T2 starts as a numeric baseline ensemble, including joint block bootstrap and shrinkage Gaussian/Student-t candidates. Rolling-origin CRPS and companion metrics select weights. Every asset/horizon remains part of one joint scenario path.
11. House text output is structured and may make bounded mean, volatility, correlation and tail adjustments in either direction. Walk-forward calibration determines utility and caps.
12. MVP data is limited to official panels and timestamped text. External data, models and artifacts require cutoff, license and provenance audit before admission.
13. Every run records image digest, toolkit/track version, card/input hash, prompt/schema version, seed, House request count, failure labels, metrics and output hash. The numeric layer is deterministic; the full House path is not required to be bit-identical.
14. Decide the image/IP route in the first project phase. Public images must be anonymously pullable and may be downloaded; confidential handling requires early organizer confirmation.
15. Model optimization starts only after Linux/amd64, anonymous digest pull, offline execution, current category/schema, T1 exemplar reward=1, T2 g0–g3, deterministic numeric core and digest rebuild gates pass. Then create the public-practice regression matrix and stop optimizing the Docker shell.

## Consequences

- Docker and submission packaging cannot own solver intelligence.
- T1 architecture is a general repair loop plus executable finance tools, not a collection of category agents.
- T2 model selection and text authority remain empirical questions resolved by rolling-origin evidence.
- Official version pins and run evidence are first-class project assets.

## Deferred experimental choices

- T1 critic activation, repair depth and category-specific prompting.
- T2 block length, ensemble weights, draw count and text caps.
- State-space, GARCH, copula and neural additions.

