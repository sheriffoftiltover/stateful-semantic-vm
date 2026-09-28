# Audit of the checks that decide gates

- **Date:** 2026-09-28.
- **Type:** read-only audit of the released code and records. No run was repeated and no code was changed.

**Motivation.** The LOCKED teardown race (paper §6) was a verification helper with the same defect the paper identifies at the semantic layer. The helper accepted evidence that was consistent with "the teacher is gone" (an HTTP error) without being complete evidence of it (HTTP 404). This audit asks, for every helper that decides a registered gate or a claim, two questions:
- what does it accept as "pass"?
- did any released run actually pass through a permissive path?

**Sources.** Every entry cites the code in `experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1/` (the final system; earlier experiments share these files) or in the named experiment. The "realized?" column is computed from the released result JSONs.

| # | Check (code) | Decides | Accepts as pass | Classification | Realized in released runs? |
|---|---|---|---|---|---|
| 1 | PDX teardown (`SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1/pdx_evaluate.py`) | `teacher_destroyed` → disconnect / distilled metrics | `modal app stop` rc 0 **and** endpoint ≠ `REACHABLE`. This includes **any** HTTP error, any exception, and **no probe at all** if the URL file is unset | **Permissive** | No. Every PDX handoff record reads HTTP 404 |
| 2 | HTG/TTP/RCI teardown, as run (`htg_evaluate.teardown`) | HOSTED_TEARDOWN_VERIFIED | rc 0 and any HTTP error | **Permissive** | **Yes, once: RCI LOCKED (HTTP 401).** All other handoffs (HTG, TTP attempts 1–2, RCI DEV-A/B) got 404 |
| 3 | Same helper, post-RCI fix (released `htg_evaluate.py`; not used by any RCI run) | same | 404, or a *non-HTTP* exception (connection refused, timeout, DNS failure), after polling up to 18×10 s | **Residual permissive**: a network failure on the prober's side would count as "destroyed" | Not used |
| 4 | Teardown app name (RCI Stage 0C) | same | rc of stopping the named app | Correct: the wrong app name gave rc 1 → **not destroyed**, and the run was repaired | Stage 0C only (acquisition-only) |
| 5 | HOSTED_CALLS_POST_HANDOFF (`htg_evaluate.py` l.304, `pdx_evaluate.py` l.212) | = 0 gate | Count of connection attempts blocked by the network guard | **Not independent.** It is the same number as NETWORK_ATTEMPTS_POST_HANDOFF; no server-side log of hosted calls exists | Both 0 everywhere; they are one measurement, not two |
| 6 | Network guard (`netguard/sitecustomize.py`) | NETWORK_ATTEMPTS; the "clean" audit | Python-level patch of `socket.socket.connect` and `socket.create_connection` in reuse processes; loopback allowed | **Instrumentation, not isolation.** It does not cover `connect_ex`, native-code sockets, subprocesses that do not load the patch, or DNS lookups | 0 logged attempts. Absence of attempts on unpatched channels is not proven by it. (For LOCKED, the endpoint was also later confirmed 404) |
| 7 | Reuse-process "clean" audit (`htg_evaluate.py` l.281, `pdx_evaluate.py` l.213) | Disconnect / distilled metrics | `all(...)` over per-process audits: guard active, no `TEACHER_URL` / `TEACHER_API_KEY` / `GROQ_API_KEY` in the environment, no teaching dir, no teacher modules loaded (`client`, `episode`, `protocol`) | **Vacuous on empty input** (`all([])` is True). The environment and module checks are name-based; Modal credentials in a config file are not checked | No: every scenario of every RCI arm and suite has non-empty audits, all clean |
| 8 | STUDENT_NEURAL_HASH_INVARIANT (`pdx_evaluate.py` l.211) | = 1 gate | The set {reuse-process hashes} ∪ {pre-acquisition hash} has one element | **Vacuous if no reuse hashes were recorded.** It checks invariance, not equality to a pinned value | No: every scenario has hashes, and exactly one distinct hash (`9b3db05b…`) occurs across all RCI suites and arms |
| 9 | Behavioral oracle (`scenarios/oracle.py`, `evaluator/behavior.py`) | Grounding / trace exactness, scenario-exact | Re-implements world and op semantics independently, but **shares `procedure/lang.py`** with the runtime for parsing reference text and `program_hash` | **Shared code.** A parsing or canonicalization defect would affect runtime and oracle alike; learned-exact uses the same hash | Not observable from records; controls (GOLD_TRACE, FORMAL_TEACH) are exact, which is consistent with but does not prove correctness |
| 10 | Demonstration completeness (`teacher/transactional.py` `completeness`) | Commit precondition; DEMONSTRATION_COMPLETENESS_EXACT | Every *lesson* slot resolved, none pending, RETURN present, trace non-empty | **Complete relative to the lesson, not to the goal.** A lesson that omits a step passes | By design. Caught downstream only by learned-exact vs the reference and by the (evaluator-only) judge |
| 11 | Evidence verifier (`procedure/verify.py`) | VERIFIED → activation | Every test passes against the committed evidence | **Evidence-only by design.** Consistent-but-wrong evidence verifies (the HTG wrong activations) | Documented in the paper; registered false-accept probes are rejected in every run |
| 12 | Judge parse failures (`evaluator/judge.py`) | Faithfulness metrics (reporting only) | Parse failure → `faithful: None`, counted as not faithful | Conservative | — |
| 13 | LEARNED_PROCEDURE_EXACT | Primary gate | Hash identity with the reference program | **Conservative** (false failures, never false passes) | — |

## Findings

1. **The teardown class of defect occurred in two helpers, not one.**
   - PDX's rule (#1) was even more permissive than the HTG helper (#2): it would have passed with no probe at all.
   - It passed through a permissive path only once in the released runs: RCI LOCKED.
   - The post-fix helper (#3) still counts prober-side network failure as teardown. A strict version should require an affirmative 404 from the hosting provider, or a provider API state of `stopped`, not the absence of a response.
2. **"0 hosted calls" and "0 network attempts" are one measurement.** Both come from the in-process network guard. The paper should present them as a single audited quantity, and should describe the guard as instrumentation rather than isolation.
3. **Two aggregate checks pass vacuously on empty input** (#7, #8). Neither was ever empty in the released runs. The checks should nonetheless fail on missing records rather than pass.
4. **The oracle is independent in execution semantics but shares parsing and hashing code with the runtime** (#9).
5. **Completeness is relative to the lesson** (#10). This is the same "consistent ≠ complete" limit at the protocol level: the controller can guarantee that it executed everything the teacher said, not that the teacher said everything the goal requires.

**Effect on the reported results:**
- None of these findings changes a released number.
- Findings 2–4 qualify how the disconnection and correctness evidence should be described.
- Findings 1 and 3 motivate treating verification code as an object of verification in its own right: with its own negative tests, e.g. a teardown probe fed 401/403/5xx/timeout must fail.
