# SEMVM_PROCEDURE_DISCOVERY_POC_V1

**Project:** Stateful Semantic VM — Procedure Discovery and Persistent Procedural Memory  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Parent systems:**  
- `SEMVM_END_TO_END_POC_V1`
- `SEMVM_SMALL_LLM_HYBRID_POC_V1`

**Primary goal:** Demonstrate that the system can acquire a new reusable procedure from interaction, verify it, store it externally, retrieve it after restart, and execute it on novel arguments without changing neural weights.

---

# 0. Executive summary

The existing Semantic VM architecture already supports:

```text
language
→ semantic structure
→ canonical IR
→ persistent state
→ deterministic execution
```

This experiment adds a new capability:

```text
interaction
→ successful execution trace
→ reusable procedure discovery
→ verification
→ persistent procedure storage
→ later retrieval
→ exact re-execution
```

The central research question is:

> Can the system increase its behavioral repertoire by discovering and storing executable procedures outside the neural model?

The target is **not** online neural fine-tuning.

Instead, the system learns by turning successful interactions into durable executable knowledge.

The intended architecture is:

```text
USER REQUEST
    ↓
language frontend
    ↓
semantic task description
    ↓
planner / procedure proposer
    ↓
known VM primitives + known procedures
    ↓
successful trace
    ↓
procedure abstraction
    ↓
verification
    ↓
persistent procedure library
    ↓
future retrieval and execution
```

The procedure library becomes a form of persistent procedural memory.

A successful result would show that the system can gain reusable capability without increasing neural parameter count.

---

# 1. Primary scientific question

> Can a Stateful Semantic VM acquire a reusable procedure from one or more successful interactions, verify that procedure against its source behavior, persist it, and later invoke it on different inputs without neural retraining?

---

# 2. Secondary questions

The experiment should also determine:

```text
1. Can repeated traces be abstracted into a parameterized procedure?

2. Can one-shot demonstrated workflows be stored safely when the abstraction is unambiguous?

3. Can learned procedures call other learned procedures?

4. Can procedures survive process restart?

5. Can procedure retrieval work from natural-language requests?

6. Can verification prevent incorrect abstractions from entering the executable library?

7. Can procedural capability grow while model weights remain frozen?
```

---

# 3. What counts as learning?

This experiment distinguishes three kinds of learning.

## 3.1 Fact learning

Example:

```text
Alice is the project manager.
```

Stored as world state.

## 3.2 Procedure learning

Example:

```text
To prepare the weekly report:
1. find this week's open customer notes;
2. group them by account;
3. summarize each account;
4. create a report;
5. return the report.
```

Stored as an executable procedure.

## 3.3 Neural learning

Example:

```text
fine-tune the language frontend from accumulated corrections
```

This is outside the primary experiment.

Procedure discovery must succeed without neural weight updates.

---

# 4. Core claim boundary

A positive result means:

> The system can acquire executable procedural knowledge externally and reuse it later.

It does **not** mean:

```text
the model learned new neural weights
the system discovered arbitrary algorithms
the system can safely synthesize unrestricted code
the system can autonomously invent new primitive semantics
the system is generally self-improving
```

---

# 5. Frozen neural components

For the primary experiment, freeze all neural components used for interaction.

This may include:

```text
small LLM frontend
frozen semantic binder
response renderer, if neural
```

Requirements:

```text
no optimizer
no gradient updates
no online fine-tuning
model hashes unchanged before/after run
```

The only persistent capability change must come from:

```text
new external procedure objects
```

---

# 6. Procedure model

A procedure is an explicitly stored executable object.

Conceptual form:

```json
{
  "procedure_id": "proc:000001",
  "name": "summarize_open_requests",
  "version": 1,
  "parameters": [
    {
      "name": "entity",
      "type": "ENTITY"
    }
  ],
  "preconditions": [],
  "program": [],
  "postconditions": [],
  "created_from": [],
  "verification_status": "VERIFIED",
  "created_at": "..."
}
```

Procedures are not stored only as natural-language prose.

They must have an executable canonical representation.

---

# 7. Procedure instruction set

V1 learned procedures may contain only:

```text
existing VM primitives
+
calls to already verified procedures
```

No new primitive semantics may be invented.

Initial procedure-level operations may include:

```text
CALL_PRIMITIVE
CALL_PROCEDURE
BIND
LET
IF
FOR_EACH
RETURN
ASSERT_PRECONDITION
ASSERT_POSTCONDITION
```

Only include control-flow operations that can be interpreted deterministically.

Do not execute arbitrary Python, shell, JavaScript, or generated source code.

---

# 8. Primitive library

Before procedure discovery, freeze the allowed primitive library.

Example categories:

```text
STATE
    CREATE
    ASSERT
    RETRACT
    DELETE
    UPDATE
    FIND
    MATCH
    GET

TRANSFORM
    FILTER
    GROUP_BY
    SORT
    SELECT
    MAP

CONTROL
    IF
    FOR_EACH

OUTPUT
    RETURN
```

If some primitives do not yet exist, implement and test them before the experiment lock.

Do not add primitives after inspecting procedure-discovery failures unless through an explicit amendment.

---

# 9. Procedure library

Use a persistent store such as:

```text
procedures.sqlite
```

or equivalent tables inside the existing Semantic VM SQLite world.

Recommended tables:

```sql
procedures(
    procedure_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    program_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    preconditions_json TEXT NOT NULL,
    postconditions_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_hash TEXT NOT NULL
)

procedure_examples(
    procedure_id TEXT NOT NULL,
    interaction_id TEXT NOT NULL,
    role TEXT NOT NULL
)

procedure_tests(
    procedure_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    passed INTEGER NOT NULL,
    result_json TEXT NOT NULL
)

procedure_aliases(
    procedure_id TEXT NOT NULL,
    alias TEXT NOT NULL
)
```

---

# 10. Procedure lifecycle

Every procedure moves through explicit states:

```text
CANDIDATE
→ TESTING
→ VERIFIED
→ ACTIVE
```

Possible rejection states:

```text
REJECTED_AMBIGUOUS
REJECTED_FAILED_REPLAY
REJECTED_FAILED_COUNTERFACTUAL
REJECTED_UNSAFE
REJECTED_NONDETERMINISTIC
```

Only:

```text
ACTIVE
```

procedures may be invoked during normal operation.

---

# 11. Discovery sources

A candidate procedure may originate from:

```text
A. explicit user instruction

B. a successful multi-step interaction

C. multiple successful traces with common structure

D. composition of existing procedures

E. a planner-generated trace that was fully executed and verified
```

Do not learn directly from an unsuccessful trace.

---

# 12. Explicit teaching mode

Support a deliberate interaction mode:

```text
:teach <procedure-name>
```

Example:

```text
semvm> :teach weekly_report

semvm> Find all open customer notes from this week.
semvm> Group them by account.
semvm> Summarize each account.
semvm> Put the summaries in a report.
semvm> :endteach
```

The resulting trace becomes a procedure candidate.

A natural-language equivalent may later be supported, but explicit teaching mode provides the cleanest first experiment.

---

# 13. Trace capture

During teaching or discovery, record:

```text
user utterance
semantic interpretation
resolved arguments
primitive call
procedure call
state before
state after
return value
branch decisions
loop iterations
errors
```

The recorded trace must be sufficient to reconstruct the executed computation.

---

# 14. One-shot procedure discovery

V1 should support the simplest successful case:

```text
one successful trace
+
explicit user indication that it should be reusable
```

Example:

```text
User:
"When I ask for an open-request summary, do what we just did."
```

Candidate abstraction:

```text
PROC summarize_open_requests(entity):
    requests = FIND(type=REQUEST, owner=entity, status=OPEN)
    summary = SUMMARIZE(requests)
    RETURN summary
```

One-shot discovery is allowed only if variable/constant separation is unambiguous.

Otherwise require additional examples.

---

# 15. Multi-example abstraction

The stronger discovery path uses multiple successful traces.

Example traces:

```text
Alice:
    FIND open requests for Alice
    → summarize
    → return

Bob:
    FIND open requests for Bob
    → summarize
    → return

Acme:
    FIND open requests for Acme
    → summarize
    → return
```

The system should propose:

```text
parameter:
    entity

constants:
    request status = OPEN

structure:
    FIND
    → SUMMARIZE
    → RETURN
```

Result:

```text
PROC summarize_open_requests(entity)
```

---

# 16. Constant versus parameter discovery

Candidate abstraction must classify values as:

```text
PARAMETER
CONSTANT
DERIVED
LOCAL_TEMPORARY
```

Example:

```text
Alice / Bob / Acme
→ PARAMETER

OPEN
→ CONSTANT

query result list
→ LOCAL_TEMPORARY
```

The system must not parameterize everything by default.

Nor may it accidentally freeze example-specific values that vary across demonstrations.

---

# 17. Procedure proposal role of the LLM

A small LLM may propose:

```text
procedure name
parameter list
candidate abstraction
candidate program
preconditions
postconditions
aliases / trigger phrases
```

But the LLM proposal is not authoritative.

The deterministic procedure system must validate and verify it before storage as ACTIVE.

Architecture:

```text
trace(s)
    ↓
LLM proposal
    ↓
canonical procedure AST
    ↓
static validator
    ↓
replay tests
    ↓
counterfactual tests
    ↓
ACTIVE or REJECTED
```

---

# 18. Canonical procedure AST

Define a stable JSON procedure representation.

Example:

```json
{
  "name": "summarize_open_requests",
  "parameters": [
    {
      "name": "entity",
      "type": "ENTITY"
    }
  ],
  "body": [
    {
      "op": "FIND",
      "bind": "requests",
      "args": {
        "type": "REQUEST",
        "entity": {"param": "entity"},
        "status": "OPEN"
      }
    },
    {
      "op": "CALL_PROCEDURE",
      "procedure": "summarize",
      "bind": "summary",
      "args": {
        "items": {"var": "requests"}
      }
    },
    {
      "op": "RETURN",
      "value": {"var": "summary"}
    }
  ]
}
```

All procedure execution must operate on this canonical representation.

---

# 19. Static validation

Before execution, validate:

```text
all ops allowed
all called primitives exist
all called procedures are ACTIVE
all parameters typed
all variables defined before use
no dangling references
no unrestricted code
no recursion unless explicitly enabled
no cycles unless explicitly enabled
bounded control flow where required
```

V1 should disable recursion.

---

# 20. Verification stage 1 — source replay

A candidate procedure must reproduce every source trace.

For each teaching example:

```text
original trace result
==
procedure execution result
```

Compare:

```text
return value
state diff
observable side effects
post-state
```

Required:

```text
SOURCE_REPLAY_EXACT = 1.0
```

Otherwise reject.

---

# 21. Verification stage 2 — counterfactual inputs

The procedure must be tested on arguments not used in its source examples.

For a parameterized procedure:

```text
source:
    Alice
    Bob

counterfactual:
    Carol
```

The counterfactual expected result should come from an independent oracle or directly executing the unabstracted primitive sequence with substituted arguments.

Required:

```text
COUNTERFACTUAL_EXACT = 1.0
```

for all deterministic V1 verification cases.

---

# 22. Verification stage 3 — negative cases

Test at least:

```text
missing required input
wrong parameter type
empty result set
ambiguous entity
deleted object
precondition false
```

The candidate must fail safely.

No partial mutation.

---

# 23. Verification stage 4 — transaction safety

A procedure invocation is one transaction unless explicitly registered otherwise.

If step N fails:

```text
all earlier state mutations rollback
```

Required:

```text
state_hash_before == state_hash_after
```

for injected failure cases.

---

# 24. Verification stage 5 — determinism

Given:

```text
same active procedure
same arguments
same starting state
```

require:

```text
same program trace
same state diff
same return
same final state hash
```

for deterministic procedures.

---

# 25. Procedure activation

Only after all required tests pass:

```text
status = ACTIVE
```

Write:

```text
procedure hash
verification manifest
source interaction IDs
test hashes
```

Activation is itself logged.

---

# 26. Procedure retrieval

At runtime:

```text
natural-language request
    ↓
frontend
    ↓
procedure retrieval candidates
    ↓
deterministic compatibility check
    ↓
procedure invocation
```

The language model may rank candidate procedures.

The final selected procedure must satisfy deterministic:

```text
name / alias match
argument compatibility
preconditions
```

---

# 27. Procedure aliases

A procedure may have aliases such as:

```text
weekly report
prepare customer report
make the customer summary
```

Aliases are external metadata.

Adding an alias does not alter procedure semantics.

---

# 28. Clarification

If more than one active procedure matches:

```text
CLARIFY
```

Do not choose arbitrarily.

Example:

```text
prepare report
```

could match:

```text
weekly_customer_report
monthly_financial_report
```

The system should ask which one.

---

# 29. Persistence requirement

This is a hard gate.

Registered test:

```text
1. teach procedure
2. verify procedure
3. activate procedure
4. terminate every process
5. restart system
6. do not supply teaching transcript
7. request procedure with new argument
8. retrieve stored procedure
9. execute correctly
```

Required:

```text
RESTART_PROCEDURE_EXACT = 1.0
```

This demonstrates true external procedural memory.

---

# 30. No hidden conversational dependence

After restart, procedure execution must not depend on:

```text
old conversation transcript
LLM hidden state
cached prompt
training-time demonstration text
```

It may depend only on:

```text
procedure library
world state
current request
registered runtime components
```

---

# 31. Procedure composition

The second major capability is composition.

Suppose the system has learned:

```text
P1:
    summarize_open_requests(entity)

P2:
    email_report(person, report)
```

A later procedure may be:

```text
P3 prepare_and_email_open_request_summary(entity, recipient):
    r = CALL P1(entity)
    CALL P2(recipient, r)
```

The new procedure may call verified procedures exactly like primitives.

---

# 32. Composition test

Register a test in which:

```text
P1 is taught
P2 is taught
```

but:

```text
P1→P2 exact composition
```

is never demonstrated.

Then request a task requiring:

```text
P2(P1(x))
```

There are two levels of success.

## Level 1 — planner composition

The system dynamically calls P1 then P2.

## Level 2 — procedure abstraction

The system stores:

```text
P3 = P2(P1(x))
```

as a new verified procedure.

Report both separately.

---

# 33. Procedure hierarchy

Track:

```text
procedure depth
number of primitive calls
number of procedure calls
dependency DAG
```

Do not permit unresolved dependency cycles.

---

# 34. Procedure versioning

Never overwrite a procedure implementation in place.

Use:

```text
proc:weekly_report:v1
proc:weekly_report:v2
```

The active alias may point to a selected version.

Record:

```text
parent version
change reason
source examples
verification results
```

---

# 35. Correcting a procedure

If the user says:

```text
"When I ask for the weekly report, also include closed high-priority issues."
```

do not mutate v1 silently.

Create:

```text
candidate v2
```

Verify it independently.

Then activate v2 if it passes.

Retain v1 for rollback/audit.

---

# 36. Learning from ordinary interaction

Outside explicit teaching mode, the system may detect a candidate reusable trace.

Example:

```text
same multi-step pattern successfully executed three times
```

It may propose:

```text
"I noticed you often do X → Y → Z. Save this as a procedure?"
```

V1 should require explicit approval before activating automatically discovered procedures.

---

# 37. Candidate discovery threshold

Suggested initial rule:

```text
explicit teaching:
    1 successful trace may be enough

implicit discovery:
    >= 2 structurally compatible successful traces
```

This is an engineering default, not a scientific claim.

Any automatic activation still requires verification.

---

# 38. Similarity / abstraction criterion

For multiple traces, distinguish:

```text
same procedure, different arguments
```

from:

```text
superficially similar but semantically different procedures
```

A candidate group must agree on:

```text
operation sequence / control structure
primitive/procedure identities
data dependencies
side-effect pattern
```

after candidate parameter substitution.

---

# 39. Procedure equivalence

Two procedures are behaviorally equivalent on a test set if they produce:

```text
same returned value
same externally visible state diff
same final semantic state
```

Internal temporary variable names and harmless canonical ordering do not matter.

---

# 40. Procedure verification oracle

Where possible, use an independent oracle.

For synthetic scenarios:

```text
gold procedure AST
```

must be generated independently from the discovery implementation.

The discovery system must not import the oracle.

---

# 41. Scenario families

Build at least these categories.

## P1 — one-shot explicit teaching

Teach one procedure from one successful trace.

## P2 — multi-example parameter discovery

Teach two or more examples differing in one argument.

## P3 — multiple parameters

Examples differ in two independent inputs.

## P4 — constant preservation

Some values vary; at least one semantic constant must remain fixed.

## P5 — restart reuse

Teach → restart → invoke.

## P6 — counterfactual argument

Invoke on never-demonstrated argument.

## P7 — procedure composition

Combine two learned procedures.

## P8 — rejected bad abstraction

Candidate over-generalizes and must fail verification.

## P9 — ambiguity

Multiple procedures match; system must clarify.

## P10 — procedure revision

Create v2 while retaining v1.

## P11 — rollback

Failure mid-procedure leaves state unchanged.

## P12 — nested procedure persistence

A stored procedure depending on another stored procedure survives restart.

---

# 42. DEV / LOCKED_TEST

Create:

```text
DEV
LOCKED_TEST
```

Recommended:

```text
DEV:
    30 procedure-learning scenarios

LOCKED_TEST:
    20 scenarios
```

Exact counts may differ before lock.

LOCKED_TEST must be generated and hash-frozen before final DEV tuning.

Run LOCKED_TEST once.

---

# 43. Metrics

Report:

```text
PROCEDURE_PROPOSAL_VALID
SOURCE_REPLAY_EXACT
COUNTERFACTUAL_EXACT
NEGATIVE_CASE_SAFE
ROLLBACK_EXACT
RESTART_PROCEDURE_EXACT
PROCEDURE_RETRIEVAL_EXACT
ARGUMENT_BINDING_EXACT
PROCEDURE_COMPOSITION_EXACT
FINAL_STATE_EXACT
SCENARIO_EXACT
```

---

# 44. Primary metric

Primary:

```text
SCENARIO_EXACT
```

A scenario is exact only if:

```text
correct procedure discovered
correct parameters abstracted
verification behaves correctly
activation/rejection correct
persistent storage correct
later retrieval correct
execution correct
final state correct
```

---

# 45. Initial gates

Before LOCKED_TEST:

```text
SOURCE_REPLAY_EXACT          = 1.00
COUNTERFACTUAL_EXACT         = 1.00
ROLLBACK_EXACT               = 1.00
RESTART_PROCEDURE_EXACT      = 1.00
PROCEDURE_RETRIEVAL_EXACT    >= .95
ARGUMENT_BINDING_EXACT       >= .95
SCENARIO_EXACT               >= .90
```

Deterministic runtime components must be perfect on gold procedures.

---

# 46. Gold-procedure bypass control

Mandatory.

Run each scenario in two modes:

```text
DISCOVERED
    interaction
    → discovery
    → candidate
    → verification
    → procedure
    → execute

GOLD_PROC
    independent gold procedure
    → execute
```

Required:

```text
GOLD_PROC DEV exact = 1.00
```

If GOLD_PROC fails, the runtime is not ready.

---

# 47. Procedure-discovery failure taxonomy

Use:

```text
PD_TRACE
    source execution trace incomplete/wrong

PD_GROUP
    incompatible traces grouped together

PD_PARAMETER
    wrong parameter/constant split

PD_PROGRAM
    wrong candidate program

PD_PRECONDITION
    incorrect precondition inference

PD_POSTCONDITION
    incorrect postcondition inference

PD_VERIFY_FALSE_REJECT
    valid candidate rejected

PD_VERIFY_FALSE_ACCEPT
    invalid candidate accepted

PR_RETRIEVE
    wrong procedure retrieved

PR_ARGUMENT
    wrong runtime arguments

PR_COMPOSE
    procedure composition failure

VM_EXEC
    deterministic runtime failure

STORE
    persistence failure

ROLLBACK
    transactional failure
```

False acceptance is especially important.

---

# 48. Safety principle

The system may learn new **procedures**, but not new unrestricted execution authority.

V1 procedures may only call:

```text
allowlisted primitives
verified procedures
```

No procedure may contain:

```text
shell command
Python eval
dynamic import
arbitrary file operation
network request
external side effect
```

unless that capability is later introduced as a separately governed primitive.

---

# 49. Procedure capabilities are typed

Every primitive/procedure should declare effects.

Example:

```json
{
  "reads": ["REQUEST"],
  "writes": [],
  "external_effects": []
}
```

or:

```json
{
  "reads": ["REMINDER"],
  "writes": ["REMINDER"],
  "external_effects": []
}
```

Static validation may reject incompatible or unauthorized compositions.

---

# 50. Pure versus effectful procedures

Distinguish:

```text
PURE
    no state mutation

STATEFUL
    modifies Semantic VM state

EXTERNAL
    causes outside-world action
```

V1 should support:

```text
PURE
STATEFUL
```

External procedures are out of scope.

---

# 51. Procedure signatures

A procedure has:

```text
name
typed parameters
return type
effect class
preconditions
postconditions
```

Example:

```text
summarize_open_requests(
    entity: ENTITY
) -> REPORT

effects:
    PURE
```

This improves deterministic retrieval and composition.

---

# 52. State-aware procedures

Procedures may query current world state.

Example:

```text
reschedule_last_reminder(time):
    r = FIND_LAST(REMINDER)
    UPDATE(r, WHEN, time)
```

They must not depend on hidden conversational memory.

---

# 53. Procedure explanation

Support:

```text
:procedure <name>
```

to show:

```text
signature
description
dependencies
source interactions
verification status
canonical program
version history
```

The user should be able to inspect what the system learned.

---

# 54. Procedure deletion / disabling

Support:

```text
:disable-procedure <name>
:enable-procedure <name>
:delete-procedure <name>
```

Deletion should be explicit and logged.

A disabled procedure remains stored but cannot be called.

---

# 55. Procedure provenance

Every procedure must record:

```text
who/what proposed it
source interactions
source trace hashes
frontend model version
binder version
runtime version
verification suite
timestamp
```

This keeps learned behavior auditable.

---

# 56. Procedure reuse after language variation

A learned procedure should be retrievable from multiple surface requests.

Example aliases:

```text
"show me Alice's open requests"
"summarize Alice's outstanding requests"
"what's still open for Alice?"
```

The language frontend may map all of these to:

```text
CALL summarize_open_requests(Alice)
```

This is a separate language-retrieval problem from procedure semantics.

---

# 57. Semantic procedure identity

Procedure identity should be based on canonical program/signature, not exact wording.

Two aliases may invoke the same procedure.

Two semantically different programs must remain separate even if their names are similar.

---

# 58. Interaction-learning relationship

The procedure library and neural interaction replay are separate.

A correction can produce:

```text
procedure update
```

without:

```text
neural fine-tune
```

Later, accumulated language examples may also fine-tune the frontend.

Do not conflate these two learning mechanisms.

---

# 59. Capability growth accounting

Track system capability in at least:

```text
number of active procedures
procedure dependency depth
number of unique primitives used
number of parameterized procedures
number of compositional procedures
verification pass rate
```

This gives a direct measure of external procedural growth.

---

# 60. Model-size accounting

Report separately:

```text
neural parameters
procedure-library bytes
world-model bytes
runtime-state bytes
```

A key architectural question is whether:

```text
procedural capability ↑
```

can occur while:

```text
neural parameter count = constant
```

---

# 61. Compute accounting

Report:

```text
procedure proposal latency
verification latency
retrieval latency
execution latency
number of LLM calls
number of VM ops
```

Compare:

```text
first-time task
vs
stored-procedure reuse
```

A stored procedure should generally require less planning work than rediscovering the workflow.

---

# 62. Cache / compile optimization

After activation, optionally precompile canonical procedure AST into an efficient internal representation.

The canonical procedure source remains authoritative.

Compiled caches may be regenerated.

---

# 63. Decisive V1 demonstration

The minimum compelling demonstration is:

```text
1. Start with no procedure P.

2. User teaches a novel multi-step task.

3. System executes it successfully using primitives.

4. System abstracts P.

5. P passes source replay and counterfactual verification.

6. P becomes ACTIVE.

7. Terminate all processes.

8. Restart from persistent databases.

9. User requests the task with a new argument and different wording.

10. System retrieves P.

11. P executes correctly.

12. No neural weight changed.
```

This is the primary proof of persistent procedural learning.

---

# 64. Stronger demonstration

Then:

```text
1. Teach P1.

2. Teach P2.

3. Restart.

4. Request a task requiring P2(P1(x)).

5. System composes the two.

6. Verify the composition.

7. Optionally store it as P3.

8. Restart again.

9. Invoke P3 directly.
```

This tests cumulative procedural composition.

---

# 65. Example

Suppose the VM already has primitives:

```text
FIND
FILTER
GROUP_BY
CREATE
APPEND
RETURN
```

User teaches:

```text
"Weekly customer report means:
find this week's customer notes,
keep the open ones,
group them by account,
and put a summary for each account into a report."
```

Candidate:

```text
PROC weekly_customer_report():
    notes = FIND(type=NOTE, time=THIS_WEEK)
    open_notes = FILTER(notes, status=OPEN)
    groups = GROUP_BY(open_notes, account)
    report = CREATE(type=REPORT)

    FOR_EACH group IN groups:
        summary = CALL_PROCEDURE(summarize, group)
        APPEND(report, summary)

    RETURN report
```

If verified, later:

```text
"Make the weekly customer report."
```

becomes:

```text
CALL_PROCEDURE weekly_customer_report()
```

No re-teaching.

---

# 66. No automatic trust from natural-language instruction

A user's prose definition is evidence for a candidate procedure.

It is not executable truth.

Always:

```text
parse
→ construct candidate
→ validate
→ verify
→ activate
```

---

# 67. Explicit acceptance after verification

Recommended UX:

```text
"I learned a procedure called `weekly_customer_report`.
It passed 6 verification cases. Save it?"
```

For the first POC, require explicit:

```text
yes
```

before ACTIVE status.

This can be relaxed in later experiments.

---

# 68. Procedure confidence

Do not use opaque scalar confidence as the primary safety mechanism.

Prefer explicit status:

```text
CANDIDATE
VERIFIED
ACTIVE
REJECTED
```

along with test evidence.

---

# 69. Generalization categories

For each procedure report:

```text
REPLAY
    same exact inputs

ARGUMENT_GENERALIZATION
    new values

SURFACE_GENERALIZATION
    different wording

COMPOSITION_GENERALIZATION
    new combination of known procedures

STATE_GENERALIZATION
    different but compatible world state
```

Do not collapse these into one accuracy number.

---

# 70. Anti-cheating rules

The procedure discovery system must not:

```text
inspect LOCKED_TEST gold procedures
use test scenario identifiers as features
hard-code known procedure names from test
retrieve source teaching transcript after restart unless stored as provenance only
use hidden gold outputs during verification
```

---

# 71. Procedure benchmark construction

Each procedure family should define:

```text
teaching examples
counterfactual examples
negative examples
restart invocation
surface paraphrases
gold canonical procedure
expected state / return
```

Generate DEV and LOCKED_TEST from separate seeds/templates.

---

# 72. Training is not required

The initial procedure-discovery POC should require:

```text
0 neural optimizer steps
```

If neural fine-tuning is later useful for better proposal quality, register it as a separate experiment.

The core capability under test is external procedural learning.

---

# 73. Recommended implementation architecture

```text
procedure/
├── ast.py
├── schema.json
├── validator.py
├── executor.py
├── compiler.py
├── store.py
├── retrieval.py
├── discovery.py
├── abstraction.py
├── verify.py
├── provenance.py
└── explain.py
```

Suggested project additions:

```text
learning/
├── procedure_candidates/
├── rejected/
└── accepted/

results/
├── PROCEDURE_DEV.json
├── PROCEDURE_LOCKED_TEST.json
└── PROCEDURE_DISCOVERY_REPORT.md
```

---

# 74. Required artifacts

Produce:

```text
spec/SEMVM_PROCEDURE_DISCOVERY_POC_V1.md
spec/PROCEDURE_SCHEMA.json
spec/PROCEDURE_PRIMITIVES_V1.json

locks/PROCEDURE_POC_LOCK.json

results/PROCEDURE_UNIT_TESTS.json
results/PROCEDURE_DEV.json
results/PROCEDURE_LOCKED_TEST.json
results/PROCEDURE_DISCOVERY_REPORT.md
results/PROCEDURE_ARTIFACT_MANIFEST.json
```

Persist:

```text
procedures.sqlite
```

for restart tests.

---

# 75. Unit tests

Before scenario evaluation require tests for:

```text
AST validation
parameter binding
constant preservation
variable scope
CALL_PROCEDURE
dependency validation
cycle rejection
source replay
counterfactual replay
transaction rollback
restart persistence
versioning
disable/enable
alias retrieval
ambiguous retrieval
canonical hashing
```

Deterministic unit tests must all pass.

---

# 76. Stop conditions

Stop for review if:

```text
S1
candidate procedures require arbitrary generated code

S2
the verifier cannot independently detect a deliberately bad abstraction

S3
procedure invocation depends on the original teaching transcript after restart

S4
persistent procedure hashes are unstable

S5
procedure composition can bypass effect restrictions

S6
GOLD_PROC deterministic execution is not exact

S7
LOCKED_TEST is exposed during development

S8
procedure activation occurs without verification
```

---

# 77. Interpretation map

## RESULT A — persistent procedural learning succeeds

If the system:

```text
discovers
verifies
stores
restarts
retrieves
executes on new arguments
```

with high scenario exact:

> The Semantic VM can acquire new reusable executable capabilities through external procedural memory without neural weight updates.

## RESULT B — replay works, abstraction fails

If exact demonstrated traces can be stored/replayed but new arguments fail:

> Episodic workflow memory works, but parameterized procedure discovery is not yet solved.

## RESULT C — abstraction works, retrieval fails

If stored procedures execute correctly when named directly but natural requests select them poorly:

> Procedural memory works; language-to-procedure retrieval is the bottleneck.

## RESULT D — proposal works, verification rejects too much

> Procedure synthesis may be adequate, but the verifier is too restrictive or the test-generation strategy is weak.

## RESULT E — verifier accepts bad procedures

> Stop. Procedure learning is unsafe/unreliable under the current verifier and must not be activated automatically.

## RESULT F — composition fails

> Atomic procedural learning works, but cumulative procedural composition remains unresolved.

---

# 78. Relation to the broader Semantic VM thesis

The architecture becomes:

```text
LANGUAGE
    ↓
small neural frontend
    ↓
semantic / procedural intent
    ↓
small structural binder where needed
    ↓
canonical IR
    ↓
persistent world model
    ↓
procedure retrieval
    ↓
persistent procedure library
    ↓
deterministic VM
```

Two persistent knowledge stores now coexist:

```text
WORLD MODEL
    what is true

PROCEDURE LIBRARY
    how to do things
```

The neural model primarily interprets and proposes.

The external system stores facts, stores procedures, and executes them.

---

# 79. Long-term hypothesis

If successful, this experiment supports a larger hypothesis:

> Model parameters need not contain every reusable skill. A system can accumulate verified executable procedures externally and compose them at runtime, allowing behavioral capability to grow independently of neural parameter count.

This is a future research direction, not a claim from V1 alone.

---

# 80. Immediate implementation order

Proceed in this order:

```text
1. Freeze primitive/effect inventory.

2. Define canonical procedure AST.

3. Implement procedure store.

4. Implement deterministic procedure executor.

5. Implement source replay verifier.

6. Implement counterfactual verifier.

7. Implement restart persistence.

8. Implement explicit :teach mode.

9. Implement trace → candidate abstraction.

10. Implement candidate proposal with the small LLM.

11. Build synthetic DEV procedure scenarios.

12. Ensure GOLD_PROC = 1.00.

13. Reach DEV gates.

14. Freeze LOCKED_TEST and implementation.

15. Run LOCKED_TEST once.

16. Report and stop.
```

---

# 81. Final target

The desired behavior is:

```text
User:
"When I ask for an open-request summary, find the person's open requests,
summarize them, and return the summary."

System:
"Understood. I'll test that procedure before saving it."

[verification passes]

System:
"I learned `summarize_open_requests(entity)`."

--- process exits and restarts ---

User:
"Give me Carol's open-request summary."

System:
[retrieves stored procedure]
[executes it with entity=Carol]

→ correct result
```

No model retraining occurs between those interactions.

The system has genuinely gained a persistent executable procedure.

---

# END
