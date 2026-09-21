# ADR-0005: T1 minimum runnable slice

Date: 2026-09-22  
Status: Accepted for implementation; capability gate remains open

## Decision

Start T1 without disturbing the calibrated T2 worktree. Pin the official T1 public repository at
commit `25975fc743d67019827652b9dfbdefc712229533`, implement the fixed `solve` CLI, and first prove
the official worked exemplar reaches `reward=1.0` under the offline checker.

The first general path uses the shared House client and the state sequence
`contract -> implement -> execute -> diagnose -> repair -> validate`. It admits at most four
requests by default and six by configuration, below the official limit of 25. Generated Python
runs in a fresh working directory with a bounded timeout, a scrubbed child environment and a small
AST network/process deny-list. This is an initial containment layer, not a strong security sandbox.

## Boundaries

- The deterministic Black-Scholes handler is an interface proof, not a public-suite baseline.
- Local T1 `qfbench2 smoke` does not run the sealed rankable verifier; the public unit's offline
  `checks/test.sh` and `reward.json` are the available local acceptance route.
- Do not reuse T2 rolling-origin predictive-power language for T1. T1 quality is measured by
  reward/pass@1 over coding tasks, with pass@3 only as an offline development diagnostic.
- Do not call vendor APIs or let generated code inherit House credentials.
