# Architecture

This page describes the final configuration, used by `SEMVM_RECOVERY_CAPACITY_ISOLATION_V1` (RCI). Figure 1 of the paper shows the same design. The organizing rule is **neural components propose; deterministic components decide.**

## Components and authority

| Component | Implementation (RCI directory) | May | May not |
|---|---|---|---|
| Hosted teacher | gpt-oss-120b, reasoning high, T=0, `max_tokens` 8192 (`teacher/protocol.py`, `teacher/routing.py`) | Write `EXAMPLE:` / `STEP:` lines; answer structured questions | Execute; see world state; write the library; survive handoff |
| Hosted grounder | Same checkpoint, reasoning low, separate role and cache (`student/hosted_grounder.py`) | Map ONE lesson line (plus the live result list) to a typed JSON plan | Pick among ambiguous referents; emit an unlicensed terminal action; execute |
| Teaching controller | `teacher/transactional.py` (state machine `spec/TEACHING_STATE_MACHINE_V1.json`, slot schema `spec/DEMONSTRATION_SLOT_SCHEMA_V1.json`) | Order slots, ask questions, COMMIT or ABORT a demonstration | Admit an incomplete or aborted demonstration as evidence |
| Plan checks + VM | `student/`, `core/vm`, `procedure/executor.py`; one SQLite transaction with rollback | Validate ops, types and references; execute in the sandbox | Run arbitrary code |
| Anti-unifier | `procedure/abstraction.py` | Propose candidate programs from committed traces | Use uncommitted material or gold |
| Evidence verifier | `procedure/verify.py` (stages 0–6) | Mark a candidate VERIFIED or REJECTED_* | Consult gold or the teacher |
| Procedure library | `procedure/procstore.py` → `procedures.sqlite` | Store versions, lifecycle, provenance, tests, `active_pointer` | Activate without VERIFIED plus an explicit accept |
| Frozen student LM | Qwen2.5-Coder-1.5B (`procedure/llm_service.py`, `procedure/retrieval.py`) | Rank ACTIVE procedure names (margin 1.0 nats); write argument text | Bypass argument, type and vocabulary checks; create or modify procedures |
| Judge | gpt-oss-120b, evaluator only | Label lesson faithfulness for reporting | Affect any system decision |

## Domain

A personal organizer:
- **Events:** REMINDER, REQUEST, PLAN and NOTE, each optionally about a CALL, EMAIL, VISIT or MESSAGE.
- **Relations:** WHO, RECIPIENT, WHEN, WHERE and TOPIC.
- **Status:** open or closed.

The VM executes 21 frozen typed primitives (`SEMVM_PROCEDURE_DISCOVERY_POC_V1/spec/PROCEDURE_PRIMITIVES_V1.json`):

FIND, FIND_LAST, GET, CHILD, PARENT, FIRST, COUNT, FILTER, SELECT, SORT, GROUP, REPORT, UPDATE, RETRACT, SET_STATUS, DELETE, FOR, IF, PRECONDITION, CALL, RETURN.

## A demonstration is a transaction

States:

NEW → OPEN → (WAITING_FOR_EXAMPLE) → WAITING_FOR_GROUNDING ⇄ WAITING_FOR_CLARIFICATION / WAITING_FOR_REPHRASE → READY_TO_COMMIT → COMMITTED

Any state can go to ABORTED. An abort restores the sandbox to the demonstration's start snapshot, and the demonstration contributes **zero evidence**.

Registered rules:
- An EXAMPLE line must come before execution.
- RETURN is licensed only on the last slot.
- Saved skills are called only by name, with explicit inputs.
- A structured `REFERENT: <id>` question is asked whenever more than one live result fits.
- PARENT.WHEN legality feedback is given.
- Injected lines are never attributed to the teacher.
- A demonstration commits only if the completeness check finds no unexecuted slot.
- Two demonstrations are required unless the parameters are declared; the count uses *committed* demonstrations (TTP Amendment 003).

## Procedure lifecycle

CANDIDATE → TESTING → VERIFIED → (explicit accept) → ACTIVE, or REJECTED_*.

Every transition is logged in `lib_log`. Rejected versions are kept but can never be executed.

The verifier battery:
1. static validation
2. interface
3. source replay
4. counterfactual argument substitution, against the *unabstracted* trace
5. state perturbation (e.g. all-closed, alternate-closed)
6. negative cases (missing input, wrong type, empty result, ambiguous entity, deleted object, empty world)
7. rollback injection after each state-changing step
8. determinism

## Handoff

1. `modal app stop --yes`.
2. Probe the endpoint. The registered requirement is **HTTP 404 / unavailable**.
3. Remove teaching transcripts and context.
4. Scrub teacher credentials from the environment.
5. Start fresh processes under a network guard (`netguard/`) that patches Python's `socket.connect` / `create_connection` to block and log non-loopback connections. This is instrumentation, not isolation; see [verification_audit.md](verification_audit.md).
6. Assert the student weight hash in every process.

The helper used by all runs up to and including RCI's LOCKED accepted *any* HTTP error. It now polls until a real 404; this post-run change was not used by any RCI run. See the paper, §6.
