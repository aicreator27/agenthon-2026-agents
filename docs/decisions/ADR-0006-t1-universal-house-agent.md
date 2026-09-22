# ADR-0006: T1 universal House agent and execution boundary

Status: Accepted, 2026-09-22

## Decision

Track 1 uses one universal House-backed coding loop rather than a fixed taxonomy of specialist
agents. The loop extracts the task contract and local-data profile, asks the approved House model
for a plan and complete Python program, executes it, classifies execution feedback, and requests a
full replacement when repair is required. The adaptive request budget is 4, 6 or 8 calls according
to contract size and supplied-file count, with an operator cap of 12 and the official per-response
maximum of 4,000 output tokens.

The deterministic executable registry remains beside that loop. Its first entry is the official
Black-Scholes exemplar path; additional entries require formula, convention, units, edge cases and
tests rather than public-unit identifiers.

Generated programs run against staged task inputs and staged outputs. `checks/` is not staged,
House credentials and proxy variables are removed from the child environment, obvious network and
process escape routes are rejected before execution, POSIX resource limits are applied, the parent
process is marked non-dumpable, failed attempts cannot commit partial outputs, verifier-owned files
are refused, and instruction UUID canaries are rejected from deliverables.

When House is absent or exhausted, the agent emits parseable contract-floor artifacts inferred
from instruction and supplied source files. This exists to avoid crashes and schema-zero failures;
it is not represented as a correct solution.

## Evidence

- T1-focused contract tests: 10/10 pass.
- Official public-practice conformance: 87/87 output contracts, no crash or unchecked unit.
- Official exemplar checker: reward 1.0, 14 tests passed.
- Pinned qfbench2 smoke: admissible, score 1.0, no failure labels.

## Boundary

The organizer House route is not available in local development. Mock-House tests establish the
transport and state-machine contract, not model quality. Public-practice correctness and hidden-task
generalization remain official-platform measurements and must not be inferred from conformance.
