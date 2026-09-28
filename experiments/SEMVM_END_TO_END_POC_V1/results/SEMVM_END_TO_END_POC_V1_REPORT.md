# SEMVM_END_TO_END_POC_V1: report

**Date:** 2026-09-26.
**Specs:** `spec/SEMVM_END_TO_END_POC_V1.md` and **Amendment 001**, `spec/SEMVM_END_TO_END_POC_V1_AMENDMENT_001.md` (input-language boundary, registered before implementation).
**Numbers:** `results/SEMVM_END_TO_END_POC_V1_RESULTS.json`.

**Verdict: RESULT A (full architectural POC succeeds), within the registered controlled-language regime.**
- **LOCKED_TEST (run once): 20/20 scenarios exact**, and every metric is 1.0.
- **DEV: 29/30.** The single failure is one neural parent-binding error.
- **GOLD_IR is 1.0 on both suites.**

The claim is bounded (§17): a frozen small neural binder translates its trained controlled compositional language into canonical semantic state, including multiple independent relation bindings, and that state participates in persistent deterministic computation across turns. **V1 does not claim English understanding** (see RESULT-E).

## 1. Frozen neural component
- **Checkpoint:** SEMVM_BINDER_POC_V1 = A-005 R20, seed 17, epoch 40 (sha `3f23d13c…`, `neural/BINDER_MANIFEST.json`).
  - Validated P2 ID_VAL: exact .9775, mixed both-correct .97, same .995.
  - Validated P0 ID_VAL: exact .9825, pair consistency .965.
- **Frozen throughout:** `requires_grad` False, no optimizer, eval mode. The state hash is identical before and after every inference session (`NEURAL_PASS.json`: frozen_ok = true on DEV, LOCKED_TEST and the Modal run).
- **Gold-free inference (`neural/binder.py`).** It reproduces `mr_forest.process` minus the gold fields. Each input uses the inventory the binder was trained with for its modifier count: 1 modifier → P0 inventory, 2 → P2 inventory, with union template indices.
- **Neural regression (§40):** on 400 P0 + 400 P2 ID_VAL items, the POC path reproduces the A-005 evaluation path's decisions **800/800** (P0 .9825 / P2 .9775). A union-inventory-for-everything policy is also 800/800 (a diagnostic only).

## 2. Implemented architecture
```
CONTROLLED ASSERTION ─► envelope check ─► frozen binder ─► graph ─► canonical IR ─► validate ─► resolve ─► compile ─► VM (SQLite txn) ─► render
COMMAND (SEMVM_CMD_V1) ─► deterministic parser ─────────────────────────────────────► resolve refs ─► compile ─► VM ─► render
```
| module | role |
|---|---|
| `neural/` | binder, envelope, frozen artifacts |
| `ir/ir.py` | IR |
| `resolver/resolver.py` | resolution |
| `state/store.py` | SQLite world model |
| `vm/vm.py` | command parser, compiler, executor, query |
| `render/render.py` | response rendering |
| `pipeline.py` | trace and audit |
| `evaluate.py` + `run_segment.py` | evaluation |
| `scenarios/` | generator and independent oracle |

The neural core only builds semantic structure. Identity, persistence, state changes, queries and bookkeeping are all deterministic and external.

## 3. IR schema
See `spec/IR_SCHEMA.json`.
- **Objects:** e0 = OUTER event, e1 = INNER event, and v\* = values (PERSON, TIME, PLACE, TOPIC_VALUE) sorted by (type, surface).
- **Relations:** TODO / WHO / WHEN / WHERE / RECIPIENT / TOPIC with typed signatures.
- **Validation (§6)** checks: types, signatures, the frozen constructor matrix, dangling or duplicate ids, exactly one TODO, each value attached exactly once, and at most one value per (event, relation).

## 4. Resolver rules
- **Persons:** by exact alias. 0 matches → new; 1 → reuse; ≥ 2 → `RESOLUTION_AMBIGUOUS`, with no mutation and never an arbitrary pick.
- **TIME:** clock / named values normalized (digits → `HH:MM`; noon / midnight / dawn / dusk → NAMED). V1 has no relative dates (Amendment 001).
- **PLACE / TOPIC:** lowercase natural keys.
- **Events in assertions:** always new.
- **References:** `LAST_<TYPE>` = the most recently created active event of that type. None → `RESOLVE_REFERENCE`.

## 5. Persistent state
SQLite (`state/store.py`) with the tables objects, relations, aliases, scalar_values, utterances, transactions, counters and audit.
- **Ids:** persistent ids `<type>:<6-digit counter>` never change; scalars use natural keys.
- **Timestamps:** logical (reference time + turn).
- **State hash:** canonical state + STATE_SHA256 after every turn.

## 6. VM instruction set
See `spec/VM_SPEC.md`: CREATE, ADD_ALIAS, ENSURE_VALUE, ASSERT, RETRACT, DELETE, MATCH, RETURN.
- **One SQLite transaction per utterance,** with postconditions (legal signatures under the frozen matrix, live endpoints, functional relations) and rollback on any failure.
- **Nothing executes code.**

## 7. Unit tests (§39)
**17/17 PASS** (`results/UNIT_TESTS.json`). They cover:
- IR types, signatures, dangling, duplicate, canonical order and round-trip;
- resolver new / existing / alias reuse / ambiguity / time / reference;
- the exact expected compiler program;
- CREATE, ASSERT, QUERY (SELF / PARENT / CHILD scopes), UPDATE, RETRACT and DELETE;
- rollback, both via postcondition and injected;
- command syntax;
- restart persistence (a new process);
- bit-identical determinism.

## 8. Gold-IR control (§24)
**GOLD_IR scenario exact = 1.00** on DEV (30/30) and LOCKED_TEST (20/20). The expected outcomes come from an **independent oracle** (`scenarios/oracle.py`, which imports no runtime module), so this checks the runtime rather than restating it.

## 9. DEV results (30 scenarios, 40 new assertions, 93 commands)
| metric | value | gate |
|---|---|---|
| IR_EXACT | .975 (39/40) | ≥ .95 ✓ |
| PARENT_ACC | .985 (64/65): single 1.0 (15), same 1.0 (10), **mixed .975 (39/40)** | ≥ .97 ✓ |
| ENTITY / TIME / REFERENCE resolution | 1.0 (26) / 1.0 (17) / 1.0 (13) | — |
| VM_PROGRAM_EXACT | 1.0 (126) | = 1.00 ✓ |
| STATE_EXACT | .962 (128/133 turns) | ≥ .95 ✓ |
| QUERY_RESULT_EXACT | .975 (77/79) | ≥ .95 ✓ |
| RENDER_EXACT / RESPONSE_EXACT | 1.0 / .985 | — |
| **SCENARIO_EXACT** | **.967 (29/30)** | ≥ .90 ✓ |

- **All DEV gates pass.** Replaying from the frozen-parser cache is bit-identical (§32).
- **Two logged DEV engineering fixes** (`results/DEV_ENGINEERING_LOG.md`), neither changing registered semantics or gates:
  - a compiler bug (duplicate new person in one UPDATE), fixed before any scenario existed;
  - RENDER_EXACT redefined to measure render correctness, plus a new RESPONSE_EXACT.

## 10. LOCKED_TEST results (20 scenarios, 27 new assertions, 62 commands; generated and hash-frozen before any DEV run; run exactly once after the integration freeze)
| metric | value |
|---|---|
| IR_EXACT | **1.0** (27/27) |
| PARENT_ACC | **1.0** (45/45): single 9, same 4, **mixed 32/32** |
| ENTITY / TIME / REFERENCE | 1.0 (20) / 1.0 (9) / 1.0 (9) |
| VM_PROGRAM_EXACT / STATE_EXACT / QUERY_RESULT_EXACT | 1.0 (88) / 1.0 (89) / 1.0 (53) |
| RENDER / RESPONSE | 1.0 / 1.0 |
| **SCENARIO_EXACT** | **1.0 (20/20)**; GOLD_IR 1.0 |

The sample is small (27 assertions). A perfect LOCKED_TEST is consistent with a binder that is about 97–98% exact per assertion; it does not show one that never errs.

## 11. Failure taxonomy
| suite | failures | taxonomy |
|---|---|---|
| DEV | 1 | **N_BIND 1** |
| LOCKED_TEST | 0 | — |

There are no runtime, resolution, compile, store, query or render failures.

## 12. Binding-specific results
Mixed-parent (OI / IO) bindings were deliberately over-represented: 20 of 40 DEV assertions and 16 of 27 LOCKED assertions.
- **Accuracy:** mixed-parent PARENT_ACC is .975 on DEV and 1.0 on LOCKED.
- **Where the query answers depend on it:** the S3 / S4 / S5 / S9 scenarios, including PARENT / CHILD-scoped queries such as `QUERY WHO OF CALL WHERE PARENT.WHEN=3`. Correct mixed attachment determines the answers there.
- **The one DEV error** is `note delta ; at 5 per delta : next and then so ; message eta : while in Seoul per eta`. `at 5 per delta` was attached to MESSAGE instead of NOTE, so both modifiers were given the same parent. That is the pre-A-004 failure mode, with a tiny margin (0.04).

## 13. Persistence / restart (§30) and transactions (§31)
- **Restart:** every S12 scenario (2 DEV + 2 LOCKED) runs in three separate OS processes (logged pids) against one SQLite file. Queries after each restart return the prior state, and an update made after a restart persists across the next one. All are exact.
- **Rollback:** the ROLLBACK scenario runs `UPDATE LAST_VISIT WHO=<p> RECIPIENT=<p>`. The WHO retract and assert execute, then RECIPIENT on VISIT violates the frozen matrix at postcondition. The result is `VM_EXEC_ERROR`, the state hash is unchanged, and the later query returns the original WHO. The unit tests add an injected mid-program failure.
- **Ambiguity (S10):** two `NEW PERSON X` commands followed by an assertion mentioning X → `RESOLUTION_AMBIGUOUS` with no mutation, while a later assertion about a different person succeeds.

## 14. Example trace (`results/example_traces/`, DEV S5)
```
INPUT     remind beta : while in Rome re gamma ; so then again soon , email gamma ; to Kevin re beta
          (gloss: reminder for Kevin; the email happens in Rome. Mixed IO binding: WHERE→EMAIL, RECIPIENT→REMINDER)
IR        TODO(e0,e1) RECIPIENT(e0=REMINDER, Kevin) WHERE(e1=EMAIL, Rome)
RESOLVE   e0,e1 NEW; Kevin NEW; Rome → place:rome
PROGRAM   CREATE REMINDER $e0; CREATE EMAIL $e1; CREATE PERSON $v0; ADD_ALIAS $v0 Kevin; ENSURE_VALUE place:rome;
          ASSERT $e0 RECIPIENT $v0; ASSERT $e0 TODO $e1; ASSERT $e1 WHERE place:rome
DIFF      +reminder:000001 +email:000001 +person:000001(Kevin) +RECIPIENT +TODO +WHERE          RESPONSE  OK.
INPUT     QUERY WHERE OF EMAIL WHERE PARENT.RECIPIENT=Kevin
PROGRAM   MATCH {target EMAIL, rel WHERE, where [PARENT RECIPIENT person:000001]}; RETURN      RESPONSE  Rome
```
Full traces for every turn, including neural output, IR, resolution, program, state before / after hashes, diff, return and response, are in `traces/`. An audit row per utterance is stored in each scenario database.

## 15. Backend / cost
- **Local:** all development, DEV and LOCKED_TEST ran on CPU; the binder needs inference only.
- **Canonical launcher:** `launch.py --backend local|modal` over the project's execution backend (`backends/`), with a single entry point `run_job.py`.
- **Backend equivalence (DEV only, since LOCKED_TEST runs once):** the Modal CPU job (cpu-small, a fresh image built from `environment/requirements-lock.txt`) produces **identical decoded neural outputs, identical FULL and GOLD_IR traces (60/60) and identical metrics** to the local job. Raw scores differ by at most 2.4e-4 across machines, which §33 allows since the decoded output is the contract.
- **Modal cost:** **$0.0011** (25 s of CPU container time).
- **Relocation:** a copy of the tree outside the repository passes 17/17 unit tests and reproduces DEV.
- **Source-experiment references:** only the scenario generator (the new-surface check against the training corpora) and the source-comparison regression reference the source experiment. Both are provenance tools, not runtime dependencies.

## 16. Deviations from the spec
1. **Amendment 001 (the user's ruling):**
   - assertions use the binder's controlled language, tags included;
   - queries, updates and references use the deterministic SEMVM_CMD_V1;
   - the English examples are glosses only;
   - no English rewriter;
   - V1 has no relative dates (TIME values are clock / named values).
2. **§19 S5** is realized as TODO + 2 modifiers (3 relations over 2 events). Four modifiers in one assertion are outside the envelope, so that version is UNSUPPORTED.
3. **§26 P3 / BEFORE_BOTH diagnostic:** not run. It is optional, and no order-robustness claim is made; BEFORE_BOTH inputs are `UNSUPPORTED_INPUT` by the envelope.
4. **The portability bwrap / file-audit acceptance harness from earlier experiments was not re-run.** Portability is supported instead by the fresh-image Modal run and the relocated copy.
6. **Post-run documentation correction.** The literal examples in Amendment 001 originally used WHEN on REMINDER, which is a V1 withheld cell outside the envelope. They were replaced with envelope-checked examples (`results/DEV_ENGINEERING_LOG.md` item 3). No scenario or result was affected.
7. **Added after the run:** an interactive shell, `repl.py`. It is a usage convenience only and was not part of the evaluation.
5. **The neural envelope check** (layout skeleton, vocabulary, supported triples) is a deterministic pre-filter. It never reads which event a tag names. Its checks were validated on the corpora: every P0 / P2 item is accepted and every BEFORE_BOTH item is rejected.

## 17. Final interpretation
- **RESULT A holds inside the registered regime.**
  - The deterministic runtime is exact given correct semantics (GOLD_IR 1.0, VM programs 1.0).
  - Persistent identity, updates, retraction, deletion, restart and rollback all behave exactly.
  - The frozen binder's independent multi-modifier binding survives integration (mixed-parent .975 / 1.0), and it drives state that later queries read back only from the external world model.
  - Every observed failure is localized and auditable: one N_BIND.
- **On the secondary questions:**
  1. The A-005 binding capability survives systems integration.
  2. The next dominant limitation is the **input-language boundary**. The binder is not an English parser (RESULT-E: 0/8 exact; 8/8 rejected by the pipeline). The tag-coindexed language is doing work that English does not provide.
  3. All multi-turn behaviour here (references, updates, queries) was handled by explicit state and deterministic resolution, with no neural memory.
  4. Queries are answered entirely from canonical persistent state.
  5. Updates are exact and auditable (transaction diffs, state hashes, audit rows).
  6. Every failure was assignable to a subsystem.

**Stopped** after the report. Nothing was fine-tuned, and no V1 / V1.1 systematic set was touched.
