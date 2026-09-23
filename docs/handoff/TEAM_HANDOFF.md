# Team handoff — Agenthon 2026, Tracks 1 and 2

Updated: 2026-09-23. Read this first; it is the entry point for anyone joining the build.

Per-track detail lives in [HANDOFF.md](HANDOFF.md) (T2 operational state) and
[VERIFICATION_T1_STATUS.md](../../evidence/reports/VERIFICATION_T1_STATUS.md) (T1). Decisions are
in `docs/decisions/`. Nothing below should be taken on trust: every claim names the evidence that
backs it.

---

## 1. Thirty-second state

| | Track 1 (coding) | Track 2 (forecasting) |
|---|---|---|
| Image | `ghcr.io/aicreator27/agenthon-t1@sha256:d9d74a40…` | `ghcr.io/aicreator27/agenthon-t2@sha256:e3991ed0…` |
| Package public | yes, verified 2026-09-23 | yes, verified anonymously |
| Local gates | 10/10 contract, 87/87 conformance, exemplar reward 1.0 | 1/1 contract, exemplar admissible, matrix 36/36 |
| Descriptor | packed, 15/15 checks | regenerated for v0.3, **zip stale, must repack** |
| Uploaded | no | no |
| Measured quality | exemplar only; no non-exemplar public task earns reward 1 | 0.826 vs M0 on daily level, p < 0.00005 |

Both tracks are legal, runnable and packaged. Neither has been uploaded. Development closes
**2026-10-12 23:59 AoE**; the joint Final + Verification phase runs Oct 13–25.

---

## 2. Blockers

### B1 — CLEARED 2026-09-23

The T1 package was private on 2026-09-22 while its descriptor declared `image_access: "public"`.
It has since been made public and re-verified by the official method:

| check | result |
|---|---|
| anonymous GHCR token | issued |
| manifest by immutable digest | HTTP 200, single OCI manifest, 10 layers |
| config + all 10 layers, credential-free | HTTP 206 |
| GitHub packages API visibility | `public` |
| credential-free pull (empty DOCKER_CONFIG) | pass; linux/amd64, interface 2.0, verb `solve` |
| official gate against the remote digest | **reward 1.0, 14 passed, 0 failed** |

Keep the lesson, not just the outcome: the original evidence recorded
`"anonymous_digest_inspect": "pass"` from `buildx imagetools inspect`, which the official guide
says *may use your saved login and therefore cannot by itself prove anonymous access*. Always use
the token method in section 6.

### B2 — the Team Key was exposed in plaintext in a chat transcript on 2026-09-22

Ask the organizers to rotate it. Rotation changes the derived `team_id`, so **both tracks must
repack** afterwards. Until then treat `team-d97f76905fee06ab78eb89d72e5e19f4` as provisional.

Also outstanding: T2's `packaging/t2/submission.json` was regenerated against the v0.3 digest, so
the existing `packaging/t2/submission.zip` points at the superseded v0.2 image and must be
repacked.

---

## 3. What the competition actually requires

Read `upstream/track2-forecasting-public/SUBMISSION_CLI.md` and
`upstream/Agenthon2026-public/starter-packs/track2/SUBMISSION-DESCRIPTOR.md` before touching
packaging. The points that cost the most if missed:

- A submission is a **zip**, not an image reference: `submission.json` + `team-claim.json`,
  nothing else at the root.
- The image must be **linux/amd64**, carry `LABEL qfbench2.interface_version="2.0"`, and be
  **anonymously pullable by immutable digest**.
- The descriptor has exactly **12 keys** with `additionalProperties: false`. Do not add
  `house_endpoint_only` — the kit's own CLI doc recommends it and the schema rejects it.
- `team_id` is **derived, never assigned**. Omit it from the descriptor and let `pack` fill it in.
- There is **no open internet** in scoring. Agent tracks reach only the organizer House endpoint
  via `MODEL_ENDPOINT` / `MODEL_NAME` / `MODEL_TOKEN`. No vendor API exists or can be supplied.
- Upload limits: **T2 five per day, twenty total** during Development; **T1 one per day**. A held
  or cancelled upload still consumes an attempt. Local packing and validation consume nothing.
- Outputs: T2 writes exactly `forecast.parquet`, `forecast_meta.json` and a non-empty
  `forecast_rationale.md`. T1 writes deliverables to `/app/output` plus `reward.txt` and
  `reward.json`.

---

## 4. Repo map and ownership

```
core/                     shared, Agenthon-unaware: House client, seeds, provenance
tracks/t1_agenthon/       T1 adapter + universal solver
tracks/t2_agenthon/       T2 adapter + forecasting ensemble
packaging/t1|t2/          Dockerfiles, lockfiles, descriptors. NO agent intelligence here
tests/contracts/          CLI/schema/policy tests, named test_t1_* / test_t2_*
tests/backtests/t2/       rolling-origin harness + local M0 reimplementation
evidence/                 manifests (pins, digests, verdicts), runs, reports
docs/decisions/           ADRs 0001-0007
upstream/                 pinned official repos. READ ONLY
```

Track separation is by name everywhere: `agenthon-t1` vs `agenthon-t2` packages,
`publish-t1-image.yml` vs `publish-t2-image.yml`. The two tracks share only `core/`.

`scripts/test_t2.ps1` scopes discovery to `test_t2_*.py` **on purpose**. The T2 image bakes only
`core/` and `tracks/t2_agenthon/`, so T1 contract tests cannot import there. Widening the pattern
reintroduces two spurious import errors. The same applies symmetrically to T1.

---

## 5. From a fresh clone to a first scored run

### Step 0 — restore `upstream/` (nothing works before this)

`upstream/` is **not committed**, on purpose: the shared toolkit is CC BY-NC 4.0, so vendoring it
here would redistribute it under terms we do not hold. It is restored from the pinned commits in
`sources/SOURCE_REGISTRY.md`:

```powershell
.\scriptsootstrap_upstream.ps1      # Windows
```
```bash
sh scripts/bootstrap_upstream.sh       # macOS / Linux
```

It clones the three official repositories, checks out the exact pinned commit, and **verifies the
resulting HEAD against the pin** rather than trusting the checkout. Re-running is safe: a
checkout already at its pin is left untouched. Expect `BOOTSTRAP_OK`.

Skip this and everything fails in confusing ways — the verifier images `COPY` from `upstream/`,
and every smoke, matrix and backtest reads the official units from it.

### Step 1 — build, test, smoke

Docker Desktop must be running. Evidence lands in `evidence/runs/`.

```powershell
.\scriptsuild_t2.ps1 ; .\scripts	est_t2.ps1 ; .\scripts\smoke_t2.ps1
.\scriptsuild_t1.ps1 ; .\scripts	est_t1.ps1 ; .\scripts\smoke_t1.ps1
```

Green means: T2 `admissible=True labels=[]`, T1 `reward=1.0 passed=14`. That is a working local
setup; you have reproduced the current state.

### Step 2 — a wider admissibility sweep (optional but cheap)

```bash
docker run --rm -v "$REPO:/proj:ro" -v "$WORK:/run" --entrypoint python agenthon-t2-verifier:dev   /proj/scripts/regression_t2.py --project /proj --run-dir /run/sweep --n-draws 200 --seed 0 --limit 36
```

`--offset` / `--limit` take bounded batches of the 104 public units. Current evidence is 36/36.

### Step 3 — iterate on the model

The T2 backtest is two staged containers, so the model runs on its own pinned stack and the
official scorer on the toolkit's:

- **Stage A** `tests/backtests/t2/stage_forecast.py` in `agenthon-t2:dev` — produces samples.
  Mount `tracks/t2_agenthon/src` and `core/src` over `PYTHONPATH` to iterate **without
  rebuilding the image**; that is the difference between a 20-second loop and a 3-minute one.
- **Stage B** `tests/backtests/t2/stage_score.py` in `agenthon-t2-verifier:dev` — computes the
  local M0, scores with the pinned official composite, runs the significance test.

`--configs` maps arm names to `EnsembleConfig` overrides; each arm becomes a scored column, all
against the same M0 draws, so comparisons are paired. `--calibrate` adds the official reference
CLI as a control arm — run it after any harness change and check it still lands near 1.26 / 1.06.

Read section 11 before changing anything: the holdouts have been spent, and there are traps here
that have already cost real time.

### Step 4 — ship

Sections 6 and 2. Do not upload without re-running the anonymous check.

## 6. Verification to re-run before any upload

```bash
REPO=aicreator27/agenthon-t1   # or agenthon-t2
DIG=sha256:<the digest in the descriptor>
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:$REPO:pull&service=ghcr.io" \
        | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/vnd.oci.image.manifest.v1+json' \
  "https://ghcr.io/v2/$REPO/manifests/$DIG"
```

`200` is the only acceptable answer, and the token step is what makes it meaningful. Then validate
the archive with `scripts/verify_submission_zip.py`.

Packing on Windows must use the hidden prompt:

```
docker run --rm -it -v "<repo>/packaging/t2:/out" --entrypoint qfbench2 agenthon-t2-verifier:dev \
  submission pack --descriptor /out/submission.json --team-number 497 --out /out/submission.zip
```

`--team-key-file` does not work from a Windows bind mount: the toolkit refuses a key file readable
by group or others, and a bind mount cannot present mode 600.

---

## 7. Track 2 — state and how it was measured

Current defaults (`EnsembleConfig` in `tracks/t2_agenthon/src/t2_agenthon/forecaster.py`):
`history_window=300`, `block_length=31`, `bootstrap_weight=0.80`, `drift_evidence_c=25.0`.
Numeric only: it makes **no House calls** and declares `models: []`.

Scoring is a ratio against **M0**, the official text-blind baseline, so **1.0 means "no better
than a forecast that never read the text"**. M0 is fully specified in
`upstream/track2-forecasting-public/docs/M0-BASELINE.md` section 3 and reimplemented in
`tests/backtests/t2/harness.py`.

Held-out results, each population split chronologically with an embargo and opened once:

| population | v0.1 | v0.2 | v0.3 | beats M0 |
|---|---|---|---|---|
| daily level (1,168) | 0.9540 | 0.8249 | **0.8264** | 71.9% |
| log_return (411) | 1.1607 | 1.0369 | **1.0218** | 59.6% |
| monthly macro (81) | 1.3197 | 1.0756 | **0.9984** | 55.6% |

Daily level is significant at p < 0.00005 (HAC t = −13.4). Roster-mix weighted expectation is
**about 0.863** — read that as "roughly 14% better than a text-blind baseline on the public roster
mix", not as a leaderboard prediction. The official cards carry no realized outcomes, so they
cannot be scored locally at all; these are proxy populations cut from published panels.

**Harness trust.** Before believing any of the above: the harness reproduces an externally
published number. The official doc measures the shipped reference CLI at mean 1.29 / median 1.05
against the real M0; through this harness it measures **1.2573 / 1.0552** on independent
pseudo-units. Re-check this whenever the harness changes.

---

## 8. Track 1 — state

One universal House-backed loop (`contract → implement → execute → diagnose → repair → validate`)
plus a deterministic executable registry whose only entry is the official Black-Scholes exemplar.
Adaptive request budget 4/6/8, operator cap 12, against the official limit of 25 per unit.

Verified: 10/10 focused contract tests; **87/87** public-practice output contracts with zero
crashes; official exemplar checker **reward 1.0, 14 tests**; pinned `qfbench2-smoke`
`admissible=True, score=1.0`, no failure labels.

Containment for generated code: staged inputs without `checks/`, scrubbed child environment with
House credentials removed, AST deny-list for network and process escapes, POSIX resource limits,
non-dumpable parent, no partial-output commits, canary rejection. ADR-0005 calls this "an initial
containment layer, not a strong security sandbox" — treat that as accurate.

**What T1 has NOT established**, and must not be claimed: the 87/87 sweep is an *admissibility
floor*, not correctness — it proves exit and output contracts, not pass@1. No non-exemplar public
task earns reward 1. The organizer House route is unavailable locally, so live model behaviour is
unmeasured; the mock fixes only the transport and the state machine.

---

## 9. Hypotheses already tested and rejected — do not repeat

Recorded so the next iteration does not re-spend the effort. Full evidence in ADR-0004 and
ADR-0007.

| hypothesis | result |
|---|---|
| Add drift to level targets, as M0 does | rejected; zero is optimal within noise on daily |
| Rescale dispersion globally (0.90–1.10) | rejected; 1.0 optimal, so the spread is already calibrated |
| Explicit variance-ratio matching for terminal spread | rejected; forcing `σ√h` was the *worst* variant, so the bootstrap's implicit horizon scaling is informative |
| Shorten the bootstrap block on coarse/monthly panels | rejected; best gain 0.007, block of 1 lost 0.053 |
| Improve the `log_return a1h21_63` joint term | **proven irreducible** — see below |

On that last one: `variogram_score` reads a forecast only through `mean_k |x_ki − x_kj|^p`, which
on a two-cell grid is a **single scalar**, so the space can be searched exhaustively rather than
argued about. Our current dispersion is the optimum, and an oracle using the mean realized value —
the best constant predictor that exists — scores *worse* (1.517 against our 1.189), because the
ratio's denominator vanishes wherever M0's prediction happens to land on the realized draw. The
metric rewards proximity to M0 there, not accuracy.

Numeric-only T2 tuning is exhausted. The knobs `variance_ratio`, `block_length_days`, `block_min`,
`dispersion_scale`, `drift_shrink` and `return_drift_shrink` all remain in the code defaulting to
inert, as recorded negative evidence.

---

## 10. Where to go next, ranked

1. **Clear B1 and B2, repack both tracks, upload.** Everything else is worth less than a scored
   run, and no local measurement substitutes for one.
2. **T1 capability.** The largest open gap in the project: only the exemplar earns reward.
   Non-exemplar public tasks are where T1 score comes from and nothing there is measured yet.
3. **T2 gate 5, bounded House text adjustments.** Our T2 contribution from reading text is
   currently exactly zero; we beat M0 purely with a better distribution over the same numbers.
   This is the only remaining lever that addresses what the track actually measures, and it is a
   different kind of change, not another parameter.
4. **T2 populations still unmeasured for score**: F2 transfer cards, and event-selected as-of
   dates. Our pseudo-units use a mechanical 21-day grid; the official cards are chosen around
   FOMC, CPI and crisis dates.

---

## 11. Rules for iterating, and traps already paid for

**Measurement discipline (ADR-0003).** Tune on development, open a holdout **once**. The daily,
log_return and monthly holdouts have all now been opened; further tuning needs a fresh split, or
the p-value measures the tuning rather than the model. Dependence runs two ways — overlapping
windows along time, shared as-of dates across the cross-section — so significance uses a
moving-block bootstrap over blocks of as-of dates, carrying every unit at a date together. An
i.i.d. bootstrap over units would report a p-value far too small.

Traps that have already cost time here:

- **buildx attaches provenance by default.** A plain local `docker push` then publishes an OCI
  *index* containing an `unknown/unknown` attestation manifest. Build with
  `--provenance=false --sbom=false`; the scripts already do.
- **Pin the base image by digest**, or a CI rebuild is not the artifact you verified.
- **A version tag is a claim CI cannot make.** Pushing to main rebuilds the image, and the T2
  workflow used to re-tag `:v0.3.0` onto that rebuild — moving the tag off the digest that had
  actually passed the gates. The submission was unaffected (descriptors pin a digest, and the
  verified one stayed pullable), but anyone resolving the tag would have got unverified bytes.
  CI now tags `sha-<commit>` only; apply a version tag by hand after the gates pass on that exact
  digest. **T1's workflow still tags `:v0.2.0` on every qualifying push** — its owner should
  decide whether to make the same change.
- **`core/` is shared, and both publish workflows trigger on `core/**`.** A change there rebuilds
  and re-tags *both* images. Check both tracks' tags after touching it.
- **PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM**, and the toolkit's `json.load`
  rejects it outright. Write descriptor bytes with `UTF8Encoding($false)`; the script now does.
- **`pack` refuses a descriptor whose `team_id` disagrees** with the derived one. Omit the field.
- **Do not trust `imagetools inspect` for anonymity.** This is exactly how B1 slipped through.
- **Keep default configs bit-exact when refactoring.** `1.0 - 0.55` is not `0.45` in float64;
  store both weights of a pair explicitly. A refactor that silently moves numbers invalidates
  every recorded hash.
- The repo may report git "dubious ownership" (it is owned by a different local user). Use
  `git -c safe.directory=...` rather than changing global config.
- Both tracks are developed in this one repository, sometimes concurrently. Check `git log`
  before assuming the working tree is yours.
