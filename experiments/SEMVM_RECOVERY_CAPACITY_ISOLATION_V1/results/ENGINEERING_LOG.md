# RCI engineering log

## #0 Setup (2026-09-28)
- Code copied from TTP post-FINAL_DEV, including Amendment 003 (baseline, not a treatment). 40 files hash-identical (`locks/PARENT_FROZEN_COMPONENTS.json`).
- New Modal app `semvm-rci-hosted` and meter `semvm-rci-meter`. Review at $5, hard cap $7. Modal billing showed $20.14 metered this month, all covered by credits.
- Serving context raised from 16384 to 32768 so that the teacher token budgets (8192 in Stage 1, 16384 in Stage 0C) plus the dialogue fit. This is a serving parameter only (`locks/HOSTED_CHECKPOINT_MANIFEST.json` rci_serving).

## #1 Stage 0A: LOCKED parity audit → Outcome N (`locks/LOCKED_PARITY_AUDIT.json`)
- The audit used generator source and manifest metadata only.
- The HTG generator (its sha matches the old LOCKED manifest) writes a 2-value `teacher_pool` into every scenario. The 4-value pool is therefore a generation-time property, so parity fails.
- The old LOCKED stays sealed and unused. A successor LOCKED set will be generated from the same never-inspected blind template file with a new seed, and sealed before DEV-A.

## #2 Stage 0B: taxonomy frozen (`spec/FAILURE_TAXONOMY_V1.json`, `evaluator/rci_metrics.py`)
Recovery metrics, factorial arms and the ceiling diagnostic are registered in `spec/*.json`.

## #3 Stage 1 build (pre-freeze)
- **4-value teacher pool:** `PGen.world` adds 2 extra teacher values per class, each with its own witness events (call, email, request, visit). The eval pool is unchanged. Names that appear inside the fixed injection texts ("Kevin") are never drawn as new teacher values.
- **Scripted demonstration 3** uses the third pool value, so the sequence is good A, bad B rejected, good C.
- **Routing (`teacher/routing.py`):**
  - lesson kinds and recovery kinds go to separately cached roles (`initial_teacher/`, `recovery_teacher/`);
  - Arm F uses OracleRecovery with the spec §31 boundary;
  - ORACLE_RECOVERY_UNSUPPORTED aborts the demonstration.
- **Replacement slots** carry `from_recovery`, for the separate initial vs recovery grounding metrics.
- **Evaluator:** `rci_evaluate.py` (per replicate; B/E/F/D + controls; one teardown per replicate; config fingerprint), `rci_pool.py` (weighted pooled gates, floors, per-replicate safety), `rci_ceiling.py` (Stage 0C).
- **Tests:**

  | Suite | Passed |
  |---|---|
  | RCI | 13/13 |
  | TTP | 18/18 |
  | HTG | 15/15 |
  | PDX | 10/10 |
  | NL_TEACH | 18/18 |
  | procedures | 18/18 |

  The inherited `test_htg` / `test_ttp` fixtures now read `scenarios/dev_a`, and two HTG tests take the first 2 of the 4 pool people.
- Controls (GOLD_TRACE, FORMAL_TEACH) are exact on the DEV-A draft.

## #4 Stage 0C: recovery-ceiling diagnostic (`results/RECOVERY_CEILING_DIAGNOSTIC.json`; $0.55)
- **4 of 5 parent D failures recovered exactly** → GO for Stage 1.
- The 4 recoveries were all low-cost: dev-009-S9 (2 turns), dev-018-S14L (3), dev-019-S14L (7 total, low after recovery started), dev-023-S15 (6).
- dev-016-S12 (move_visit_and_parent) did not recover: HIGH cost, 13 turns, 5 demonstrations.
- **Teardown defect:** `rci_ceiling.py` called the HTG teardown helper without setting its app name. It stopped the absent `semvm-htg-hosted` (rc 1) and the RCI endpoint was still reachable (401). It was repaired at once: `semvm-rci-hosted` stopped, 404 verified. Stage 0C is acquisition-only, so no reuse ran. The script now sets the app name. `rci_evaluate.py` always set it.

## #5 Freeze (before DEV-A)
- Successor LOCKED generated (20 scenarios, seed `SEMVM-RCI-V1-LOCKED-20260928-sealed`, blind HTG templates) and sealed without inspection (`locks/LOCKED_TEST_MANIFEST.json`).
- DEV-A and DEV-B generated with the same generator sha; controls exact 30/30 on both.
- `locks/FINAL_CONFIG_FREEZE.json` records the config fingerprint. The same value must appear in both replicate summaries.

## #6 DEV-A complete
- Config fingerprint = the freeze value. Arm D passes every gate on DEV-A: learned 36/36, scenario 1.0, distilled 1.0, grounding 1.0, 0 wrong actions. Controls exact.
- DEV-B launched next with no change of any kind (spec §59).

## #7 DEV-B complete → pooled decision (`results/DEV_POOLED.json`): LOCKED_ELIGIBLE = true
- The config fingerprint is identical in DEV-A and DEV-B (`dacd7a90…`).
- **Pooled Arm D:** learned 70/72, scenario 58/60, distilled 62/64, grounding 71/71. The per-replicate floors pass, and safety and backend pass in each replicate. Controls exact.
- **LOCKED scope and pass rule, registered BEFORE running:**
  - one run of the sealed successor LOCKED set (20 scenarios);
  - arms: GOLD_TRACE, FORMAL_TEACH and D, the confirmatory arm (B/E/F are DEV attribution arms, not run on LOCKED);
  - the identical frozen config.
- **LOCKED passes iff** D reaches learned ≥ .90, scenario ≥ .90, distilled ≥ .90, grounding ≥ .95, and all safety and backend gates hold, and the controls are exact. Otherwise it fails; there is no rerun.

## #8 LOCKED (run once; `results/LOCKED_TEST.json`)
- **Arm D:** learned 23/23, scenario 20/20, distilled 21/21 (as recorded), grounding .957, 0 wrong / incomplete / unrequested-return / ambiguous-reference, completeness 1.0. Retention given acquisition 1.0. Controls exact. The config fingerprint equals the freeze.
- **Teardown verification defect:** `modal app stop` returned rc 0, but the immediate probe got **HTTP 401**: the endpoint was still answering while it stopped.
  - `htg_evaluate.teardown` treated any HTTP error as destroyed, so HOSTED_TEARDOWN_VERIFIED was recorded as 1.0. The spec requires 404 / unavailable.
  - A later probe returned 404 and the app shows `stopped`. Reuse had 0 network attempts and 0 hosted calls; credentials were scrubbed and the network guard was on.
- **Strict evaluator-only rescore** (scratch copy): HOSTED_TEARDOWN_VERIFIED = 0, so the teardown-dependent TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION = 0 and DISTILLED_SKILL_EXACT = 0.
- **Ruling:** reported as NOT a clean LOCKED pass. LOCKED is not rerun (spec §85).
- **Fix for future experiments:** `teardown` now polls until a real 404 and never accepts 401 / 403 / 5xx. No RCI run used this fixed version.
- **Total Modal spend: $3.57** (Stage 0C + DEV-A + DEV-B + LOCKED).
