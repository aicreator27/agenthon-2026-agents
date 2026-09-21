# Track 1 verification status

Updated: 2026-09-22  
Model path: deterministic exemplar handler plus bounded House generate/repair scaffold

## Verified

- Official T1 public repository pinned at commit
  `25975fc743d67019827652b9dfbdefc712229533`.
- Python compile check: pass.
- PowerShell build/test/smoke scripts parse without errors.
- Linux/amd64 image build: pass; interface label `2.0`; fixed `solve` verb responds.
- Container contract test: 1/1 pass, including deterministic rerun and financial parity.
- Official worked exemplar executed with `--network=none`.
- Official offline checker: 14 passed, reward `1.0`.
- Pinned `qfbench2-smoke`: `admissible=True`, `score=1.0`, no failure labels. Under the
  sequential Track 1 verifier contract this is the local exemplar evidence for g0-g3 acceptance.

Evidence run: `evidence/runs/t1-smoke-20260922-022459/`.

## Not yet verified

- The House generate/execute/repair path has no local organizer House endpoint and has not been
  exercised end to end.
- No non-exemplar public task has earned reward 1. The current deterministic handler is intentionally
  limited to the worked Black-Scholes exemplar.
- Full 87-unit public-practice pass@1/pass@3 regression has not started. Running the current image
  offline over those units would measure House unavailability, not general solving quality.
- No T1 registry image has been pushed and no submission descriptor has been generated.

## Interpretation boundary

This establishes a legal, runnable T1 submission shell and one real official reward path. It does
not establish hidden-task generalization or a competitive Track 1 score.
