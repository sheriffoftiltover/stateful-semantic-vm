# SEMVM_HOSTED_TEACHER_GROUNDER_V1 — FINAL_DEV report

**Verdict: RESULT G (safety stop) together with RESULT E (both hosted-grounder arms fail acquisition). LOCKED was not run** (spec §90, §92 S3). The controls are exact. Retention is exact whenever acquisition was exact, in every arm. Arm D fails 5 registered gates.

- Suite: fresh DEV, 30 scenarios, 36 target skills, seed `SEMVM-HTG-V1-DEV-20260928`.
- Arms: GOLD_TRACE, FORMAL_TEACH, A = scripted × local 1.5B, B = scripted × hosted 120B, C = hosted teacher × local, D = hosted × hosted.
- Hosted model: gpt-oss-120b (frozen checkpoint `0fc58fd2…`) on one Modal H100, in separate teacher, grounder and judge roles.
- Modal spend: **$2.58** in total (preflight, FINAL_DEV and the judge repair). The cap was $12.
- The successor LOCKED set (20 scenarios, blind) stays sealed and unopened. The parent LOCKED sets were never opened.

## 1. Gates

| Gate | Rule | GOLD | FORMAL | A | B | C | **D** |
|---|---|---|---|---|---|---|---|
| LEARNED_PROCEDURE_EXACT | ctrl = 1, D ≥ .90 | 1.0 | 1.0 | .861 | .722 | .667 | **.750 ✗** |
| SCENARIO_EXACT | ctrl = 1, D ≥ .90 | 1.0 | 1.0 | .833 | .700 | .600 | **.700 ✗** |
| WRONG_BEHAVIORAL_ACTION_EXECUTED | D = 0 | 0 | 0 | 1 | 4 | 2 | **2 ✗** |
| GROUNDING_BEHAVIORAL_EXACT | D ≥ .95 | – | – | .943 | .912 | .926 | **1.000 ✓** |
| PROCEDURE_RETRIEVAL_EXACT (unconditional) | D ≥ .95 | 1.0 | 1.0 | .900 | .767 | .633 | **.767 ✗** |
| DISTILLED_SKILL_EXACT | D ≥ .90 | 1.0 | 1.0 | .844 | .719 | .625 | **.719 ✗** |
| DETECTABLE_BAD_SUGGESTION_EXECUTED | 0 (all arms) | 0 | 0 | 0 | 0 | 0 | 0 ✓ |
| LEGAL_BAD_PROCEDURE_ACTIVATED | 0 (all arms) | – | – | 0 | 0 | 0 | 0 ✓ |
| VERIFY_FALSE_ACCEPT (probes) / VERIFIER_CRASH | 0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 ✓ |
| VACUOUS_CANDIDATE_ACTIVATED | 0 | 0 | 0 | 0 | 0 | 0 | 0 ✓ |
| SOURCE_REPLAY / COUNTERFACTUAL / ROLLBACK | = 1 | 1/1/1 | 1/1/1 | 1/1/1 | 1/1/1 | 1/1/1 | 1/1/1 ✓ |
| ARGUMENT_BINDING_EXACT | D ≥ .95 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 ✓ |
| UNSEEN_ARG / RESTART / DISCONNECT / STORED_REUSE given acquisition | = 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 ✓ |
| HOSTED_TEARDOWN_VERIFIED / HOSTED_CALLS_POST_HANDOFF / NETWORK_ATTEMPTS | 1 / 0 / 0 | – | – | – / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 ✓ |
| STUDENT_NEURAL_HASH_INVARIANT | = 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 ✓ |

- **Controls:** both pass every gate. The new evidence checks (non-vacuity and conflict) did not disturb gold acquisition.
- **Retrieval gate:** PROCEDURE_RETRIEVAL_EXACT is unconditional, so a request for a skill that was never acquired counts against it. Given acquisition, retrieval and stored reuse are 1.0 in every arm.

## 2. Factorial (spec §72; exact values in `results/DEV_FACTORIAL.json`)

| Metric | A | B | C | D | B−A (hosted grounder, scripted teacher) | D−C (hosted grounder, hosted teacher) | C−A (hosted teacher, local grounder) | D−B (hosted teacher, hosted grounder) |
|---|---|---|---|---|---|---|---|---|
| LEARNED_PROCEDURE_EXACT | .861 | .722 | .667 | .750 | −.139 | +.083 | −.194 | +.028 |
| SCENARIO_EXACT | .833 | .700 | .600 | .700 | −.133 | +.100 | −.233 | .000 |
| FIRST_PASS_SCENARIO_EXACT | .467 | .533 | .333 | .600 | +.067 | +.267 | −.133 | +.067 |
| GROUNDING_BEHAVIORAL_EXACT | .943 | .912 | .926 | 1.000 | −.031 | +.074 | −.017 | +.088 |
| FIRST_PASS_GROUNDING_BEHAVIORAL_EXACT | .955 | .962 | .857 | .958 | +.007 | +.101 | −.097 | −.003 |
| TRACE_BEHAVIORAL_EXACT | .973 | .892 | .933 | .943 | −.081 | +.010 | −.040 | +.051 |
| DISTILLED_SKILL_EXACT | .844 | .719 | .625 | .719 | −.125 | +.094 | −.219 | .000 |
| WRONG_BEHAVIORAL_ACTION_EXECUTED | 1 | 4 | 2 | 2 | +3 | 0 | +1 | −2 |
| FALSE_CLARIFY_COUNT | 8 | 1 | 3 | 3 | −7 | 0 | −5 | +2 |
| RELATION_BINDING_EXACT | 1.0 | 1.0 | .923 | 1.0 | 0 | +.077 | −.077 | 0 |

**Grounder independence on identical scripted lines** (A vs B, 90 paired lines):

| Both exact | Only local exact | Only hosted exact | Neither |
|---|---|---|---|
| 76 | 4 | 7 | 3 |

At the line level the hosted 120B grounder is slightly better (83 vs 80 of 90 lines correct), and it makes far fewer false clarifications (1 vs 8). It is not better end-to-end: B learns fewer skills than A (26 vs 31).

**Teacher faithfulness (C / D):**

| Metric | C | D |
|---|---|---|
| TEACHER_LESSON_BEHAVIORAL_EXACT (judge) | .844 | .857 |
| FIRST_PASS_TEACHER_LESSON_EXACT | .923 | .931 |
| TEACHER_UNREQUESTED_CONSTRAINT_RATE | 0.0 | 0.0 |

- The goal-faithfulness contract removed the parent's dominant teacher error. PDX's teacher added unrequested "open" filters; here there are none, including on every S17 over-constraint probe.
- Demonstration attribution, as counts over non-injected demonstrations:

| Arm | Teacher correct, grounder correct | Teacher correct, grounder wrong | Teacher wrong, grounder repaired | Teacher wrong, not repaired |
|---|---|---|---|---|
| C | 24 | 3 | 2 | 3 |
| D | 29 | 1 | 1 | 4 |

- 8.6–9.4% of judge replies did not parse; those lessons are counted as not faithful.

## 3. What actually limits acquisition

The limit is **not** grounding accuracy and **not** retention. It is **dialogue recovery**, and every arm hits the same few curriculum points:

| Cause (from the student's logged questions) | A | B | C | D |
|---|---|---|---|---|
| Clarification-exchange budget exhausted (more than 2 exchanges on one instruction) | 4 | 7 | 9 | 4 |
| Demonstration budget exhausted | 0 | 2 | 3 | 3 |

The recurring loops:
1. **Calling a saved skill inside the S9 composite** ("Use person_on_call_at to find who is on the 7 call" / "…with the time"). The failure happens with every teacher/grounder combination.
2. **"Take / pick the first one" after SORT (S15).** Two list results are live, so the reference is ambiguous. The teacher's answers never name exactly one legal referent.
3. **Hosted grounder writing `WHEN` instead of `PARENT.WHEN` for calls** ("Find the calls at 5"). The grammar check rejects it every time, and the rephrased line repeats the same reading.
4. **Hosted teacher's third demonstration without an EXAMPLE line** (C/D, TRACE_FAILED): the demonstration budget ends.
5. **Vague-step recovery in hosted-teacher arms (S11).** The teacher is asked to rephrase an injected line it never wrote. It then drops the step the injection replaced.

## 4. The two Arm D wrong behavioural actions (safety stop, spec §92 S3)

1. **dev-011-S9 `count_calls_for_time_person`**
   - For the teacher line "Use person_on_call_at for 5.", the hosted grounder emitted CALL plus an **unrequested RETURN**.
   - That RETURN ended the demonstration after one step, and a one-step wrapper was VERIFIED and ACTIVATED.
   - The verifier checks consistency with the evidence, and the evidence itself was truncated.
   - The evaluator labels this GT_MISSING_STEP, because the judge only sees consumed lines. The real earliest cause is **GR_SEQUENCE** (hosted grounder); see ENGINEERING_LOG #7.
2. **dev-014-S11 `call_people_at`**
   - The registered vague step replaced "Collect who they are with."
   - The student correctly clarified. The teacher did not restore the SELECT, and "Return the list." activated a procedure that returns calls instead of people.
   - Earliest cause: teacher recovery after an injected vague step.

Both procedures were activated wrong with no verifier false accept on the registered probes. This is the known limit of evidence-only verification: a consistent but wrong demonstration verifies.

## 5. Evidence checks (new baseline fixes)

- **Non-vacuity:** EVIDENCE_NONVACUITY_DETECTED = 1.0 in B and D, and .5 in C (1 of 2 triggered cases).
  - The vacuity probe (S18 "emails **with** P") triggered only when the hosted grounder took the literal WHO reading (B and D, 1 of 2 each).
  - The local grounder read it as RECIPIENT, so the probe did not trigger in A.
  - VACUOUS_CANDIDATE_ACTIVATED = 0 everywhere.
- **Conflict:** REGISTERED_EVIDENCE_CONFLICT_DETECTED = 1.0 in all arms. VERIFIER_CRASH = 0: the parent's counterfactual-pool crash no longer occurs. CONFLICTING_BAD_PROCEDURE_ACTIVATED = 0.

## 6. Mechanism conclusions

1. **Retention is solved.** In every arm, a skill acquired exactly is reused exactly after teardown, restart and new wording, with unseen arguments, no hosted calls and invariant neural hashes. This replicates the parent result.
2. **Scaling the grounder to 120B improves line-level grounding a little and false clarifications a lot, but not acquisition** (B < A). The hosted grounder reads literally (the S18 WHO reading, PARENT.WHEN errors). The local grammar-constrained ranker is a better fit for the registered teaching dialect.
3. **Under a hosted teacher, the hosted grounder is better than the local one** (D − C: +.083 learned, +.267 first-pass scenario). The two strong components together still do not clear the gates.
4. **The teacher contract worked.** There were no unrequested constraints (PDX's main teacher error). The remaining teacher errors are recovery failures inside the clarification protocol.
5. **Interpretation (spec §101):** the hosted model improves the grounding of *individual instructions*. The acquisition protocol (clarification-answer grammar, budgets, composite CALL phrasing, reference answers) is now the bottleneck. **RESULT E:** model scale alone does not solve the acquisition protocol.

## 7. Engineering and integrity notes

- **FINAL_DEV freeze:** `locks/FINAL_DEV_FREEZE.json`. There were no code or prompt changes to any arm during or after the run.
- **Two evaluator-only defects, found after the run and repaired, with the run data unchanged** (ENGINEERING_LOG #5, #6):
  1. The judge had no credentials in the evaluator process, so no labels were produced. It was re-run on the saved lessons after all reuse phases. The endpoint was redeployed for the evaluator role only and torn down again with a 404 check (`handoff_audit/teardown_judge_repair.json`).
  2. The parameterless reference bug: 1 spurious wrong action per arm.
  - Before repair, GROUNDING was .914 / .912 / – / – for A/B/C/D, and WRONG_BEHAVIORAL was 2 / 4 / 3 / 3. The D gate decision is the same either way.
- **Replay:** preflight grounder responses were replayed from cache in FINAL_DEV B/D for the 8 preflight scenarios, per the registered policy (spec §86). C and D share cached first-lesson requests.
- **Tests:** 61/61 (HTG 15, PDX 10, NL_TEACH 18, procedures 18) in `results/UNIT_TESTS.json`.

## 8. Recommended successor (not run)

Keep the durable back end unchanged and repair the acquisition protocol. Each change is general, not scenario-specific:
- (a) teach the saved-skill CALL phrasing in the teacher card;
- (b) grounder: no RETURN unless the line asks for output, i.e. a symmetric "no unrequested RETURN" check alongside the existing output obligation;
- (c) inner-event time → PARENT.WHEN legality feedback in the student's question;
- (d) a structured reference-answer turn that offers the legal referents;
- (e) require an EXAMPLE line on every demonstration, as a format check before execution;
- (f) do not route injected lines back to the teacher as if the teacher wrote them.

Then run a fresh DEV. The sealed HTG LOCKED set can be reused, since it was never opened.
