# SEMVM_PROCEDURE_DISCOVERY_POC_V1: report

**Date:** 2026-09-26.
**Specs:** `spec/SEMVM_PROCEDURE_DISCOVERY_POC_V1.md` and `spec/…AMENDMENT_001.md` (LLM role and domain, per the user's rulings).
**Changes:** `results/ENGINEERING_LOG.md`.
**Numbers:** `results/PROCEDURE_LOCKED_TEST.json` and `results/PROCEDURE_DEV.json`.

**Verdict: RESULT A (persistent procedural learning succeeds), within the registered domain.**
- **LOCKED_TEST_v2, run once after the integration freeze: 20/20 scenarios exact.** Every registered gate is at 1.0.
- **GOLD_PROC control:** 1.0 on DEV and on LOCKED.
- **No neural weight changed:** 0 optimizer steps. The frozen LLM's parameter hash is identical across all 20+ service restarts.

**Claim boundary.** The system acquires *executable procedural knowledge externally* and reuses it after restart, on new arguments and new wording. It does not learn neural weights, invent primitives, synthesize unrestricted code, or understand open English.

## 1. The system
```
teach (step language) ─► trace (+ start snapshot) ─► proposals: deterministic anti-unification ‖ frozen Qwen2.5-Coder-1.5B
      ─► static validation ─► verification against the EVIDENCE (replay, counterfactual, state perturbation, negative cases,
         injected rollback after every op, determinism) ─► VERIFIED ─► explicit :accept ─► ACTIVE in procedures.sqlite
REQUEST (controlled paraphrase) ─► alias rule / LLM ranking ─► LLM argument text ─► deterministic repair + checks
      ─► typed fallback + type-directed composition search ─► equivalent-plan collapse + stored-procedure preference ─► ONE transaction
```
- **Two persistent stores:** the world (SQLite) and the procedure library (`procedures.sqlite`: versions, lifecycle, aliases, provenance, tests).
- **Frozen primitive inventory:** `spec/PROCEDURE_PRIMITIVES_V1.json`, 21 ops. The effects are PURE or STATEFUL; nothing EXTERNAL exists.
- **Canonical AST:** `spec/PROCEDURE_SCHEMA.json`, with identity by `program_hash`.
- **Domain:** the END_TO_END_POC world, plus a STATUS attribute and a structured REPORT value (Amendment 001).

## 2. Results (DISCOVERED mode)
| metric (gate) | DEV v3 (30) | **LOCKED_v2 (20)** |
|---|---|---|
| SOURCE_REPLAY_EXACT (= 1.0) | 1.0 | **1.0** (32 procedures) |
| COUNTERFACTUAL_EXACT (= 1.0) | 1.0 (48) | **1.0** (33) |
| ROLLBACK_EXACT (= 1.0) | 1.0 | **1.0** (27) |
| RESTART_PROCEDURE_EXACT (= 1.0) | 1.0 (21) | **1.0** (17) |
| PROCEDURE_RETRIEVAL_EXACT, strict (≥ .95) | 1.0 (29) | **1.0** (20) |
| ARGUMENT_BINDING_EXACT (≥ .95) | 1.0 | **1.0** (19) |
| SCENARIO_EXACT (≥ .90) | 1.0 | **1.0** (20/20) |
| FINAL_STATE_EXACT | 1.0 | 1.0 |
| NEGATIVE_CASE_SAFE | 1.0 | 1.0 (199 checks) |
| VERIFY_FALSE_ACCEPT (deliberately bad candidates) | 0 | **0** (0/6) |
| composition L1 (dynamic P2(P1(x))) / L2 save / L2 invoke | 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 (5 each) |
| STORED_PROCEDURE_REUSE_EXACT / DYNAMIC_RECOMPOSITION_RATE | 1.0 / 0.0 | 1.0 / 0.0 (3) |
| EQUIVALENT_PLAN_COLLAPSE_COUNT / FALSE_AMBIGUITY_COUNT | 3 / 0 | 3 / 0 |
| PROCEDURE_RETRIEVAL_BEHAVIORAL, BEHAVIORAL_PLAN_EXACT (descriptive) | 1.0, 1.0 | 1.0, 1.0 |

**Generalization split (§69; not collapsed into one number)**
| split | DEV v3 | LOCKED_v2 |
|---|---|---|
| demonstrated arguments (REPLAY) | 1.0 (11) | 1.0 (7) |
| never-demonstrated arguments | 1.0 (48) | 1.0 (33) |
| surface paraphrase retrieval (LOCKED uses disjoint templates) | 1.0 (29) | 1.0 (20) |
| post-restart invocations | 1.0 (21) | 1.0 (17) |
| composition (L1 + L2 invoke) | 1.0 (12) | 1.0 (10) |

## 3. LLM vs deterministic proposals (the Amendment 001 comparison)
| | DEV v3 | LOCKED_v2 |
|---|---|---|
| discoveries with both paths | 46 | 32 |
| deterministic VERIFIED | 46 (1.0) | 32 (1.0) |
| LLM proposal parseable + statically valid | .848 | .875 |
| LLM VERIFIED | 36 (.78) | 25 (.78) |
| LLM-only verified (deterministic failed) | **0** | **0** |
| identical canonical program when both verified | 35/36 | 25/25 |

- **In proposal, the frozen 1.5B model contributed nothing beyond symbolic anti-unification.** Every procedure it got right, the anti-unifier also got right, and in all but one case with the identical program.
- **In retrieval, the LLM is load-bearing for choosing the procedure:** its ranking selected the procedure in every non-alias request. Its argument text is weak. On LOCKED it was used directly in 11 / 19 requests; the deterministic typed fallback handled 5, and the equivalent-plan collapse 3.
- **The deterministic checks never let a wrong LLM argument execute.**

## 4. Verification and safety
- **Candidates are judged only against evidence** from the traces, never against gold. The counterfactual reference is the *unabstracted* trace with value substitution.
- **A false accept was found and fixed before DEV** (ENGINEERING_LOG #1):
  - the unit suite caught the first verifier design accepting a candidate that dropped a constant `STATUS=OPEN` filter, because every evidence state had all calls OPEN;
  - a state-perturbation stage fixed it.
  - **Lesson:** an evidence-only verifier needs state diversity to detect constant-dropping.
- **Afterwards:** 0 / 6 deliberately bad LOCKED candidates were accepted (frozen value, parameterized constant, dropped filter, wrong scope), and 0 / 4 on DEV.
- **Activation requires VERIFIED plus an explicit `:accept`** (an S8 guard in code). Rollback-injection after every op leaves the state hash unchanged.

## 5. Persistence (the hard gate)
- **Restart is strict:** every RESTART terminates the scenario process and **kills and restarts the LLM service**.
- **After a restart,** requests use a new argument and new wording and are served only from `procedures.sqlite` and the world. **RESTART_PROCEDURE_EXACT is 1.0 (17 / 17 on LOCKED).**
- **Nested persistence (P12):** the composite P3 = count_calls_with(person_on_call_at(time)) survives two restarts and is **reused as the stored procedure**, not re-planned (reuse 1.0, dynamic recomposition 0.0).

## 6. Development history (all disclosed)
1. **DEV v1, DISCOVERED:** SCENARIO_EXACT .60 (retrieval .52). The frozen LLM's argument text (lowercase names, positional / spurious arguments, a hallucinated few-shot procedure, no composition) failed the deterministic checks. The system asked CLARIFY and never executed wrongly.
   - P11 exposed a **scenario-design defect**: one-shot teaching of a family whose parameter occurs twice violates the registered one-shot rule, so the system correctly refused.
2. **ENGINEERING_LOG #3** (general runtime changes): deterministic argument repair, a typed-candidate fallback plus type-directed composition search, and a behavioral metric kept descriptive. P11 was fixed to two demonstrations, and DEV was regenerated as v2.
   - **LOCKED_TEST v1** (never opened) was **archived as invalidated-before-run**, and a fresh independently seeded **LOCKED_TEST_v2** was frozen without inspection (user ruling).
3. **DEV v2:** .967. The only miss was a P12 stored-vs-dynamic equivalence tie.
   - **ENGINEERING_LOG #4:** structural canonical-plan equivalence, collapsing equivalent candidates before tie detection, and a preference for an ACTIVE stored procedure over its expansion. The version was tightened per the review; the score margin is never evidence of equivalence.
4. **DEV v3:** all gates pass. Integration freeze covering code, prompts, the margin and the model hashes. LOCKED_TEST_v2 was run once: 20 / 20.

## 7. Capability and cost accounting (LOCKED)
- **Library:** about 1.6 active procedures per scenario at the end (up to 3, including composite depth 1); about 50 KB of procedure library vs about 127 KB of world.
- **Model size is constant:** 1.54 B LLM parameters (frozen) plus the frozen binder.
- **Time:**
  - verification about 0.5 s per candidate;
  - LLM proposal about 6.1 s;
  - retrieval about 2.0 s and about 2 LLM calls per request;
  - stored-procedure execution about 1 s including process overhead (7.3 VM ops).
- **Reuse vs first time:** first-time acquisition needs teaching plus proposal plus verification; reuse is 1 retrieval plus 1 transaction.
- **Hardware / cost:** local only (RTX 2060 for the LLM), $0.

## 8. Limits
- **Small, synthetic, controlled domain:** 13 procedure families. Requests are templated paraphrases.
- **The teaching interface is a formal step language,** not natural-language instruction.
- **The LLM's proposal role is not shown to add value** at 1.5B.
- **The binder** (END_TO_END_POC) is available in the shell but is **not exercised** in the scenarios, whose fixtures use gold IR.
- **One LOCKED run, one seed-set;** no multi-seed replication.

**STOPPED** after the report.
