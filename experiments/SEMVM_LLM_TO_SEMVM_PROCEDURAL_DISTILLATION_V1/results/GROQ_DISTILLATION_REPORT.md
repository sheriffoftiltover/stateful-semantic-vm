# SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1: report

**Date:** 2026-09-28.
**Status:** DEV complete; registered gates **FAIL** for the primary TEACHER arm; **LOCKED_TEST not run** (spec §60, §72).

**Documents**
- Spec: `spec/SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1.md`
- Amendment 001: the teacher is a Modal self-hosted gpt-oss-120b (user ruling); bad-teacher suggestions are scored by detectability (user ruling).
- Log: `results/ENGINEERING_LOG.md`
- Numbers: `results/GROQ_DISTILLATION_DEV.json`

**Spend and hygiene**
- Modal spend: **$4.78** of the $20 credit (hard cap $17).
- No secrets were written anywhere (scan clean).

## Verdict
**RESULT E / F conditions present on DEV → stop before LOCKED. The mechanism result is positive; the acquisition result is negative.**

### 1. Retention (distillation proper): positive
- **Whenever a skill was acquired exactly, it was retained and reused exactly after the teacher no longer existed:**
  - the Modal app was stopped, and the endpoint returned HTTP 404;
  - all processes, including the student LLM service, were restarted;
  - the teaching transcript and examples were removed;
  - the network guard blocked all egress.
- **TEACHER arm:** 54 / 54 post-handoff invocations of exactly-learned skills correct. SCRIPTED: 78 / 78. Both controls: 86 / 86.
- Unseen arguments, new wording, restarts and stored composites were all correct.
- **Across every run:** 0 post-handoff teacher calls, a clean removal audit in 30 / 30 scenarios, student neural hash invariant, 0 optimizer steps.

### 2. Acquisition from the hosted teacher: negative at the registered thresholds
- **Frozen teacher:** gpt-oss-120b at reasoning high.
- **Scores:**
  - learned-procedure exact **.667**, against SCRIPTED lessons .917 and controls 1.0;
  - scenario exact .633;
  - **WRONG_TEACHER_ACTION_EXECUTED 12**;
  - **VERIFY_FALSE_ACCEPT 1**.
- **Failure split:** roughly half are teacher-side (wrong or over-specified lessons) and half student-side (correct lessons mis-grounded by the frozen 1.5B frontend).

### 3. The interactive teacher added no value over static registered lessons (RESULT G flavour)
- SCRIPTED beat TEACHER on every acquisition metric: first pass .667 vs .361; learned .917 vs .667.

### 4. Direct program writing by the 120B teacher is nearly as good as trace-mediated distillation
- **DIRECT_TEACHER_AST_EXACT** .639 vs **TRACE_MEDIATED** .667.
- The two paths make complementary errors: 6 procedures correct only on the direct path, 7 only through traces.
- This is unlike the 1.5B model in NL_TEACH, which managed 5.6% direct vs 86% trace-mediated.

**The claim that is supported:** SEMVM can persist, verify and reuse procedural knowledge after the teacher is permanently destroyed, exactly whenever the demonstration trace was correct.

**The claim that is not supported (spec §2):** a hosted LLM reliably teaches new procedures through dialogue to this frozen 1.5B student. The teaching channel, meaning the teacher's lesson plus the student's grounding, is the bottleneck.

## 1. System
```
curriculum goal + capability card ─► frozen gpt-oss-120b (Modal H100, vLLM, T=0) ─► EXAMPLE + STEP lines
   ─► frozen student (Qwen2.5-Coder-1.5B + NL_TEACH V1.2 compiler + PDX baseline fixes) grounds each STEP ─► validated plan ─► ONE transaction (sandbox)
   ─► student questions on any problem (rephrase / which result / another demonstration) ─► teacher answers (budgets 8 / 2 / 3)
   ─► frozen anti-unifier + evidence verifier ─► evaluator :accept iff VERIFIED ─► procedures.sqlite
HANDOFF: modal app stop (teacher destroyed, 404 verified) · learn/ removed · env scrubbed · network guard · student service restarted
REUSE: new wording + never-demonstrated arguments + restarts ─► retrieval from procedures.sqlite only ─► execution
```
- **Frozen components:**
  - parent runtime, byte-identical (`locks/PARENT_FROZEN_COMPONENTS.json`);
  - teacher checkpoint (HF revision `b5c939de…`, sha256 `0fc58fd2…`, 60.8 GiB, per-file hashes in `locks/TEACHER_WEIGHTS_MANIFEST.json`);
  - student weights (`9b3db05b…`).
- **vLLM at temperature 0 is not bitwise repeatable,** so the response cache (`teacher_responses/`, by request hash) is the experimental record (§13, §74).

## 2. DEV results (30 scenarios, 36 target skills; final run `results/dev/`)

| Gate (spec §54) | Rule | GOLD_TRACE | FORMAL | SCRIPTED | **TEACHER** |
|---|---|---|---|---|---|
| LEARNED_PROCEDURE_EXACT | ≥ .90 (controls = 1) | 1.0 | 1.0 | .917 | **.667** ✗ |
| STUDENT_TRACE_EXACT | ≥ .90 | — | — | .974 | **.700** ✗ |
| WRONG_TEACHER_ACTION_EXECUTED | = 0 | 0 | 0 | 0 | **12** ✗ |
| BAD_TEACHER_SUGGESTION_EXECUTED (detectable) | = 0 | — | — | 0 | **0** ✓ |
| BAD_PROCEDURE_ACTIVATED (legal-bad) | = 0 | — | — | 0 | **0** ✓ |
| VERIFY_FALSE_ACCEPT (41 registered probes) | = 0 | 0 | 0 | 0 | **1** ✗ |
| SOURCE_REPLAY / ROLLBACK | = 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 ✓ |
| COUNTERFACTUAL = UNSEEN_ARGUMENT = RESTART = TEACHER_DISCONNECT_REUSE | = 1 | 1.0 | 1.0 | .922 | **.767** ✗ |
| PROCEDURE_RETRIEVAL_EXACT | ≥ .95 | 1.0 | 1.0 | .917 | **.867** ✗ |
| ARGUMENT_BINDING_EXACT | ≥ .95 | 1.0 | 1.0 | 1.0 | 1.0 ✓ |
| STORED_PROCEDURE_REUSE_EXACT | = 1 | 1.0 | 1.0 | .75 | **.75** ✗ |
| DISTILLED_SKILL_EXACT | ≥ .90 | 1.0 | 1.0 | .906 | **.719** ✗ |
| POST_HANDOFF_TEACHER_CALLS | = 0 | 0 | 0 | 0 | **0** ✓ |
| INSUFFICIENT_EVIDENCE_DETECTED / SECOND_DEMO_REQUEST_EXACT | = 1 | — | — | 1 / 1 | 1 / 1 ✓ |
| STUDENT_NEURAL_HASH_INVARIANT | = 1 | 1 | 1 | 1 | 1 ✓ |
| Scenario exact | — | 1.0 | 1.0 | .900 | .633 |

- **Reuse misses equal acquisition misses.** Every reuse failure in SCRIPTED and TEACHER is an invocation of a skill that was *not* learned exactly. Given exact acquisition, reuse is 1.0 in every arm (§Verdict 1).
- **"Stored composite reuse" of .75** means the composite skill was never learned in one scenario per arm. It does not mean the stored composite was bypassed.

**Safety diagnostics** (§34, §43–§45; TEACHER / SCRIPTED)
- UNSUPPORTED_TEACHER_ACTION_BLOCKED: 3 / 3 in each.
- Detectable bad suggestions executed: 0.
- Legal-bad suggestions:
  - injected into one of two demonstrations, and they executed in the sandbox, which the ruling allows (2 / 2);
  - CROSS_DEMO_INCONSISTENCY_DETECTED 2 / 2;
  - BAD_PROCEDURE_ACTIVATED 0.
- INSUFFICIENT_EVIDENCE_DETECTED 2 / 2.
- TEACHER_REPHRASE_SUCCESS: 1 / 2 in each.

**Teacher value decomposition** (§46, §63; TEACHER, 36 targets)

| Class | Count |
|---|---|
| First-lesson success | 13 |
| Second-demonstration success | 7 |
| Rephrase success | 3 |
| Clarification success | 1 |
| Active but wrong | 7 |
| Episode failed (budget) | 5 |

- SCRIPTED: 24 first-lesson, 4 second-demonstration, 5 rephrase, 3 failed.

**By stratum** (TEACHER learned-exact)
- 1.0: S1, S2, S3, S6, S7, S10, S12, S14D.
- 0.5: S4, S9, S11, S13, S14L.
- 0.0: S5, S8, S15.

**By teaching style** (TEACHER learned-exact): A .86, B .43, C .75, D .75, E .50. Compact "B" lessons are worst, as in NL_TEACH band D.

## 3. Why the TEACHER arm fails (earliest-cause attribution, §61–§62)
Of the **12 wrong executed demonstrations**:

**Teacher-side (GT_WRONG_STEP), 6**
- The teacher adds constraints the goal does not ask for. It taught "Find the **open** calls with Bob" for "mark every call with that person closed", and "Find the **open** emails" for the topic report (twice).
- It confused skills: `count_calls_with` was taught through `person_on_call_at`, plus an extra "open" filter (3 demonstrations).

**Student-side (SG_ARGUMENT / SG_OP), 4**
- The frozen 1.5B student grounds "the open emails **to** Nina" as SELF.WHO instead of RECIPIENT (3 demonstrations).
- With WHO the evidence set is empty, so the registered dropped-filter probe VERIFIES. This is the **1 false accept**: the verifier behaved per its evidence-only contract; the evidence was vacuous because of the mis-grounding.
- The fourth case is the cascade: a composite whose component skill had failed to be learned; the student grounded the unknown skill name as RETURN.
- (Inside the teacher-side dev-018 demonstrations the student also dropped a person reference, "the open calls with that person" becoming FIND CALL STATUS=OPEN; it is counted under the earliest cause, which is teacher-side.)

**Strict-metric artefacts, 2**
- The teacher counts before closing, which is behaviourally equivalent but not the gold order. It counts as wrong under the registered strict definition.

Episode failures (5) are turn-budget exhaustion on rephrase loops ("sort them by when", unusual constructions such as "requests with who Frank and when 1").

## 4. Development history (all disclosed; nothing hidden)
1. **Pre-DEV** (engineering log #0–#2): the Modal teacher, the baseline fixes (§9.1, §9.2), cross-demonstration consistency, the SET_STATUS cue rule, and the card fix after the smoke test.
   - The local subset test fixed an open-demonstration leak and the typing of empty (NONE) results.
   - The preflight selected reasoning = high (9 / 10 vs medium 9 / 10 and low 6 / 10). Caveat: the preflight ran under the 1200-token output cap later found to truncate high-effort replies.
   - The preflight transcripts led to fixes for the per-instruction budget and the silent abandonment of unresolved steps, and to one added SORT few-shot for the student.
2. **DEV attempt 1** (`results/dev_run1_design_defect/`): the controls were NOT exact (2 false accepts, 1 miss).
   - Scenario-design defect: teacher-pool values had no matching events.
   - Fixed; LOCKED v1 archived unopened as INVALIDATED_BEFORE_RUN; LOCKED v2 generated blind with a new seed.
   - Also found: the non-interactive `modal app stop` needs `--yes`, so the teacher teardown would have failed silently. Fixed, and the disconnect metrics now require a verified teardown.
3. **DEV attempt 2** (`results/dev_run2_teacher_truncated/`): 32 / 98 teacher replies were truncated at the 1200-token cap, 29 of them empty. An injected constant swap passed the consistency check, turned STATUS into a parameter, and crashed the parent verifier: an empty counterfactual pool once both STATUS values are in the evidence, a **latent parent bug reported, not patched**. Fixes:
   - the output cap raised to 4096 tokens;
   - consistency now also requires equal constants outside the target signature;
   - learner exceptions are caught and fail the target.
4. **Final DEV** (`results/dev/`): the table above. The controls are the post-fix full runs; the code they depend on is unchanged since.

## 5. Cost and performance (final DEV, TEACHER arm)

**Teacher load**
- 78 teacher calls (none cached in the final run): 77.7K input and 65.6K output tokens.
- Per skill: 2.2 teacher turns, 1.2 demonstrations, 1.2 student questions.

**Latency**
- Teacher: 5.5 s mean per call.
- Student grounding: 3.6 s per line (4.9 local LLM calls).
- Acquisition: about 63 s per scenario, for 2 workers on an RTX 3060.

**Library and model size**
- The procedure library grows (about 49 KB and 1–3 active procedures per scenario); the student's 1.54 B parameters are unchanged.
- The teacher is external and was destroyed after acquisition.

**Totals**
- Total Modal spend for the experiment: $4.78, covering the weight download and hashing, smoke tests, the preflight, three DEV attempts and the direct-AST diagnostic.
- Efficiency: about 0.17 exactly-verified skills per 1K teacher tokens (24 / 143K), about $0.20 per exactly-verified skill.

## 6. Limits
- **Setting:** a synthetic, bounded domain of 15 families and 1 composite, on one seed and one DEV set used for engineering.
- **Student:** the frozen 1.5B student is unchanged from NL_TEACH plus small registered fixes. Its known RECIPIENT / WHO confusion is a large contributor.
- **Metric strictness:** WRONG_TEACHER_ACTION_EXECUTED is strict; behaviourally equivalent alternative programs count as wrong.
- **LOCKED_TEST v2:** blind, frozen, never opened or run (`results/GROQ_DISTILLATION_LOCKED_TEST.json`). The NL_TEACH LOCKED set is untouched.

## 7. What would change the result (not run)
1. A stronger student grounding layer, since half the failures are student-side. The obvious next arm is the 120B model as a *grounding* frontend for the teacher's own lines.
2. Tighter teacher instructions against adding unrequested constraints ("do not add filters the goal does not state").
3. A behavioural rather than syntactic definition of a wrong teacher action, registered before a new DEV.

**STOPPED.** DEV complete; gates fail; LOCKED untouched.
