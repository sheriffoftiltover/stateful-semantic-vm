# SEMVM_END_TO_END_POC_V1

**Project:** Stateful Semantic VM — End-to-End Proof of Concept  
**Version:** V1  
**Status:** Proposed implementation / integration specification  
**Primary frozen neural component:** A-005 R20, seed 17, epoch 40  
**Purpose:** Demonstrate a complete stateful semantic system in which a small frozen neural core converts language into structured semantic relations, while identity, persistence, exact state manipulation, query execution, and bookkeeping are performed outside the neural model.

---

# 0. Executive summary

This experiment moves the Stateful Semantic VM project from isolated semantic-binding experiments to an end-to-end integrated proof of concept.

The central system under test is:

```text
NATURAL LANGUAGE
        ↓
frozen neural semantic/binding core
        ↓
canonical semantic IR
        ↓
entity / temporal / reference resolution
        ↓
persistent world model
        ↓
deterministic semantic VM
        ↓
state update / query / action result
```

The primary POC question is:

> Can a frozen small neural core that has demonstrated single- and multi-modifier parent binding serve as the language-facing front end of a persistent deterministic semantic computer?

The POC is deliberately constrained. It does **not** attempt unrestricted conversational language, general-purpose reasoning, open-domain knowledge, or arbitrary action execution.

The initial ontology is restricted to the event and relation inventory already used in the parent-binding research:

```text
outer events:
    REMINDER
    PLAN
    REQUEST
    NOTE

inner events:
    CALL
    EMAIL
    VISIT
    MESSAGE

relations:
    TODO
    WHO
    WHEN
    WHERE
    RECIPIENT
    TOPIC
```

The POC must demonstrate:

1. natural language → canonical typed semantic structure;
2. correct independent parent binding for multiple modifiers;
3. persistent object and relation storage;
4. deterministic updates;
5. deterministic queries over previously stored state;
6. multi-turn reference resolution within a bounded supported regime;
7. transparent execution traces;
8. strict localization of failures to neural parsing, resolution, compilation, storage, execution, or response rendering.

The primary neural checkpoint is frozen throughout the POC.

No integration debugging is allowed to silently fine-tune or alter the neural core.

---

# 1. Motivation

The project has now demonstrated the following sequence.

## 1.1 P0

A successful P0 seed learned strong single-parent binding.

The successful model generalized nearly perfectly on held-out single-modifier examples.

However, frozen zero-shot transfer into P2 showed that the P0 solution was not genuinely modifier-local.

With two simultaneous modifiers:

```text
same-parent structures:
    OO / II
```

transferred strongly, while:

```text
mixed-parent structures:
    OI / IO
```

collapsed.

The model often made one sentence-level parent decision and reused it for both modifiers.

## 1.2 A-004

Continuation training from the successful P0 checkpoint on P2 rapidly acquired independent multi-modifier binding.

By epoch 40:

```text
P2 ID_VAL mixed-parent both-correct ≈ .925
P2 ID_TEST mixed-parent both-correct ≈ .96
P2 same-parent remained ≈ ceiling
```

This established that independent modifier-local parent binding is within the representational capacity of the existing neural architecture.

However, pure P2 continuation caused partial forgetting on P0.

## 1.3 A-005

A-005 introduced ordinary P0 replay during P2 continuation.

The R20 arm simultaneously preserved:

```text
P2 ID_VAL mixed-parent both-correct = .97
P2 ID_VAL same-parent both-correct  = .995
P0 ID_VAL exact                     = .9825
P0 pair consistency                 = .965
```

and descriptive ID_TEST results remained strong.

Therefore the project now has a concrete checkpoint that supports:

```text
single-modifier binding
multiple same-parent bindings
multiple independent mixed-parent bindings
```

within the tested P0/P2 regime.

That checkpoint is sufficient to justify an end-to-end systems integration POC.

---

# 2. Core scientific claim under test

The POC tests the following architectural proposition:

> A small neural model can be restricted to language-conditioned semantic structure prediction while persistent identity, exact state, graph traversal, deterministic updates, and query execution are externalized into a symbolic runtime.

The intended division of labor is:

```text
NEURAL CORE
-----------
language-conditioned semantic recognition
relation identification
argument identification
parent binding
local structured semantic evidence


EXTERNAL SEMANTIC SYSTEM
------------------------
persistent identity
canonical object IDs
persistent memory
exact relation storage
state transitions
graph traversal
query execution
temporal normalization
deterministic bookkeeping
auditable execution
```

The POC is successful if the entire pipeline can operate coherently without asking the neural core to perform responsibilities assigned to the external runtime.

---

# 3. Scope

## 3.1 In scope

The V1 POC includes:

- frozen A-005 R20 semantic binder;
- controlled natural-language inputs;
- canonical semantic IR;
- persistent entity/event IDs;
- deterministic relation storage;
- deterministic VM instructions;
- bounded entity resolution;
- bounded temporal normalization;
- multi-turn state updates;
- state queries;
- transparent traces;
- reproducible scenario evaluation;
- local and Modal-compatible execution;
- persistent SQLite-backed storage for the reference implementation.

## 3.2 Out of scope

The V1 POC does **not** attempt:

- arbitrary open-domain language;
- unrestricted pronoun/coreference resolution;
- arbitrary world knowledge;
- free-form planning;
- LLM-style answer generation;
- autonomous tool use;
- external web actions;
- arbitrary code execution;
- probabilistic database semantics;
- neural persistent memory;
- learning during normal POC operation;
- continual online updating of the neural checkpoint;
- replacement of the deterministic VM with a language model.

---

# 4. Frozen neural component

## 4.1 Engineering checkpoint

Freeze one explicit checkpoint as the POC neural artifact:

```text
SEMVM_BINDER_POC_V1

source experiment:
    A-005 — P0/P2 Replay Preservation

arm:
    R20

seed:
    17

checkpoint:
    epoch 40

status:
    engineering / existence-proof checkpoint
```

The checkpoint manifest must include:

```text
checkpoint SHA-256
model code SHA-256
configuration SHA-256
union vocabulary mapping hash
union template mapping hash
training corpus hashes
forest hashes
source experiment identifier
validated P0 metrics
validated P2 metrics
```

## 4.2 Frozen means frozen

During POC development and evaluation:

```text
requires_grad = false
optimizer = none
training mode = disabled
checkpoint state hash before inference = checkpoint state hash after inference
```

No integration failure may be repaired by changing neural weights.

Any future learned change requires a new separately registered model version.

## 4.3 Supported neural contract

The binder is responsible for producing evidence sufficient to identify:

- event constructor/type;
- entity/argument spans;
- relation type;
- relation arguments;
- parent event for each modifier/relation;
- local semantic structure needed to construct canonical IR.

The binder is **not** responsible for persistent IDs.

For example, it may output:

```text
PERSON("Alice")
CALL(event_1)
WHO(event_1, "Alice")
```

but it must not invent a persistent database key such as:

```text
person:alice:00017
```

That key belongs to the resolver/world model.

---

# 5. Canonical semantic IR

The neural output must be converted into one canonical representation before any persistent state mutation occurs.

The canonical IR is the contract between language understanding and deterministic execution.

## 5.1 Design requirements

The IR must be:

- typed;
- explicit;
- serializable;
- deterministic after parsing;
- independent of neural hidden states;
- sufficiently expressive for all V1 scenarios;
- easy to diff;
- easy to validate;
- easy to compile to VM instructions.

## 5.2 Canonical object types

Initial object types:

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
TOPIC_VALUE
TEXT_VALUE
```

Additional implementation-only types may exist, but must not alter semantic meaning.

## 5.3 Canonical relation types

Initial relation types:

```text
TODO
WHO
WHEN
WHERE
RECIPIENT
TOPIC
```

Each relation has a typed signature.

Example:

```text
TODO:
    OUTER_EVENT × INNER_EVENT

WHO:
    EVENT × PERSON

WHEN:
    EVENT × TIME

WHERE:
    EVENT × PLACE

RECIPIENT:
    EVENT × PERSON

TOPIC:
    EVENT × TOPIC_VALUE
```

The exact event subsets allowed for each relation must remain consistent with the frozen ontology used by the semantic binder.

## 5.4 Example IR

Input:

```text
Remind me tomorrow to call Alice and email Bob on Friday.
```

Possible canonical IR:

```json
{
  "utterance_id": "u000001",
  "objects": [
    {"local_id": "e0", "type": "REMINDER"},
    {"local_id": "e1", "type": "CALL"},
    {"local_id": "e2", "type": "EMAIL"},
    {"local_id": "p0", "type": "PERSON", "surface": "Alice"},
    {"local_id": "p1", "type": "PERSON", "surface": "Bob"},
    {"local_id": "t0", "type": "TIME", "surface": "tomorrow"},
    {"local_id": "t1", "type": "TIME", "surface": "Friday"}
  ],
  "relations": [
    {"predicate": "TODO", "subject": "e0", "object": "e1"},
    {"predicate": "TODO", "subject": "e0", "object": "e2"},
    {"predicate": "WHO", "subject": "e1", "object": "p0"},
    {"predicate": "RECIPIENT", "subject": "e2", "object": "p1"},
    {"predicate": "WHEN", "subject": "e0", "object": "t0"},
    {"predicate": "WHEN", "subject": "e2", "object": "t1"}
  ]
}
```

This example intentionally contains multiple distinct relation attachments.

The neural front end must not collapse them to a common parent.

---

# 6. IR validation layer

Before resolution or execution, every canonical IR object must pass deterministic validation.

Validation includes:

```text
known object type
known relation type
correct relation arity
correct relation signature
all local IDs defined
no duplicate local IDs
no dangling references
allowed event constructor for relation
well-formed local graph
```

Invalid IR must never partially mutate persistent state.

The system returns a structured failure:

```json
{
  "status": "IR_VALIDATION_ERROR",
  "reason": "...",
  "utterance_id": "..."
}
```

---

# 7. Persistent world model

## 7.1 Reference implementation

Use SQLite for V1.

This is deliberate.

The POC does not require a specialized graph database.

SQLite provides:

- persistence;
- transactions;
- portability;
- inspectability;
- reproducibility;
- deterministic query behavior;
- trivial backup/reset.

## 7.2 Core schema

A minimal schema may contain:

```sql
objects(
    object_id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by_utterance TEXT,
    status TEXT
)

relations(
    relation_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by_utterance TEXT,
    active INTEGER NOT NULL DEFAULT 1
)

aliases(
    alias_id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    alias_text TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    created_at TEXT NOT NULL
)

scalar_values(
    value_id TEXT PRIMARY KEY,
    value_type TEXT NOT NULL,
    normalized_value TEXT,
    surface_value TEXT
)

utterances(
    utterance_id TEXT PRIMARY KEY,
    raw_text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    parse_status TEXT NOT NULL
)

transactions(
    transaction_id TEXT PRIMARY KEY,
    utterance_id TEXT NOT NULL,
    committed INTEGER NOT NULL,
    state_diff_json TEXT NOT NULL
)
```

The implementation may normalize this differently if necessary.

The semantic behavior must remain equivalent.

---

# 8. Persistent identity

Persistent identity must be external to the neural model.

## 8.1 Local versus persistent IDs

Neural/IR stage:

```text
p0
e0
e1
```

Persistent layer:

```text
person:000017
reminder:000008
call:000012
```

The mapping occurs in the resolver.

## 8.2 Identity invariants

Once committed:

```text
persistent object ID never changes
```

Aliases may change or accumulate.

Example:

```text
Alice
Alice Smith
Dr. Alice
```

may all resolve to:

```text
person:000017
```

within a controlled test scenario.

---

# 9. Entity resolver

The V1 resolver should be intentionally simple and deterministic where possible.

## 9.1 Resolution order

For named entities:

```text
1. exact normalized alias match
2. unambiguous case-insensitive alias match
3. scenario-local reference rules
4. create new entity if explicitly allowed
5. otherwise RESOLUTION_AMBIGUOUS
```

Do not hide ambiguity by choosing arbitrarily.

## 9.2 Entity creation

Example:

```text
PERSON("Alice")
```

If no existing alias matches:

```text
CREATE PERSON → person:000017
ADD_ALIAS person:000017 "Alice"
```

## 9.3 Ambiguity

If two existing people are both named Alice:

```text
RESOLUTION_AMBIGUOUS
```

unless the supported controlled language supplies sufficient disambiguating information.

This is a feature, not a failure of the POC.

The VM should prefer explicit uncertainty over silent identity corruption.

---

# 10. Temporal resolver

Time normalization is external to the neural binder.

Examples:

```text
tomorrow
Friday
next Monday
at 3 PM
```

must resolve relative to an explicit reference timestamp.

Every test scenario must supply that reference time.

Example:

```text
reference:
    2026-09-26T16:00:00-07:00

"tomorrow"
→ 2026-09-27
```

The temporal resolver must produce both:

```text
surface form
normalized form
```

No scenario may depend on implicit wall-clock time.

---

# 11. Reference resolution across turns

V1 supports bounded discourse references.

Examples:

```text
"Remind me tomorrow to call Alice."

"Actually make that Friday."
```

The phrase:

```text
that
```

may resolve to the most recent compatible active semantic object under a registered deterministic rule.

Initial supported reference classes may include:

```text
that reminder
that call
that email
that visit
that message
it
that
```

The rules must be explicit.

Unsupported ambiguous references should fail rather than invoke unrestricted language-model inference.

---

# 12. Deterministic semantic VM

The VM consumes resolved canonical IR or explicit query/update instructions.

## 12.1 Initial instruction set

Minimum V1 instruction set:

```text
CREATE(type)
DELETE(object_id)

ASSERT(subject_id, predicate, object_id)
RETRACT(subject_id, predicate, object_id)

GET(subject_id, predicate)
FIND(type, constraints...)
MATCH(pattern)

SET_STATE(object_id, key, value)

RETURN(value)
RETURN_OBJECT(object_id)
RETURN_RELATIONS(object_id)
```

Implementation convenience instructions are allowed if they can be reduced to deterministic operations over persistent state.

## 12.2 Transactional execution

Each utterance executes as one transaction.

Pipeline:

```text
parse
validate
resolve
compile
begin transaction
execute
validate postconditions
commit
```

If execution fails:

```text
rollback
```

No partial semantic update is permitted.

---

# 13. Compilation

The compiler converts resolved IR into VM instructions.

Example resolved IR:

```text
REMINDER r8
CALL c12
PERSON alice17

TODO(r8, c12)
WHO(c12, alice17)
WHEN(r8, 2026-09-27)
```

compiles to:

```text
CREATE REMINDER → r8
CREATE CALL → c12
ASSERT(r8, TODO, c12)
ASSERT(c12, WHO, alice17)
ASSERT(r8, WHEN, 2026-09-27)
```

Compilation must be deterministic.

The compiler must not use neural inference.

---

# 14. Query path

Queries should use the same front end where possible, but compile to read-only VM programs.

Example:

```text
Who am I supposed to call tomorrow?
```

Possible query IR:

```text
target_type = PERSON

pattern:
    REMINDER r
    CALL c
    PERSON p

    TODO(r, c)
    WHO(c, p)
    WHEN(r, tomorrow)
```

Compiled VM query:

```text
MATCH {
    r: REMINDER
    c: CALL
    p: PERSON

    TODO(r,c)
    WHO(c,p)
    WHEN(r,2026-09-27)
}

RETURN p
```

The response should be generated from the deterministic query result.

No neural world-state recall is allowed.

---

# 15. Update path

Example:

```text
Actually make that Friday.
```

Resolution identifies:

```text
target = reminder:000008
```

Compiler emits:

```text
RETRACT(reminder:000008, WHEN, 2026-09-27)
ASSERT(reminder:000008, WHEN, 2026-10-02)
```

The transaction commits atomically.

Subsequent queries must reflect the updated state.

---

# 16. Response rendering

V1 response rendering should be intentionally simple.

Preferred implementation:

```text
structured result
        ↓
deterministic template renderer
```

Examples:

```text
PERSON result → "Alice"
TIME result   → "Friday"
confirmation  → "Okay."
not found     → "I don't have a matching item."
ambiguous     → explicit ambiguity response
```

Do not introduce a generative response model in V1.

The goal is to test semantic computation, not response fluency.

---

# 17. End-to-end trace

Every processed utterance must produce a trace.

Required trace stages:

```text
INPUT
NEURAL OUTPUT
CANONICAL IR
IR VALIDATION
RESOLUTION
COMPILED VM PROGRAM
STATE BEFORE
VM EXECUTION
STATE DIFF
STATE AFTER
RETURN VALUE
RESPONSE
```

Example:

```text
INPUT
"Remind me tomorrow to call Alice."

NEURAL OUTPUT
REMINDER
CALL
TODO REMINDER→CALL
WHO CALL→Alice
WHEN REMINDER→tomorrow

CANONICAL IR
...

RESOLUTION
Alice → person:000017
tomorrow → 2026-09-27

VM PROGRAM
CREATE REMINDER
CREATE CALL
ASSERT TODO
ASSERT WHO
ASSERT WHEN

STATE DIFF
+ reminder:000008
+ call:000012
+ TODO(reminder:000008, call:000012)
+ WHO(call:000012, person:000017)
+ WHEN(reminder:000008, 2026-09-27)

RETURN
ACK

RESPONSE
"Okay."
```

---

# 18. Failure taxonomy

Every end-to-end failure must be assigned to exactly one primary stage where possible.

Initial taxonomy:

```text
N_PARSE
    wrong event / relation / argument prediction

N_BIND
    relation recognized but attached to wrong parent

IR_INVALID
    neural output cannot be converted into legal IR

RESOLVE_ENTITY
    wrong or ambiguous persistent entity mapping

RESOLVE_TIME
    wrong temporal normalization

RESOLVE_REFERENCE
    cross-turn reference failure

COMPILE
    valid resolved semantics compiled incorrectly

STORE
    persistence/state mutation defect

VM_EXEC
    deterministic instruction execution defect

QUERY
    graph pattern/query defect

RENDER
    correct result rendered incorrectly

UNSUPPORTED
    request lies outside registered V1 capability
```

This taxonomy is mandatory in evaluation reports.

---

# 19. Development scenario suite

Do not begin with a large benchmark.

Construct a small audited suite of compositional end-to-end scenarios.

Target:

```text
20–50 scenario families
```

Each scenario may contain multiple turns.

## 19.1 Scenario categories

At minimum include:

### S1 — single binding

```text
Remind me tomorrow to call Alice.
```

### S2 — multiple same-parent modifiers

```text
Remind me tomorrow at the office to call Alice.
```

### S3 — independent mixed-parent bindings

Example semantics requiring different event parents:

```text
WHEN → outer
WHO  → inner
```

and other legal relation combinations.

### S4 — two independent modifiers

Require:

```text
modifier A → outer
modifier B → inner
```

and reversed:

```text
modifier A → inner
modifier B → outer
```

### S5 — three or more simultaneous relations

For example:

```text
WHO
WHEN
WHERE
TOPIC
```

distributed legally across multiple events.

### S6 — persistent query

Write state in one turn, query it in a later turn.

### S7 — update

Create an item, modify one relation, verify old value is absent and new value is present.

### S8 — entity reuse

Mention the same person across several utterances and verify persistent ID reuse.

### S9 — multiple entities

Store multiple people/events and verify queries return only the correct one.

### S10 — ambiguity

Create an intentionally ambiguous reference and verify deterministic failure rather than silent corruption.

### S11 — deletion/retraction

Create a relation, retract it, verify it is no longer returned.

### S12 — restart persistence

Commit state, terminate process, restart, and verify state remains queryable.

---

# 20. Scenario design discipline

Every scenario must include a machine-readable gold specification:

```json
{
  "scenario_id": "...",
  "reference_time": "...",
  "turns": [...],
  "expected_ir": [...],
  "expected_state_diffs": [...],
  "expected_queries": [...],
  "allowed_responses": [...]
}
```

The gold must distinguish:

```text
semantic correctness
execution correctness
rendering correctness
```

---

# 21. Development versus held-out scenarios

Split scenarios into:

```text
DEV
LOCKED_TEST
```

Recommended first version:

```text
DEV:
    30 scenario families

LOCKED_TEST:
    20 scenario families
```

Exact counts may vary if construction requires adjustment before lock.

LOCKED_TEST must be frozen before integration tuning concludes.

Development may inspect DEV traces freely.

Do not inspect LOCKED_TEST results during normal debugging.

---

# 22. End-to-end metrics

## 22.1 Neural semantic exact

Exact canonical IR before persistent resolution.

```text
IR_EXACT
```

## 22.2 Binding accuracy

For every relation requiring a parent:

```text
PARENT_ACC
```

Also report:

```text
single-binding
same-parent multi-binding
mixed-parent multi-binding
```

separately.

## 22.3 Resolver accuracy

```text
ENTITY_RESOLUTION_ACC
TIME_RESOLUTION_ACC
REFERENCE_RESOLUTION_ACC
```

## 22.4 VM program exact

Compare compiled instruction program to canonical expected program modulo explicitly permitted canonicalization.

```text
VM_PROGRAM_EXACT
```

## 22.5 State exact

After every turn:

```text
STATE_EXACT
```

The complete active semantic graph must match expected state.

## 22.6 Query exact

```text
QUERY_RESULT_EXACT
```

## 22.7 End-to-end scenario exact

A scenario is exact only if all required turns:

```text
parse correctly
resolve correctly
mutate correctly
query correctly
leave correct final state
```

Metric:

```text
SCENARIO_EXACT
```

This is the primary POC metric.

---

# 23. Initial POC acceptance gates

Before running LOCKED_TEST, DEV must satisfy:

```text
IR_EXACT                  >= .95
PARENT_ACC                >= .97
VM_PROGRAM_EXACT          = 1.00
STATE_EXACT               >= .95
QUERY_RESULT_EXACT        >= .95
SCENARIO_EXACT            >= .90
```

For deterministic components alone:

```text
given gold IR:
    resolver/compiler/VM unit suite must be 100%
```

Any deterministic implementation bug must be fixed before LOCKED_TEST.

The neural front end is allowed to be imperfect.

The deterministic runtime is not.

---

# 24. Gold-IR bypass control

This is mandatory.

For every scenario, run two paths:

```text
A. FULL
   natural language
   → neural parser
   → IR
   → resolver
   → VM

B. GOLD_IR
   gold canonical IR
   → resolver
   → VM
```

The GOLD_IR path isolates the deterministic system.

Required before final evaluation:

```text
GOLD_IR DEV scenario exact = 1.00
```

If GOLD_IR is below 1.00, do not attribute FULL failures to the neural core.

---

# 25. Frozen-parser replay control

Store the raw neural outputs for every DEV and LOCKED_TEST utterance.

The deterministic downstream stack must be rerunnable from cached neural output.

This allows:

```text
same parser output
different runtime version
```

without invoking the neural model again.

It also permits exact regression testing.

---

# 26. P3 / BEFORE_BOTH diagnostic

P3 is not a prerequisite for starting integration.

However, before claiming the binder is broadly order-robust, run a frozen diagnostic using the selected POC checkpoint.

Question:

> Does A-005 R20 generalize to the previously untested BEFORE_BOTH geometry?

This diagnostic must remain separate from the core integration acceptance test.

Possible outcomes:

```text
P3 zero-shot strong:
    broader binding primitive than demonstrated by P0/P2

normal strong, BEFORE_BOTH weak:
    independent binding solved;
    order/context geometry remains a separate neural limitation

P3 broad failure:
    P2 solution is narrower than desired
```

Do not modify the frozen POC checkpoint in response during V1 integration.

---

# 27. Implementation architecture

Recommended repository structure:

```text
semvm_end_to_end_poc_v1/
│
├── README.md
├── launch.py
├── pyproject.toml
├── requirements.lock
│
├── config/
│   ├── poc.yaml
│   ├── ontology.yaml
│   └── vm.yaml
│
├── neural/
│   ├── adapter.py
│   ├── checkpoint.py
│   ├── decode.py
│   └── manifest.json
│
├── ir/
│   ├── schema.py
│   ├── canonicalize.py
│   └── validate.py
│
├── resolver/
│   ├── entity.py
│   ├── temporal.py
│   └── discourse.py
│
├── vm/
│   ├── instructions.py
│   ├── compiler.py
│   ├── executor.py
│   └── query.py
│
├── state/
│   ├── schema.sql
│   ├── store.py
│   └── migrations/
│
├── render/
│   └── deterministic.py
│
├── traces/
│
├── scenarios/
│   ├── dev/
│   ├── locked_test/
│   └── schema.json
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden/
│
├── backends/
│   ├── local.py
│   └── modal.py
│
└── results/
```

Exact paths may differ, but subsystem boundaries should remain explicit.

---

# 28. Canonical launcher

Maintain the project-wide backend rule:

```text
python3 launch.py --backend local ...
python3 launch.py --backend modal ...
```

Scientific/semantic behavior must not branch on backend.

Backend-specific code may control only:

```text
resource provisioning
filesystem mounting
GPU selection
job lifecycle
artifact transfer
```

---

# 29. Portability requirements

Apply the previously established SEMVM portability standard.

The POC must be runnable from a fresh Linux environment with:

```text
no original repo dependency
no user-specific absolute paths
no hidden .pth dependency
no undeclared external files
```

Bundle or manifest:

```text
source
environment lock
checkpoint
checkpoint manifest
ontology
scenario sets
database schema
configuration
hash manifest
```

---

# 30. Persistence test

At minimum one registered scenario must:

```text
1. create semantic state;
2. commit;
3. terminate the process;
4. start a fresh process;
5. reopen the same database;
6. query the prior state successfully.
```

This is mandatory.

Without this test, the system demonstrates transient structured parsing rather than persistent semantic state.

---

# 31. Transaction test

At least one scenario must deliberately trigger a post-parse execution failure.

Verify:

```text
state before == state after
```

after rollback.

No partial mutations are allowed.

---

# 32. Determinism requirements

Given:

```text
same frozen neural output
same resolver context
same database state
same reference timestamp
```

the downstream system must produce bit-identical:

```text
canonical IR
resolution
VM program
state diff
query result
response
```

where serialization order is canonicalized.

---

# 33. Neural nondeterminism

If GPU inference itself is not bit-exact across hardware, preserve:

```text
raw score tensors or decoded semantic output
hardware identifier
software versions
```

The semantic decoded output is the contract used for downstream reproducibility.

---

# 34. Audit logging

Every committed utterance must record:

```text
utterance ID
raw text
reference timestamp
neural checkpoint hash
decoded neural output
canonical IR
resolution decisions
VM program
pre-state hash
state diff
post-state hash
response
```

Every failed utterance must record the stage and failure reason.

---

# 35. State hashing

Canonicalize semantic state and compute a hash after every committed transaction.

Example:

```text
STATE_SHA256
```

This supports exact regression and persistence tests.

---

# 36. No hidden neural state

The neural component must be stateless across utterances for V1.

No conversation memory may live in hidden activations.

Every turn receives only the explicit textual input/context defined by the scenario.

Persistent semantic memory lives in the external world model.

---

# 37. Conversation context policy

For V1, distinguish:

```text
LINGUISTIC CONTEXT
```

from:

```text
PERSISTENT WORLD STATE
```

If a bounded amount of previous text is needed for reference resolution, it must be explicit and logged.

Do not silently feed the entire conversation history into the binder.

Preferred design:

```text
current utterance
+ deterministic resolver candidates / explicit local context
```

rather than unrestricted transcript concatenation.

---

# 38. Integration milestone sequence

## M0 — artifact freeze

Freeze:

```text
A-005 R20 checkpoint
union mapping
ontology
model code
```

Output:

```text
BINDER_MANIFEST.json
```

## M1 — IR adapter

Implement:

```text
neural output → canonical IR
```

Pass isolated P0/P2 examples.

## M2 — deterministic runtime

Implement:

```text
IR validator
resolver
SQLite store
VM
renderer
```

with gold-IR unit tests.

Gate:

```text
gold-IR deterministic tests = 100%
```

## M3 — single-turn integration

Run controlled single-turn create/query examples through the frozen binder.

## M4 — multi-turn state

Add:

```text
persistent IDs
updates
queries
references
restart persistence
```

## M5 — DEV scenario suite

Reach DEV acceptance gates.

## M6 — integration freeze

Freeze:

```text
runtime code
scenario LOCKED_TEST
checkpoint
config
```

## M7 — LOCKED_TEST

Run once.

No repair before reporting the locked result.

---

# 39. Unit-test requirements

## 39.1 IR

Test:

```text
type validation
relation signatures
dangling IDs
duplicate IDs
canonical ordering
serialization round-trip
```

## 39.2 Resolver

Test:

```text
new entity
existing entity
alias reuse
ambiguity
time normalization
bounded discourse reference
```

## 39.3 VM

Test:

```text
CREATE
ASSERT
RETRACT
DELETE
GET
FIND
MATCH
transaction rollback
```

## 39.4 Persistence

Test:

```text
commit
restart
reload
query
```

## 39.5 Compiler

For gold resolved IR:

```text
expected VM instruction sequence == actual
```

---

# 40. Neural regression suite

Before integration and after any code change around the neural adapter, rerun a compact fixed regression set containing:

```text
P0 single-binding examples
P2 OO
P2 II
P2 OI
P2 IO
```

The frozen checkpoint's decoded predictions must not change unexpectedly.

This protects against tokenizer/template/indexing integration regressions.

---

# 41. Example POC interaction A — write and query

Turn 1:

```text
Remind me tomorrow to call Alice.
```

Expected semantics:

```text
REMINDER r
CALL c
PERSON Alice
TIME tomorrow

TODO(r,c)
WHO(c,Alice)
WHEN(r,tomorrow)
```

Expected state:

```text
r exists
c exists
Alice persistent entity exists
TODO(r,c)
WHO(c,Alice)
WHEN(r,date)
```

Turn 2:

```text
Who am I supposed to call tomorrow?
```

Expected query result:

```text
Alice
```

---

# 42. Example POC interaction B — update

Turn 1:

```text
Remind me tomorrow to call Alice.
```

Turn 2:

```text
Actually make that Friday.
```

Expected diff:

```text
- WHEN(r,tomorrow)
+ WHEN(r,Friday)
```

Turn 3:

```text
When am I calling Alice?
```

Expected:

```text
Friday
```

---

# 43. Example POC interaction C — independent binding

Use a sentence whose legal gold structure requires at least two different modifier parents.

Required property:

```text
modifier A → outer
modifier B → inner
```

The persisted graph must preserve both attachments.

A later query must distinguish them.

This category directly exercises the A-005 capability in an end-to-end stateful context.

---

# 44. Example POC interaction D — persistent restart

Session 1:

```text
Remind me Friday to call Alice.
```

Commit and terminate.

Session 2:

```text
Who am I supposed to call Friday?
```

Expected:

```text
Alice
```

No neural memory from Session 1 exists.

The answer must come from persistent external state.

---

# 45. Example POC interaction E — ambiguity safety

Create:

```text
Alice Smith
Alice Jones
```

Then request a supported ambiguous reference to:

```text
Alice
```

Expected:

```text
RESOLUTION_AMBIGUOUS
```

No arbitrary identity selection.

No state mutation.

---

# 46. POC success definition

The POC is successful if:

1. the frozen neural core can drive the canonical semantic interface;
2. multiple independent relation bindings survive integration;
3. deterministic downstream components pass gold-IR tests perfectly;
4. persistent state survives process restart;
5. updates modify exactly the intended semantic facts;
6. later queries are answered from external state rather than neural recall;
7. failures are localized and auditable;
8. DEV reaches the registered acceptance gates;
9. LOCKED_TEST demonstrates substantial end-to-end scenario success.

The POC does not require perfect neural parsing.

It does require exact deterministic behavior given correct semantics.

---

# 47. Interpretation map

## RESULT A — full architectural POC succeeds

If:

```text
gold-IR runtime = perfect
FULL end-to-end scenario exact is high
binding remains strong
persistent multi-turn queries/updates work
```

then:

> The core Semantic VM architecture is operational as an end-to-end proof of concept.

This supports the design principle that neural language understanding can be separated from deterministic persistent semantic computation.

## RESULT B — neural bottleneck

If:

```text
gold-IR runtime = perfect
FULL failures primarily N_PARSE/N_BIND
```

then:

> The systems architecture is coherent, but the frozen neural front end remains the dominant limitation.

## RESULT C — resolution bottleneck

If neural IR is mostly correct but:

```text
entity/time/reference resolution fails
```

then:

> Binding is no longer the limiting subsystem; contextual resolution is the next research target.

## RESULT D — runtime bottleneck

If gold IR does not produce exact state/query behavior:

> The deterministic Semantic VM implementation is incomplete or incorrect.

Fix runtime engineering before making neural conclusions.

## RESULT E — integration distribution shift

If the frozen binder loses capabilities specifically because the integrated input representation changes:

> The neural component is functional in isolation but the integration contract perturbs its tested regime.

Localize the interface difference before any retraining.

---

# 48. Claims explicitly NOT permitted from V1 alone

Even a successful POC does not establish:

```text
unrestricted natural-language understanding
human-level semantic parsing
arbitrary compositional generalization
seed-stable training
universal systematicity
open-domain world modeling
general autonomous agency
```

It establishes an architectural existence proof in a bounded controlled domain.

---

# 49. Parallel research tracks after POC start

Integration should not block continued research on training stability.

Maintain separate tracks:

```text
TRACK A — SYSTEM INTEGRATION
    frozen A-005 R20
    build end-to-end Semantic VM
    locate next architectural bottleneck

TRACK B — TRAINING RELIABILITY
    seed stability
    why successful basins emerge
    P0/P2 replay replication
    optimization dynamics

TRACK C — STRUCTURAL GENERALIZATION
    P3 BEFORE_BOTH
    future systematic recombination evaluations
```

No track should silently modify another track's frozen artifacts.

---

# 50. Blinded systematic sets

Do not inspect or use existing V1/V1.1:

```text
RECOMB
SURFACE_RECOMB
DOUBLE_RECOMB
```

for POC development.

The POC should use its own DEV scenarios and separately frozen LOCKED_TEST scenarios.

The older withheld systematic sets retain their independent scientific value.

---

# 51. Cost policy

Prefer local execution for deterministic runtime development.

Use Modal only where:

```text
GPU neural evaluation materially accelerates work
```

The frozen binder requires inference only, so most POC development should be inexpensive.

Record any Modal cost in the artifact manifest.

---

# 52. Security / safety of execution

The V1 VM must not execute arbitrary shell commands or arbitrary Python.

VM instructions operate only on the registered semantic state API.

No natural-language input may compile into unrestricted code execution.

External actions are out of scope for V1.

---

# 53. Reproducibility manifest

Final bundle must include:

```text
SEMVM_END_TO_END_POC_V1.md
BINDER_MANIFEST.json
ONTOLOGY.json/yaml
IR_SCHEMA.json
VM_SPEC.md
SCENARIO_SCHEMA.json
DEV scenario manifest
LOCKED_TEST manifest
environment lock
source manifest
artifact hashes
results report
```

---

# 54. Final report requirements

Produce:

```text
SEMVM_END_TO_END_POC_V1_REPORT.md
SEMVM_END_TO_END_POC_V1_RESULTS.json
SEMVM_END_TO_END_POC_V1_ARTIFACT_MANIFEST.json
```

The report must include:

```text
1. frozen neural component provenance
2. implemented architecture
3. IR schema
4. resolver rules
5. persistent state schema
6. VM instruction set
7. unit-test results
8. gold-IR control
9. DEV results
10. LOCKED_TEST results
11. failure taxonomy counts
12. binding-specific results
13. persistence/restart results
14. example execution traces
15. backend/cost
16. deviations from spec
17. final interpretation
```

---

# 55. Stop conditions

Stop and review if any of the following occurs:

```text
S1
frozen neural checkpoint cannot be integrated without changing weights

S2
canonical IR cannot represent a legal P0/P2 semantic structure

S3
gold-IR deterministic runtime cannot reach exact behavior

S4
integration requires unrestricted generative reasoning inside the VM

S5
persistent identity cannot be separated from neural hidden state

S6
DEV acceptance gates fail after ordinary implementation debugging

S7
LOCKED_TEST has been accidentally exposed during development
```

Do not respond to a stop by silently expanding scope.

---

# 56. Initial implementation order

Implement in this exact order unless a concrete engineering dependency requires otherwise:

```text
1. Freeze A-005 R20 binder artifact.

2. Define canonical IR schema.

3. Build neural-output → IR adapter.

4. Build gold-IR test fixtures.

5. Build SQLite world model.

6. Build deterministic entity/time resolver.

7. Build VM instruction representation.

8. Build IR → VM compiler.

9. Build VM executor and transaction layer.

10. Make gold-IR end-to-end tests perfect.

11. Add deterministic response renderer.

12. Connect frozen neural binder.

13. Build DEV scenario suite.

14. Debug against DEV traces.

15. Freeze integration implementation.

16. Run LOCKED_TEST once.

17. Produce final report.
```

---

# 57. Primary research question

The final POC should answer:

> Can a small frozen neural semantic core, trained to produce reusable compositional bindings, be integrated with explicit persistent state and deterministic execution to form a functioning stateful semantic computer?

---

# 58. Secondary questions

The POC should also localize:

```text
1. Does the A-005 independent-binding capability survive ordinary systems integration?

2. Once parent binding is available, what becomes the next dominant failure mode?

3. How much of multi-turn language behavior can be handled by explicit state and deterministic resolution rather than neural memory?

4. Can later queries be answered entirely from canonical persistent state?

5. Can semantic updates be exact and auditable?

6. Does the architecture remain understandable enough that each failure can be assigned to a subsystem?
```

---

# 59. Expected contribution of V1

A successful V1 would not merely show that a parser can achieve good held-out accuracy.

It would demonstrate a functioning architecture in which:

```text
language
    ↓
small learned semantic interface
    ↓
canonical meaning
    ↓
persistent machine state
    ↓
exact execution
```

operates across multiple turns.

That is the intended proof of concept for the broader Stateful Semantic VM program.

---

# 60. Registration note

This document defines the initial integration target.

Before implementation begins, freeze:

```text
document hash
binder checkpoint hash
ontology hash
initial acceptance gates
```

Any substantive changes to:

```text
neural checkpoint
ontology
canonical IR semantics
acceptance gates
LOCKED_TEST contents
```

must be recorded as an amendment before the affected result is inspected.

Engineering bug fixes that preserve registered semantics may proceed on DEV and must be logged.

---

# END
