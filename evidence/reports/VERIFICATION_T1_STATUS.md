# Track 1 verification status

Updated: 2026-09-22  
Model path: deterministic registry handler plus adaptive House generate/execute/repair agent

## Verified

- Official T1 public repository pinned at commit
  `25975fc743d67019827652b9dfbdefc712229533`.
- Python compile check: pass.
- PowerShell build/test/smoke scripts parse without errors.
- Linux/amd64 image build: pass; interface label `2.0`; fixed `solve` verb responds.
- T1-focused contract suite: 10/10 pass. It covers CLI/determinism, the House HTTP contract,
  repair after execution failure, failed-output isolation, credential scrubbing, canary rejection,
  forbidden imports, and offline output-contract fallback.
- Generated programs receive a staged copy of task inputs without `checks/`, no House credentials,
  bounded CPU/address-space/file/process resources, and an isolated output staging directory.
- Official 87-unit public-practice conformance: `87/87 OK`, zero crashes, zero missing expected
  deliverables, zero unchecked. This is an admissibility floor check, not a correctness score.
- Official worked exemplar executed with `--network=none`.
- Official offline checker: 14 passed, reward `1.0`.
- Pinned `qfbench2-smoke`: `admissible=True`, `score=1.0`, no failure labels. Under the
  sequential Track 1 verifier contract this is the local exemplar evidence for g0-g3 acceptance.

Evidence run: `evidence/runs/t1-smoke-20260922-105434/`. Full conformance log:
`evidence/reports/t1-conformance-v01.log` (SHA-256
`b15737aeeafd24da311db6c10b78f0cc68956a7b9b8f149f6dcde7ffc27922ec`).

## Not yet verified

- The HTTP route and full generate/execute/repair state transitions are covered with a local mock,
  but the organizer House endpoint is unavailable locally; live House behavior remains unmeasured.
- No non-exemplar public task has earned reward 1. The current deterministic handler is intentionally
  limited to the worked Black-Scholes exemplar.
- The 87-unit sweep proves exit/output contract compatibility only. It does not establish public
  pass@1 because the offline run correctly has no organizer House route.
- The submission descriptor generator is implemented and uses the official House disclosure.
  Registry digest, anonymous pullability and sealed team claim remain pending.

## Interpretation boundary

This establishes a legal, runnable universal-agent container, a complete public output-contract
sweep, and one real official reward path. It does not establish House-powered public/hidden-task
generalization or a competitive Track 1 score; only an official Development run can measure that.
