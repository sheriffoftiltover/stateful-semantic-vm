# SEMVM_HOSTED_TEACHER_GROUNDER_V1

**Project:** Stateful Semantic VM — Hosted Teacher × Grounder Factorial  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Primary hosted model:** frozen `gpt-oss-120b`, self-hosted on Modal H100  
**Local grounder baseline:** frozen `Qwen2.5-Coder-1.5B` frontend inherited from NL_TEACH / PDX  
**Primary scientific target:** acquisition, not retention  
**Parent experiment:** `SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1`  
**Parent outcome:** DEV stopped; hosted-teacher acquisition gates failed; LOCKED was not run

---

# 0. Executive summary

The parent procedural-distillation experiment established two sharply different facts.

First, the **retention / handoff mechanism worked**:

```text
correctly acquired procedure
        ↓
verified
        ↓
persisted
        ↓
teacher destroyed
        ↓
all processes restarted
        ↓
teaching transcript removed
        ↓
network blocked
        ↓
new wording + unseen arguments
        ↓
correct stored-procedure reuse
```

Whenever a skill was acquired exactly, post-handoff reuse was exact.

Second, **acquisition through dialogue failed the registered gates**.

The parent final DEV localized failures to both sides of the language channel:

```text
hosted 120B teacher
    ├── sometimes adds unrequested constraints
    ├── sometimes confuses target skills
    └── sometimes produces awkward / difficult lesson wording

frozen 1.5B grounder
    ├── sometimes chooses the wrong relation
    ├── sometimes chooses the wrong operation
    └── can create vacuous evidence from a mis-grounded demonstration
```

The parent also showed that fixed scripted lessons outperform the interactive hosted teacher under the 1.5B grounder.

This successor therefore asks a narrower question:

> Is the acquisition bottleneck primarily the teacher, the grounder, or their interaction?

The experiment is a paired 2 × 2 factorial:

```text
                              GROUNDER
                         local 1.5B       hosted 120B

TEACHER
scripted lesson               A                B

hosted 120B teacher           C                D
```

The primary arm is:

```text
D = hosted 120B teacher + hosted 120B grounder
```

The hosted teacher and hosted grounder may use the **same frozen checkpoint**, but they are logically isolated roles with separate prompts, separate contexts, separate response caches, and no hidden-state sharing.

The procedure learner, verifier, store, VM, persistence mechanism, and post-handoff evaluation remain frozen.

---

# 1. Main research question

Can a stronger frozen hosted model reliably mediate both sides of the teaching language channel:

```text
goal
  ↓
teacher lesson
  ↓
grounding into typed executable action
  ↓
sandbox trace
  ↓
deterministic procedure learning
```

such that the resulting procedure remains correct after the hosted model is fully removed?

---

# 2. Primary hypotheses

## H1 — hosted grounding

A hosted 120B grounder will reduce grounding failures relative to the frozen 1.5B grounder when both receive the same scripted lessons.

Operational comparison:

```text
B versus A
```

where:

```text
A = SCRIPTED_TEACHER + LOCAL_1P5B_GROUNDER
B = SCRIPTED_TEACHER + HOSTED_120B_GROUNDER
```

## H2 — hosted teacher interaction

Once grounding quality is improved, an interactive hosted teacher may add value over fixed scripted lessons.

Operational comparison:

```text
D versus B
```

where:

```text
D = HOSTED_120B_TEACHER + HOSTED_120B_GROUNDER
```

## H3 — durable handoff remains independent of the teacher

For every exactly learned skill:

```text
post-handoff reuse must remain exact
```

with:

```text
hosted model destroyed
teaching transcript removed
all processes restarted
network blocked
no hosted calls after handoff
```

---

# 3. Strongest permitted claim

If all registered gates pass:

> Within the registered Semantic VM domain, a frozen hosted 120B model can serve as both a non-authoritative procedural teacher and a constrained semantic grounding frontend. Natural-language lessons can be converted into validated execution traces, abstracted into independently verified persistent procedures, and later reused after the hosted model is destroyed, with no student neural weight updates.

This does **not** establish:

```text
open-domain autonomous learning
general self-improvement
arbitrary tool invention
new primitive invention
general software engineering ability
weight-level model distillation
open-ended autonomous curriculum generation
```

---

# 4. Parent result imported as frozen evidence

The parent `SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1` result is not rerun or rewritten.

Its historical findings remain:

```text
GOLD_TRACE controls               exact
FORMAL_TEACH controls             exact

SCRIPTED + local 1.5B:
    learned procedure exact       .917
    scenario exact                .900

hosted teacher + local 1.5B:
    learned procedure exact       .667
    scenario exact                .633
    wrong demonstrations executed 12
    verifier false accepts        1
```

Historical post-handoff result:

```text
given exact acquisition:
    post-handoff reuse = exact
```

The successor must preserve these numbers as historical results, not merge them with new runs.

---

# 5. Why this is a new experiment

The successor changes material scientific components:

```text
new hosted grounding arm
new teacher × grounder factorial
new behavioural action-equivalence definition
new evidence non-vacuity precondition
new evidence-conflict precondition
new teacher goal-faithfulness contract
```

Therefore:

```text
do not reuse the parent DEV result as the successor result
do not run the parent unopened LOCKED set
```

A fresh DEV set and fresh blind LOCKED set are required.

The parent unopened LOCKED set remains preserved for exact replication of the parent protocol.

---

# 6. Experimental arms

Use the same scenario instances across all four arms.

## Arm A — SCRIPTED × LOCAL

```text
registered scripted lesson
        ↓
frozen local 1.5B grounder
        ↓
deterministic checks
        ↓
execution / learning
```

Purpose:

```text
local-grounder baseline
```

## Arm B — SCRIPTED × HOSTED

```text
registered scripted lesson
        ↓
frozen hosted 120B grounder
        ↓
deterministic checks
        ↓
execution / learning
```

Purpose:

```text
isolate the causal value of stronger grounding
```

## Arm C — HOSTED × LOCAL

```text
hosted 120B teacher
        ↓
natural-language lesson
        ↓
frozen local 1.5B grounder
        ↓
deterministic checks
        ↓
execution / learning
```

Purpose:

```text
replicate the parent acquisition configuration
under the successor's corrected evaluation contract
```

## Arm D — HOSTED × HOSTED

```text
hosted 120B teacher
        ↓
natural-language lesson
        ↓
separate hosted 120B grounder call
        ↓
deterministic checks
        ↓
execution / learning
```

Purpose:

```text
primary successor arm
```

---

# 7. Sanity controls

Retain:

```text
GOLD_TRACE
FORMAL_TEACH
```

These bypass natural-language acquisition.

Required:

```text
all registered control metrics = 1.0
VERIFY_FALSE_ACCEPT = 0
```

Any control regression is an infrastructure failure.

Stop before interpreting factorial results.

---

# 8. Hosted checkpoint freeze

Use the exact parent hosted teacher checkpoint identified by:

```text
locks/TEACHER_WEIGHTS_MANIFEST.json
```

from the parent experiment.

Do not redownload a different revision under the same model name.

Record:

```text
checkpoint manifest hash
all model-file hashes
tokenizer hashes
vLLM version
Modal image hash / source manifest
GPU class
generation settings
```

Primary hardware:

```text
1 × Modal H100
```

The existing Modal Volume may be reused.

---

# 9. Logical isolation of teacher and grounder

Even though arms C/D may use the same checkpoint, the roles are separate agents.

## Teacher call sees

```text
target skill goal
capability card
teacher dialogue history
student clarification questions
student-reported execution outcomes permitted by protocol
```

Teacher call does not see:

```text
gold trace
gold procedure AST
hidden evaluator labels
grounder prompt
grounder hidden reasoning
LOCKED answers
```

## Grounder call sees

```text
one teacher/scripted instruction
currently defined result variables
their static types
available primitives
ACTIVE procedure signatures
local execution context required for grounding
```

Grounder call does not see:

```text
teacher hidden reasoning
teacher system prompt
gold trace
gold AST
future lesson lines
hidden evaluator annotations
full curriculum answer
```

The hosted model receives two distinct system prompts and two distinct cache namespaces:

```text
teacher/
grounder/
```

---

# 10. No same-context shortcut

Forbidden:

```text
one 120B conversation generates the lesson
and then directly emits the executable plan
from the same hidden context
```

Arm D must contain an observable language bottleneck:

```text
TEACHER RESPONSE TEXT
        ↓
serialized / hashed
        ↓
new independent GROUNDER request
        ↓
typed candidate plan
```

Only the teacher's visible lesson text crosses the boundary.

---

# 11. Hosted generation policy

Freeze before full DEV:

```text
reasoning effort
temperature
top-p
max output tokens
stop conditions
vLLM version
prompt templates
schema / constrained-decoding configuration
```

Teacher and grounder may use different reasoning effort or token budgets only if frozen before full DEV.

Recommended starting point:

```text
teacher:
    reasoning = high
    temperature = 0
    max_tokens = 4096

grounder:
    reasoning = low or medium
    temperature = 0
    output constrained to typed plan schema
```

Grounder reasoning level may be selected in a registered preflight before full DEV.

---

# 12. Preflight policy

A small preflight may choose:

```text
hosted grounder reasoning level
hosted grounder output-token cap
schema formatting mechanics
provider/runtime reliability parameters
```

Preflight may use:

```text
<= 8 DEV-design scenarios
```

not LOCKED.

Selection criterion must be frozen before the full DEV run.

Do not select on LOCKED.

---

# 13. Grounder output contract

The grounder does not emit prose as its authoritative result.

It emits a constrained candidate representation such as:

```json
{
  "status": "PLAN",
  "steps": [
    {
      "op": "FIND",
      "args": {
        "type": "EMAIL",
        "recipient": "Nina",
        "status": "OPEN"
      },
      "bind": "r1"
    },
    {
      "op": "RETURN",
      "args": {
        "value": "r1"
      }
    }
  ]
}
```

or:

```json
{
  "status": "CLARIFY",
  "question": "Does 'them' refer to the emails found in the previous step?"
}
```

or:

```json
{
  "status": "UNSUPPORTED",
  "reason": "No registered primitive or ACTIVE procedure supports this operation."
}
```

The grounder cannot execute directly.

---

# 14. Grounder authority boundary

The hosted grounder may:

```text
select a registered primitive
select an ACTIVE stored procedure
bind arguments
bind result references
sequence steps
request clarification
mark an instruction unsupported
```

It may not:

```text
invent primitives
write arbitrary code
mutate the world directly
write procedures.sqlite
activate a learned procedure
declare verification success
read hidden gold
bypass deterministic checks
```

---

# 15. Teacher authority boundary

The teacher remains non-authoritative.

It may:

```text
teach
rephrase
answer clarification
provide examples
provide second demonstrations
refer to available primitives/procedures in natural language
```

It may not:

```text
install procedures
approve its own candidate
bypass execution
bypass verification
supply hidden gold ASTs
```

---

# 16. Teacher goal-faithfulness contract

The teacher system prompt must explicitly state:

```text
Teach exactly the requested skill.

Do not add filters, restrictions, state predicates,
ordering criteria, constants, entity scopes, or side conditions
unless:

1. the target goal explicitly requires them; or
2. a registered primitive/procedure signature makes them necessary.

Do not silently narrow "all" to "open",
"emails" to "open emails",
"calls with X" to "open calls with X",
or analogous restrictions.

If the goal is ambiguous, ask rather than inventing a constraint.
```

This is a general semantic rule.

Do not add scenario-specific phrases after DEV begins.

---

# 17. Teacher faithfulness metrics

Report:

```text
TEACHER_GOAL_SEMANTIC_EXACT
TEACHER_UNREQUESTED_CONSTRAINT_COUNT
TEACHER_SKILL_CONFUSION_COUNT
TEACHER_MISSING_REQUIRED_CONSTRAINT_COUNT
TEACHER_UNSUPPORTED_STEP_COUNT
```

Primary teacher-side diagnostic:

```text
UNREQUESTED_CONSTRAINT_RATE
```

These localize errors but do not replace end-to-end acquisition gates.

---

# 18. Baseline deterministic frontend

Retain all general deterministic semantic checks from the NL_TEACH / PDX lineage:

```text
typed operation validation
argument legality
reference antecedent validity
defined-before-use
dead pure-result checks
required-output checks
clause coverage
plan completeness
transactional execution
clarification scoping
unsupported-operation rejection
status cue legality
failed decomposition -> CLARIFY
demonstration rollback
```

Do not weaken these because the grounder is stronger.

---

# 19. New baseline fix: evidence non-vacuity

The parent demonstrated that a wrong grounding can create an empty evidence set, making two hypotheses observationally indistinguishable.

Add a deterministic pre-verifier check:

```text
EVIDENCE_NONVACUOUS
```

Before a learned candidate may enter verification:

```text
for every registered semantic distinction relevant to the target:
    confirm that at least one demonstration / perturbation
    contains a witness that can distinguish the candidate
    from the registered contrast.
```

Examples:

```text
OPEN emails vs all emails
recipient=Nina vs WHO=Nina
constant Sam vs parameter person
```

If no distinguishing witness exists:

```text
INSUFFICIENT_EVIDENCE
```

and:

```text
REQUIRE_SECOND_DEMONSTRATION
or
REQUIRE_CLARIFICATION
```

The candidate cannot be VERIFIED.

---

# 20. Evidence non-vacuity gate

Report:

```text
VACUOUS_VERIFICATION_ATTEMPT
VACUOUS_CANDIDATE_ACTIVATED
EVIDENCE_NONVACUITY_DETECTED
```

Hard requirements:

```text
VACUOUS_CANDIDATE_ACTIVATED = 0
VERIFY_FALSE_ACCEPT = 0
```

For registered vacuity probes:

```text
EVIDENCE_NONVACUITY_DETECTED = 1.0
```

---

# 21. New baseline fix: evidence conflict

The parent exposed a latent verifier crash when contradictory demonstrations exhausted the counterfactual pool.

Do not patch the frozen parent verifier internally for this experiment.

Add a deterministic precondition:

```text
EVIDENCE_CONFLICT_CHECK
```

Before calling the frozen verifier:

```text
if demonstrations disagree on a non-parameterizable constant
or produce mutually incompatible semantic constraints:
    return EVIDENCE_CONFLICT
```

Allowed next states:

```text
teacher clarification
new demonstration
episode failure
```

Forbidden:

```text
calling the verifier on a known-invalid evidence set
crashing the scenario
silently parameterizing the contradiction
```

---

# 22. Evidence conflict gates

Required:

```text
REGISTERED_EVIDENCE_CONFLICT_DETECTED = 1.0
VERIFIER_CRASH = 0
CONFLICTING_BAD_PROCEDURE_ACTIVATED = 0
```

---

# 23. Parameter-vs-constant sufficiency

Retain the inherited rule:

```text
one unhinted demonstration is not sufficient
to infer that a potentially varying value is a parameter
```

If the registered target signature contains an unhinted varying slot and only one value has been observed:

```text
REQUIRE_SECOND_DEMONSTRATION
```

No candidate proceeds to verification.

---

# 24. Behavioural definition of action correctness

The parent strict metric counted some order differences as wrong even when they had identical observable behavior.

This successor preregisters two separate notions.

## Structural exactness

```text
TRACE_STRUCTURAL_EXACT
```

Requires equivalence to the registered canonical trace modulo already-frozen canonicalization rules.

## Behavioural exactness

```text
TRACE_BEHAVIORAL_EXACT
```

Requires the candidate and reference trace to have the same observable semantics across the registered equivalence world set.

Observable semantics include:

```text
returned value
returned ordering where semantically observable
final world state
objects mutated
mutation values
selected scope
report contents
registered side-effect trace
error / clarification behavior
```

---

# 25. Behavioural equivalence world set

For each evaluated demonstration, compare candidate and reference on:

```text
W0 = scenario initial world
W1..Wk = registered counterfactual perturbations
```

Perturbations must include enough variation to expose:

```text
dropped filters
wrong constants
wrong relation binding
wrong scope
premature selection
order-dependent mutations
```

A candidate is behaviorally exact only if every world produces an identical observable signature.

Do not decide equivalence manually per failure.

---

# 26. Example: allowed order difference

Suppose:

```text
r = materialized list of open requests
```

Candidate A:

```text
COUNT(r) -> n
FOR_EACH r: CLOSE
RETURN n
```

Candidate B:

```text
FOR_EACH r: CLOSE
COUNT(r) -> n
RETURN n
```

If:

```text
r remains the same materialized list
COUNT is pure
closing does not change list membership
all final world state and returned values match
```

then:

```text
STRUCTURAL_EXACT = 0
BEHAVIORAL_EXACT = 1
```

This is not a wrong executed action.

---

# 27. Example: disallowed order difference

Candidate:

```text
CLOSE all open requests
FIND open requests
COUNT
RETURN
```

Reference:

```text
FIND open requests
COUNT
CLOSE those requests
RETURN count
```

These are not behaviorally equivalent because the post-mutation `FIND` changes the result.

Registered counterfactual replay must expose this.

---

# 28. Primary wrong-action safety metric

Replace the parent broad strict gate with:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED
```

Definition:

```text
a grounded demonstration was executed
whose complete transactional behavior
is not equivalent to the registered intended demonstration
on the registered equivalence world set
```

Hard gate:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED = 0
```

Retain:

```text
WRONG_STRUCTURAL_ACTION_EXECUTED
```

as a diagnostic.

---

# 29. Detectable bad suggestions

Maintain the detectability split.

Class A:

```text
unsupported primitive
wrong argument type
undefined result
illegal enum/value
structurally invalid scope
known use-before-definition
known output-obligation violation
```

Hard requirement:

```text
DETECTABLE_BAD_SUGGESTION_EXECUTED = 0
```

---

# 30. Legal-but-wrong suggestions

Class B:

```text
dropped filter
wrong type-valid constant
legal but wrong scope
wrong but legal status
unnecessary restriction
```

These may execute in the teaching sandbox when a single demonstration cannot reveal their wrongness.

They must not survive contradictory evidence.

Report:

```text
LEGAL_BAD_SANDBOX_EXECUTED
CROSS_DEMO_INCONSISTENCY_DETECTED
LEGAL_BAD_PROCEDURE_ACTIVATED
```

Hard requirement:

```text
LEGAL_BAD_PROCEDURE_ACTIVATED = 0
```

---

# 31. Teacher / grounder error attribution

Every failed acquisition receives an earliest-cause label.

Teacher:

```text
GT_UNREQUESTED_CONSTRAINT
GT_WRONG_SKILL
GT_MISSING_STEP
GT_WRONG_STEP
GT_WRONG_ARGUMENT
GT_UNSUPPORTED
GT_AMBIGUOUS
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
GR_FALSE_CLARIFY
GR_MISSED_CLARIFY
GR_SCHEMA
GR_UNSUPPORTED
```

Evidence / learner:

```text
EV_VACUOUS
EV_CONFLICT
EV_INSUFFICIENT
PD_PARAMETER
PD_PROGRAM
PD_VERIFY_FALSE_ACCEPT
PD_VERIFY_FALSE_REJECT
PD_LEARNER_ERROR
```

Runtime:

```text
VM_EXEC
ROLLBACK
STORE
RESTART
PROVIDER
```

Count the earliest causal failure only.

---

# 32. Special relation-binding diagnostic

The parent repeatedly observed:

```text
"emails to Nina"
```

being grounded as:

```text
WHO = Nina
```

instead of:

```text
RECIPIENT = Nina
```

The successor must include a registered general relation-binding diagnostic covering at least:

```text
emails to X        -> RECIPIENT
calls with X       -> WHO / registered participant relation
messages to X      -> RECIPIENT where ontology defines it
events at PLACE    -> WHERE
events about TOPIC -> TOPIC
```

Do not special-case the literal name `Nina`.

Metric:

```text
RELATION_BINDING_EXACT
```

Report by relation family.

---

# 33. Grounder comparison metric

Primary factorial metric:

```text
GROUNDING_BEHAVIORAL_EXACT
```

Compute paired by scenario / instruction for:

```text
A vs B
C vs D
```

Also report:

```text
GROUNDING_STRUCTURAL_EXACT
OP_EXACT
ARGUMENT_EXACT
RELATION_BINDING_EXACT
REFERENCE_BINDING_EXACT
SEQUENCE_BEHAVIORAL_EXACT
CLARIFICATION_PRECISION
CLARIFICATION_RECALL
```

---

# 34. Acquisition metrics

Per arm:

```text
LEARNED_PROCEDURE_EXACT
SCENARIO_EXACT
FIRST_PASS_SCENARIO_EXACT
SOURCE_REPLAY_EXACT
COUNTERFACTUAL_EXACT
ROLLBACK_EXACT
VERIFY_FALSE_ACCEPT
DISTILLED_SKILL_EXACT
```

---

# 35. Retention metrics

For every exactly learned skill:

```text
UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION
RESTART_EXACT_GIVEN_ACQUISITION
TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION
SURFACE_GENERALIZATION_GIVEN_ACQUISITION
STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION
```

These conditional metrics are separate from unconditional end-to-end scores.

This avoids conflating:

```text
failure to acquire
```

with:

```text
failure to retain
```

---

# 36. Primary end-to-end metric

Define:

```text
DISTILLED_SKILL_EXACT
```

A target counts only if:

```text
lesson acquisition succeeds
trace is behaviorally correct
procedure learned exactly
procedure verified
procedure activated
hosted model destroyed
student restarted
new wording used
unseen argument used where registered
stored procedure retrieved
execution exact
zero post-handoff hosted calls
```

---

# 37. Handoff protocol

After acquisition phase:

```text
1. stop the Modal teacher/grounder app with verified non-interactive command;
2. require successful process return code;
3. probe endpoint and require failure / 404;
4. remove teacher/grounder credentials from evaluation subprocess;
5. delete teaching transcript from student-accessible context;
6. clear hosted response access from the reuse process;
7. kill local student service;
8. restart student service;
9. enable network egress guard;
10. run post-handoff evaluation.
```

---

# 38. Teardown hardening

The parent found that:

```text
modal app stop
```

required non-interactive confirmation.

The successor must use the already-corrected teardown path.

Define:

```text
HOSTED_TEARDOWN_VERIFIED
```

as true only if:

```text
stop command succeeded
endpoint is unreachable / returns expected terminated state
network audit records no post-handoff hosted request
```

Required:

```text
HOSTED_TEARDOWN_VERIFIED = 1.0
```

---

# 39. No transcript leakage

After handoff, the student may retain:

```text
verified procedure AST
procedure name / alias
procedure signature
procedure provenance hashes
world state
normal persistent metadata
```

It may not retain in context:

```text
teacher lesson text
teacher reasoning
grounder prompt
grounder response
demonstration text
clarification dialogue
```

---

# 40. Hosted-call audit

Track separately:

```text
TEACHER_CALLS_ACQUISITION
GROUNDER_CALLS_ACQUISITION
HOSTED_CALLS_POST_HANDOFF
NETWORK_ATTEMPTS_POST_HANDOFF
```

Hard requirements:

```text
HOSTED_CALLS_POST_HANDOFF = 0
NETWORK_ATTEMPTS_POST_HANDOFF = 0
```

---

# 41. Neural invariance

Local student model:

```text
hash before run
hash after acquisition
hash after handoff
hash at end
```

Required:

```text
identical
optimizer = null
optimizer steps = 0
```

Hosted checkpoint:

```text
exact frozen manifest
```

No model fine-tuning.

---

# 42. Procedure learner freeze

Freeze the parent downstream procedure system:

```text
AST schema
anti-unifier
candidate canonicalization
procedure hash
procedure store
verification core
negative-case generation
state perturbation core
rollback injection
retrieval
argument binding
stored-procedure preference
composition
VM
world state
```

Only the explicitly registered wrappers may differ:

```text
evidence non-vacuity precheck
evidence-conflict precheck
behavioral evaluation layer
```

---

# 43. No verifier weakening

The new behavioural action metric affects evaluation of demonstration correctness.

It does **not** weaken the stored-procedure verifier.

A candidate procedure must still pass the frozen verifier after all new preconditions are satisfied.

---

# 44. Scripted teacher

The scripted teacher remains deterministic.

It emits a registered natural-language lesson for each target.

Its purpose is to isolate grounding quality.

It must not adapt except through frozen lookup-table responses for registered clarification cases.

---

# 45. Hosted teacher interaction

Hosted teacher may:

```text
provide lesson
respond to clarification
rephrase
provide another demonstration
```

Register finite budgets.

Recommended:

```text
max teacher turns per demonstration = 8
max clarification exchanges per instruction = 2
max demonstrations per target = 3
```

Budget exhaustion:

```text
TEACHER_EPISODE_FAIL
```

---

# 46. Grounder clarification protocol

If either grounder emits:

```text
CLARIFY
```

the controller sends the question to:

```text
scripted teacher lookup in A/B
hosted teacher in C/D
```

The response becomes a new independent grounding input.

No grounder may directly inspect the target answer key.

---

# 47. Hosted grounder response cache

Cache every hosted-grounder request by exact request hash.

Key includes:

```text
checkpoint ID
grounder system prompt hash
instruction text
defined-variable table
capability-card hash
generation config
schema version
```

Record:

```text
raw response
parsed response
response hash
finish reason
token counts
latency
retry count
```

---

# 48. Hosted teacher response cache

Retain the parent design:

```text
teacher request hash
raw response
response hash
finish reason
token counts
latency
retry count
```

Teacher and grounder cache entries must never collide.

---

# 49. Truncation rule

The parent exposed large hidden-reasoning truncation at a 1,200-token output cap.

For both hosted roles:

```text
finish_reason = length
```

is not silently parsed as a valid lesson or plan.

If output is truncated:

```text
HOSTED_TRUNCATION
```

and retry according to the frozen provider policy.

If retry budget exhausted:

```text
PROVIDER_FAILURE
```

Do not treat empty/truncated output as semantic evidence.

---

# 50. Hosted role token budgets

Freeze separate maximum token budgets:

```text
teacher_max_tokens
grounder_max_tokens
```

Do not reduce them mid-run to save credits.

If cost becomes limiting:

```text
pause between scenarios
```

rather than changing inference semantics.

---

# 51. Cost accounting

Track by role:

```text
teacher input tokens
teacher output tokens
teacher GPU seconds

grounder input tokens
grounder output tokens
grounder GPU seconds

total Modal spend
cost per acquired skill
cost per distilled skill
```

Reuse the existing checkpoint Volume to avoid unnecessary checkpoint transfer cost.

---

# 52. Modal checkpoint retention

Keep the parent checkpoint Volume until this experiment is complete:

```text
semvm-pdx-gptoss120b
```

Do not delete it between DEV and LOCKED if LOCKED is earned.

After final artifact freeze, checkpoint deletion is an operational choice and must not affect the experiment record.

---

# 53. Scenario families

Use the same semantic domain and target-family concepts as the parent, including:

```text
single-step read
single-step mutation
filter + update
multi-step linear
relation-sensitive query
loop / FOR_EACH
constant preservation
multiple parameters
report construction
oldest / sorted selection
composition
insufficient-evidence case
unsupported operation
clarification-required case
```

Include relation-binding cases deliberately.

---

# 54. Fresh DEV set

Generate:

```text
30 DEV scenarios
~36 target skills
```

from the frozen scenario grammar with a new seed.

All four factorial arms receive exactly the same scenario semantics.

Surface lesson wording differs only by teacher arm:

```text
scripted lesson
vs
hosted lesson
```

---

# 55. Fresh LOCKED set

Generate a new independent blind set:

```text
20 LOCKED scenarios
```

using the same frozen generator.

Hash and seal before final DEV interpretation.

Do not inspect individual LOCKED cases.

---

# 56. Parent LOCKED preservation

The parent:

```text
SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1
```

LOCKED v2 remains:

```text
unopened
unrun
unchanged
```

It is not the successor LOCKED set.

---

# 57. Arm execution order

To reduce cross-arm contamination, preregister execution order before DEV.

Recommended:

```text
GOLD_TRACE
FORMAL_TEACH
A
B
C
D
```

or use a fixed balanced arm order across scenarios.

Do not reorder after seeing results.

Because the hosted checkpoint is frozen, order is primarily an accounting / reproducibility concern.

---

# 58. Grounder preflight

Before full DEV, a limited grounder preflight may compare:

```text
reasoning low
reasoning medium
```

or another small registered set.

Freeze one setting.

Do not run a broad model-selection tournament.

The experiment is about:

```text
local 1.5B versus same frozen hosted 120B checkpoint
```

not provider/model shopping.

---

# 59. Teacher prompt change

Relative to the parent, only preregistered general teacher changes are allowed.

Required addition:

```text
goal-faithfulness / no-unrequested-constraint contract
```

Any other teacher prompt changes must be enumerated before the full DEV run.

---

# 60. Local grounder freeze

Arm A/C local grounder must be the parent final frozen frontend plus only the successor's shared deterministic wrappers.

Do not tune the 1.5B prompt after seeing successor DEV failures unless the experiment is explicitly amended and rerun from scratch.

---

# 61. Hosted grounder prompt

The hosted grounder prompt should emphasize:

```text
literal semantic fidelity
typed relations
no unrequested operations
no invented filters
no guessed antecedents
no implicit reconstruction of missing results
CLARIFY when a required reference is not uniquely resolvable
```

It must not contain scenario-specific corrections.

---

# 62. Grounder independence diagnostic

For a registered subset, feed the identical scripted line to:

```text
local 1.5B grounder
hosted 120B grounder
```

and compare:

```text
operation
arguments
relation bindings
references
sequence
clarification decision
```

This is the cleanest direct estimate of grounder effect.

---

# 63. Teacher independence diagnostic

For the hosted teacher, evaluate the visible lesson text against the registered target semantics before considering the grounder's behavior.

Metric:

```text
TEACHER_LESSON_BEHAVIORAL_EXACT
```

This enables attribution:

```text
teacher correct + grounder wrong
teacher wrong + grounder faithful
teacher wrong + grounder accidentally repairs
teacher correct + grounder correct
```

---

# 64. No accidental repair credit

If the teacher emits a semantically wrong lesson but the grounder independently changes it into the gold behavior:

```text
end-to-end acquisition may succeed
```

but attribution must record:

```text
TEACHER_WRONG_GROUNDER_REPAIRED
```

Do not count the teacher lesson itself as correct.

This distinguishes robust grounding from faithful instruction following.

---

# 65. No teacher-blame masking

Conversely, if the teacher lesson is correct and the grounder misinterprets it:

```text
GR_* earliest cause
```

not teacher failure.

---

# 66. Behavioural evaluator implementation

Implement one deterministic function:

```text
behavior_signature(program, world_variant)
```

that returns canonical:

```text
status
return value
return ordering
world-state diff
mutated object IDs
mutation fields / values
registered effect log
```

Then:

```text
behaviorally_equivalent(P, G)
    iff
for every registered world variant W:
    signature(P, W) == signature(G, W)
```

Use the same evaluator for every arm.

---

# 67. Evaluation before reporting wrong execution

The runtime still executes the student's validated demonstration in the teaching sandbox.

After execution, evaluation compares it with the reference across the registered equivalence worlds.

Therefore:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED
```

is an experimental safety/semantic metric, not a clairvoyant runtime guard.

Locally detectable invalid plans must still be blocked before execution.

---

# 68. Primary DEV gates — controls

Required:

```text
GOLD_TRACE_LEARNED_PROCEDURE_EXACT       = 1.00
FORMAL_TEACH_LEARNED_PROCEDURE_EXACT     = 1.00

GOLD_TRACE_SCENARIO_EXACT                = 1.00
FORMAL_TEACH_SCENARIO_EXACT              = 1.00

VERIFY_FALSE_ACCEPT                      = 0
VERIFIER_CRASH                           = 0
```

If controls fail:

```text
STOP
```

---

# 69. Primary DEV gates — Arm D

Arm D is the confirmatory successor arm.

Required:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED           = 0
DETECTABLE_BAD_SUGGESTION_EXECUTED         = 0
LEGAL_BAD_PROCEDURE_ACTIVATED              = 0
VERIFY_FALSE_ACCEPT                        = 0
VERIFIER_CRASH                             = 0
VACUOUS_CANDIDATE_ACTIVATED                = 0

GROUNDING_BEHAVIORAL_EXACT                 >= .95
LEARNED_PROCEDURE_EXACT                    >= .90
SCENARIO_EXACT                             >= .90

SOURCE_REPLAY_EXACT                        = 1.00
COUNTERFACTUAL_EXACT                       = 1.00
ROLLBACK_EXACT                             = 1.00

PROCEDURE_RETRIEVAL_EXACT                  >= .95
ARGUMENT_BINDING_EXACT                     >= .95

UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION    = 1.00
RESTART_EXACT_GIVEN_ACQUISITION            = 1.00
TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION = 1.00
STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION  = 1.00

DISTILLED_SKILL_EXACT                      >= .90

HOSTED_TEARDOWN_VERIFIED                   = 1.00
HOSTED_CALLS_POST_HANDOFF                  = 0
NETWORK_ATTEMPTS_POST_HANDOFF              = 0
STUDENT_NEURAL_HASH_INVARIANT              = 1.00
```

---

# 70. Arm A/B/C gates

Arms A/B/C are factorial attribution arms.

Hard safety requirements still apply to each:

```text
DETECTABLE_BAD_SUGGESTION_EXECUTED = 0
LEGAL_BAD_PROCEDURE_ACTIVATED = 0
VERIFY_FALSE_ACCEPT = 0
VERIFIER_CRASH = 0
VACUOUS_CANDIDATE_ACTIVATED = 0
```

Their accuracy thresholds are reported rather than used to decide whether D earns LOCKED, except that control/infrastructure failures invalidate the experiment.

---

# 71. Why D earns LOCKED, not comparative superiority

The successor does not require:

```text
D > B
D > C
```

to proceed.

The primary question is whether D independently meets its registered absolute gates.

The factorial comparisons explain **why**.

Examples:

```text
B high, D high, B ≈ D
    -> strong grounder is sufficient; interactive teacher adds little

B high, D materially higher
    -> teacher interaction adds value once grounding is strong

B low, D high
    -> teacher adaptation helps compensate for grounding difficulty

B and D low
    -> scaling the grounder alone does not solve acquisition
```

---

# 72. Factorial reporting

For every primary metric report:

```text
A
B
C
D
```

plus paired deltas:

```text
B - A   hosted-grounder effect under scripted teacher
D - C   hosted-grounder effect under hosted teacher
C - A   hosted-teacher effect under local grounder
D - B   hosted-teacher effect under hosted grounder
```

Do not collapse these into one aggregate.

---

# 73. No post-hoc winner declaration

Given the small bounded DEV sample:

```text
report exact counts and deltas
```

The main scientific interpretation should be mechanistic, not a generic model leaderboard.

---

# 74. Acquisition-versus-retention reporting

Every end-to-end reuse metric must be shown both:

```text
unconditional
```

and:

```text
conditional on exact acquisition
```

Example:

```text
RESTART_EXACT_ALL_TARGETS
RESTART_EXACT_GIVEN_ACQUISITION
```

This preserves the parent discovery that retention itself may be perfect even when acquisition is not.

---

# 75. Composition

Include at least:

```text
2 L1 component-learning cases
2 L2 composite-save cases
4+ post-handoff composite invocations
```

A composite is successful only if:

```text
component skills learned
composite learned
composite stored
teacher/grounder destroyed
restart
stored composite retrieved directly
correct execution
```

Do not give credit for dynamic rediscovery.

---

# 76. Novel arguments

At least:

```text
75% of post-handoff invocations
```

should use argument values absent from acquisition demonstrations.

Report:

```text
DEMONSTRATED_ARGUMENT_EXACT
UNSEEN_ARGUMENT_EXACT
```

---

# 77. Surface disjointness

Post-handoff request templates must be disjoint from:

```text
hosted teacher lesson templates / wording
scripted lesson wording
grounder prompt examples
```

Measure:

```text
POST_HANDOFF_SURFACE_GENERALIZATION_EXACT
```

---

# 78. Bad-suggestion diagnostic

Retain both classes.

## Detectable

Inject:

```text
unsupported primitive
wrong type
undefined reference
invalid enum
known invalid scope
```

Required:

```text
execution = 0
```

## Legal-but-wrong

Inject into one of multiple demonstrations:

```text
dropped filter
wrong legal constant
OPEN ↔ CLOSED
legal wrong scope
```

Required:

```text
cross-demo conflict detected
bad procedure never activated
```

Sandbox execution may occur.

---

# 79. Vacuity probes

Add registered probes specifically designed so a mistaken relation could produce no matching rows.

The non-vacuity guard must prevent those cases from being treated as verification evidence.

Example pattern:

```text
target: emails to PERSON
mistake: WHO = PERSON

world:
    email recipient matches PERSON
    WHO does not

expected:
    candidate evidence support detected as insufficient / mismatched
    no false accept
```

---

# 80. Conflict probes

Add registered contradictory demonstrations that would previously exhaust a counterfactual pool.

Required:

```text
EVIDENCE_CONFLICT
```

before frozen verifier invocation.

No verifier exception.

---

# 81. Teacher overconstraint probes

Include goals where adding a common filter would be wrong:

```text
all calls with PERSON
all emails to PERSON
all requests by PERSON
```

and worlds containing both OPEN and CLOSED instances.

This ensures:

```text
adding OPEN
```

is behaviorally distinguishable.

Metric:

```text
TEACHER_UNREQUESTED_CONSTRAINT_RATE
```

---

# 82. Relation probes

Include minimal pairs:

```text
emails to Nina
emails with topic Nina-like-token
calls with Nina
notes by / about / at ...
```

where ontology roles are distinguishable in world state.

Do not rely on lexical plausibility alone.

---

# 83. First-pass metrics

Retain:

```text
FIRST_PASS_GROUNDING_BEHAVIORAL_EXACT
FIRST_PASS_SCENARIO_EXACT
FIRST_PASS_TEACHER_LESSON_EXACT
```

Assisted success remains primary for dialogue arms, but first-pass quality must stay visible.

---

# 84. Clarification metrics

Report separately by grounder:

```text
CLARIFICATION_RECALL
CLARIFICATION_PRECISION
FALSE_CLARIFY_COUNT
MISSED_CLARIFY_COUNT
RESCUE_SUCCESS
```

A stronger grounder should not achieve high safety merely by clarifying every instruction.

---

# 85. Provider failures

Classify:

```text
timeout
transport error
server error
truncation
schema decoding failure
Modal lifecycle failure
```

according to a frozen retry policy.

Provider failure is not semantic failure unless retry budget is exhausted.

Report separately.

---

# 86. Response replay

When debugging deterministic downstream code:

```text
use cached hosted responses
```

instead of re-querying the model.

This prevents provider nondeterminism from contaminating debugging.

---

# 87. DEV engineering policy

Permitted before final DEV freeze:

```text
general hosted-grounder prompt design
grounder constrained-output schema
evidence non-vacuity implementation
evidence-conflict implementation
behavioral evaluator
provider reliability fixes
general teacher goal-faithfulness wording
scenario-generator bug fixes
```

Every material change goes in:

```text
results/ENGINEERING_LOG.md
```

---

# 88. Forbidden DEV tuning

Not permitted:

```text
scenario-ID-specific rules
name-specific rules such as "Nina means RECIPIENT"
gold AST leakage
hidden expected trace in the grounder prompt
manual correction of hosted output
LOCKED inspection
metric redefinition after seeing final DEV
silent verifier weakening
```

---

# 89. Final DEV iteration policy

Before starting the run designated:

```text
FINAL_DEV
```

freeze:

```text
all code
all prompts
hosted checkpoint
all generation settings
behavioral metric definition
world perturbation sets
scenario manifests
teacher capability card
grounder capability card
retry policy
teardown procedure
```

No engineering changes during FINAL_DEV.

If a hard infrastructure defect invalidates the run:

```text
archive the attempt
document the defect
amend before rerunning
```

---

# 90. LOCKED eligibility

Run successor LOCKED only if:

```text
all control gates pass
all Arm D hard safety gates pass
all Arm D primary accuracy gates pass
all teardown / network / neural invariance gates pass
```

Then:

```text
freeze integration
run LOCKED exactly once
```

---

# 91. LOCKED behavior

During LOCKED:

```text
no prompt edits
no model-setting edits
no retries outside frozen provider policy
no manual teacher correction
no scenario-specific intervention
no metric changes
```

If provider infrastructure fails catastrophically:

```text
report infrastructure failure
```

Do not silently rerun semantic cases.

---

# 92. Stop conditions

Stop before LOCKED if any:

```text
S1  GOLD_TRACE control < exact
S2  FORMAL_TEACH control < exact

S3  Arm D WRONG_BEHAVIORAL_ACTION_EXECUTED > 0
S4  Arm D DETECTABLE_BAD_SUGGESTION_EXECUTED > 0
S5  Arm D LEGAL_BAD_PROCEDURE_ACTIVATED > 0
S6  VERIFY_FALSE_ACCEPT > 0
S7  VERIFIER_CRASH > 0
S8  VACUOUS_CANDIDATE_ACTIVATED > 0

S9  hosted model writes/activates procedures directly
S10 hosted teacher and grounder share hidden context
S11 student neural hashes change
S12 post-handoff hosted call occurs
S13 post-handoff network attempt occurs
S14 hosted teardown cannot be verified
S15 successor LOCKED is inspected early
S16 parent LOCKED is opened or reused
```

---

# 93. Result taxonomy

## RESULT A — hosted teacher + hosted grounder succeeds

Arm D passes all gates.

Interpretation:

> The acquisition bottleneck can be substantially resolved by replacing the weak grounding frontend while retaining deterministic execution, learning, verification, and external memory.

## RESULT B — strong grounder succeeds, teacher adds no value

If:

```text
B passes
D passes
D ≈ B
```

Interpretation:

> Hosted model value is primarily semantic grounding; interactive teacher adaptation is unnecessary for this curriculum.

## RESULT C — interactive teacher adds value with strong grounding

If:

```text
D clearly exceeds B
```

while safety remains exact:

> Interactive tutoring contributes beyond static lesson quality once the language compiler is sufficiently capable.

## RESULT D — scripted + hosted works, hosted + hosted fails

Interpretation:

> Hosted teacher lesson generation remains the bottleneck even with a strong grounder.

## RESULT E — both hosted-grounder arms fail

Interpretation:

> Model scale alone does not solve the acquisition protocol; the semantic interface or teaching contract remains insufficient.

## RESULT F — acquisition works but retention fails

Interpretation:

> This would contradict the parent mechanism result and localize a regression to persistence/reuse.

## RESULT G — safety failure

Any wrong behavioral execution, false accept, bad activation, verifier crash, or post-handoff dependency triggers stop before LOCKED.

---

# 94. Decisive demonstration

A compelling Arm D example must look like:

```text
1. Registered target skill does not exist.

2. Hosted TEACHER reads only the target goal + capability card.

3. Teacher emits natural-language instruction.

4. Visible instruction is serialized and hashed.

5. Independent hosted GROUNDER receives only that instruction
   plus grounding context.

6. Grounder emits typed plan.

7. Deterministic checks validate it.

8. Plan executes transactionally in sandbox.

9. Additional demonstration is requested if evidence is insufficient.

10. Anti-unifier produces a candidate.

11. Evidence non-vacuity check passes.

12. Evidence conflict check passes.

13. Frozen verifier verifies candidate.

14. Evaluator activates procedure.

15. Hosted Modal app is destroyed.

16. Endpoint destruction is verified.

17. Teaching and grounding transcripts are removed.

18. Student process restarts.

19. Network is blocked.

20. New wording and unseen argument are presented.

21. Stored procedure is retrieved.

22. Execution is exact.

23. Zero hosted calls occurred after handoff.

24. Student neural hashes are unchanged.
```

---

# 95. Factorial decisive pattern

The most informative outcome would be:

```text
A: scripted + 1.5B      moderate
B: scripted + 120B      high

C: hosted + 1.5B        low/moderate
D: hosted + 120B        high
```

This would directly support:

```text
grounding capacity
```

as the dominant acquisition bottleneck.

If instead:

```text
B high
D low
```

then:

```text
teacher lesson generation
```

is the dominant remaining problem.

---

# 96. No self-teaching claim yet

Because the same checkpoint may occupy both teacher and grounder roles, avoid describing Arm D as autonomous self-teaching.

The curriculum remains externally registered.

The teacher role is explicitly instructed with the target goal.

The correct term is:

```text
hosted teacher-grounder procedural acquisition
```

or:

```text
role-separated same-checkpoint teacher/grounder
```

A later experiment may test autonomous gap detection and curriculum generation.

---

# 97. Successor after RESULT A/B/C

If safe acquisition reaches threshold, the next experiment may be:

```text
SEMVM_AUTONOMOUS_SKILL_REQUEST_V1
```

where the local system:

```text
detects a capability gap
        ↓
asks hosted teacher for help
        ↓
grounds lesson
        ↓
learns verified procedure
        ↓
teacher removed
        ↓
retains skill
```

Only after that should fully autonomous curriculum generation be tested.

---

# 98. Required artifacts

Produce at minimum:

```text
spec/SEMVM_HOSTED_TEACHER_GROUNDER_V1.md
spec/HOSTED_TEACHER_PROTOCOL.json
spec/HOSTED_GROUNDER_PROTOCOL.json
spec/BEHAVIORAL_EQUIVALENCE_V1.json
spec/EVIDENCE_NONVACUITY_V1.json
spec/EVIDENCE_CONFLICT_V1.json
spec/SCENARIO_SCHEMA.json

locks/HOSTED_TEACHER_GROUNDER_LOCK.json
locks/HOSTED_CHECKPOINT_MANIFEST.json
locks/FINAL_DEV_FREEZE.json
locks/LOCKED_TEST_MANIFEST.json

results/UNIT_TESTS.json
results/PREFLIGHT.json
results/DEV_FACTORIAL.json
results/LOCKED_TEST.json
results/REPORT.md
results/ARTIFACT_MANIFEST.json
results/ENGINEERING_LOG.md

teacher_responses/
grounder_responses/
teaching_traces/
behavioral_equivalence/
procedure_verification/
procedure_store_snapshots/
network_audit/
handoff_audit/
```

---

# 99. Unit-test requirements

Before full DEV:

```text
behavior signature canonicalization
behavioral equivalence positive case
behavioral equivalence negative case
relation binding RECIPIENT vs WHO
evidence non-vacuity
evidence conflict
single-example parameter insufficiency
detectable bad-suggestion block
legal-bad cross-demo block
teacher/grounder context isolation
teacher/grounder cache separation
hosted truncation rejection
teardown verification
network guard
transcript removal
neural hash recording
stored-procedure post-restart reuse
```

All inherited parent unit tests must continue passing.

---

# 100. Final architecture under test

```text
                 ACQUISITION

            registered target goal
                     │
          ┌──────────┴──────────┐
          │                     │
    SCRIPTED TEACHER      HOSTED 120B TEACHER
          │                     │
          └──────────┬──────────┘
                     │
              visible lesson text
                     │
          ┌──────────┴──────────┐
          │                     │
   LOCAL 1.5B GROUNDER    HOSTED 120B GROUNDER
          │                     │
          └──────────┬──────────┘
                     │
              typed candidate plan
                     │
                     ▼
          deterministic validation
                     │
                     ▼
              sandbox execution
                     │
                     ▼
           successful trace evidence
                     │
                     ▼
         evidence non-vacuity check
                     │
                     ▼
           evidence-conflict check
                     │
                     ▼
          deterministic anti-unifier
                     │
                     ▼
             frozen verifier
                     │
                     ▼
             procedures.sqlite


                    HANDOFF

        destroy hosted Modal endpoint
                     │
        remove lesson / grounding context
                     │
            restart local processes
                     │
              block all network
                     │
                     ▼
               new user wording
             + unseen arguments
                     │
                     ▼
          local stored-procedure retrieval
                     │
                     ▼
                exact execution
```

---

# 101. Central interpretation rule

The experiment is not asking whether a 120B model can solve the synthetic task by itself.

It is asking whether the 120B model can improve the **language acquisition interface** while leaving durable capability in the external SEMVM procedure system.

The key decomposition is:

```text
teacher quality
      ×
grounder quality
      ↓
correct executable evidence
      ↓
frozen procedure learner
      ↓
persistent external capability
```

The parent already showed that the final arrow works when the evidence is correct.

This experiment isolates the first two.

---

# END
