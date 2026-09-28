# SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1

**Project:** Stateful Semantic VM — Natural-Language Procedure Teaching  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Parent experiment:** `SEMVM_PROCEDURE_DISCOVERY_POC_V1`  
**Parent result:** RESULT A — persistent procedural learning succeeds in the registered domain  
**Primary goal:** Replace the formal step-language teaching interface with natural-language teaching while keeping the proven procedure abstraction, verification, storage, retrieval, persistence, and execution machinery frozen.

---

# 0. Executive summary

`SEMVM_PROCEDURE_DISCOVERY_POC_V1` established that the Semantic VM can acquire reusable executable procedures externally without neural weight updates.

The proven pipeline is:

```text
formal teaching steps
        ↓
successful execution trace
        ↓
deterministic anti-unification
        ↓
candidate procedure AST
        ↓
static validation
        ↓
evidence-based verification
        ↓
explicit acceptance
        ↓
ACTIVE procedure in procedures.sqlite
        ↓
restart
        ↓
new wording + unseen argument
        ↓
stored-procedure retrieval
        ↓
correct execution
```

The one-time locked test passed 20/20 scenarios. The system generalized to new arguments, reworded requests, post-restart invocation, and composition while neural parameters remained frozen.

The dominant remaining limitation is the **teaching interface**:

```text
procedures are currently taught in a formal step language
```

rather than ordinary human instructions.

This experiment changes only the teaching ingress.

Target architecture:

```text
NATURAL-LANGUAGE TEACHING
        ↓
small frozen language model
        ↓
candidate primitive / procedure action
        ↓
deterministic type + schema validation
        ↓
execute one verified-safe step
        ↓
successful teaching trace
        ↓
FROZEN deterministic anti-unification
        ↓
FROZEN verifier
        ↓
persistent procedure library
```

The small LLM is **not** allowed to declare a procedure learned.

The LLM only helps translate teaching language into executable actions from the existing frozen primitive/procedure inventory.

The actual reusable procedure must still be inferred from the resulting successful execution trace and pass the same verifier used in the parent experiment.

The primary question is:

> Can a user teach a new persistent executable procedure in natural language, with the system grounding the instruction into a successful trace and then learning the reusable procedure from that trace rather than directly trusting generated code?

---

# 1. Parent result being extended

The parent procedure-discovery experiment is treated as frozen evidence, not as a development target.

The parent established:

```text
SOURCE_REPLAY_EXACT               1.0
COUNTERFACTUAL_EXACT              1.0
ROLLBACK_EXACT                    1.0
RESTART_PROCEDURE_EXACT           1.0
PROCEDURE_RETRIEVAL_EXACT         1.0
ARGUMENT_BINDING_EXACT            1.0
SCENARIO_EXACT                    1.0
VERIFY_FALSE_ACCEPT               0
```

on the final DEV and one-time locked evaluation.

The parent also established that:

```text
deterministic anti-unification
```

was sufficient for procedure proposal in the registered domain.

The 1.5B LLM added no verified procedure that the deterministic path missed.

Therefore this V1 **removes the LLM from procedure abstraction as a scientific dependency**.

The LLM's new primary role is teaching-language interpretation.

---

# 2. Primary research question

> Can natural-language procedural instructions be grounded into correct executable teaching traces often enough that the existing frozen deterministic procedure learner can acquire the same persistent parameterized procedures?

---

# 3. Secondary questions

This experiment should also answer:

```text
Q1. Can a frozen 1.5B local model map varied natural-language teaching
    instructions onto the existing primitive/procedure vocabulary?

Q2. Does deterministic typing and validation prevent malformed or
    hallucinated LLM actions from executing?

Q3. Can the system ask for clarification rather than inventing an
    action when a teaching instruction is ambiguous?

Q4. Does a successfully grounded natural-language demonstration produce
    the same procedure AST as the formal-step control?

Q5. Does the resulting learned procedure retain the parent experiment's
    unseen-argument, restart, and composition behavior?

Q6. How much natural-language diversity can be tolerated while preserving
    exact procedural semantics?

Q7. Are failures localized to language grounding rather than procedure
    abstraction, verification, persistence, or execution?
```

---

# 4. Core claim boundary

A positive result permits:

> Within the registered synthetic domain, users can teach reusable procedures using natural-language instructions; a frozen small language model grounds those instructions into existing typed operations, and the resulting successful traces are abstracted, verified, persisted, and later reused without neural weight updates.

It does **not** permit claims of:

```text
open-ended English understanding
general natural-language programming
arbitrary code synthesis
general autonomous task learning
new primitive invention
unbounded tool learning
online neural self-modification
open-domain procedure induction
```

---

# 5. Experimental principle

The key scientific separation is:

```text
LANGUAGE INTERPRETATION
        ≠
PROCEDURE LEARNING
```

Natural language may propose actions.

Only **executed, validated traces** become evidence for procedure learning.

Therefore:

```text
natural-language instruction
        ↓
LLM proposes action
        ↓
deterministic validator
        ↓
safe execution
        ↓
TRACE
        ↓
deterministic procedure learner
```

is allowed.

This is forbidden:

```text
natural-language instruction
        ↓
LLM writes final procedure AST
        ↓
save directly
```

A direct-AST arm may exist only as a diagnostic and may never bypass the verifier.

---

# 6. Frozen components

Before any DEV run, copy or reference the final frozen parent components and record their hashes.

Freeze:

```text
procedure AST schema
procedure program hashing
procedure anti-unification / abstraction
procedure static validator
procedure verifier
state-perturbation verifier stage
negative-case generation
rollback-injection tests
procedure store
procedure lifecycle
procedure versioning
procedure retrieval runtime
argument repair
typed argument fallback
type-directed composition search
canonical plan equivalence
stored-procedure preference
world-model schema
STATUS extension
REPORT representation
primitive inventory
procedure executor
transaction semantics
```

No failure in natural-language teaching may be repaired by silently altering these components.

Any parent-runtime change requires:

```text
explicit amendment
+
new parent-runtime control
```

---

# 7. Domain

Use exactly the registered parent domain.

Do not introduce a new customer/account/task ontology.

Available semantic world includes the parent END_TO_END_POC entities/events and its registered extension, including:

```text
REMINDER
PLAN
REQUEST
NOTE

CALL
EMAIL
VISIT
MESSAGE

PERSON
TIME
PLACE
TOPIC

WHO
WHEN
WHERE
RECIPIENT
TOPIC
TODO

STATUS:
    OPEN
    CLOSED

structured REPORT values
```

Use the existing frozen constructor/signature legality constraints.

---

# 8. Primitive and procedure vocabulary

Use exactly the frozen `PROCEDURE_PRIMITIVES_V1` inventory from the parent experiment.

The language frontend may only ground an instruction into:

```text
existing primitive
or
already ACTIVE procedure
```

It may not invent:

```text
new opcode
new effect type
new database operation
new relation semantics
new external tool
new arbitrary code fragment
```

---

# 9. Neural component

## 9.1 Primary model

Use the same locally runnable frozen model family used in the parent experiment unless changed before lock:

```text
Qwen2.5-Coder-1.5B base
```

Record exact:

```text
model files
model hash
tokenizer hash
transformers version
dtype
device
prompt
few-shot examples
generation settings
```

Primary generation policy:

```text
greedy / deterministic
no sampling
```

No optimizer.

No weight updates.

## 9.2 Model role

The model may:

```text
classify a teaching utterance
select a primitive/procedure
extract candidate arguments
rank candidate actions
identify an explicit sequencing relation
propose CLARIFY
```

The model may not:

```text
write arbitrary executable code
directly mutate world state
activate a procedure
declare verification success
invent a primitive
bypass type checking
```

---

# 10. Natural-language teaching interface

Support:

```text
:teach <name>(optional-parameter-hints)
```

followed by one or more natural-language teaching utterances.

Example:

```text
semvm> :teach close_open_requests(person=Alice)

teach> Find Alice's open requests.
teach> Close each of them.
teach> Return how many were closed.
teach> :endteach
```

The system grounds each teaching utterance into one or more executable operations.

The user does not type formal VM steps.

---

# 11. Natural-language teaching forms

V1 intentionally supports bounded natural-language instructions rather than unrestricted conversation.

Registered variation should include:

```text
imperatives
polite imperatives
pronouns with locally unambiguous referents
simple conjunctions
simple sequencing words
lexical paraphrases
argument reordering
singular / plural surface variation
explicit constants
explicit variables / example values
```

Examples:

```text
"Find all of Alice's open requests."
"Look up the open requests for Alice."
"Get Alice's requests that are still open."
"Pull up every request Alice has that hasn't been closed."
```

These may all map to the same primitive action.

---

# 12. Unsupported teaching forms

Register as unsupported in V1:

```text
deeply nested conditionals
unbounded loops
recursion
open-domain concepts
implicit external-world actions
arbitrary shell/file/network actions
instructions requiring unstated primitives
long free-form documents
multi-party dialogue
cross-session pronoun resolution
metaphorical or highly indirect instructions
```

Unsupported input must produce:

```text
UNSUPPORTED_TEACHING_INPUT
```

or:

```text
CLARIFY
```

rather than guessed execution.

---

# 13. Grounding representation

The LLM must output a constrained candidate-action object.

Conceptual form:

```json
{
  "intent": "EXECUTE_STEP",
  "op": "FIND",
  "arguments": {
    "type": "REQUEST",
    "person": "Alice",
    "status": "OPEN"
  },
  "bind": "requests"
}
```

or:

```json
{
  "intent": "CLARIFY",
  "reason": "ambiguous target"
}
```

Output must be parsed and validated before execution.

---

# 14. Deterministic action validation

Before any proposed step executes:

```text
op exists
arguments allowed
required arguments present
argument names canonicalized
argument values typed
object/relation legality satisfied
variables exist if referenced
procedure dependencies ACTIVE
effect class allowed
```

If validation fails:

```text
do not execute
```

Then either:

```text
deterministic repair
typed fallback
CLARIFY
UNSUPPORTED_TEACHING_INPUT
```

depending on the registered policy.

---

# 15. Argument repair policy

Reuse the parent experiment's lessons.

Allowed deterministic repair includes:

```text
case normalization
known alias normalization
positional → named argument mapping
canonical enum normalization
type-preserving formatting
unambiguous argument-name correction
```

Do not silently repair:

```text
unknown extra semantic argument
wrong semantic type
multiple plausible target bindings
missing information with >1 valid completion
```

Those require:

```text
CLARIFY
```

or rejection.

---

# 16. Teaching execution trace

Every accepted teaching step produces an auditable trace:

```text
natural-language utterance
LLM raw output
parsed candidate
repair/fallback path
validated operation
state before
executed primitive/procedure
state diff
return value
state after
```

Only successfully executed steps enter procedure-learning evidence.

---

# 17. Failed teaching steps

A failed or rejected teaching step is not procedure evidence.

Examples:

```text
schema failure
wrong type
ambiguous entity
unsupported operation
unsafe effect
execution failure
```

The system may ask for clarification and continue teaching.

The failed proposal itself must not contaminate the final source trace.

---

# 18. Clarification loop

Example:

```text
teach> Close those.

system> Do you mean the requests returned by the previous step,
        or all open requests for Alice?
```

The user's response may resolve the candidate action.

Track:

```text
CLARIFICATION_REQUIRED
CLARIFICATION_SUCCESS
CLARIFICATION_TURNS
```

A clarification is part of teaching interaction history but only the final grounded operation enters the execution trace.

---

# 19. Teaching with references to prior step results

Support bounded procedural references such as:

```text
them
those requests
each one
the results
that report
```

only where deterministic local trace context provides a unique referent.

Example:

```text
Step 1:
    FIND(...) → requests

Step 2:
    "Close each of them."
```

may bind:

```text
them → requests
```

If more than one compatible variable exists:

```text
CLARIFY
```

---

# 20. Teaching constants versus parameters

Natural-language examples use concrete values.

The language model does not decide final procedure parameterization.

Example teaching:

```text
"Find Alice's open requests."
```

produces trace values:

```text
PERSON=Alice
STATUS=OPEN
```

Later, the frozen deterministic anti-unifier decides whether:

```text
Alice → parameter
OPEN  → constant
```

from the registered demonstration evidence.

This preserves the parent experiment's parameter/constant separation.

---

# 21. One-shot versus multi-example teaching

Retain the parent rule.

One-shot teaching is permitted only when the abstraction is unambiguous under the registered anti-unifier.

If variable/constant separation cannot be justified from one example:

```text
REQUIRE_SECOND_DEMONSTRATION
```

Do not make the LLM guess which values should become parameters.

---

# 22. Teaching demonstrations

For a multi-example procedure:

```text
:teach proc_name

Example 1:
    natural-language teaching using Alice

Example 2:
    natural-language teaching using Bob
```

The system should produce two grounded traces.

The existing anti-unifier receives only those traces, not the natural-language text.

---

# 23. Formal-step control

Every natural-language teaching scenario must have a paired formal control.

Two teaching modes:

```text
FORMAL
    parent experiment step language
    → trace

NL_TEACH
    natural language
    → frozen LLM + deterministic grounding
    → trace
```

Both feed the same downstream frozen procedure learner.

This isolates the new capability.

---

# 24. Gold-trace control

Mandatory.

For every teaching scenario, maintain an independently generated gold primitive/procedure trace.

Run:

```text
GOLD_TRACE
    gold trace
    → frozen anti-unifier
    → verifier
    → procedure store
```

Required:

```text
GOLD_TRACE procedure-learning success = 1.00
```

This checks that the scenario remains solvable by the frozen parent machinery.

---

# 25. Trace equivalence metric

Define:

```text
TEACH_TRACE_EXACT
```

A grounded teaching trace is exact if it matches the gold trace behaviorally:

```text
same primitive/procedure calls
same typed arguments
same data dependencies
same externally visible state effects
same returned values
```

Ignore:

```text
temporary variable names
harmless canonical ordering
```

where the parent canonicalizer treats them as equivalent.

---

# 26. Procedure equivalence metric

Define:

```text
LEARNED_PROCEDURE_EXACT
```

After natural-language grounding and downstream abstraction, compare the resulting canonical procedure AST/program hash with the formal/gold procedure.

This directly asks:

> Did natural-language teaching lead to the same reusable program?

---

# 27. End-to-end teaching success

Define:

```text
NL_TEACH_SCENARIO_EXACT
```

A scenario passes only if:

```text
natural-language teaching is grounded correctly
source traces execute correctly
procedure is discovered
procedure passes verification
procedure becomes ACTIVE when accepted
processes restart where required
new wording retrieves procedure
new argument binds correctly
procedure executes correctly
final state / return is correct
```

---

# 28. Teaching-language dataset structure

Organize natural-language teaching examples by semantic equivalence group.

Example:

```text
TEACH_MEANING_001
    formal trace:
        FIND REQUEST person=<P> status=OPEN

    surfaces:
        "Find <P>'s open requests."
        "Get the requests for <P> that are still open."
        "Look up all open requests belonging to <P>."
        "Pull up every request <P> has that hasn't been closed."
```

The operation target is identical.

---

# 29. Surface-diversity dimensions

Vary:

```text
lexical choice
word order
politeness
determiners
contractions
singular/plural
active phrasing
simple relative clauses
simple pronouns
sequencing markers
conjunctions
punctuation
```

Do not vary semantics inside an equivalence group.

---

# 30. DEV / LOCKED surface separation

Natural-language teaching surfaces must be split by template family.

DEV and LOCKED_TEST must use:

```text
disjoint teaching paraphrase templates
```

not merely different slot values.

This tests surface generalization.

Record:

```text
TEACH_SURFACE_GENERALIZATION
```

separately.

---

# 31. Procedure-family split

Retain the existing parent domain/procedure families where possible.

Recommended evaluation strata:

```text
T1 single primitive-derived procedure
T2 multi-step linear procedure
T3 loop / FOR_EACH procedure
T4 state mutation procedure
T5 read-only/report procedure
T6 multi-parameter procedure
T7 constant-preservation procedure
T8 one-shot unambiguous
T9 requires multiple demonstrations
T10 nested existing-procedure call
T11 composition
T12 rollback / failure case
T13 clarification-required teaching
```

Exact family names may reuse the parent P1–P12 mapping if cleaner.

---

# 32. Natural-language teaching difficulty bands

Report separately:

```text
BAND A — direct imperative
    "Find Alice's open requests."

BAND B — lexical paraphrase
    "Pull up the open requests for Alice."

BAND C — local anaphora
    "Find Alice's open requests. Close each of them."

BAND D — compact multi-action instruction
    "Find Alice's open requests and close them."

BAND E — instruction with constant + variable contrast
    "For Alice, find only requests that are still open, then count them."
```

Do not collapse these into one number.

---

# 33. Multi-action utterances

V1 may support bounded multi-action instructions if the frontend emits a sequence:

```json
{
  "intent": "EXECUTE_SEQUENCE",
  "steps": [
    {},
    {}
  ]
}
```

Every step must validate independently.

If sequence segmentation is uncertain:

```text
CLARIFY
```

---

# 34. No hidden final-program shortcut

The evaluator must verify that NL_TEACH mode does not pass the full gold procedure AST to the LLM.

The LLM may see:

```text
current teaching utterance
bounded local step context
allowed operations/signatures
few-shot grounding examples
```

It may not see:

```text
gold procedure
LOCKED expected program
future teaching demonstrations
gold parameterization
```

---

# 35. LLM prompt lock

Before final DEV tuning is complete, maintain a versioned prompt.

Before LOCKED:

```text
hash prompt
hash few-shot examples
hash model
hash tokenizer
hash generation config
```

No changes after freeze.

---

# 36. Deterministic fallback

The language model is non-authoritative.

A deterministic fallback may operate only on information explicitly available in the teaching utterance and registered local context.

Examples:

```text
exact primitive alias match
typed argument extraction from canonical slot syntax
reference to unique prior result variable
```

Do not build an unrestricted hand-written natural-language parser that silently replaces the LLM.

Report:

```text
LLM_DIRECT_GROUNDING
DETERMINISTIC_REPAIR
TYPED_FALLBACK
CLARIFICATION
```

counts separately.

---

# 37. Frontend contribution accounting

For every correctly grounded step classify:

```text
A. raw LLM proposal was correct

B. LLM selected correct op, deterministic repair fixed formatting

C. LLM selected correct semantic action, typed fallback filled argument(s)

D. deterministic alias path solved without LLM

E. clarification was required

F. failure
```

This identifies whether the small LLM is truly carrying language variation.

---

# 38. Direct natural-language-to-AST diagnostic

Optional diagnostic only.

Ask the same frozen 1.5B model to produce the final procedure AST directly from the full teaching text.

Do not activate it.

Compare:

```text
DIRECT_AST_EXACT
```

against:

```text
TRACE_MEDIATED_PROCEDURE_EXACT
```

This tests whether trace-mediated learning is more reliable than trusting direct program synthesis.

---

# 39. Parent verifier remains authoritative

Natural-language teaching changes nothing about procedure activation.

Candidate procedure lifecycle remains:

```text
CANDIDATE
→ TESTING
→ VERIFIED
→ explicit :accept
→ ACTIVE
```

The same source replay, counterfactual, state perturbation, negative-case, rollback, and determinism tests remain required.

---

# 40. State-diversity verification remains mandatory

The parent experiment discovered that replay alone can falsely accept a candidate that drops a constant constraint.

Therefore every candidate verifier must preserve:

```text
state perturbation
```

that varies relevant latent state dimensions.

No simplification of this verifier is permitted in V1.

---

# 41. Safety invariant

No wrong LLM teaching action may execute if deterministic validation detects the mismatch.

Track:

```text
WRONG_LLM_ACTION_PROPOSED
WRONG_LLM_ACTION_BLOCKED
WRONG_LLM_ACTION_EXECUTED
```

Required:

```text
WRONG_LLM_ACTION_EXECUTED = 0
```

on DEV and LOCKED.

---

# 42. Mutation discipline during teaching

Every teaching step executes transactionally.

If a step fails:

```text
state hash unchanged
```

unless the user explicitly accepted prior successful steps as part of the teaching demonstration.

For multi-action utterances, prefer one transaction per utterance.

---

# 43. Teaching sandbox

Recommended:

```text
teaching world snapshot
```

separate from the user's durable world.

Procedure teaching may execute against a temporary scenario state.

After teaching:

```text
procedure may persist
teaching-state mutations may be discarded
```

unless explicitly registered otherwise.

This avoids teaching examples accidentally becoming permanent world facts.

---

# 44. Teaching snapshot provenance

For each learned procedure store:

```text
natural-language teaching utterances
grounding traces
start-state snapshot hash
executed trace hash
formal/gold control hash
abstraction inputs
procedure hash
verification manifest
```

Natural-language text is provenance.

The canonical procedure remains authoritative.

---

# 45. Retrieval after teaching

Reuse the parent retrieval stack unchanged.

The new experiment should not conflate:

```text
teaching-language grounding
```

with:

```text
later procedure retrieval
```

The parent system already demonstrated controlled paraphrase retrieval.

Still report post-learning invocation using:

```text
new request wording
+
new arguments
+
restart
```

to ensure the newly taught procedure entered the same persistent library correctly.

---

# 46. Restart gate

For registered restart scenarios:

```text
1. teach in natural language
2. ground to successful trace
3. learn + verify procedure
4. explicitly accept
5. terminate scenario process
6. terminate LLM service
7. restart
8. do not provide teaching transcript
9. request with unseen wording/argument
10. retrieve stored procedure
11. execute correctly
```

Required:

```text
NL_TEACH_RESTART_EXACT = 1.00
```

---

# 47. Unseen-argument gate

Natural-language teaching examples use specific entities/times/places.

Later invocations should predominantly use never-demonstrated arguments.

Report:

```text
DEMONSTRATED_ARGUMENT_EXACT
UNSEEN_ARGUMENT_EXACT
```

separately.

Do not allow high replay accuracy to hide poor parameterization.

---

# 48. Composition

Include natural-language teaching scenarios in which the taught procedure uses already ACTIVE procedures.

Example:

```text
teach> Get the count using `count_open_requests`.
teach> Then make a report from that result.
```

or a natural equivalent resolved to existing procedures.

The resulting trace may contain:

```text
CALL_PROCEDURE P1
CALL_PROCEDURE P2
```

The frozen anti-unifier then learns the composite.

---

# 49. No procedure invention from unexecuted prose

If the user describes an operation but the system cannot ground and execute it safely:

```text
do not learn procedure
```

Natural-language description alone is insufficient evidence.

This is a core invariant.

---

# 50. Explicit user correction

If the system proposes the wrong teaching step, support correction.

Example:

```text
system:
    "I interpreted that as SET_STATE on the request. Correct?"

user:
    "No, set the call to CLOSED."
```

The corrected, successfully executed action enters the trace.

The incorrect proposal remains provenance only.

Report:

```text
CORRECTION_RATE
POST_CORRECTION_TRACE_EXACT
```

---

# 51. Explicit acceptance

After verification:

```text
"I learned candidate `close_open_requests(person)`.
It passed N verification cases. Save it?"
```

Require explicit acceptance in V1.

Do not auto-activate from natural-language teaching alone.

---

# 52. Unit tests

Before scenario evaluation, require all parent unit tests plus new tests for:

```text
NL action schema parsing
primitive selection
argument normalization
typed validation
multi-action segmentation
local anaphora resolution
clarification on ambiguous variable
unsupported instruction rejection
teaching transaction rollback
teaching sandbox reset
trace provenance
no failed proposal enters evidence
prompt/model hash recording
restart without teaching transcript
```

All deterministic unit tests must pass.

---

# 53. Evaluation modes

Run three primary modes.

## A. GOLD_TRACE

```text
gold execution trace
→ frozen procedure learner
```

Purpose:

```text
prove parent machinery is still exact
```

## B. FORMAL_TEACH

```text
formal parent step language
→ execution trace
→ frozen procedure learner
```

Purpose:

```text
same interface as parent experiment
```

## C. NL_TEACH

```text
natural-language instruction
→ frozen 1.5B frontend
→ validated actions
→ execution trace
→ frozen procedure learner
```

Purpose:

```text
primary new capability
```

---

# 54. Optional fourth mode

## D. DIRECT_AST_DIAGNOSTIC

```text
natural-language procedure description
→ LLM final AST proposal
→ static validation + verifier
```

Descriptive only.

Do not make this the main system.

---

# 55. Metrics — language grounding

Report:

```text
ACTION_OP_EXACT
ACTION_ARGUMENT_EXACT_RAW
ACTION_ARGUMENT_EXACT_AFTER_REPAIR
ACTION_SEQUENCE_EXACT
REFERENCE_BINDING_EXACT
TEACH_TRACE_EXACT
CLARIFICATION_PRECISION
CLARIFICATION_RECALL
UNSUPPORTED_REJECTION_EXACT
```

---

# 56. Metrics — downstream procedure learning

Report:

```text
LEARNED_PROCEDURE_EXACT
SOURCE_REPLAY_EXACT
COUNTERFACTUAL_EXACT
VERIFY_FALSE_ACCEPT
NEGATIVE_CASE_SAFE
ROLLBACK_EXACT
```

---

# 57. Metrics — persistent reuse

Report:

```text
PROCEDURE_RETRIEVAL_EXACT
ARGUMENT_BINDING_EXACT
UNSEEN_ARGUMENT_EXACT
SURFACE_GENERALIZATION_EXACT
RESTART_PROCEDURE_EXACT
STORED_PROCEDURE_REUSE_EXACT
COMPOSITION_EXACT
FINAL_STATE_EXACT
NL_TEACH_SCENARIO_EXACT
```

---

# 58. Primary metrics

Primary scientific metrics:

```text
TEACH_TRACE_EXACT
LEARNED_PROCEDURE_EXACT
NL_TEACH_SCENARIO_EXACT
```

All three are required because:

```text
correct final behavior
```

alone could hide:

```text
wrong teaching interpretation
followed by compensating downstream behavior
```

---

# 59. Initial DEV gates

Before LOCKED_TEST:

```text
GOLD_TRACE learned-procedure exact       = 1.00
FORMAL_TEACH learned-procedure exact     = 1.00

WRONG_LLM_ACTION_EXECUTED                = 0
VERIFY_FALSE_ACCEPT                      = 0

TEACH_TRACE_EXACT                        >= .90
LEARNED_PROCEDURE_EXACT                  >= .90
ACTION_OP_EXACT                          >= .95
ACTION_ARGUMENT_EXACT_AFTER_REPAIR       >= .95

SOURCE_REPLAY_EXACT                      = 1.00
COUNTERFACTUAL_EXACT                     = 1.00
ROLLBACK_EXACT                           = 1.00

PROCEDURE_RETRIEVAL_EXACT                >= .95
ARGUMENT_BINDING_EXACT                   >= .95
RESTART_PROCEDURE_EXACT                  = 1.00
STORED_PROCEDURE_REUSE_EXACT             = 1.00

NL_TEACH_SCENARIO_EXACT                  >= .90
```

These may be amended only before LOCKED exposure, with explicit justification.

---

# 60. Natural-language success criterion

The experiment is not successful merely because the system eventually reaches the correct final state after repeated correction.

Report two success levels:

```text
FIRST_PASS
    natural teaching grounded correctly without clarification/correction

ASSISTED
    correct after bounded clarification/correction
```

Primary `NL_TEACH_SCENARIO_EXACT` should permit registered clarification but report first-pass separately.

---

# 61. Scenario counts

Recommended:

```text
DEV:
    30 scenarios

LOCKED_TEST:
    20 scenarios
```

Maintain similar family coverage to the parent procedure POC.

Each scenario may contain multiple teaching instructions and later procedure invocations.

---

# 62. Locked-test construction

Before final DEV tuning completes:

```text
generate LOCKED_TEST
hash freeze
do not inspect per-scenario content
```

LOCKED must use:

```text
new slot values
disjoint natural-language teaching templates
disjoint later-request templates
```

relative to DEV.

Run once after integration freeze.

---

# 63. Scenario-design audit

Before freezing LOCKED, audit each scenario for:

```text
sufficient demonstrations for registered anti-unifier
unambiguous gold trace
all operations in frozen primitive set
all entities/types legal
no hidden unsupported concept
no accidental one-shot ambiguity
counterfactual cases executable
negative cases meaningful
restart artifacts isolated
```

This specifically prevents recurrence of the parent P11 design defect.

---

# 64. Anti-shortcut audit

Check for trivial mappings such as:

```text
unique keyword → unique procedure
fixed sentence template → fixed operation sequence
argument position → parameter role
procedure name copied verbatim in every instruction
```

Where possible, balance or vary these.

A shallow lexical classifier may be reported as a diagnostic.

---

# 65. Procedure-name leakage

Some teaching scenarios may provide:

```text
:teach close_open_requests
```

which leaks a semantic summary.

Therefore create two strata:

```text
NAMED
    descriptive procedure name supplied

OPAQUE
    name such as proc_17 supplied
```

The OPAQUE stratum tests whether teaching succeeds without relying on the procedure name.

Report separately.

---

# 66. Parameter-hint leakage

Likewise compare:

```text
HINTED
    :teach proc(person=Alice)

UNHINTED
    :teach proc
```

In UNHINTED mode, parameterization must emerge only from multiple traces / anti-unification.

Do not collapse the two.

---

# 67. Teaching example

Natural-language teaching:

```text
semvm> :teach proc_17

teach> Find Alice's requests that are still open.
teach> Close each one.
teach> Tell me how many you changed.
teach> :endteach
```

Grounded trace:

```text
r = FIND(type=REQUEST, person=Alice, status=OPEN)
FOR_EACH x IN r:
    SET_STATE(x, CLOSED)
n = COUNT(r)
RETURN n
```

Second demonstration:

```text
teach> Find Bob's open requests.
teach> Mark each of those closed.
teach> Return the number you closed.
```

Frozen anti-unifier:

```text
Alice/Bob → person parameter
OPEN      → constant
CLOSED    → constant
```

Learned procedure:

```text
PROC proc_17(person):
    r = FIND(type=REQUEST, person=person, status=OPEN)
    FOR_EACH x IN r:
        SET_STATE(x, CLOSED)
    n = COUNT(r)
    RETURN n
```

---

# 68. Verification example

Candidate A:

```text
status=OPEN
```

Candidate B:

```text
no status filter
```

If demonstrations happen to contain only OPEN requests, replay alone cannot distinguish them.

State perturbation must insert:

```text
CLOSED request
```

and require Candidate B to fail.

The verifier must continue rejecting B.

---

# 69. Ambiguity example

Teaching:

```text
"Close them."
```

with two compatible previous lists.

Required:

```text
CLARIFY
```

Forbidden:

```text
pick most recent silently
```

unless the registered reference grammar makes recency deterministically decisive.

---

# 70. Unsupported primitive example

Teaching:

```text
"Send Alice a Slack message."
```

if no external messaging primitive exists.

Required:

```text
UNSUPPORTED_TEACHING_INPUT
```

Do not synthesize:

```text
shell
HTTP
Python
```

to approximate it.

---

# 71. Natural-language retrieval after learning

Later request:

```text
"Clear out Carol's outstanding requests and tell me how many there were."
```

may map to:

```text
CALL proc_17(person=Carol)
```

The procedure itself must come from `procedures.sqlite`.

Do not replay the original teaching instruction.

---

# 72. Restart demonstration

Compelling scenario:

```text
1. Teach proc_17 in natural language using Alice and Bob.

2. Verify and :accept.

3. Kill scenario process.

4. Kill LLM service.

5. Restart both.

6. Do not include teaching transcript.

7. Request:
   "Take care of Carol's still-open requests and give me the count."

8. Retrieve proc_17.

9. Execute with Carol.

10. Exact result.
```

This is the primary persistent-learning demonstration.

---

# 73. Composition demonstration

Assume already ACTIVE:

```text
P1 count_open_requests(person)
P2 make_count_report(person, count)
```

Teach naturally:

```text
"First get the number of open requests for the person.
Then make a report containing their name and that count."
```

Grounded trace:

```text
n = CALL P1(person)
r = CALL P2(person, n)
RETURN r
```

Anti-unification / verification produces:

```text
P3 report_open_request_count(person)
```

After restart, P3 must be retrieved as the stored composite rather than dynamically rediscovered when the request matches it.

---

# 74. Failure taxonomy

Add teaching-language failures:

```text
NL_SCHEMA
    malformed frontend output

NL_OP
    wrong primitive/procedure selected

NL_ARGUMENT
    wrong semantic argument

NL_SEQUENCE
    wrong operation ordering / segmentation

NL_REFERENCE
    wrong local anaphora binding

NL_MISSED_CLARIFY
    ambiguity existed but system executed

NL_FALSE_CLARIFY
    unambiguous instruction rejected as ambiguous

NL_UNSUPPORTED
    unsupported concept not detected

TRACE_MISMATCH
    grounded execution trace differs from gold

PD_PARAMETER
PD_PROGRAM
PD_VERIFY_FALSE_ACCEPT
PD_VERIFY_FALSE_REJECT

PR_RETRIEVE
PR_ARGUMENT
PR_COMPOSE

VM_EXEC
ROLLBACK
STORE
```

---

# 75. Localization rule

Every failed scenario must identify the earliest subsystem failure.

Example:

```text
natural instruction
→ wrong primitive
→ wrong trace
→ wrong learned procedure
→ wrong later state
```

Primary failure:

```text
NL_OP
```

Do not additionally count downstream consequences as independent causes unless reporting propagation metrics.

---

# 76. Development policy

DEV is for engineering.

Permitted before lock:

```text
prompt improvements
schema/parser fixes
general argument normalization
general clarification rules
general grounding repairs
scenario-design corrections
```

Requirements:

```text
log every change
apply general changes to eventual LOCKED runtime
do not tune to locked outcomes
```

If a locked-set design defect is discovered from DEV before LOCKED is inspected/run:

```text
archive unopened locked set as INVALIDATED_BEFORE_RUN
fix generator
generate fresh independently seeded locked set
freeze again
```

---

# 77. Freeze protocol

Before one-time LOCKED run record hashes of:

```text
model
tokenizer
prompt
few-shot examples
generation config
grounding schema
grounding code
argument repair
clarification rules
primitive inventory
procedure learner
verifier
procedure store
executor
scenario generator
DEV manifest
LOCKED manifest
```

---

# 78. Cost / performance accounting

Report:

```text
LLM calls per teaching step
LLM latency per teaching step
grounding-validation latency
clarification turns
procedure verification latency
procedure acquisition total latency
later retrieval latency
stored-procedure execution latency
```

Compare:

```text
FORMAL_TEACH
vs
NL_TEACH
```

---

# 79. Model-size accounting

Report constant neural parameter count.

Primary expectation:

```text
neural params remain fixed
```

while:

```text
number of ACTIVE procedures increases
```

Track:

```text
procedure library bytes
world bytes
number of active procedures
procedure dependency depth
```

---

# 80. LLM usefulness analysis

Because the parent experiment found no LLM value for procedure proposal, this experiment should explicitly quantify its new role.

Report:

```text
fraction of teaching steps solved by raw LLM
fraction requiring deterministic repair
fraction requiring typed fallback
fraction requiring clarification
fraction rejected
```

The question is no longer:

> Can the LLM discover the procedure?

It is:

> Can the LLM provide a sufficiently good natural-language grounding layer for the deterministic learning system?

---

# 81. Comparison to parent

Do not compare only scenario exactness.

Produce a table:

```text
                        FORMAL_PARENT    NL_TEACH
-------------------------------------------------
teaching trace exact
learned procedure exact
counterfactual exact
restart exact
retrieval exact
composition exact
scenario exact
acquisition latency
```

This quantifies the cost of replacing formal teaching with language.

---

# 82. Result interpretation map

## RESULT A — natural-language teaching succeeds

If:

```text
NL_TEACH_SCENARIO_EXACT >= gate
TEACH_TRACE_EXACT >= gate
LEARNED_PROCEDURE_EXACT >= gate
all hard safety/runtime gates pass
```

then:

> Natural-language teaching can serve as the ingress to the already-demonstrated persistent procedural learning system within the registered domain.

## RESULT B — grounding fails, gold/formal controls pass

Then:

> Procedure learning remains sound; natural-language grounding is the bottleneck.

## RESULT C — trace exact is high but learned procedures fail

Then:

> The parent procedure learner does not transfer under the new trace distribution; inspect trace canonicalization/abstraction assumptions.

## RESULT D — learning succeeds but retrieval fails

Then:

> Natural-language teaching works, but later language-to-procedure retrieval remains the bottleneck.

## RESULT E — unsafe proposal executes

If:

```text
WRONG_LLM_ACTION_EXECUTED > 0
```

stop.

The language-grounding safety boundary failed.

## RESULT F — verifier false-accepts

If a deliberately bad procedure becomes VERIFIED/ACTIVE:

```text
stop
```

Do not continue to LOCKED.

---

# 83. Strongest permitted V1 claim

If RESULT A holds:

> In a bounded synthetic semantic domain, a user can teach new reusable procedures using natural-language instructions. A frozen small language model grounds those instructions into typed operations, while a deterministic trace-based learner abstracts and verifies the reusable procedure. The learned procedure persists outside neural weights and can later be retrieved after restart, applied to unseen arguments, and composed with other stored procedures.

---

# 84. Stronger claims deferred

The following require later experiments:

```text
free-form open English teaching
spontaneous procedure discovery from ordinary use
procedure learning without explicit :teach
learning new primitives/tools
large heterogeneous domains
deep procedure hierarchies
long-horizon workflows
software-engineering tasks
SWE-bench
multi-user procedure learning
multi-seed replication
```

---

# 85. Suggested next experiment after V1

If natural-language teaching succeeds, the next step is:

```text
SEMVM_SPONTANEOUS_PROCEDURE_DISCOVERY_V1
```

Target:

```text
ordinary successful interaction
        ↓
system detects repeated reusable structure
        ↓
proposes procedure
        ↓
user approves
        ↓
verify
        ↓
persist
```

No explicit `:teach` would be required.

That experiment should not begin until this V1 cleanly separates natural-language grounding from procedural abstraction.

---

# 86. Required artifacts

Produce at minimum:

```text
spec/SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1.md
spec/NL_TEACH_ACTION_SCHEMA.json
spec/NL_TEACH_LANGUAGE_V1.json

locks/NL_TEACH_POC_LOCK.json

results/NL_TEACH_UNIT_TESTS.json
results/NL_TEACH_DEV.json
results/NL_TEACH_LOCKED_TEST.json
results/NL_TEACH_REPORT.md
results/NL_TEACH_ARTIFACT_MANIFEST.json
results/ENGINEERING_LOG.md
```

Also preserve:

```text
teaching_traces/
procedure_verification/
procedure_store_snapshots/
```

for audit.

---

# 87. Interactive REPL target

Example user experience:

```text
semvm> :teach close_open_requests

teach> Find all of Alice's requests that are still open.
system> Found the open requests for Alice.

teach> Close every one of them.
system> Applied CLOSED to each result.

teach> Return how many you closed.
system> The teaching trace returns a count.

teach> :endteach

system> I found a reusable candidate:
        close_open_requests(person)

        It passed source replay, counterfactual,
        state-perturbation, rollback and negative tests.

        Save it?

semvm> :accept close_open_requests
system> Saved.

--- restart ---

semvm> REQUEST take care of Bob's outstanding requests and tell me how many there were

system> [retrieves close_open_requests(person=Bob)]
        4
```

---

# 88. Decisive demonstration

The minimum compelling V1 result is:

```text
1. Start without procedure P.

2. Teach P entirely through natural-language instructions.

3. No formal primitive steps are supplied by the user.

4. The frozen small LLM grounds the teaching instructions.

5. Deterministic validation allows only legal actions.

6. The grounded actions execute successfully.

7. The frozen anti-unifier abstracts P from the resulting trace(s).

8. The existing verifier accepts P.

9. User explicitly activates P.

10. Kill every process, including the LLM service.

11. Restart without the teaching transcript.

12. Request P using different wording and an unseen argument.

13. Retrieve the stored procedure itself.

14. Execute it exactly.

15. Neural model hashes are unchanged.
```

If this passes, the system has advanced from:

```text
formal procedure teaching
```

to:

```text
natural-language-mediated persistent procedural learning
```

without moving procedure semantics into the language model.

---

# 89. Stop conditions

Stop before LOCKED if:

```text
S1  GOLD_TRACE or FORMAL_TEACH is not exact

S2  wrong LLM actions can bypass deterministic validation

S3  verifier accepts deliberately bad procedures

S4  successful procedure learning requires direct access to gold AST

S5  natural-language frontend must invent new primitives to pass

S6  failed grounding steps enter procedure evidence

S7  procedure persistence depends on teaching transcript after restart

S8  LOCKED_TEST is inspected/run before final freeze

S9  natural-language test templates overlap materially with DEV templates

S10 parent runtime must be repeatedly modified to compensate for language errors
```

---

# 90. Final architecture

If successful:

```text
NATURAL LANGUAGE
      ↓
small frozen language model
      ↓
typed candidate action
      ↓
deterministic validation / clarification
      ↓
successful execution trace
      ↓
deterministic anti-unification
      ↓
evidence-based verifier
      ↓
persistent procedure library
      ↓
restart
      ↓
natural-language request
      ↓
procedure retrieval
      ↓
deterministic execution
```

Persistent capability lives primarily in:

```text
WORLD MODEL
    what the system knows

PROCEDURE LIBRARY
    what the system knows how to do
```

The neural model remains a bounded language interface rather than the sole repository of state, skills, or executable behavior.

---

# END
