# ADR-0002: T2-first runnable submission

Date: 2026-09-21  
Status: Accepted; supersedes ADR-0001 only where delivery priority differs

## Decision

Architecture documents are not the first milestone. The first milestone is a submission image
that implements the official T2 `forecast` command, works with no network, emits exactly three
legal deliverables and passes the official exemplar smoke gates. T2 owns the main engineering
effort because it is the user's primary track.

Shared work is allowed only when it immediately supports T2 or can be reused by T1 without
introducing a platform project. The current shared slice is deterministic seed handling,
provenance conventions and an organizer-only House client.

## Initial forecasting baseline

The first scoreable model is numeric-only and declares `models: []`. It generates joint paths
using a mixture of block-bootstrap residual paths and shrinkage Student-t paths. The same path
produces every asset/horizon cell in a draw. House-conditioned text knobs are deliberately gated
behind a verified numeric reference.

## Acceptance

1. Linux/amd64 image builds with interface label `2.0`.
2. `forecast --help` exits zero.
3. Exemplar run succeeds under `--network=none`.
4. Official `qfbench2-smoke` reports g0–g3 pass.
5. Numeric reruns with the same seed are identical.
6. Descriptor can be generated and sealed once team, registry, digest and license values exist.

