# T1 Agenthon Adapter

The first runnable slice implements the official `solve --task-dir ... --out ...` contract.
It contains:

- a deterministic Black-Scholes handler for the official worked exemplar;
- a bounded House-driven generate/execute/diagnose/repair loop for unfamiliar tasks;
- child-process environment scrubbing so generated code cannot inherit House credentials;
- offline fallback diagnostics when the House endpoint is unavailable.

The deterministic exemplar path is an interface gate, not a general Track 1 score claim.
