# Verification status

Updated: 2026-09-21

## Verified

- Python compile check: exit 0.
- Contract test: 1/1 pass, including exact three-file output and deterministic rerun.
- Official worked exemplar: producer exit 0 with 1,000 draws.
- Pinned official scorer verdict on exemplar: `admissible: true`; g0, g1, g2 and g3 all pass.
- Representative public matrix: 6/6 admissible, covering exemplar, F1–F4, log-return and
  explicit monthly handling.
- Linux/amd64 image build: pass; interface label `2.0` and `forecast --help` verified.
- Container contract test: 1/1 pass.
- Offline (`--network=none`) exemplar container run plus pinned official verifier: admissible,
  with no failure labels.

Evidence:

- `evidence/reports/test-t2-local.log`
- `evidence/runs/t2-exemplar-local-20260921-213942/official-scorer.log`
- `evidence/runs/t2-matrix-20260921-214515/summary.json`
- `evidence/runs/t2-matrix-20260921-214515/results.csv`
- `evidence/runs/t2-smoke-20260921-232528/smoke.log`
- `evidence/manifests/t2-v0.1-verification.json` (pins, verdicts and output hashes)

## Not yet verified

- Anonymous registry pull, immutable remote digest and CodaBench execution require the user's
  registry/team configuration.
- Full 104-directory public sweep did not finish in one foreground runner window. The reusable
  regression script now supports `--offset` and `--limit` for bounded batches; the representative
  matrix is the current acceptance evidence.
