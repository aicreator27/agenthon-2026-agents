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
- GitHub Actions run `35681724143`: success for source commit
  `4ab5aad5371b43241d47bab48b723d3b6f7c62e9`.
- Published single-manifest image:
  `ghcr.io/aicreator27/agenthon-t1@sha256:d9d74a4070117654603166244546bb7df026f0aa41066918b684e27d7f22caff`.
- Remote digest inspection and pull: linux/amd64, interface `2.0`.
- Anonymous digest inspection with a fresh empty Docker config: pass.
- The exact remote digest passed the official exemplar checker (`reward=1.0`, 14 tests) and pinned
  qfbench2 verifier (`admissible=True`, `score=1.0`, no labels).
- The unsealed Development descriptor passes the pinned official C5 parser after in-memory sealing;
  it declares the exact official House model row and immutable image digest.
- Official `qfbench2 submission pack` produced `packaging/t1/submission.zip` for site team 497 and
  derived team id `team-d97f76905fee06ab78eb89d72e5e19f4`.
- Sealed archive verification: 15/15 checks pass, including exact two-file layout, official
  descriptor parsing, immutable digest, House disclosure, descriptor-byte binding and Team Key
  HMAC proof. The key itself is absent from the archive.
- Submission zip SHA-256:
  `599dc65b430dc4e315f87846d15ca03cb6aaf45e59b34a8a42a00c139564666c`.

Registry evidence run: `evidence/runs/t1-smoke-20260922-110803/`. Full conformance log:
`evidence/reports/t1-conformance-v01.log` (SHA-256
`b15737aeeafd24da311db6c10b78f0cc68956a7b9b8f149f6dcde7ffc27922ec`).

## Not yet verified

- The HTTP route and full generate/execute/repair state transitions are covered with a local mock,
  but the organizer House endpoint is unavailable locally; live House behavior remains unmeasured.
- No non-exemplar public task has earned reward 1. The current deterministic handler is intentionally
  limited to the worked Black-Scholes exemplar.
- The 87-unit sweep proves exit/output contract compatibility only. It does not establish public
  pass@1 because the offline run correctly has no organizer House route.
- Packaging is complete. No Team Key is stored in the repository or archive.
- No official Development upload has been made. Therefore competitive public/hidden-task pass@1
  remains unmeasured; the exemplar reward proves usability, not leaderboard competitiveness.

## Interpretation boundary

This establishes a legal, runnable universal-agent container, a complete public output-contract
sweep, and one real official reward path. It does not establish House-powered public/hidden-task
generalization or a competitive Track 1 score; only an official Development run can measure that.
