# SEMVM_RECOVERY_CAPACITY_ISOLATION_V1 — report

**Verdict.**
- **Stage 1 succeeds** (RESULT A pattern on DEV). The cheap resource fixes plus the frozen transactional protocol are sufficient across **two independent DEV draws**:
  - Arm D passes every pooled gate, every per-replicate floor, and all safety and backend gates in both replicates;
  - the controls are exact.
- **LOCKED was run once and passes every acquisition, grounding, safety and retention gate.** However, the **hosted-teardown verification gate was not satisfied as registered**: the handoff probe returned HTTP 401, not 404. Under the strict reading, the teardown-dependent DISTILLED_SKILL_EXACT and TEACHER_DISCONNECT_REUSE also fail.
- **Therefore this is not a clean LOCKED pass.** The shortfall is in handoff *verification*, not in capability or safety: 0 post-handoff network attempts, 0 hosted calls, the app stopped with rc 0, and a later probe returned 404. See §6.

**Cost and integrity:**
- Modal spend is **$3.57** in total (Stage 0C $0.55; DEV-A, DEV-B and LOCKED about $1 each).
- Frozen config fingerprint: `dacd7a90…`, identical in DEV-A, DEV-B and LOCKED.
- The old HTG LOCKED set was never opened. The successor LOCKED set was sealed before DEV-A and opened only by the one registered run.

## 1. Stage 0

- **0A, LOCKED parity: Outcome N** (`locks/LOCKED_PARITY_AUDIT.json`).
  - Using generator source only, the audit found the parent generator (its sha matches the old manifest) writes a 2-value `teacher_pool` into every scenario.
  - The successor LOCKED set was generated from the same never-inspected blind templates with a new seed, and sealed before DEV-A.
- **0B, taxonomy frozen:** `spec/FAILURE_TAXONOMY_V1.json`; implementation `evaluator/rci_metrics.py`.
- **0C, recovery-ceiling diagnostic** (non-confirmatory; the 5 parent D failures; relaxed ceilings of 16k tokens, 20 turns, 5 clarifications, 5 rephrases, 5 demonstrations, a pool of 4): **4/5 recovered exactly → GO**.

| Parent failure | Recovered | Teacher turns | Cost band |
|---|---|---|---|
| composite / provider truncation (dev-009-S9) | ✓ | 2 | low |
| conflict / pool exhaustion (dev-018-S14L) | ✓ | 3 | low |
| conflict / pool exhaustion (dev-019-S14L) | ✓ | 7 | low after recovery start |
| teacher-turn budget (dev-023-S15) | ✓ | 6 | low |
| false clarification / budget (dev-016-S12, move_visit_and_parent) | ✗ | 13 (5 demos) | high |

The Stage 0C teardown targeted the wrong app name. It was repaired immediately (404 verified), and that run was acquisition-only (ENGINEERING_LOG #4).

## 2. Stage 1: Arm D pooled decision (`results/DEV_POOLED.json`)

| Gate | DEV-A | DEV-B | Pooled (weighted) | Minimum | Pass |
|---|---|---|---|---|---|
| LEARNED_PROCEDURE_EXACT ≥ .90 | 36/36 | 34/36 | **70/72 = .972** | 65 | ✓ |
| SCENARIO_EXACT ≥ .90 | 30/30 | 28/30 | **58/60 = .967** | 54 | ✓ |
| DISTILLED_SKILL_EXACT ≥ .90 | 32/32 | 30/32 | **62/64 = .969** | 58 | ✓ |
| GROUNDING_BEHAVIORAL_EXACT ≥ .95 | 1.0 | 1.0 | **71/71 = 1.0** | 68 | ✓ |
| Per-replicate floor .80 (all four) | ✓ | ✓ | | | ✓ |

**Safety, both replicates independently:**
- all 0: wrong behavioural actions, detectable-bad, legal-bad / conflicting / vacuous activations, false accepts, verifier crashes, incomplete commits, unrequested RETURN, ambiguous reference;
- completeness and committed trace are 1.0.

**Backend, both replicates:**
- source replay, counterfactual, rollback and argument binding are 1.0;
- unseen argument, restart, disconnect and stored reuse given acquisition are 1.0;
- teardown 404, 0 post-handoff calls, invariant neural hash.

**The parent TTP D had** learned .861, scenario .833, distilled .844, grounding .842, on its own DEV draw.

## 3. Factorial (all arms use the same hosted 120B grounder)

| Pooled over DEV-A + DEV-B | B (scripted / scripted) | E (scripted / hosted) | F (hosted / oracle) | D (hosted / hosted) |
|---|---|---|---|---|
| Learned | 71/72 .986 | **72/72 1.0** | 68/72 .944 | 70/72 .972 |
| Scenario | 59/60 | 60/60 | 56/60 | 58/60 |
| Distilled | 63/64 | 64/64 | 60/64 | 62/64 |
| Grounding (gate definition) | 71/78 .910 | 72/72 1.0 | 72/73 .986 | 71/71 1.0 |
| Initial-slot grounding | 213/225 .947 | 214/222 .964 | 221/228 .969 | 212/221 .959 |
| Recovery-slot grounding | **0/14** | 3/3 | 2/4 | 5/6 |
| Recovery events: resolved / total (A; B) | 4/5; 5/11 | 5/5; 7/7 | 9/10; 4/6 | 12/13; 4/5 |
| Recovery-target success | 11/12 | 11/11 | 13/14 | 14/15 |
| Wrong committed actions (A, B) | 0, 0 | 0, 0 | 0, 1 | 0, 0 |

Contrasts on learned procedure (DEV-A; DEV-B):

| Contrast | DEV-A | DEV-B |
|---|---|---|
| E − B | 0 | +.028 |
| D − F | +.056 | 0 |
| F − B | −.056 | −.028 |
| D − E | 0 | −.056 |
| Interaction | +.056 | −.028 |

**Mechanism (spec §54, §78):**
- **Hosted recovery is better than scripted recovery.**
  - B's scripted recovery replays the registered band-A rephrase, and the hosted grounder often clarifies it again. As a result, 0 of 14 recovery slots resolved, and B recovered by starting new demonstrations instead.
  - The hosted recovery teacher (E) resolved 12/12 events: recovery responses exact 1.0 in E, and 13/15 then 5/7 exact in D.
  - So scripted recovery, not hosted recovery, was the weak recovery source.
- **The hosted initial lesson costs a little.**
  - F and D lose 2–4 targets to initial-lesson content: TEACHER_INITIAL_SEMANTIC_ERROR / MISSING_CONTENT, 1 in each replicate.
  - The teacher's initial lessons are judged faithful at .92–.97.
- **The contrasts are small and do not repeat in sign across the draws.** This is not a winner ranking. With enough resources, lesson source and recovery source each move acquisition by at most about 2 targets out of 36.

**D's failure modes by replicate** (EARLIEST_CAUSE; frozen rule):
- DEV-A: none.
- DEV-B: TEACHER_INITIAL_SEMANTIC_ERROR 1; EVIDENCE_NONVACUITY_FAILURE 1.
- **No cause repeats across the draws.** Wrong-action causes: none in D. F's single wrong action was TEACHER_INITIAL_SEMANTIC_ERROR, a hosted lesson under oracle recovery.

## 4. What changed versus the parent, and why it matters

Stage 1 changed only the teacher value pool (2 → 4) and the teacher's max_tokens (4096 → 8192), with Amendment 003 as the baseline. The serving context was raised to 32k so the budgets fit.

In the parent, D's five misses were attributed to provider truncation, a 2-value pool that couldn't survive a rejected demonstration, turn budgets, and one false clarification. Both DEV draws now show:
- **0 truncations** on hosted teacher calls, down from 9 in the parent D;
- **no pool-exhaustion failures**.

The residual misses are isolated semantic events, not resource exhaustion. That is RESULT A's interpretation: *the residual parent failures were largely compatible with resource/configuration insufficiency rather than requiring a new recovery architecture.* A Stage-2 structured-clarification experiment is **not triggered** (§71): GROUNDER_FALSE_CLARIFICATION, GROUNDER_RECOVERY_SEMANTIC_ERROR and TEACHER_RECOVERY_SEMANTIC_ERROR carry no mass in D.

## 5. LOCKED (one run; `results/LOCKED_TEST.json`)

The scope and pass rule were registered before running (ENGINEERING_LOG #7): controls + D, the same frozen config, and the same thresholds as the pooled gates.

| Metric | LOCKED D |
|---|---|
| Learned procedure | 23/23 = 1.0 |
| Scenario exact | 20/20 = 1.0 |
| Grounding | 22/23 = .957 |
| Wrong / incomplete / unrequested-return / ambiguous-reference | 0 / 0 / 0 / 0 |
| Completeness, committed trace | 1.0, 1.0 |
| Unseen-argument / restart / stored-reuse / surface given acquisition | 1.0 each |
| Post-handoff hosted calls / network attempts | 0 / 0 |
| Controls | exact |
| **HOSTED_TEARDOWN_VERIFIED** | **recorded 1.0; strict 0 (probe HTTP 401)** |
| DISTILLED_SKILL_EXACT | recorded 21/21; strict 0 (requires verified teardown) |
| TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION | recorded 1.0; strict 0 |

## 6. The teardown-verification defect (honest accounting)

- **What happened.** After LOCKED acquisition, `modal app stop --yes` returned rc 0, but the immediate endpoint probe answered **HTTP 401**: the app was still draining and rejecting unauthenticated requests.
- **Why it was missed.** The evaluator's teardown helper, inherited from HTG, counted *any* HTTP error as "destroyed". It therefore recorded the teardown as verified and started reuse. The spec (§62, §80) requires the endpoint to be unavailable (404).
- **The same defect in earlier runs.** DEV-A and DEV-B happened to get a real 404, and so did every earlier experiment's handoff except this one.
- **Evidence the student did not depend on the teacher:**
  - every reuse process ran with credentials scrubbed and under the network guard: **0 connection attempts, 0 hosted calls**;
  - `modal app list` shows the app `stopped`, and a later probe returns 404;
  - all reuse results match the oracle.
- **Ruling:** by the letter of the registered rule, LOCKED's teardown-verification gate failed. LOCKED cannot be rerun (spec §85), so it is reported as not a clean pass.
- **Fix:** the helper now polls until a real 404 and never accepts 401/403/5xx. It is fixed for future experiments; no RCI run used it.

## 7. Claims

- **Supported (DEV, two independent draws):** with the frozen models, the transactional teaching protocol plus cheap resource settings acquires reusable procedures above the registered gates:
  - learned .972 and scenario .967 pooled;
  - with zero unsafe committed or activated behaviour.
- **Supported (LOCKED, behaviourally):** the full acquisition + persistence system generalizes to 20 sealed unseen scenarios: 23/23 learned, 20/20 scenarios, with exact stored reuse after restart, new wording and unseen arguments.
- **Not cleanly established:** the LOCKED *teardown verification* formality (§6).
- **Library-growth dependency (spec §70).** Continued growth of the procedure library currently depends on access to a teacher or other source capable of supplying usable demonstrations. Post-acquisition execution does not require that teacher.
- **Not claimed:** open-domain learning, self-improvement, weight-level learning, a larger-model effect.

## 8. Artifacts

| Kind | Location |
|---|---|
| Specs | `spec/` (taxonomy, recovery metrics, factorial arms, ceiling diagnostic + inherited) |
| Locks | `locks/`: `LOCKED_PARITY_AUDIT.json`, `FINAL_CONFIG_FREEZE.json`, `DEV_A_MANIFEST.json`, `DEV_B_MANIFEST.json`, `LOCKED_TEST_MANIFEST.json`, `HOSTED_CHECKPOINT_MANIFEST.json` |
| Results | `results/`: `RECOVERY_CEILING_DIAGNOSTIC.json`, `DEV_A_FACTORIAL.json`, `DEV_B_FACTORIAL.json`, `DEV_POOLED.json`, `LOCKED_TEST.json`, `UNIT_TESTS.json` (92/92 at freeze), `ENGINEERING_LOG.md` |
| Evidence directories | `initial_teacher_responses/`, `recovery_teacher_responses/`, `grounder_responses/`, `judge_responses/`, `teaching_transactions/`, `slot_ledgers/`, `recovery_events/`, `procedure_verification/`, `procedure_store_snapshots/`, `handoff_audit/`, `network_audit/` |
