# SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1

**Project:** Stateful Semantic VM — LLM-to-SEMVM Procedural Distillation  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Parent experiments:** `SEMVM_PROCEDURE_DISCOVERY_POC_V1`; `SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1`  
**Primary teacher:** Groq-hosted LLM through the existing Groq integration  
**Primary student:** frozen local SEMVM language frontend + frozen procedure-learning stack  
**Primary goal:** Determine whether a stronger hosted LLM can teach durable executable procedures to SEMVM through dialogue, such that the learned skill remains usable after the Groq teacher is disconnected and all local processes restart.

---

# 0. Executive summary

The procedure-discovery parent established that SEMVM can convert successful execution traces into verified persistent procedures and later reuse them on new arguments, after restart, without neural weight updates.

The natural-language teaching successor established a second result:

```text
GOLD_TRACE      = exact
FORMAL_TEACH    = exact
NL_TEACH        = below registered gates
```

The bottleneck was not procedure abstraction, verification, storage, retrieval, or VM execution. It was:

```text
natural language
        ↓
safe, complete executable teaching trace
```

with the frozen Qwen2.5-Coder-1.5B frontend.

This experiment introduces a stronger external teacher while preserving SEMVM as the learner and judge.

Target architecture:

```text
Groq teacher LLM
        │
        │ natural-language lesson / correction / answer
        ▼
frozen SEMVM student frontend
        │
        ▼
typed candidate plan
        │
        ▼
deterministic semantic + dataflow checks
        │
        ▼
sandbox execution
        │
        ▼
successful trace(s)
        │
        ▼
frozen anti-unifier
        │
        ▼
frozen evidence-based verifier
        │
        ▼
procedures.sqlite
        │
        ▼
TEACHER DISCONNECTED
        │
        ▼
full restart
        │
        ▼
new wording + unseen arguments
        │
        ▼
stored procedure executes correctly
```

The decisive question is:

> Can knowledge supplied conversationally by a stronger hosted LLM be converted into persistent executable procedural knowledge in the smaller SEMVM system, with no neural weight updates and no need for the teacher after learning?

This is **procedural distillation**, not weight distillation.

---

# 1. Primary hypothesis

A strong external LLM can serve as a non-authoritative procedural teacher:

```text
teacher knowledge
        ↓
dialogue
        ↓
student-grounded successful execution
        ↓
verified reusable procedure
```

such that:

```text
teacher online during acquisition
teacher absent during reuse
```

and the acquired procedure remains correct.

---

# 2. Strongest permitted claim

If all registered gates pass:

> Within the registered Semantic VM domain, a stronger Groq-hosted language model can teach new executable procedures to a smaller frozen SEMVM student through dialogue. The student grounds and executes the lesson, learns only from validated execution traces, independently verifies the resulting procedure, persists it outside neural weights, and later reuses it after the teacher is disconnected and the system is restarted.

This does **not** establish:

```text
general autonomous self-improvement
open-domain skill acquisition
arbitrary tool learning
new primitive invention
weight-level model distillation
general English understanding
general software engineering
unrestricted code synthesis
```

---

# 3. Core scientific separation

The experiment must preserve four distinct roles:

```text
TEACHER
    proposes knowledge / lessons

STUDENT FRONTEND
    interprets teacher language

ENVIRONMENT + VM
    determines what actually executes

VERIFIER
    determines what becomes persistent knowledge
```

The teacher is never the judge. The student never learns directly from the teacher's confidence or self-assessment.

---

# 4. Non-authoritative teacher rule

Groq may:

```text
explain a procedure
give demonstrations
rephrase an instruction
answer student clarifications
suggest sequencing
suggest use of an existing primitive
suggest use of an ACTIVE procedure
provide another example
```

Groq may not:

```text
write directly into procedures.sqlite
activate a procedure
declare a candidate VERIFIED
bypass deterministic validation
invent VM opcodes
mutate the world directly
supply hidden gold ASTs
approve its own candidate
```

Teacher output becomes learning evidence only after the student successfully grounds and executes it.

---

# 5. Parent results frozen

## 5.1 Procedure discovery

The parent procedure learner has already demonstrated:

```text
persistent external procedure storage
new-argument reuse
post-restart reuse
composition
stored-composite reuse
zero neural weight updates
```

within its registered domain.

## 5.2 Natural-language teaching

The NL teaching experiment stopped at DEV.

Controls were exact:

```text
GOLD_TRACE      1.0
FORMAL_TEACH    1.0
```

The local 1.5B frontend did not meet the registered language-grounding/safety gates.

The untouched NL-teaching LOCKED set remains unopened and must remain untouched in this experiment.

---

# 6. Why a new LOCKED set is required

This experiment changes the task from:

```text
human/scripted NL teaching
```

to:

```text
interactive external-teacher dialogue
```

Therefore the prior unopened NL-teaching LOCKED set must **not** be repurposed as the primary locked evaluation here.

Create a new independently seeded:

```text
GROQ_DISTILLATION_LOCKED_TEST
```

for this experiment.

Preserve the old NL-teaching LOCKED set unchanged for a future stronger-frontend replication of the original task.

---

# 7. Stage -1: reproducibility prerequisite

Before beginning the primary science run:

```text
freeze parent source
freeze parent specs
freeze parent result files
freeze environment manifest
freeze model hashes
```

Preferred:

```text
build the portable bundle required by the standing portability protocol
```

At minimum, the experiment must have a complete artifact manifest and clean launch path.

Do not run any locked evaluation as part of portability validation.

---

# 8. Parent runtime components frozen

Freeze the successful downstream machinery:

```text
procedure AST schema
program hashing
anti-unification
static procedure validation
evidence-based verifier
state perturbation
negative cases
rollback injection
procedure lifecycle
procedure store
versioning
retrieval stack
argument repair
typed fallback
type-directed composition
canonical plan equivalence
stored-procedure preference
world model
primitive inventory
executor
transaction semantics
```

A teacher experiment may not silently modify these to compensate for poor teacher/student dialogue.

Any downstream change requires an explicit amendment and revalidation of GOLD/FORMAL controls.

---

# 9. Mandatory baseline fixes inherited from NL_TEACH

The two known unresolved V1.2 defects become preregistered baseline requirements here.

## 9.1 Failed multi-clause split

If an utterance contains an apparent sequencing connector such as:

```text
and
then
and then
;
```

and clause decomposition fails or yields incompatible fragments:

```text
CLARIFY
```

Do not silently execute an incompatible whole-sentence fallback.

## 9.2 Evidence sufficiency before learning

Before `:learn`, `:propose`, or equivalent procedure abstraction:

```text
check whether the evidence is sufficient to distinguish
parameters from constants
```

For an unhinted candidate with only one evidential value for a potentially varying slot:

```text
REQUIRE_SECOND_DEMONSTRATION
```

The verifier must not be asked to distinguish hypotheses the supplied evidence cannot distinguish.

---

# 10. Groq integration

Use the existing Groq integration rather than building a one-off caller.

Required environment:

```text
GROQ_API_KEY
```

The key must never be written into:

```text
logs
reports
traces
manifests
procedure provenance
```

Use the existing provider abstraction where possible.

Conceptual interface:

```text
GenerationResult generate(
    messages,
    model,
    generation_config,
    optional_schema
)
```

---

# 11. Groq provenance

For every teacher call, record:

```text
provider = "groq"
model identifier
request identifier if available
timestamp
prompt/template version
prompt hash
generation settings
input token count if available
output token count if available
latency
response hash
retry count
```

Do not store secrets.

Teacher provenance should be linkable to the procedure-learning trace.

---

# 12. Teacher model selection

Do not hard-code the scientific claim to one Groq model before DEV.

During a **teacher-selection preflight only**, compare a small registered set of Groq-hosted candidates.

Selection criteria:

```text
lesson correctness
instruction completeness
clarification usefulness
unsupported-operation rate
student trace success
cost / latency
```

Freeze one teacher model before full DEV.

After the full DEV begins:

```text
teacher model ID is frozen
```

No teacher-model switching based on scenario failures.

---

# 13. Teacher generation policy

Default:

```text
temperature = 0 or lowest deterministic supported setting
sampling minimized
```

Record exact provider settings.

If the hosted API cannot guarantee bitwise repeatability:

```text
record every raw teacher response
```

and treat response hashes as the experimental record.

---

# 14. Student neural component

Primary student language frontend remains the frozen local:

```text
Qwen2.5-Coder-1.5B base
```

unless an amendment is made **before full DEV**.

Record:

```text
weight hashes
tokenizer hashes
generation settings
prompt hash
worker identity
```

No optimizer. No weight changes.

---

# 15. Student deterministic frontend

Retain and freeze the semantic/compiler checks developed in NL_TEACH, including:

```text
typed operation validation
argument legality
defined-before-use
reference antecedent checks
dead pure-result checks
required-output checks
clause coverage
plan completeness
transactional execution
clarification state scoping
unsupported-operation rejection
```

Teacher quality is not allowed to replace these guards.

---

# 16. Teacher capability card

The teacher receives a machine-generated capability card describing what the student can do.

It may include:

```text
available object/event types
available relations
available primitives
primitive argument signatures
ACTIVE procedure names and signatures
unsupported effect classes
teaching protocol
clarification protocol
```

It must not include:

```text
gold target procedure AST
gold expected trace
LOCKED answer
hidden verifier cases
counterfactual gold outputs
```

---

# 17. Teacher objective

For a registered target skill, the teacher is asked to:

```text
teach the student how to perform the skill
using only available capabilities
```

The teacher may choose:

```text
one demonstration
multiple demonstrations
incremental steps
compact multi-step instructions
rephrasing after clarification
examples with different arguments
```

The student remains responsible for grounding.

---

# 18. Primary interaction protocol

For each skill acquisition episode:

```text
1. Initialize registered world state.

2. Provide teacher with:
       goal
       capability card
       allowed interaction protocol

3. Teacher sends a lesson utterance.

4. Student grounds the utterance.

5. Deterministic validator checks the complete proposed plan.

6. If valid:
       execute in sandbox
       append successful trace evidence.

7. If ambiguous/invalid:
       student sends a clarification/question to teacher.

8. Teacher answers.

9. Continue until:
       successful demonstration complete
       OR turn budget exhausted.

10. If evidence is insufficient for abstraction:
       student requests another demonstration.

11. Teacher supplies another example.

12. Frozen anti-unifier proposes procedure.

13. Frozen verifier tests procedure.

14. Evaluator issues the external ACCEPT event only if VERIFIED.

15. Procedure becomes ACTIVE.
```

---

# 19. Teacher turn budget

Register a finite budget.

Recommended initial limits:

```text
max teacher turns per demonstration: 8
max clarification exchanges per instruction: 2
max demonstrations per target procedure: 3
```

If exceeded:

```text
TEACHER_EPISODE_FAIL
```

Do not allow unlimited dialogue until success.

---

# 20. Teaching sandbox

Every lesson executes in a sandboxed world snapshot.

Teacher/student demonstrations may mutate the sandbox.

After acquisition:

```text
procedure persists
teaching-world mutations are discarded
```

unless the scenario explicitly tests persistence of world state.

---

# 21. Teacher cannot see hidden evaluation state

The teacher may observe only what a real tutor would reasonably receive:

```text
task goal
student capability card
student questions
student-reported execution outputs
```

The teacher must not receive:

```text
hidden gold procedure
hidden evaluator annotations
future locked requests
hidden counterfactual tests
```

---

# 22. Student questions

The student may ask questions such as:

```text
"Which result does 'them' refer to?"

"Do you mean the earliest WHEN value?"

"I do not have a primitive for sending Slack messages.
Can you express the skill using available operations?"

"I have only one demonstration.
Should the person name vary, or remain fixed?"
```

Teacher answers remain non-authoritative and are grounded/checked normally.

---

# 23. Example teacher episode

Target skill:

```text
close_oldest_open_request(person)
```

Teacher:

```text
Find the person's open requests.
Sort those requests by their time from earliest to latest.
Take the first request.
Close it.
Return the request you changed.
```

Student trace:

```text
r = FIND(type=REQUEST, person=Alice, status=OPEN)
s = SORT(r, key=WHEN, order=ASC)
x = SELECT(s, FIRST)
SET_STATE(x, CLOSED)
RETURN x
```

Second demonstration:

```text
person=Bob
```

Then:

```text
anti-unify
→ close_oldest_open_request(person)
```

---

# 24. Distillation definition

A skill counts as successfully distilled only if all are true:

```text
teacher supplied the instructional knowledge
student grounded and executed valid traces
procedure was learned from those traces
procedure passed independent verification
procedure was persisted
teacher was disconnected
all relevant processes restarted
student later retrieved and used the stored procedure
new invocation used unseen arguments and/or wording
no teacher call occurred during reuse
```

---

# 25. Hard teacher disconnect

After acquisition:

```text
terminate teacher session
clear teacher conversation
remove teacher client state
unset or revoke GROQ_API_KEY in the evaluation process
optionally block network egress to Groq
restart scenario process
restart local LLM service
```

Then run reuse evaluation.

Required metric:

```text
POST_HANDOFF_GROQ_CALLS = 0
```

---

# 26. Teacher-disconnect gate

Define:

```text
TEACHER_DISCONNECT_REUSE_EXACT
```

A case is exact only if:

```text
teacher disconnected
student restarted
teaching transcript absent
new request presented
stored procedure retrieved
correct new arguments bound
correct execution occurs
```

Required:

```text
TEACHER_DISCONNECT_REUSE_EXACT = 1.00
```

---

# 27. No transcript leakage

Post-handoff student context must not contain:

```text
teacher lesson text
teacher chain of dialogue
teacher demonstrations
teacher explanations
```

Permitted persistent artifacts:

```text
verified procedure
procedure provenance hashes
world state
procedure aliases
registered metadata
```

The student may know that the procedure exists. It may not replay the lesson.

---

# 28. Neural-weight invariance

Record student neural hashes:

```text
before teacher interaction
after teacher interaction
after restart
end of scenario
```

Required:

```text
all identical
optimizer steps = 0
```

Teacher weights are external and are not part of the student's stored capability.

---

# 29. Primary control modes

Run the same registered scenario semantics in:

## A. GOLD_TRACE

```text
gold execution trace
→ frozen procedure learner
```

Required exact.

## B. FORMAL_TEACH

```text
formal step language
→ trace
→ frozen procedure learner
```

Required exact.

## C. GROQ_TEACH

```text
Groq teacher dialogue
→ student grounding
→ validated execution trace
→ frozen procedure learner
```

Primary experimental arm.

---

# 30. Scripted-teacher control

Recommended additional control:

## D. SCRIPTED_TEACHER

A deterministic teacher emits a registered natural-language lesson.

Purpose:

```text
separate teacher reasoning/adaptation
from merely receiving better-written instructions
```

The scripted teacher may not adapt to student questions except via registered lookup responses.

---

# 31. Optional direct-Groq-program diagnostic

Diagnostic only:

```text
goal
→ Groq teacher writes final procedure AST directly
→ static validation
→ verifier
```

Never activate without the normal verifier.

Report:

```text
DIRECT_GROQ_AST_EXACT
```

against:

```text
TRACE_MEDIATED_GROQ_PROCEDURE_EXACT
```

This tests whether conversational trace-mediated distillation is more reliable than direct program synthesis.

---

# 32. Acquisition metrics

Report:

```text
TEACHER_EPISODE_SUCCESS
TEACHER_TURNS
TEACHER_DEMONSTRATIONS
STUDENT_CLARIFICATION_COUNT
STUDENT_TRACE_EXACT
LEARNED_PROCEDURE_EXACT
SOURCE_REPLAY_EXACT
COUNTERFACTUAL_EXACT
VERIFY_FALSE_ACCEPT
```

---

# 33. Teacher-language metrics

Report:

```text
TEACHER_INSTRUCTION_GROUNDING_EXACT
TEACHER_ACTION_OP_EXACT
TEACHER_ACTION_ARGUMENT_EXACT
TEACHER_SEQUENCE_EXACT
REFERENCE_BINDING_EXACT
CLAUSE_COVERAGE
```

---

# 34. Safety metrics

Report:

```text
WRONG_TEACHER_ACTION_PROPOSED
WRONG_TEACHER_ACTION_BLOCKED
WRONG_TEACHER_ACTION_EXECUTED

UNSUPPORTED_TEACHER_ACTION
UNSUPPORTED_TEACHER_ACTION_BLOCKED

VERIFY_FALSE_ACCEPT
ROLLBACK_EXACT
NEGATIVE_CASE_SAFE
```

Hard requirements:

```text
WRONG_TEACHER_ACTION_EXECUTED = 0
VERIFY_FALSE_ACCEPT = 0
```

---

# 35. Reuse metrics

After teacher disconnect:

```text
PROCEDURE_RETRIEVAL_EXACT
ARGUMENT_BINDING_EXACT
UNSEEN_ARGUMENT_EXACT
SURFACE_GENERALIZATION_EXACT
RESTART_PROCEDURE_EXACT
TEACHER_DISCONNECT_REUSE_EXACT
STORED_PROCEDURE_REUSE_EXACT
FINAL_STATE_EXACT
```

---

# 36. Composition metrics

Include:

```text
COMPOSITION_L1_EXACT
COMPOSITION_L2_SAVE_EXACT
COMPOSITION_L2_REUSE_EXACT
```

At least some composite procedures must be taught by Groq using already ACTIVE student procedures.

After disconnect:

```text
stored composite must be reused
```

rather than reconstructed with Groq.

---

# 37. Distillation-specific metric

Define:

```text
DISTILLED_SKILL_EXACT
```

A skill counts only if:

```text
acquisition succeeded
procedure verified
procedure persisted
teacher disconnected
restart occurred
new invocation succeeded
```

Primary gate:

```text
DISTILLED_SKILL_EXACT >= .90
```

with hard subgates below.

---

# 38. Teacher dependence metrics

Track:

```text
TEACHER_CALLS_DURING_ACQUISITION
TEACHER_CALLS_POST_HANDOFF
TEACHER_TOKENS_PER_SKILL
TEACHER_SECONDS_PER_SKILL
TEACHER_COST_PER_SKILL
```

Required:

```text
TEACHER_CALLS_POST_HANDOFF = 0
```

---

# 39. Capability-growth accounting

For each scenario record:

```text
active procedures before
active procedures after
procedure library bytes before
procedure library bytes after
student neural parameter count
student neural hashes
```

The desired pattern is:

```text
neural parameters     constant
procedure capability  increases
```

---

# 40. Novel-argument requirement

Most post-distillation invocations must use values absent from demonstrations.

Report separately:

```text
DEMONSTRATED_ARGUMENT_EXACT
UNSEEN_ARGUMENT_EXACT
```

Target at least:

```text
>= 75% of post-handoff invocations use never-demonstrated arguments
```

---

# 41. New-wording requirement

Post-handoff invocation wording must be disjoint from teacher lesson wording.

The student should not succeed by matching a memorized teacher sentence.

Report:

```text
POST_HANDOFF_SURFACE_GENERALIZATION_EXACT
```

---

# 42. Teacher rephrasing test

Some scenarios should intentionally induce a student clarification or rejected grounding.

Teacher must rephrase.

Measure:

```text
TEACHER_REPHRASE_SUCCESS
```

This tests whether interactive tutoring adds value over a static lesson.

---

# 43. Insufficient-evidence test

Include scenarios where one demonstration cannot determine parameterization.

Student must request another demonstration.

Teacher provides a second example with a changed value.

Required:

```text
INSUFFICIENT_EVIDENCE_DETECTED = 1.0
SECOND_DEMO_REQUEST_EXACT = 1.0
```

No single-example constant procedure may be accepted when the registered abstraction is underdetermined.

---

# 44. Unsupported-teacher test

Include teacher outputs that reference unavailable actions, either naturally occurring or deliberately injected in a diagnostic subset.

Example:

```text
"Send the report by Slack."
```

when no Slack primitive exists.

Required behavior:

```text
UNSUPPORTED
or
ask teacher to reformulate using available capabilities
```

Forbidden:

```text
invent arbitrary shell / HTTP / Python
```

---

# 45. Bad-teacher-candidate diagnostic

Inject a small registered set of deliberately wrong teacher suggestions:

```text
wrong constant
dropped filter
wrong scope
wrong argument type
unsupported primitive
premature RETURN
```

Student must block or clarify.

Required:

```text
BAD_TEACHER_SUGGESTION_EXECUTED = 0
```

---

# 46. Teacher adaptation versus static knowledge

Classify successful teacher episodes:

```text
FIRST_LESSON_SUCCESS
REPHRASE_SUCCESS
CLARIFICATION_SUCCESS
SECOND_DEMO_SUCCESS
```

This tells us whether the teacher contributes through:

```text
better initial instructions
```

or:

```text
interactive adaptation
```

---

# 47. Curriculum source

Primary experiment uses a registered fixed curriculum of target skills.

The teacher does not choose the test target.

This prevents:

```text
teacher chooses only easy skills
```

A later experiment may allow teacher-generated curriculum.

---

# 48. Procedure families

Use the existing domain and construct a teacher curriculum spanning:

```text
single-step read
single-step state mutation
multi-step linear
filter + state update
loop / FOR_EACH
constant preservation
multiple parameters
report construction
nested procedure call
composition
clarification-required
insufficient-evidence
unsupported-operation
```

---

# 49. Domain freeze

Use the same Semantic VM world as the parent procedure experiments.

Do not add a new ontology merely to make teacher demonstrations easier.

Freeze:

```text
world schema
STATUS
REPORT
primitive inventory
type rules
```

before DEV.

---

# 50. Teacher lesson styles

Stratify:

```text
STYLE A
direct stepwise instruction

STYLE B
compact natural-language procedure

STYLE C
interactive Socratic / question-answer

STYLE D
example-based teaching

STYLE E
procedure composition using existing named skills
```

Report separately.

---

# 51. Student-local frontend baseline

Retain the final frozen local frontend behavior from the NL_TEACH experiment as a diagnostic baseline.

Do not erase the historical result.

Report:

```text
LOCAL_NL_V1_FINAL
vs
GROQ_TEACH
```

on comparable DEV scenario semantics where possible.

---

# 52. What Groq is allowed to improve

Groq may improve:

```text
instruction wording
instruction decomposition
choice of demonstrations
responses to student clarification
selection of useful second examples
```

Groq may not improve the score by receiving:

```text
gold AST
gold trace
hidden expected action sequence
verifier answer key
locked test annotations
```

---

# 53. First-pass versus assisted performance

Report:

```text
DISTILLATION_FIRST_PASS
DISTILLATION_ASSISTED
```

First-pass:

```text
teacher's initial lesson succeeds without clarification/rephrasing
```

Assisted:

```text
bounded teacher/student dialogue succeeds within turn budget
```

The primary experiment may use assisted performance, but first-pass must remain visible.

---

# 54. Primary DEV gates

Recommended:

```text
GOLD_TRACE learned procedure exact              = 1.00
FORMAL_TEACH learned procedure exact            = 1.00

WRONG_TEACHER_ACTION_EXECUTED                   = 0
BAD_TEACHER_SUGGESTION_EXECUTED                 = 0
VERIFY_FALSE_ACCEPT                             = 0

STUDENT_TRACE_EXACT                             >= .90
LEARNED_PROCEDURE_EXACT                         >= .90

SOURCE_REPLAY_EXACT                             = 1.00
COUNTERFACTUAL_EXACT                            = 1.00
ROLLBACK_EXACT                                  = 1.00

PROCEDURE_RETRIEVAL_EXACT                       >= .95
ARGUMENT_BINDING_EXACT                          >= .95
UNSEEN_ARGUMENT_EXACT                           = 1.00
RESTART_PROCEDURE_EXACT                         = 1.00
TEACHER_DISCONNECT_REUSE_EXACT                  = 1.00
STORED_PROCEDURE_REUSE_EXACT                    = 1.00

DISTILLED_SKILL_EXACT                           >= .90
POST_HANDOFF_GROQ_CALLS                         = 0
```

---

# 55. Why reuse gates remain strict

The central claim is not:

```text
Groq can solve the task
```

It is:

```text
Groq can teach the student a skill
that the student retains after Groq is gone
```

Therefore post-handoff gates are intentionally stricter than teacher-session acquisition gates.

---

# 56. DEV / LOCKED counts

Recommended:

```text
DEV:
    30 scenarios

LOCKED:
    20 scenarios
```

Each scenario may teach one or more procedures.

Ensure meaningful coverage of:

```text
new arguments
new wording
restart
composition
insufficient evidence
teacher clarification
unsupported suggestion
```

---

# 57. Locked generation

A separate blind generator/agent should create:

```text
GROQ_DISTILLATION_LOCKED_TEST
```

using the frozen scenario grammar.

Before full DEV tuning completes:

```text
freeze LOCKED manifest
hash it
do not inspect individual scenarios
```

If a generator defect is discovered from DEV before locked exposure:

```text
archive unopened locked set as INVALIDATED_BEFORE_RUN
fix generator
create fresh independent locked set
```

---

# 58. No reuse of prior NL LOCKED

The unopened:

```text
SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1 LOCKED_TEST
```

must remain untouched.

This experiment has its own lock.

---

# 59. Full integration freeze before LOCKED

Freeze:

```text
Groq provider code
Groq teacher model ID
teacher system prompt
teacher capability-card template
teacher generation settings
student model hash
student prompt
student deterministic frontend
all baseline fixes
procedure learner
verifier
procedure store
executor
scenario generator
DEV manifest
LOCKED manifest
```

No edits after freeze.

---

# 60. One locked run

If and only if all registered DEV gates pass:

```text
run LOCKED exactly once
```

No prompt tuning.

No provider/model switching.

No scenario-specific repair.

No rerun because of an undesirable score.

---

# 61. Failure taxonomy

Teacher-side:

```text
GT_UNSUPPORTED
GT_WRONG_STEP
GT_WRONG_ARGUMENT
GT_INCOMPLETE
GT_BAD_REPHRASE
GT_INSUFFICIENT_DEMOS
GT_TURN_BUDGET
```

Student grounding:

```text
SG_SCHEMA
SG_OP
SG_ARGUMENT
SG_SEQUENCE
SG_REFERENCE
SG_FALSE_CLARIFY
SG_MISSED_CLARIFY
SG_CLAUSE_COVERAGE
SG_OUTPUT_OBLIGATION
SG_USE_BEFORE_DEFINITION
```

Procedure learning:

```text
PD_INSUFFICIENT_EVIDENCE
PD_PARAMETER
PD_PROGRAM
PD_VERIFY_FALSE_ACCEPT
PD_VERIFY_FALSE_REJECT
```

Reuse:

```text
PR_RETRIEVE
PR_ARGUMENT
PR_COMPOSE
PR_DYNAMIC_REPLAN
PR_TEACHER_DEPENDENCE
```

Runtime:

```text
VM_EXEC
ROLLBACK
STORE
RESTART
```

---

# 62. Earliest-cause localization

Count the earliest causal failure.

Example:

```text
teacher gives correct lesson
→ student drops clause
→ trace wrong
→ procedure wrong
→ post-restart fails
```

Primary failure:

```text
SG_CLAUSE_COVERAGE
```

Do not count all downstream effects as independent root causes.

---

# 63. Teacher value decomposition

For every successful skill, report whether success required:

```text
teacher initial lesson only
teacher rephrase
teacher clarification answer
teacher second demonstration
teacher composition explanation
```

This distinguishes:

```text
stronger static instruction generation
```

from:

```text
interactive tutoring
```

---

# 64. Direct program writing comparison

Because the prior NL experiment found a large gap between direct program writing and trace-mediated learning, retain a direct-program diagnostic for Groq.

Compare:

```text
DIRECT_GROQ_AST_EXACT
vs
TRACE_MEDIATED_GROQ_PROCEDURE_EXACT
```

This is descriptive.

The production learning path remains trace-mediated.

---

# 65. Cost accounting

Record:

```text
Groq teacher input tokens
Groq teacher output tokens
Groq calls per skill
Groq latency per call
Groq acquisition latency per skill
Groq billed cost if available
local student calls
local grounding latency
verification latency
post-handoff retrieval latency
execution latency
```

Do not hard-code provider prices into the spec.

---

# 66. Distillation efficiency

Report:

```text
VERIFIED_SKILLS_PER_1K_TEACHER_TOKENS
VERIFIED_SKILLS_PER_MINUTE
VERIFIED_SKILLS_PER_DOLLAR
```

where billing data exists.

These are engineering metrics, not primary scientific gates.

---

# 67. Procedure provenance

Store for each learned procedure:

```text
procedure hash
teacher provider
teacher model ID
teacher prompt hash
teacher response hashes
teacher request IDs if available
teaching transcript hash
successful trace hashes
abstraction evidence hashes
verification manifest hash
activation event
```

Do not store secrets.

---

# 68. Teacher removal audit

After handoff, assert:

```text
no active Groq client
no GROQ_API_KEY in evaluation subprocess
no teacher transcript in model context
no teacher response cache mounted into scenario
no Groq HTTP requests
```

A hidden network monitor/log is recommended.

---

# 69. Strong decisive demo

The minimum compelling demonstration is:

```text
1. Student does not have procedure P.

2. Groq teacher is connected.

3. Teacher explains P in natural language.

4. Student asks clarification if needed.

5. Student executes a successful demonstration.

6. Student requests another example if evidence is insufficient.

7. Student executes second demonstration.

8. Frozen anti-unifier derives P.

9. Frozen verifier accepts P.

10. External evaluator activates P.

11. Groq teacher is disconnected.

12. GROQ_API_KEY is removed from evaluation process.

13. Student process is killed.

14. Local LLM service is killed.

15. Student restarts with no teacher transcript.

16. User asks for P in different language.

17. Argument was never demonstrated.

18. Student retrieves P from procedures.sqlite.

19. P executes exactly.

20. Network audit confirms zero Groq calls after handoff.

21. Student neural hashes are unchanged.
```

---

# 70. Composition decisive demo

Stronger version:

```text
Teacher teaches P1.
Teacher teaches P2.

Student verifies and stores both.

Teacher then teaches:
    P3 = composition of P1 and P2.

Student verifies and stores P3.

Teacher is disconnected.

Full restart.

New user request matches P3.

Student retrieves P3 itself,
not P1/P2 through dynamic rediscovery,
and executes exactly.
```

---

# 71. Result interpretation

## RESULT A — procedural distillation succeeds

All hard gates pass.

Interpretation:

> Stronger-model procedural knowledge was converted into durable external executable skill in the smaller system.

## RESULT B — teacher helps acquisition, but post-handoff fails

Interpretation:

> The teacher acts as online scaffolding rather than producing durable independent capability.

## RESULT C — teacher lessons are good, student grounding fails

Controls exact; teacher content diagnostically correct; student traces wrong.

Interpretation:

> Student language compiler remains the bottleneck even with a stronger teacher.

## RESULT D — student traces are correct, procedure learner fails

Interpretation:

> Unexpected regression in the frozen downstream machinery; investigate before any locked run.

## RESULT E — unsafe teacher action executes

If:

```text
WRONG_TEACHER_ACTION_EXECUTED > 0
```

stop before LOCKED.

## RESULT F — verifier false-accepts

If:

```text
VERIFY_FALSE_ACCEPT > 0
```

stop before LOCKED.

## RESULT G — teacher not needed

If scripted/static teaching matches Groq and teacher adaptation adds no measurable value:

> Hosted teacher reasoning is not necessary for the registered curriculum.

This is still scientifically informative.

---

# 72. Stop conditions

Stop before LOCKED if any of:

```text
S1  GOLD_TRACE < 1.0

S2  FORMAL_TEACH < 1.0

S3  WRONG_TEACHER_ACTION_EXECUTED > 0

S4  BAD_TEACHER_SUGGESTION_EXECUTED > 0

S5  VERIFY_FALSE_ACCEPT > 0

S6  teacher directly writes/activates procedures

S7  student requires teacher after handoff

S8  POST_HANDOFF_GROQ_CALLS > 0

S9  neural hashes change

S10 evidence-insufficiency rule is bypassed

S11 locked scenarios are inspected before freeze

S12 parent NL-teaching LOCKED set is opened or reused

S13 success requires new primitives not frozen in the domain
```

---

# 73. Development policy

DEV is for general engineering.

Permitted before freeze:

```text
teacher prompt improvements
capability-card improvements
student/teacher protocol fixes
general grounding safety rules
general clarification rules
provider reliability fixes
scenario-generator corrections
```

Not permitted:

```text
per-scenario hard coding
gold AST leakage
locked-set tuning
silent downstream verifier weakening
```

Every material change goes in:

```text
results/ENGINEERING_LOG.md
```

---

# 74. Teacher failure replay

Cache raw Groq responses by response hash.

When debugging deterministic downstream behavior:

```text
replay cached teacher responses
```

instead of repeatedly calling the hosted model.

This separates:

```text
teacher nondeterminism
```

from:

```text
student/runtime bugs
```

---

# 75. Hosted-provider failure handling

Provider/network errors are engineering failures, not semantic failures.

Retry according to a frozen policy.

Record:

```text
timeout
rate limit
transport error
provider error
retry
```

If a scenario cannot acquire a teacher response within the allowed retry budget:

```text
PROVIDER_FAILURE
```

Report separately.

---

# 76. Security boundary

Teacher text is untrusted input.

Do not permit teacher content to:

```text
change system prompts
modify evaluator files
write shell commands
read secrets
access arbitrary network tools
alter procedure DB outside typed APIs
```

Only registered semantic actions may reach the VM.

---

# 77. Student autonomy boundary

This experiment does **not** yet allow the student to decide what to learn.

The curriculum is externally registered.

The student may:

```text
ask questions
request another example
reject unsupported teaching
learn the registered target
```

It may not autonomously create an unregistered training curriculum in V1.

---

# 78. Successor experiment

If RESULT A holds, the next experiment should be:

```text
SEMVM_AUTONOMOUS_SKILL_CURRICULUM_V1
```

where:

```text
student identifies a capability gap
        ↓
asks Groq teacher for instruction
        ↓
learns + verifies procedure
        ↓
teacher disconnects
        ↓
student retains new capability
```

After that:

```text
SEMVM_SELF_TEACHING_PROCEDURE_DISCOVERY_V1
```

where the external teacher can be removed from curriculum generation as well.

---

# 79. Required artifacts

Produce at minimum:

```text
spec/SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1.md
spec/GROQ_TEACHER_PROTOCOL_V1.json
spec/GROQ_TEACHER_CAPABILITY_CARD_V1.json
spec/GROQ_DISTILLATION_SCENARIO_SCHEMA.json

locks/GROQ_DISTILLATION_LOCK.json

results/GROQ_DISTILLATION_UNIT_TESTS.json
results/GROQ_DISTILLATION_DEV.json
results/GROQ_DISTILLATION_LOCKED_TEST.json
results/GROQ_DISTILLATION_REPORT.md
results/GROQ_DISTILLATION_ARTIFACT_MANIFEST.json
results/ENGINEERING_LOG.md

teacher_transcripts/
teacher_responses/
teaching_traces/
procedure_verification/
procedure_store_snapshots/
network_audit/
```

---

# 80. Final architecture under test

```text
          ACQUISITION TIME

      Groq teacher LLM
              │
              ▼
      natural-language lesson
              │
              ▼
    frozen student frontend
              │
              ▼
 semantic/dataflow validation
              │
              ▼
       sandbox execution
              │
              ▼
      successful trace(s)
              │
              ▼
 deterministic anti-unification
              │
              ▼
  independent evidence verifier
              │
              ▼
       procedures.sqlite


             HANDOFF

     disconnect Groq entirely
              │
              ▼
          full restart
              │
              ▼
       new user request
              │
              ▼
      local retrieval only
              │
              ▼
    stored procedure executes
```

The intended capability transfer is:

```text
teacher knows how
        ↓
student demonstrates how
        ↓
SEMVM verifies how
        ↓
procedure library remembers how
```

The teacher may disappear.

The skill must remain.

---

# END
