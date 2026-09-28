# SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1 — FINAL_DEV report

**Verdict: RESULT D.** The protocol fixes remove the safety failures, but acquisition accuracy is still too low. **LOCKED was not run** (spec §84, stop conditions S11–S13).

- **Arm D** (hosted 120B teacher × hosted 120B grounder) passes **every safety gate** and fails **4 accuracy gates**.
- **Controls:** exact.
- **Retention given exact acquisition:** 1.0 in every arm.
- The sealed HTG LOCKED set (20 scenarios) stays unopened and remains reusable.

**Setup and cost:**
- FINAL_DEV **attempt 2** on the fresh DEV2 set: 30 scenarios, 36 targets, seed `SEMVM-TTP-V1-DEV2-20260928`.
- Frozen models are unchanged (gpt-oss-120b checkpoint `0fc58fd2…`; Qwen2.5-Coder-1.5B student).
- Modal spend for this experiment: **$3.62**. That covers the pre-freeze hosted smoke, the invalid attempt 1 and attempt 2; the cap was $9.

**Attempt 1 was invalid** (ENGINEERING_LOG #5). The hosted grounder emitted a CHILD action without its required `of` field, which passed validation and crashed one Arm D acquisition. Under spec §83 the run was archived, the defect fixed generally (a required-field check plus a no-crash guard; amendment 002), and FINAL_DEV rerun from scratch on a fresh DEV seed.

## 1. Arm D gates (attempt 2)

| Gate | Rule | D |
|---|---|---|
| WRONG_BEHAVIORAL_ACTION_EXECUTED | = 0 | **0 ✓** |
| DETECTABLE_BAD / LEGAL_BAD / CONFLICTING_BAD / VACUOUS activated | = 0 | **0 / 0 / 0 / 0 ✓** |
| VERIFY_FALSE_ACCEPT / VERIFIER_CRASH | = 0 | 0 / 0 ✓ |
| INCOMPLETE_DEMO_COMMITTED | = 0 | **0 ✓** |
| UNREQUESTED_RETURN_EXECUTED | = 0 | **0 ✓** (5 blocked) |
| AMBIGUOUS_REFERENCE_EXECUTED | = 0 | **0 ✓** |
| DEMONSTRATION_COMPLETENESS_EXACT | = 1 | **1.0 ✓** |
| GROUNDING_BEHAVIORAL_EXACT | ≥ .95 | **.842 ✗** |
| LEARNED_PROCEDURE_EXACT | ≥ .90 | **.861 ✗** (31/36) |
| SCENARIO_EXACT | ≥ .90 | **.833 ✗** |
| DISTILLED_SKILL_EXACT | ≥ .90 | **.844 ✗** |
| SOURCE_REPLAY / COUNTERFACTUAL / ROLLBACK | = 1 | 1 / 1 / 1 ✓ |
| ARGUMENT_BINDING_EXACT | ≥ .95 | 1.0 ✓ |
| UNSEEN_ARG / RESTART / DISCONNECT / STORED_REUSE given acquisition | = 1 | 1 / 1 / 1 / 1 ✓ |
| HOSTED_TEARDOWN_VERIFIED / HOSTED_CALLS_POST_HANDOFF / NETWORK_ATTEMPTS | 1 / 0 / 0 | 1 / 0 / 0 ✓ |
| STUDENT_NEURAL_HASH_INVARIANT | = 1 | 1.0 ✓ |

Both controls (GOLD_TRACE, FORMAL_TEACH) are exact: learned 1.0, scenario 1.0, no false accepts, no verifier crash.

**Against the parent HTG FINAL_DEV Arm D** (a different DEV draw, so this is indicative, not paired):

| Metric | HTG D | TTP D |
|---|---|---|
| LEARNED_PROCEDURE_EXACT | .750 | .861 |
| SCENARIO_EXACT | .700 | .833 |
| DISTILLED_SKILL_EXACT | .719 | .844 |
| WRONG_BEHAVIORAL_ACTION_EXECUTED | 2 | 0 |

## 2. The registered protocol probes: every mechanism works in D

| Probe (spec §72–§78) | D |
|---|---|
| P1 saved-skill CALL in composite: SAVED_SKILL_CALL_EXACT / dynamic reimplementation | 1.0 / 0 |
| P2 SORT + "first one": structured reference choice exact | .667 (3 events) |
| P3 PARENT.WHEN legality feedback → retry → recovery | 1.0 (2 of 2) |
| P4/S19 EXAMPLE withheld → MISSING_EXAMPLE_DETECTED before any step | 1.0 |
| P5 vague-step injection → INJECTED_STEP_RESTORED | 1.0 |
| P6/P7 unrequested RETURN executed / blocked | 0 / 5 |
| P9 legal-bad cross-demo conflict detected / activated | 1.0 / 0 |
| P10 unsupported operation executed | 0 |
| Teacher lesson faithful (judge) / unrequested-constraint rate | .974 / 0.0 |

All six parent failure classes are now handled: saved-skill CALL phrasing, "first one" after SORT, WHEN vs PARENT.WHEN, missing EXAMPLE, vague-step recovery, and an unrequested RETURN ending a demonstration. The one miss is a single reference-choice event in D, where the teacher picked a referent that led to a non-exact committed demonstration. There were zero ambiguous references executed.

## 3. Why Arm D still fails accuracy (5 of 36 targets not learned)

| Target | Earliest cause | What happened |
|---|---|---|
| dev-009-S9 composite | PROVIDER | Two demonstrations aborted on slot recovery. Then the teacher (high reasoning) truncated twice at 4096 tokens, which is PROVIDER_FAILURE under the frozen rule. |
| dev-016-S12 move_visit_and_parent | GR_FALSE_CLARIFY → budget | Slot recovery failed; the teacher restarted twice; the demonstration budget was exhausted. |
| dev-018-S14L, dev-019-S14L count_open_calls_with | EV_CONFLICT → insufficiency | The injected legal-bad demonstration was correctly rejected (conflict detected). The third demonstration reused demonstration 1's value (the pool has only 2 people), so the majority group had a non-varying parameter and was not learnable. |
| dev-023-S15 close_oldest_open_request | GT recovery → teacher-turn budget | The 10-turn budget per target ran out. |

**GROUNDING_BEHAVIORAL_EXACT = .842** counts every faithful demonstration that reached grounding, including aborted ones. The hosted grounder's recovery rate is low (SLOT_RECOVERY_SUCCESS .417 in D), so aborted-but-faithful demonstrations pull the metric down. Every *committed* D demonstration is behaviourally exact (TRACE_BEHAVIORAL_EXACT = 1.0).

The residual is therefore **recovery capacity within the budgets**:
- the hosted grounder's clarifications on lines the teacher then cannot rephrase into something groundable;
- teacher truncation at high reasoning;
- the two-value teacher pool interacting with the legal-bad probe.

## 4. Factorial (attempt 2; `results/DEV_FACTORIAL.json`)

| Metric | A | B | C | D | B−A | D−C | C−A | D−B |
|---|---|---|---|---|---|---|---|---|
| LEARNED_PROCEDURE_EXACT | .917 | .944 | .778 | .861 | +.028 | +.083 | −.139 | −.083 |
| SCENARIO_EXACT | .900 | .933 | .733 | .833 | +.033 | +.100 | −.167 | −.100 |
| FIRST_PASS_SCENARIO_EXACT | .567 | .567 | .533 | .600 | 0 | +.067 | −.033 | +.033 |
| GROUNDING_BEHAVIORAL_EXACT | .917 | .897 | .886 | .842 | −.019 | −.044 | −.031 | −.055 |
| TRACE_BEHAVIORAL_EXACT (committed) | .974 | 1.0 | .854 | 1.0 | +.026 | +.146 | −.121 | 0 |
| DEMONSTRATION_COMPLETENESS_EXACT | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 0 |
| DISTILLED_SKILL_EXACT | .906 | .938 | .750 | .844 | +.031 | +.094 | −.156 | −.094 |
| WRONG_BEHAVIORAL_ACTION_EXECUTED | 1 | 0 | 6 | 0 | −1 | −6 | +5 | 0 |
| SLOT_RECOVERY_SUCCESS | .769 | .636 | .846 | .417 | −.133 | −.430 | +.077 | −.220 |

**Arm B passes every accuracy threshold that D is held to, and all of its safety gates.** B is scripted teacher × hosted grounder. Its values: learned .944, scenario .933, distilled .938, 0 wrong actions, completeness 1.0. B's accuracy thresholds are descriptive, not gates.

With the transactional protocol, the hosted grounder is therefore sufficient to acquire from registered lessons. Hosted-teacher dialogue (D − B: −.083 learned) now costs accuracy, through recovery loops and budgets. The local grounder under a hosted teacher (C) is the weakest arm and executes the most wrong actions (6 committed, all safely contained except the defect below).

## 5. A controller defect found after the run (amendment 003; affects A and C only)

- **The defect:** the two-demonstration rule counted demonstration *indices*, not *committed* demonstrations.
- **Effect:** in dev-019-S14L, demonstration 1 was aborted, which by design yields zero evidence. The evaluator-injected DROPPED_FILTER demonstration 2 was then learned **alone**. That produced one LEGAL_BAD_PROCEDURE_ACTIVATED in A and one in C.
- **Scope:** it occurred only there. **No Arm D target is affected.** Every ACTIVE target was checked for having the required number of committed demonstrations.
- **Status:** under spec §83, the A/C safety results of attempt 2 are not a valid measurement of the protocol. The fix (count committed evidence, with a unit test; 18/18) is implemented and **not yet run**.

## 6. Interpretation (spec §87–§88)

- **What the result supports.** Treating teaching as a transaction removes every safety failure the parent saw in Arm D:
  - no incomplete commits;
  - no premature or unrequested RETURN;
  - no unnamed CALLs;
  - no ambiguous references executed;
  - injected steps are restored;
  - missing EXAMPLEs are requested before execution.

  It does this while the durable backend stays exact. It also raises acquisition substantially: parent HTG D learned .750, TTP D learned .861, on a different DEV draw.
- **What it does not support.** The claim that protocol alone gets the hosted × hosted stack to the ≥ .90 acquisition gates. The residual is dialogue recovery under finite budgets. Every committed D demonstration is behaviourally exact.
- **Falsification criterion (§88).** The protocol is now structurally exact (completeness 1.0, all probe mechanisms working), and the remaining failures are recovery and budget limits, not protocol holes. So "the 120B model is too small" is neither confirmed nor excluded. The B result (hosted grounder + registered lessons ≥ .93) shows the grounder is not the limit when lessons are well formed.

## 7. Options (not run; the user decides)

1. **Attempt 3** with amendment 003 on a fresh DEV seed. Estimated ~3 h and ~$2.
   - Expected to clear the A/C defect.
   - D would still likely fall short of .90 unless the recovery residuals change: larger teacher pool, teacher max_tokens (a registered setting change), or the per-target turn budget.
2. **A successor spec** targeting recovery capacity:
   - a 3-value teacher pool;
   - a registered teacher token budget above 4096 at high reasoning;
   - grounder-clarification questions forwarded in structured form.
3. **Stop here** and keep the finding. With the transactional protocol, hosted grounding plus registered lessons (B) is sufficient; hosted-teacher dialogue remains the bottleneck.

## 8. Integrity

- **Freeze and tests:** `locks/FINAL_DEV_FREEZE.json` (attempt 2). Unit tests at freeze are 78/78: TTP 17, HTG 15, PDX 10, NL_TEACH 18, procedures 18.
- **Judge:** the preflight passed, reaching the endpoint, parsing the label and writing the cache. FINAL_DEV's preflight request was byte-identical to the pre-freeze smoke, so it was served from cache.
- **LOCKED:** the sealed set was copied by `cp` and verified by hash only (`locks/LOCKED_TEST_MANIFEST.json`). It was never opened, and the generator refuses to regenerate it.
- **Secrets:** no secrets in any artifact (scan in `results/ARTIFACT_MANIFEST.json`).
- **Archives:** attempt 1 is at `results/archive/final_dev_attempt1_INVALID` (with `ACQUISITION_DIAGNOSTIC.json`); its DEV set is at `scenarios/archive/dev_attempt1`.
