# SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1: report

- **Date:** 2026-09-27.
- **Status:** DEV complete (V1 → V1.1 → V1.2, final). Registered gates **FAIL**. **LOCKED_TEST not run**, per the user's ruling and spec §89.
- **Specs:** `spec/SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1.md` and Amendments 001 (registered design), 002 (V1.1) and 003 (V1.2).
- **Log:** `results/ENGINEERING_LOG.md`.
- **Numbers:** `results/NL_TEACH_DEV.json`.

## Verdict

**Outcome: RESULT B with a hard safety stop (RESULT E / F conditions present on DEV).**
- Procedure learning stays sound: GOLD_TRACE and FORMAL_TEACH are exact on all 30 DEV scenarios, every metric 1.0, 0 false accepts.
- Natural-language grounding by the frozen Qwen2.5-Coder-1.5B frontend is the bottleneck.
- The deterministic layer between the frontend and execution cut unsafe executions from 9 (V1) to 1 (V1.2) but did not reach 0.
- The final DEV also has one verifier "false accept". It was caused upstream, by a lost demonstration, not by the verifier (§5).
- LOCKED_TEST (20 scenarios, templates written blind by an independent agent) stays untouched and can still be used.

**What the evidence supports**

**1. Trace-mediated learning beats direct program synthesis by a wide margin (DEV, 36 procedures).**

| Path | Procedures exact |
|---|---|
| Same 1.5B model writing the procedure directly from the teaching text (DIRECT_AST) | **5.6%** |
| NL → grounded trace → frozen anti-unifier (trace-mediated) | **86.1%** |

- Most direct proposals don't parse: invented ops such as `FIND_CALL`, wrong relations, dropped steps.

**2. The frozen 1.5B model grounds single-clause instructions well.**
- Bands A and C (direct imperatives, anaphora) are **1.0** at the utterance level; band B (lexical paraphrase) is .93.
- It fails at composing several clauses:
  - band D (compact multi-action) .50 in V1 → .65 in V1.2;
  - band E (constant/variable contrast) .77.

**3. Deterministic invariants catch many LLM errors before execution, but not all.**
- Final DEV: the LLM's raw proposal was wrong for 22 utterances. 16 were blocked or repaired; 1 was executed.
- The rest became clarifications.

**The claim that is not supported:** "a user can teach procedures in natural language with a frozen small LM grounding the instructions" at the registered thresholds.

## 1. System (only the teaching ingress is new; the parent runtime is byte-identical, `locks/PARENT_FROZEN_COMPONENTS.json`)

```
NL instruction ─► V1.1/1.2 clause compiler: candidate segmentation (strong / weak connectors)
   ─► per clause: frozen 1.5B ranks LEGAL typed options (grammar-constrained beam, schema spec/NL_TEACH_ACTION_SCHEMA.json)
   ─► combined plan ─► deterministic checks: static validation, named event search, reference grammar R0-R4, antecedent validity,
      value / procedure coverage, dead-pure-result liveness, output obligation, RETURN-last, clause coverage, margin (1.0 nats)
   ─► OK: ONE transaction │ CLARIFY │ UNSUPPORTED_TEACHING_INPUT
successful steps ─► trace ─► FROZEN parent anti-unifier ─► FROZEN verifier ─► explicit :accept ─► procedures.sqlite
```
- The LLM never:
  - emits an op outside the inventory, or a value that is not in the instruction;
  - mutates state, activates or verifies;
  - sees the taught procedure's name, hints or gold.
- Procedure abstraction is deterministic only (Amendment 001 A2).
- Teaching sandbox: the world is restored after each demonstration.
- An unhinted one-shot demonstration gets `REQUIRE_SECOND_DEMONSTRATION`.
- Corrections (`No, …`), `:undo`, and structured REFERENCE clarifications are supported.

## 2. Results across the three DEV iterations (NL_TEACH, 30 scenarios, 136 utterances)

| Gate (spec §59) | Rule | V1 | V1.1 | **V1.2 (final)** |
|---|---|---|---|---|
| WRONG_LLM_ACTION_EXECUTED | = 0 | 9 | 2 | **1** ✗ |
| VERIFY_FALSE_ACCEPT | = 0 | 0 | 0 | **1** ✗ (see §5) |
| TEACH_TRACE_EXACT (first pass) | ≥ .90 | .614 | .727 | **.705** ✗ |
| LEARNED_PROCEDURE_EXACT | ≥ .90 | .857 | .944 | **.914** ✓ |
| ACTION_OP_EXACT | ≥ .95 | .869 | .923 | **.908** ✗ |
| ACTION_ARGUMENT_EXACT_AFTER_REPAIR | ≥ .95 | .823 | .885 | **.862** ✗ |
| SOURCE_REPLAY_EXACT | = 1 | 1.0 | 1.0 | **1.0** ✓ |
| COUNTERFACTUAL_EXACT (unseen arguments) | = 1 | .813 | .896 | **.854** ✗ |
| ROLLBACK_EXACT | = 1 | 1.0 | 1.0 | **1.0** ✓ |
| PROCEDURE_RETRIEVAL_EXACT | ≥ .95 | .938 | .938 | **.906** ✗ |
| ARGUMENT_BINDING_EXACT | ≥ .95 | .933 | 1.0 | **.966** ✓ |
| RESTART_PROCEDURE_EXACT | = 1 | .804 | .891 | **.848** ✗ |
| STORED_PROCEDURE_REUSE_EXACT | = 1 | .75 | .75 | **.75** ✗ |
| NL_TEACH_SCENARIO_EXACT (ASSISTED) | ≥ .90 | .733 | .933 | **.867** ✗ |
| NL_TEACH_SCENARIO_EXACT_FIRST_PASS | — | .600 | .667 | .667 |

**Controls (V1.2 code).** GOLD_TRACE and FORMAL_TEACH: every metric 1.0. This covers teaching-trace, learned, counterfactual, restart, retrieval, composition and stored-reuse exactness, with VERIFY_FALSE_ACCEPT 0. Spec gate S1 passes.

**Other V1.2 metrics**

*Grounding*
- ACTION_ARGUMENT_EXACT_RAW: .846.
- ACTION_SEQUENCE_EXACT (multi-action utterances): .389, up from .167 in V1.
- REFERENCE_BINDING_EXACT: .964.

*Clarification, correction and failure handling*
- CLARIFICATION_RECALL: 1.0. The designed ambiguous "Return them." clarified every time, and every designed answer resolved (CLARIFICATION_SUCCESS 1.0).
- CLARIFICATION_PRECISION: .125, meaning most clarifications were unnecessary. There were 17 first-pass false clarifications.
- UNSUPPORTED_REJECTION_EXACT: 1.0.
- POST_CORRECTION_TRACE_EXACT: 1.0.
- TEACHING_ROLLBACK_EXACT: 1.0. Failing teaching steps left the state unchanged and never entered the evidence.
- NEGATIVE_CASE_SAFE: 1.0.

*Plan compiler*
- CLAUSE_COVERAGE: 1.0 over 151 input clauses.
- SEGMENTATION_DISAGREE: 1.
- Dataflow blocks: DEAD_PURE_RESULT 3, USE_BEFORE_DEFINITION 3.

**Frontend contribution (spec §37, first pass, 130 executable utterances)**

| Category | Count |
|---|---|
| A: raw LLM proposal correct | 106 |
| B: deterministic repair made it correct | 6 |
| C: typed fallback | 0 (none exists in V1) |
| D: deterministic alias path | 0 |
| E: clarification needed | 8 |
| F: failure | 10 |

**Bands, per utterance (V1.2)**

| Band | Exact |
|---|---|
| A, direct imperative | 1.0 |
| B, lexical paraphrase | .927 |
| C, local anaphora | 1.0 |
| D, compact multi-action | .647 |
| E, constant/variable contrast | .769 |

**Strata (scenario exact, V1.2)**
- **NAMED vs OPAQUE:** .77 vs 1.0. Grounding is identical by construction, since the prompt never contains the name. OPAQUE procedures appear only in single-procedure scenarios, where retrieval is decided by the only candidate (Amendment 001 A7).
- **HINTED vs UNHINTED:** .84 vs .60.

**Categories (V1.2)**
- T1–T6, T8, T9, T12 and T13: 1.0.
- **T7 (constant preservation with deliberately bad candidates): 0.0.** Both of its scenarios fail. This is a regression from V1.1, where it was 1.0.
- **T10 and T11 (composition): .5 each.** A mis-grounded or clarified demonstration of a component procedure spoils the composite built on top of it. This accounts for most of the restart, counterfactual and stored-reuse misses.

## 3. What changed between iterations
All changes are general and deterministic, logged in the engineering log, and kept for LOCKED. None touches the LLM weights or the parent runtime.

**Before DEV** (log entries #0–#3)
- Free generation replaced by grammar-constrained ranking of legal options.
- Exact tokenization-boundary scoring.
- Few-shot rebalancing.
- Collapse of equivalent canonical outcomes before the margin test.
- Status options only when a status cue word is present.
- Coverage treated as a candidate outcome rather than a decoding constraint.
- RETURN must be the last action.
- The first liveness rule and R4.
- **Teacher-forced grounding probe:** 93 → 110 → 120 → 119 of 136 utterances.

**V1.1** (Amendment 002, after the first full DEV run: 9 unsafe executions)
- An explicit multi-clause plan compiler: candidate segmentation into non-executable plan fragments, cross-clause dataflow, and whole-plan validation with equal authority on every path.
- Clause coverage.
- Segmentation-disagreement CLARIFY.
- Structured REFERENCE-only pending clarification, which stops cascades.

**V1.2** (Amendment 003, the final iteration)
- An event search must name its event type.
- Antecedent validity: an anaphor needs an existing result.
- Output obligation: an output request needs a terminal RETURN of the requested kind.
- **Effect:** unsafe executions 2 → 1. T7 regressed and the assisted scenario score fell from .933 to .867. So V1.2 is not a strict improvement over V1.1.

## 4. The remaining unsafe execution (V1.2)
The instruction was "Among the emails to Sam, find only the open ones and close each of them."
1. The clause-wise reading failed, because the second clause false-clarified.
2. By the V1.1 rule, a weak `and` that does not produce valid clauses is not treated as a clause boundary.
3. The whole utterance was therefore checked as one clause. The model grounded it as FIND (open), COUNT, RETURN, which passes every invariant, and it executed.

This is the weak-boundary fallback the review had flagged. Its guard, clause coverage computed from the strong segmentation only, is too permissive. A stricter policy, where a failed weak split means CLARIFY rather than a single-clause reading, is the obvious next invariant. It was **not** applied, because V1.2 was declared the final iteration.

## 5. The VERIFY_FALSE_ACCEPT (V1.2, dev-016-T7)
- **What happened:** the deliberately bad "frozen value" candidate (no parameters, constant `Sam`) was VERIFIED.
  1. The second unhinted demonstration false-clarified twice (first pass and the one rescue) and never executed, so only ONE example trace was recorded.
  2. With one unhinted trace, the evidence interface has no varying slot.
  3. The parent's evidence-only verifier correctly finds that the constant candidate matches all the evidence. That is its frozen contract.
- **The gap is in the NL layer:** the `REQUIRE_SECOND_DEMONSTRATION` rule is applied at `:endteach` but not at `:learn` / `:propose` over a single recorded unhinted example.
- **Formally it still counts:** under spec §82 RESULT F this is a false accept, and it is reported as one.
- **Comparison:** the parent's unit and verifier tests, and both controls, have 0 false accepts.

## 6. Language-model usefulness (spec §80)
- **What the frozen 1.5B does well:** it is load-bearing for choosing ops, types, relations, status, references and procedure calls within a clause. It produced 106 of 130 first-pass groundings correctly without repair.
- **Where it fails:**
  - multi-clause composition: it drops a clause or adds a spurious action;
  - "tell me how many" style output requests;
  - over-cautious low-margin decisions: 17 first-pass false clarifications.
- **What the deterministic compiler does:** it catches the composition errors (dataflow, clause, antecedent and output checks). It cannot supply missing semantic fidelity.
- **Changing MARGIN (1.0 nats) was deliberately rejected:** a lower margin would trade conservative clarifications for more wrong executions.

## 7. Cost, performance and model size (V1.2 DEV)

**NL_TEACH vs FORMAL_TEACH (spec §81)**

| | FORMAL_TEACH | NL_TEACH |
|---|---|---|
| Teaching trace exact | 1.0 | .705 |
| Learned procedure exact | 1.0 | .914 |
| Counterfactual exact | 1.0 | .854 |
| Restart exact | 1.0 | .848 |
| Retrieval exact | 1.0 | .906 |
| Composition exact | 1.0 | .50 |
| Scenario exact (assisted) | 1.0 | .867 |
| Teaching-segment wall time (mean) | 13.2 s | 36.5 s |

**LLM cost**
- Grounding: about 6.3 LLM calls per NL utterance, 4.3 s mean per utterance on an RTX 3060 fp16.
- The two runs made 1,186 grounding calls and 62 retrieval calls in total.

**Verification, retrieval and execution**
- Verification: 0.66 s per candidate.
- Retrieval plus execution: 1.96 s per request. Stored-procedure execution: 0.10 s.

**Model and library size**
- **Model:** constant at 1.54 B parameters, frozen, no optimizer. The byte-level weight hash is identical across all service instances and restarts.
- **Library:** about 50 KB mean; up to 3 active procedures; dependency depth 1.

## 8. Limits and caveats
- **Scope:** a synthetic, bounded domain with 13 families plus one composite. Teaching surfaces are templated (DEV templates written by the experimenter).
- **Seeds:** one seed.
- **Hardware:** RTX 3060 fp16. Instances on the RTX 2060 give slightly different fp16 scores, so the final runs were pinned to the 3060.
- **DEV reuse:** DEV was used for three engineering iterations, so the DEV numbers are optimistic for V1.1 and V1.2.
- **Simulated user:** the ASSISTED protocol's user knows the gold intent. Its rescues are counted, and first-pass figures are reported next to them.
- **LOCKED_TEST:** frozen, never opened or run. Manifest hash is in `results/NL_TEACH_LOCKED_TEST.json`.

## 9. What would change the result (not run)
1. A failed weak-boundary split means CLARIFY, not a single-clause reading (closes the remaining unsafe path).
2. `REQUIRE_SECOND_DEMONSTRATION` at `:learn` / `:propose` over a single unhinted recorded example (closes the false-accept path).
3. A stronger frontend model, e.g. a larger or hosted instruction model, behind the same compiler. It would target the multi-clause and false-clarification failures, which are the model's.

**STOPPED.** DEV complete; gates fail; LOCKED untouched.
