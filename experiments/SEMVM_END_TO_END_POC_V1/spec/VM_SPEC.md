# SEMVM POC V1: VM specification (as implemented in `vm/vm.py`)

**Instructions.** Tuples. `$<name>` registers bind objects created earlier in the same program.

| instruction | effect |
|---|---|
| `CREATE(type, reg)` | new object with id `<type>:<6-digit per-type counter>`, status active |
| `ADD_ALIAS(ref, alias)` | alias row (normalized = lowercase) |
| `ENSURE_VALUE(id, type, normalized, surface)` | scalar with natural key `<type>:<normalized>` (idempotent) |
| `ASSERT(s, p, o)` | active relation |
| `RETRACT(s, p, o)` | deactivates exactly one active relation, else `VM_EXEC_ERROR` |
| `DELETE(id)` | status deleted, and every active relation touching it is deactivated |
| `MATCH(pattern)` | read-only query: `{target: type or id, rel, where: [[SCOPE, REL, value_id]]}` with SCOPE ∈ SELF / PARENT (via TODO) / CHILD (via TODO) |
| `RETURN(kind)` | returns the MATCH result |

**Execution.** One SQLite transaction per utterance: `BEGIN → instructions → postconditions → COMMIT`. Any exception leads to `ROLLBACK`, with no partial mutation. The postconditions are:
- every active relation has an active subject;
- TODO is outer → inner;
- relations are legal under the frozen validity matrix;
- PERSON relations point at an active PERSON;
- scalar relations point at a scalar of the right type;
- there are no duplicate relations;
- each (event, relation) has at most one value.

**Compilation.** Deterministic, never neural.
- **Assertion:** CREATE the events (e0, e1), then new persons (with an alias) and ENSURE_VALUE for scalars in canonical order, then ASSERT the relations in canonical order.
- **UPDATE:** per assignment, RETRACT the active (ref, rel, \*) values (read at compile time), then ASSERT the new one.
- **RETRACT / DELETE:** explicit.
- **QUERY:** MATCH + RETURN.

**Safety.** No instruction can execute code, a shell, or anything outside the semantic-state API. Natural-language input never compiles to anything else.
