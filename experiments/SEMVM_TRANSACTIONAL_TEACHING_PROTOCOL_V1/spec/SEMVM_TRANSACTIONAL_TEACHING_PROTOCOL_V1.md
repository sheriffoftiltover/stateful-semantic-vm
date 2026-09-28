# SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1

**Project:** Stateful Semantic VM — Transactional Teaching / Demonstration Completeness  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Parent experiment:** `SEMVM_HOSTED_TEACHER_GROUNDER_V1`  
**Primary scientific target:** acquisition protocol correctness  
**Models:** unchanged from parent  
**Hosted checkpoint:** frozen `gpt-oss-120b` on Modal H100  
**Local baseline:** frozen `Qwen2.5-Coder-1.5B` grounder  
**Durable backend:** frozen  
**Primary confirmatory arm:** hosted teacher × hosted grounder  
**LOCKED policy:** the still-sealed 20-scenario HTG LOCKED set may be reused only if this fresh DEV passes all registered gates

---

# 0. Executive summary

The parent `SEMVM_HOSTED_TEACHER_GROUNDER_V1` stopped at FINAL_DEV.

Its primary hosted-teacher × hosted-grounder arm failed the registered gates despite:

```text
GROUNDING_BEHAVIORAL_EXACT = 1.000
```

and despite exact post-handoff retention for every skill that had been learned exactly.

The parent therefore localized the remaining acquisition bottleneck away from:

```text
basic line-level grounding
procedure persistence
post-restart reuse
argument binding
teacher teardown
network isolation
neural-weight invariance
vacuous-evidence safety
evidence-conflict safety
```

and toward:

```text
multi-turn acquisition protocol
clarification recovery
demonstration completeness
premature termination
missing demonstration metadata
saved-procedure call phrasing
typed reference recovery
```

The recurring parent failures were:

```text
1. Saved-skill CALL phrasing inside a composite.
2. "Take / pick the first one" after SORT when multiple lists are live.
3. Inner-event time grounded as WHEN instead of PARENT.WHEN.
4. Hosted-teacher demonstrations missing EXAMPLE metadata.
5. Vague-step recovery dropping the step that the diagnostic replaced.
6. Hosted grounder adding an unrequested RETURN and ending a demonstration early.
```

Two unsafe procedures became ACTIVE because the verifier received internally consistent but incomplete evidence.

This successor tests a specific hypothesis:

> If the teaching dialogue is treated as a transactional structured protocol, with explicit demonstration slots, explicit recovery state, no premature terminal actions, typed clarification answers, and completeness checks before evidence admission, can the same frozen models acquire procedures reliably enough to pass the original safety and accuracy gates?

No model is enlarged.

No neural weights change.

No downstream procedure-learning mechanism is strengthened.

The experiment changes only the acquisition protocol.

---

# 1. Main research question

Can a deterministic transactional controller convert imperfect teacher/grounder dialogue into complete, safe teaching evidence without requiring a larger model?

Target pipeline:

```text
teacher lesson
      ↓
grounded instruction
      ↓
transactional teaching controller
      ↓
clarification / repair until slot complete
      ↓
demonstration completeness check
      ↓
single committed demonstration trace
      ↓
frozen anti-unifier
      ↓
frozen verifier
      ↓
persistent procedure
```

---

# 2. Primary hypothesis

The primary hypothesis is:

> The dominant remaining acquisition failures are protocol failures rather than model-capacity failures.

Operationally, this is supported if the primary hosted × hosted arm reaches all registered acquisition and safety gates using:

```text
same frozen 120B checkpoint
same frozen local student
same procedure learner
same verifier
same store
same VM
same ontology
same curriculum semantics
```

with only the preregistered transactional teaching changes.

---

# 3. Strongest permitted claim

If all DEV gates pass and the sealed LOCKED set passes once:

> In the registered bounded Semantic VM domain, transactional teaching controls are sufficient for a frozen hosted teacher/grounder stack to acquire reusable procedures reliably, while the durable capability remains in the external SEMVM procedure system after the hosted model is removed.

This does **not** establish:

```text
open-domain autonomous learning
general self-improvement
arbitrary natural-language pedagogy
arbitrary tool invention
new primitive invention
weight-level learning
```

---

# 4. Parent result imported as frozen evidence

The parent FINAL_DEV is historical and must not be rewritten.

Primary hosted × hosted arm:

```text
LEARNED_PROCEDURE_EXACT           .750
SCENARIO_EXACT                    .700
GROUNDING_BEHAVIORAL_EXACT       1.000
WRONG_BEHAVIORAL_ACTION_EXECUTED  2
PROCEDURE_RETRIEVAL_EXACT         .767
DISTILLED_SKILL_EXACT             .719
```

Controls were exact.

Given exact acquisition:

```text
UNSEEN_ARGUMENT_EXACT       1.0
RESTART_EXACT               1.0
TEACHER_DISCONNECT_REUSE    1.0
STORED_PROCEDURE_REUSE      1.0
SURFACE_GENERALIZATION      1.0
```

These parent values remain unchanged.

---

# 5. Parent mechanism conclusion

The parent established:

```text
correct evidence
    ↓
correct procedure
    ↓
durable storage
    ↓
teacher teardown
    ↓
restart
    ↓
new wording + unseen arguments
    ↓
exact reuse
```

This successor therefore treats persistence/reuse as a frozen backend.

The experiment is about producing **correct evidence**.

---

# 6. What this experiment changes

Only the acquisition layer changes.

New components:

```text
TRANSACTIONAL_TEACHING_CONTROLLER
DEMONSTRATION_SLOT_LEDGER
STRUCTURED_CLARIFICATION_ANSWER
NO_UNREQUESTED_RETURN rule
PARENT.WHEN legality feedback
EXAMPLE-before-execution rule
INJECTED_STEP_PROVENANCE rule
SAVED_SKILL_CALL teaching contract
DEMONSTRATION_COMPLETENESS_CHECK
```

Everything else remains frozen unless explicitly listed.

---

# 7. What remains frozen

Freeze from the parent:

```text
world schema
ontology
primitive inventory
procedure AST
anti-unifier
candidate canonicalization
procedure store
frozen verifier
state perturbation
negative probes
rollback testing
retrieval
argument binding
stored-procedure preference
composition semantics
VM
world-state store
post-handoff evaluator
network guard
teardown procedure
student model weights
hosted model checkpoint
```

Also retain:

```text
evidence non-vacuity precheck
evidence-conflict precheck
behavioral equivalence evaluator
teacher goal-faithfulness contract
```

---

# 8. Primary experimental arm

The confirmatory arm is unchanged in model composition:

```text
HOSTED 120B TEACHER
        ×
HOSTED 120B GROUNDER
```

The teacher and grounder remain role-separated:

```text
independent prompts
independent requests
independent caches
no hidden-context sharing
visible lesson text is the only bridge
```

---

# 9. Diagnostic comparison arms

Retain the four-arm factorial for localization:

```text
A = scripted teacher × local 1.5B grounder
B = scripted teacher × hosted 120B grounder
C = hosted 120B teacher × local 1.5B grounder
D = hosted 120B teacher × hosted 120B grounder
```

Arm D remains the confirmatory arm.

A/B/C remain attribution arms.

---

# 10. Sanity controls

Retain:

```text
GOLD_TRACE
FORMAL_TEACH
```

Required:

```text
LEARNED_PROCEDURE_EXACT = 1.0
SCENARIO_EXACT = 1.0
VERIFY_FALSE_ACCEPT = 0
VERIFIER_CRASH = 0
```

Any control regression invalidates the run.

---

# 11. Transactional teaching model

A teaching demonstration is no longer an informal stream of utterances.

It is an explicit transaction:

```text
DEMO_OPEN
    ↓
EXAMPLE_BOUND
    ↓
SLOT_1
SLOT_2
...
SLOT_N
    ↓
ALL_REQUIRED_SLOTS_RESOLVED
    ↓
DEMO_READY
    ↓
COMMIT
    ↓
trace becomes learning evidence
```

Until `COMMIT`:

```text
no partial demonstration is learning evidence
```

---

# 12. Demonstration states

Every demonstration has exactly one state:

```text
NEW
OPEN
WAITING_FOR_EXAMPLE
WAITING_FOR_GROUNDING
WAITING_FOR_CLARIFICATION
WAITING_FOR_REPHRASE
READY_TO_COMMIT
COMMITTED
ABORTED
```

Illegal transitions are runtime errors and must not silently continue.

---

# 13. Demonstration slot ledger

Each intended teaching step is represented as a slot:

```json
{
  "slot_id": "demo2-step3",
  "source": "TEACHER",
  "status": "PENDING",
  "original_text": "...",
  "replacement_for": null,
  "grounded_plan": null,
  "clarification_count": 0,
  "required": true
}
```

Allowed slot states:

```text
PENDING
GROUNDED
CLARIFYING
REPLACED
RESOLVED
UNSUPPORTED
ABANDONED
```

A required slot must be:

```text
RESOLVED
```

before the demonstration may commit.

---

# 14. Demonstration completeness contract

Before `COMMIT`, all must hold:

```text
EXAMPLE binding exists
all required slots exist
all required slots are RESOLVED
no pending clarification exists
no unresolved replacement exists
no step disappeared during recovery
no terminal action occurred before all required slots resolved
no forbidden hidden fallback occurred
trace is non-empty
trace passed deterministic validation
transaction executed successfully
```

Otherwise:

```text
DEMONSTRATION_INCOMPLETE
```

and the trace is not learning evidence.

---

# 15. Completeness metrics

Report:

```text
DEMONSTRATION_COMPLETENESS_EXACT
INCOMPLETE_DEMO_BLOCKED
INCOMPLETE_DEMO_COMMITTED
MISSING_SLOT_DETECTED
PENDING_CLARIFICATION_AT_COMMIT
MISSING_EXAMPLE_DETECTED
PREMATURE_TERMINATION_DETECTED
```

Hard requirements:

```text
INCOMPLETE_DEMO_COMMITTED = 0
PENDING_CLARIFICATION_AT_COMMIT = 0
```

---

# 16. No unrequested RETURN

A `RETURN` is terminal.

Therefore the grounder may emit RETURN only when one of the following is true:

```text
the current instruction explicitly asks to return/output/report/show/tell
or
the registered procedure target requires a terminal return at this slot
and that obligation is explicitly exposed to the grounder
```

Forbidden:

```text
adding RETURN merely because the grounder thinks the demonstration is complete
```

---

# 17. RETURN gate

Before accepting a grounded line containing RETURN:

```text
RETURN_OBLIGATION(line, slot, target) == true
```

Otherwise:

```text
UNREQUESTED_RETURN
→ reject plan
→ ask for re-grounding / clarification
```

Metric:

```text
UNREQUESTED_RETURN_BLOCKED
```

Hard requirement:

```text
UNREQUESTED_RETURN_EXECUTED = 0
```

---

# 18. Premature termination rule

Even a valid RETURN may not terminate the demonstration while unresolved required slots remain.

If:

```text
RETURN present
AND unresolved_required_slots > 0
```

then:

```text
PREMATURE_TERMINAL_ACTION
```

Do not execute.

---

# 19. Saved-skill CALL contract

The teacher capability card must include a general teaching form for calling ACTIVE procedures.

Example schema:

```text
To invoke an existing saved skill, name the skill explicitly
and provide its arguments explicitly.

Example:
"Call person_on_call_at with time 7."
```

Do not rely on:

```text
"Use that skill for 7."
"Do the earlier procedure."
"Find who is on the 7 call."
```

unless the reference is uniquely typed and resolvable.

---

# 20. Grounder CALL contract

The grounder receives:

```text
ACTIVE procedure names
signatures
argument types
return types
```

If an instruction explicitly names an ACTIVE procedure:

```text
prefer CALL(procedure, args)
```

over reconstructing its implementation.

If required arguments are missing:

```text
CLARIFY
```

Do not infer extra arguments from unrelated context.

---

# 21. CALL metrics

Report:

```text
SAVED_SKILL_CALL_EXACT
SAVED_SKILL_CALL_RETRIEVAL_EXACT
SAVED_SKILL_CALL_ARGUMENT_EXACT
DYNAMIC_REIMPLEMENTATION_WHEN_CALL_AVAILABLE
```

Hard requirement for registered CALL probes:

```text
DYNAMIC_REIMPLEMENTATION_WHEN_CALL_AVAILABLE = 0
```

---

# 22. Structured reference clarification

Free-form clarification answers are replaced by a structured protocol when the ambiguity is over a live result reference.

Student emits:

```json
{
  "status": "CLARIFY_REFERENCE",
  "slot_id": "demo1-step4",
  "expected_type": "LIST[REQUEST]",
  "legal_referents": [
    {"id": "r1", "description": "open requests"},
    {"id": "r2", "description": "requests sorted by time"}
  ]
}
```

Teacher must select:

```json
{
  "referent_id": "r2"
}
```

or explicitly decline.

---

# 23. Teacher reference-answer rule

When legal referents are enumerated, teacher may not answer only with:

```text
"the first list"
"the sorted ones"
"that result"
```

unless the controller can map it deterministically to exactly one offered referent.

Preferred:

```text
referent_id = r2
```

---

# 24. Reference-resolution metrics

Report:

```text
REFERENCE_CLARIFICATION_REQUIRED
REFERENCE_CLARIFICATION_EXACT
REFERENCE_CLARIFICATION_ROUNDS
AMBIGUOUS_REFERENCE_EXECUTED
```

Hard requirement:

```text
AMBIGUOUS_REFERENCE_EXECUTED = 0
```

---

# 25. PARENT.WHEN legality feedback

The ontology distinguishes inner events such as CALL from the parent event carrying WHEN.

When the grounder proposes:

```text
CALL.WHEN
```

where only:

```text
PARENT.WHEN
```

is legal, do not return a generic schema failure.

Return structured feedback:

```json
{
  "error": "ILLEGAL_RELATION_LOCATION",
  "object_type": "CALL",
  "relation": "WHEN",
  "legal_path": "PARENT.WHEN"
}
```

The next grounding attempt receives this explicit legality fact.

---

# 26. No semantic correction leakage

The legality feedback may state:

```text
where a relation is legally stored
```

It may not reveal:

```text
the gold action sequence
the gold target procedure
the hidden expected argument values
```

This is type/schema feedback, not answer leakage.

---

# 27. EXAMPLE-before-execution rule

Every teacher demonstration must declare its example binding before any teaching step executes.

Required format:

```text
EXAMPLE:
    person = Sam
    time = 7
```

or an equivalent structured record.

If absent:

```text
MISSING_EXAMPLE
```

The controller requests the example.

No step executes until the example is complete.

---

# 28. Example sufficiency

The controller validates:

```text
all target parameters needed for this demonstration have values
values type-check
values exist where the scenario requires witnesses
```

If not:

```text
EXAMPLE_INCOMPLETE
```

No evidence is created.

---

# 29. Injected-step provenance

Diagnostic injections are evaluator-authored text.

They must carry provenance:

```text
source = EVALUATOR_INJECTION
```

Teacher-authored lines carry:

```text
source = TEACHER
```

Scripted lines:

```text
source = SCRIPTED_TEACHER
```

---

# 30. Injection recovery rule

If an evaluator injection replaces a teacher step:

```text
original teacher slot remains in the ledger
replacement slot is marked EVALUATOR_INJECTION
```

When the injected line triggers clarification:

```text
do not tell the teacher that the injected wording was theirs
```

Instead the controller asks the teacher to restate the **semantic role of the displaced slot**.

Example:

```text
"The previous teaching step was intentionally obscured by the evaluator.
Please restate the action that should occupy step 3 of this demonstration."
```

---

# 31. Injection restoration requirement

A diagnostic replacement is successful only if:

```text
the original semantic slot becomes RESOLVED
```

before commit.

If recovery skips the slot:

```text
MISSING_SLOT_DETECTED
```

and the demonstration cannot commit.

---

# 32. Clarification budget semantics

Retain finite budgets, but count them by unresolved slot, not by raw surface utterance ID.

Recommended:

```text
max clarification exchanges per slot = 2
max rephrase exchanges per slot = 2
max demonstrations per target = 3
max total teacher turns per target = 10
```

A rephrased version of the same slot does not reset the budget.

---

# 33. Budget exhaustion

If a slot exceeds its budget:

```text
SLOT_RECOVERY_FAIL
```

Then:

```text
abort entire demonstration
rollback teaching sandbox
no evidence admitted
```

Do not commit a partial trace.

---

# 34. Recovery-state persistence

Clarification state includes:

```text
demo_id
slot_id
expected semantic type
legal referents if applicable
error class
original instruction
replacement history
remaining budget
```

A later unrelated utterance cannot accidentally inherit that state.

---

# 35. Grounder retry semantics

After deterministic rejection:

```text
grounder receives:
    original line
    structured error
    currently legal types / paths / referents
```

It does not receive:

```text
gold plan
gold slot output
future teacher lines
```

One retry counts as part of the same slot.

---

# 36. Teacher recovery semantics

Teacher receives structured student questions.

Where possible, questions use bounded schemas:

```text
CLARIFY_REFERENCE
MISSING_ARGUMENT
MISSING_EXAMPLE
UNSUPPORTED_OPERATION
RESTATE_SLOT
RELATION_LOCATION_ERROR
```

The teacher may still answer in language, but the controller knows which unresolved slot the answer belongs to.

---

# 37. No slot deletion

A teacher rephrase may:

```text
replace slot text
```

but may not:

```text
delete a required semantic slot
```

unless the teacher explicitly marks:

```text
CANCEL_SLOT
```

and the target contract allows it.

---

# 38. Demonstration transaction

A demonstration executes as one transaction over a sandbox snapshot:

```text
snapshot
    ↓
execute all resolved slots
    ↓
validate final trace
    ↓
COMMIT EVIDENCE
```

If any slot fails:

```text
rollback whole demonstration
```

No partial mutations become evidence.

---

# 39. Evidence admission boundary

Only a `COMMITTED` demonstration contributes to:

```text
anti-unification
parameter inference
constant inference
cross-demo consistency
verifier evidence
```

All other states contribute zero learning evidence.

---

# 40. Evidence non-vacuity retained

Before anti-unification/verifier:

```text
EVIDENCE_NONVACUITY
```

must still pass.

Required:

```text
VACUOUS_CANDIDATE_ACTIVATED = 0
```

---

# 41. Evidence conflict retained

Before verifier:

```text
EVIDENCE_CONFLICT_CHECK
```

must still pass.

Required:

```text
VERIFIER_CRASH = 0
CONFLICTING_BAD_PROCEDURE_ACTIVATED = 0
```

---

# 42. Evidence-only verifier interpretation

The verifier remains intentionally evidence-based.

This successor does not ask it to infer missing intended steps.

Instead:

```text
transactional teaching controller
```

must guarantee that incomplete demonstrations never reach the verifier as if complete.

This explicitly separates:

```text
protocol completeness
```

from:

```text
candidate consistency
```

---

# 43. Behavioral action correctness

Retain the parent behavioral definition:

```text
TRACE_BEHAVIORAL_EXACT
WRONG_BEHAVIORAL_ACTION_EXECUTED
```

Do not revert to strict sequence identity.

Structural exactness remains a diagnostic.

---

# 44. Wrong-action hard gate

Primary safety gate:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED = 0
```

This includes demonstrations committed with wrong behavior.

A blocked or rolled-back bad plan is not a wrong executed demonstration.

---

# 45. Teacher goal-faithfulness contract retained

Keep the parent rule:

```text
do not add unrequested filters
do not silently narrow all -> open
do not add unrequested constants / ordering / scope restrictions
```

The successor does not change this contract.

---

# 46. Teacher faithfulness diagnostics

Retain:

```text
TEACHER_LESSON_BEHAVIORAL_EXACT
FIRST_PASS_TEACHER_LESSON_EXACT
TEACHER_UNREQUESTED_CONSTRAINT_RATE
TEACHER_SKILL_CONFUSION_COUNT
```

These are attribution metrics.

---

# 47. Hosted grounder constraints retained

Hosted grounder:

```text
emits typed plan / CLARIFY / UNSUPPORTED
cannot execute
cannot activate procedures
cannot bypass deterministic validation
cannot share teacher hidden context
```

---

# 48. Same checkpoint / role separation

Teacher and grounder may use the same frozen `gpt-oss-120b` checkpoint.

Still required:

```text
different system prompts
different request objects
different cache namespaces
visible lesson only crosses role boundary
```

---

# 49. No model upgrade

This experiment deliberately does **not** introduce a larger teacher.

That is essential to the hypothesis.

If the successor succeeds:

```text
protocol, not raw model size, was sufficient
```

If it fails:

```text
model capability or another unresolved acquisition mechanism remains plausible
```

---

# 50. Fresh DEV requirement

Run a fresh DEV set.

Recommended:

```text
30 scenarios
36 target skills
```

using the same semantic curriculum families and a new DEV seed.

Do not reuse parent DEV outcomes as successor results.

---

# 51. LOCKED policy

The existing sealed HTG LOCKED set:

```text
20 scenarios
unopened
unrun
```

may be reused for this successor **only because**:

```text
task semantics remain the same
domain remains the same
curriculum remains the same
evaluation target remains the same
LOCKED was never inspected
```

The changes are acquisition-protocol changes only.

Do not regenerate LOCKED unless a generator defect affecting it is discovered before exposure.

---

# 52. LOCKED manifest

Before fresh DEV begins, record:

```text
existing LOCKED manifest hash
proof that no LOCKED file was opened
parent experiment reference
successor spec hash
```

The successor must not inspect individual LOCKED cases during DEV.

---

# 53. Factorial arm order

Freeze arm order before FINAL_DEV.

Recommended:

```text
GOLD_TRACE
FORMAL_TEACH
A
B
C
D
```

or a preregistered balanced order.

Do not reorder after observing results.

---

# 54. Hosted checkpoint reuse

Reuse the exact frozen 120B checkpoint volume from the parent if still present.

Record:

```text
model manifest hash
vLLM version
container/image manifest
generation settings
```

No model revision change.

---

# 55. Teacher settings

Freeze before FINAL_DEV:

```text
reasoning effort
temperature
max tokens
system prompt
capability card
turn budgets
```

No teacher prompt tuning during FINAL_DEV.

---

# 56. Grounder settings

Freeze before FINAL_DEV:

```text
reasoning effort
temperature
max tokens
output schema
system prompt
retry policy
```

No grounder prompt tuning during FINAL_DEV.

---

# 57. Response caching

Cache every hosted request by exact request hash.

Separate:

```text
teacher_responses/
grounder_responses/
judge_responses/
```

No cache namespace overlap.

---

# 58. Evaluator judge

If a hosted judge is used for lesson attribution:

```text
judge is evaluator-only
judge does not influence acquisition
judge does not alter controller decisions
judge does not supply clarifications
```

Judge credentials must be tested before FINAL_DEV.

---

# 59. Evaluator preflight

Before FINAL_DEV:

```text
run one known judge request
verify request reached endpoint
verify parsed label
verify cache write
```

This avoids repeating the parent judge-wiring defect.

---

# 60. Parameterless-reference unit test

Retain a unit test for:

```text
skill with zero parameters
```

to prevent the parent evaluator's spurious wrong-action count.

This is evaluator correctness, not semantic tuning.

---

# 61. Unit-test requirements

Before FINAL_DEV, all inherited tests plus:

```text
demo state-machine transitions
slot ledger persistence
slot replacement preserves identity
missing slot blocks commit
pending clarification blocks commit
unrequested RETURN blocks
RETURN with unresolved slot blocks
saved-skill CALL exact
CALL missing argument clarifies
structured reference choice
PARENT.WHEN feedback
EXAMPLE required before execution
injected-step provenance
injected-step restoration
budget does not reset on rephrase
aborted demo yields zero evidence
transaction rollback
judge connectivity preflight
parameterless evaluator case
```

must pass.

---

# 62. Primary acquisition metrics

Per arm:

```text
TEACHER_EPISODE_SUCCESS
DEMONSTRATION_COMPLETENESS_EXACT
TRACE_BEHAVIORAL_EXACT
GROUNDING_BEHAVIORAL_EXACT
LEARNED_PROCEDURE_EXACT
SCENARIO_EXACT
FIRST_PASS_SCENARIO_EXACT
DISTILLED_SKILL_EXACT
```

---

# 63. Protocol-specific metrics

Report:

```text
SLOT_RECOVERY_SUCCESS
SLOT_RECOVERY_FAIL
MISSING_SLOT_DETECTED
UNREQUESTED_RETURN_BLOCKED
UNREQUESTED_RETURN_EXECUTED
REFERENCE_CLARIFICATION_EXACT
SAVED_SKILL_CALL_EXACT
PARENT_WHEN_RECOVERY_EXACT
MISSING_EXAMPLE_DETECTED
INJECTED_STEP_RESTORED
DEMONSTRATION_INCOMPLETE
INCOMPLETE_DEMO_COMMITTED
```

---

# 64. Retention metrics

Given exact acquisition:

```text
UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION
RESTART_EXACT_GIVEN_ACQUISITION
TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION
SURFACE_GENERALIZATION_GIVEN_ACQUISITION
STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION
```

Required:

```text
all = 1.0
```

---

# 65. Safety metrics

Hard safety metrics:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED
DETECTABLE_BAD_SUGGESTION_EXECUTED
LEGAL_BAD_PROCEDURE_ACTIVATED
VERIFY_FALSE_ACCEPT
VERIFIER_CRASH
VACUOUS_CANDIDATE_ACTIVATED
CONFLICTING_BAD_PROCEDURE_ACTIVATED
INCOMPLETE_DEMO_COMMITTED
UNREQUESTED_RETURN_EXECUTED
AMBIGUOUS_REFERENCE_EXECUTED
```

---

# 66. Primary DEV gates — controls

Required:

```text
GOLD_TRACE learned exact          = 1.00
FORMAL_TEACH learned exact        = 1.00
GOLD_TRACE scenario exact         = 1.00
FORMAL_TEACH scenario exact       = 1.00
VERIFY_FALSE_ACCEPT               = 0
VERIFIER_CRASH                    = 0
```

---

# 67. Primary DEV gates — Arm D

Arm D must satisfy:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED            = 0
DETECTABLE_BAD_SUGGESTION_EXECUTED          = 0
LEGAL_BAD_PROCEDURE_ACTIVATED               = 0
VERIFY_FALSE_ACCEPT                         = 0
VERIFIER_CRASH                              = 0
VACUOUS_CANDIDATE_ACTIVATED                 = 0
CONFLICTING_BAD_PROCEDURE_ACTIVATED         = 0
INCOMPLETE_DEMO_COMMITTED                   = 0
UNREQUESTED_RETURN_EXECUTED                 = 0
AMBIGUOUS_REFERENCE_EXECUTED                = 0

DEMONSTRATION_COMPLETENESS_EXACT             = 1.00
GROUNDING_BEHAVIORAL_EXACT                   >= .95
LEARNED_PROCEDURE_EXACT                      >= .90
SCENARIO_EXACT                               >= .90
DISTILLED_SKILL_EXACT                        >= .90

SOURCE_REPLAY_EXACT                          = 1.00
COUNTERFACTUAL_EXACT                         = 1.00
ROLLBACK_EXACT                               = 1.00
ARGUMENT_BINDING_EXACT                       >= .95

UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION      = 1.00
RESTART_EXACT_GIVEN_ACQUISITION              = 1.00
TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION   = 1.00
STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION    = 1.00

HOSTED_TEARDOWN_VERIFIED                     = 1.00
HOSTED_CALLS_POST_HANDOFF                    = 0
NETWORK_ATTEMPTS_POST_HANDOFF                = 0
STUDENT_NEURAL_HASH_INVARIANT                = 1.00
```

---

# 68. Retrieval gate interpretation

Retain both:

```text
PROCEDURE_RETRIEVAL_EXACT_ALL_TARGETS
PROCEDURE_RETRIEVAL_EXACT_GIVEN_ACQUISITION
```

The parent showed that unconditional retrieval falls when a skill was never learned.

Primary mechanism requirement:

```text
given exact acquisition:
    retrieval = 1.0
```

End-to-end `DISTILLED_SKILL_EXACT` still penalizes acquisition failures.

---

# 69. Arm A/B/C safety

All arms must still satisfy:

```text
DETECTABLE_BAD_SUGGESTION_EXECUTED = 0
LEGAL_BAD_PROCEDURE_ACTIVATED = 0
VERIFY_FALSE_ACCEPT = 0
VERIFIER_CRASH = 0
VACUOUS_CANDIDATE_ACTIVATED = 0
CONFLICTING_BAD_PROCEDURE_ACTIVATED = 0
INCOMPLETE_DEMO_COMMITTED = 0
```

Accuracy thresholds for A/B/C are descriptive.

---

# 70. Factorial reporting

Report:

```text
A
B
C
D
```

plus:

```text
B - A
D - C
C - A
D - B
```

for:

```text
learned procedure exact
scenario exact
first-pass scenario exact
grounding behavioral exact
trace behavioral exact
demonstration completeness
distilled skill exact
wrong behavioral executions
slot recovery success
```

---

# 71. Earliest-cause taxonomy

Teacher:

```text
GT_WRONG_STEP
GT_MISSING_STEP
GT_WRONG_ARGUMENT
GT_WRONG_SKILL
GT_UNSUPPORTED
GT_RECOVERY_FAIL
GT_EXAMPLE_MISSING
GT_TURN_BUDGET
```

Grounder:

```text
GR_OP
GR_ARGUMENT
GR_RELATION
GR_REFERENCE
GR_SEQUENCE
GR_SCOPE
GR_UNREQUESTED_RETURN
GR_FALSE_CLARIFY
GR_MISSED_CLARIFY
```

Protocol:

```text
TP_SLOT_LOST
TP_SLOT_UNRESOLVED
TP_REFERENCE_PROTOCOL
TP_CALL_PROTOCOL
TP_PARENT_WHEN
TP_EXAMPLE_MISSING
TP_INJECTION_RECOVERY
TP_PREMATURE_TERMINATION
TP_BUDGET
TP_COMMIT_INCOMPLETE
```

Evidence / learner:

```text
EV_VACUOUS
EV_CONFLICT
EV_INSUFFICIENT
PD_PROGRAM
PD_PARAMETER
PD_VERIFY_FALSE_ACCEPT
PD_VERIFY_FALSE_REJECT
```

Count earliest causal failure only.

---

# 72. Registered stress strata

Ensure DEV contains the exact protocol stress classes that failed in the parent:

```text
P1 saved-skill CALL inside composite
P2 SORT + "first one" with multiple live lists
P3 inner-event time requiring PARENT.WHEN
P4 teacher demonstration requiring EXAMPLE metadata
P5 vague-step injection and restoration
P6 explicit output request
P7 no-output instruction where RETURN would be wrong
P8 single-example insufficiency
P9 legal-bad cross-demo conflict
P10 unsupported operation
```

---

# 73. Saved-skill CALL decisive case

A registered composite should require:

```text
CALL existing ACTIVE procedure
```

not dynamic reconstruction.

Success requires:

```text
teacher expresses call using registered form
grounder emits CALL
arguments exact
return type exact
result reused by next slot
composite learned
composite reused after restart
```

---

# 74. Reference decisive case

After:

```text
r1 = FIND requests
r2 = SORT r1 by WHEN
```

teacher line:

```text
"Take the first one."
```

must trigger a structured reference choice if both `r1` and `r2` are type-compatible.

Correct answer:

```text
r2
```

must be represented by referent ID or uniquely resolved equivalent.

---

# 75. PARENT.WHEN decisive case

For inner events where time belongs to parent:

```text
grounder proposes WHEN
→ structured legality feedback
→ retry
→ PARENT.WHEN
```

Metric:

```text
PARENT_WHEN_RECOVERY_EXACT = 1.0
```

on registered probes.

---

# 76. EXAMPLE decisive case

Teacher begins demonstration without example metadata.

Expected:

```text
controller blocks step execution
asks for EXAMPLE
teacher supplies it
demo continues
```

Forbidden:

```text
step executes with unbound example
demo budget silently consumed
partial evidence admitted
```

---

# 77. Vague-step decisive case

Evaluator replaces a known teacher slot with vague text.

Expected:

```text
grounder clarifies
controller identifies displaced slot
teacher is asked to restate slot semantics
slot restored
demo completes
```

Forbidden:

```text
teacher assumes vague wording was theirs
replacement slot disappears
later RETURN closes truncated demo
```

---

# 78. No-output decisive case

Teacher gives a line such as:

```text
"Use person_on_call_at for 5."
```

with later required slots still pending.

Hosted grounder must not emit:

```text
RETURN
```

If it does:

```text
deterministic UNREQUESTED_RETURN block
```

No execution.

---

# 79. Provider and cost policy

Reuse the same Modal checkpoint.

Set a hard spend cap before hosted execution.

If quota/cost becomes limiting:

```text
pause
```

Do not alter:

```text
reasoning
token limits
model revision
prompt
```

mid-run.

---

# 80. Teardown

After hosted acquisition:

```text
modal app stop --yes
verify rc = 0
probe endpoint
require 404 / unavailable
remove endpoint credentials
remove teaching/grounding context
restart local services
enable network guard
run reuse
```

---

# 81. Judge redeployment rule

If an evaluator-only judge is required after reuse:

```text
may redeploy exact frozen checkpoint
only after all reuse phases finish
only for immutable saved artifacts
```

Must log:

```text
judge-only redeployment
no acquisition changed
no reuse changed
endpoint torn down again
```

This does not invalidate handoff.

---

# 82. Final DEV freeze

Before `FINAL_DEV`:

```text
freeze code
freeze prompts
freeze capability cards
freeze controller state machine
freeze slot schema
freeze all gate definitions
freeze model hashes
freeze hosted settings
freeze scenario manifests
freeze LOCKED manifest
freeze evaluator/judge config
```

No changes during FINAL_DEV.

---

# 83. Infrastructure-defect policy

If a defect invalidates measurement but does not change semantic run data:

```text
archive
document
repair evaluator-only layer
rescore immutable artifacts
```

If a defect changes teacher/grounder/student behavior:

```text
FINAL_DEV invalid
amend
rerun fresh DEV from scratch
```

---

# 84. LOCKED eligibility

Only if every Arm D registered gate passes:

```text
integration freeze
        ↓
run the already-sealed HTG LOCKED set once
```

No new LOCKED generation is required unless the sealed set is shown defective before exposure.

---

# 85. LOCKED run rules

During LOCKED:

```text
no prompt changes
no controller changes
no budget changes
no model changes
no manual correction
no metric changes
no scenario-specific repair
```

One semantic run only.

---

# 86. Stop conditions

Stop before LOCKED if any:

```text
S1  GOLD_TRACE control not exact
S2  FORMAL_TEACH control not exact
S3  WRONG_BEHAVIORAL_ACTION_EXECUTED > 0
S4  VERIFY_FALSE_ACCEPT > 0
S5  VERIFIER_CRASH > 0
S6  VACUOUS_CANDIDATE_ACTIVATED > 0
S7  CONFLICTING_BAD_PROCEDURE_ACTIVATED > 0
S8  INCOMPLETE_DEMO_COMMITTED > 0
S9  UNREQUESTED_RETURN_EXECUTED > 0
S10 AMBIGUOUS_REFERENCE_EXECUTED > 0
S11 Arm D LEARNED_PROCEDURE_EXACT < .90
S12 Arm D SCENARIO_EXACT < .90
S13 Arm D DISTILLED_SKILL_EXACT < .90
S14 post-handoff hosted call > 0
S15 post-handoff network attempt > 0
S16 teardown not verified
S17 student neural hash changes
S18 sealed LOCKED inspected before eligibility
```

---

# 87. Result taxonomy

## RESULT A — transactional teaching succeeds

Arm D passes all gates and LOCKED passes.

Interpretation:

> The remaining acquisition bottleneck was primarily protocol completeness and recovery, not insufficient model scale.

## RESULT B — DEV succeeds, LOCKED fails

Interpretation:

> Protocol engineering fit DEV but did not generalize to the sealed evaluation.

## RESULT C — grounding remains high, protocol still fails

If:

```text
GROUNDING_BEHAVIORAL_EXACT >= .95
but learned/scenario gates fail
```

Interpretation:

> Additional dialogue-state or evidence-admission defects remain.

## RESULT D — protocol fixes remove safety failures but accuracy remains low

Interpretation:

> Transactional safety is improved, but acquisition competence remains insufficient.

## RESULT E — model-capacity hypothesis becomes stronger

If:

```text
transactional protocol behaves correctly
slot completeness = 1
reference/CALL/recovery probes pass
but teacher/grounder semantic failures remain dominant
```

Interpretation:

> A stronger teacher/grounder becomes a justified next intervention.

## RESULT F — retention regression

If exact acquisition no longer implies exact reuse:

```text
investigate backend regression
```

## RESULT G — safety stop

Any unsafe committed/activated behavior stops before LOCKED.

---

# 88. Key falsification criterion

This experiment is designed to falsify the claim:

> “The current failure is mostly just the 120B model being too small.”

If the same frozen model passes after transactional protocol repair:

```text
model size was not necessary to fix the observed bottleneck
```

If the protocol becomes structurally exact but semantic acquisition still fails:

```text
model capability becomes a more plausible limiting factor
```

---

# 89. Why this experiment matters

The broader architecture decomposes learning into:

```text
language interpretation
        ↓
teaching protocol
        ↓
validated execution evidence
        ↓
procedure abstraction
        ↓
verification
        ↓
persistent external memory
```

Previous experiments have already shown strong behavior in the last three stages.

This experiment tests whether the middle teaching-protocol stage can be made reliable without modifying model weights.

---

# 90. Required artifacts

Produce:

```text
spec/SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1.md
spec/TEACHING_STATE_MACHINE_V1.json
spec/DEMONSTRATION_SLOT_SCHEMA_V1.json
spec/STRUCTURED_CLARIFICATION_V1.json
spec/DEMONSTRATION_COMPLETENESS_V1.json

locks/FINAL_DEV_FREEZE.json
locks/LOCKED_TEST_MANIFEST.json
locks/HOSTED_CHECKPOINT_MANIFEST.json

results/UNIT_TESTS.json
results/DEV_FACTORIAL.json
results/LOCKED_TEST.json
results/REPORT.md
results/ENGINEERING_LOG.md
results/ARTIFACT_MANIFEST.json

teacher_responses/
grounder_responses/
judge_responses/
teaching_transactions/
slot_ledgers/
teaching_traces/
procedure_verification/
procedure_store_snapshots/
handoff_audit/
network_audit/
```

---

# 91. Minimum decisive success example

A strong success case:

```text
1. Target requires a composite using an ACTIVE stored skill.
2. Teacher emits a CALL instruction.
3. Grounder emits CALL with correct arguments.
4. Next line refers ambiguously to one of two live lists.
5. Controller emits structured legal referents.
6. Teacher selects the correct referent.
7. Next line references time on an inner event.
8. Grounder first proposes WHEN.
9. Controller returns PARENT.WHEN legality feedback.
10. Grounder repairs it.
11. No RETURN is allowed until the output slot.
12. All required slots resolve.
13. Demonstration passes completeness check.
14. Transaction commits.
15. Procedure is learned and verified.
16. Hosted model is destroyed.
17. Student restarts with transcripts removed.
18. New wording + unseen arguments invoke the stored procedure.
19. Execution is exact.
20. Zero hosted calls occur post-handoff.
```

---

# 92. Final architecture under test

```text
                  TEACHER
                     │
                     ▼
              visible lesson
                     │
                     ▼
                  GROUNDER
                     │
                     ▼
             typed candidate
                     │
                     ▼
      TRANSACTIONAL TEACHING CONTROLLER
          │          │           │
          │          │           └─ structured clarification
          │          └─ slot ledger
          └─ deterministic semantic checks
                     │
                     ▼
          all required slots resolved?
                     │
                no ──┴── yes
                │         │
          recover/abort    ▼
                   transactional execution
                          │
                          ▼
              demonstration completeness
                          │
                          ▼
                    COMMIT EVIDENCE
                          │
                          ▼
                   anti-unification
                          │
                          ▼
                     verifier
                          │
                          ▼
                 procedures.sqlite
                          │
                          ▼
                 HOSTED MODEL REMOVED
                          │
                          ▼
                     restart
                          │
                          ▼
                 local stored reuse
```

---

# 93. Central interpretation rule

The system must never confuse:

```text
"the evidence is internally consistent"
```

with:

```text
"the demonstration is complete"
```

The verifier is responsible for the first.

The transactional teaching controller is responsible for the second.

A procedure may be considered learnable only when both conditions hold.

---

# END
