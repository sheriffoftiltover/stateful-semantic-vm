# SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1 — Amendment 001 (registered before DEV)

**Date:** 2026-09-27.

## A1. Teacher provider and model (user ruling)
- **Teacher (Groq → self-hosted):** the teacher is **frozen `openai/gpt-oss-120b`, self-hosted on ONE Modal H100 with vLLM 0.11.0**, not a Groq-hosted API model.
  - Groq's free plan (200K tokens/day/model) could not hold the run.
  - Self-hosting freezes the exact weights: HF revision `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`, checkpoint sha256 `0fc58fd24ef9…`, per-file sha256 in `locks/TEACHER_WEIGHTS_MANIFEST.json`. A hosted API cannot be hashed.
  - The provider is an implementation detail of the hypothesis. The Groq integration remains a possible later replication arm.
- **Endpoint:** `teacher/modal_teacher.py`. It is OpenAI-compatible, scales to zero after 180 s idle, and uses a random API key held in a Modal secret (never logged).
- **Budget:** the user's $20 Modal credit, with review at $12 and a hard cap of $17.
  - The live cost meter counts container-alive heartbeat seconds × the H100 rate ($3.95/h) plus CPU/memory, cross-checked against `modal billing`.
  - Every uncached teacher call checks the meter first.
- **Stricter hard teacher disconnect (§25):** at handoff the Modal app is **stopped**, so the teacher no longer exists, and endpoint unreachability is verified.
- **Generation (§13):** temperature 0, top_p 1, seed 0, reasoning_effort fixed by the preflight (A3), max_tokens 1200.
  - vLLM is **not** bitwise repeatable at temperature 0 (verified: two identical requests gave different text).
  - The response cache is therefore the experimental record (§74): every raw response is stored by request hash and replayed on identical requests.

## A2. Bad teacher suggestions (§45, user ruling: split by detectability)
- **Locally detectable classes:** UNSUPPORTED_PRIMITIVE, PREMATURE_RETURN, WRONG_ARGUMENT_TYPE, INVALID_VALUE.
  - These must never execute: `BAD_TEACHER_SUGGESTION_EXECUTED = 0`.
- **Legal-but-wrong classes:** DROPPED_FILTER, CONSTANT_SWAP.
  - They are injected into ONE of two demonstrations and may execute in the teaching sandbox; this is reported as `LEGAL_BAD_SANDBOX_EXECUTED`.
  - Hard requirement: `BAD_PROCEDURE_ACTIVATED = 0`. Contradictory multi-example evidence must stop them from becoming VERIFIED or ACTIVE.
  - Reported alongside: `CROSS_DEMO_INCONSISTENCY_DETECTED`.
  - The student is never required to decide which of two conflicting demonstrations is right. It asks for another demonstration, and it learns only from a strict-majority consistent group of at least 2.

## A3. Teacher-selection preflight (§12)
- **Candidates:** the model is fixed by the user ruling. The registered candidate set is the three reasoning-effort settings of the frozen checkpoint: `low`, `medium`, `high`.
- **Preflight subset:** 8 DEV scenarios (strata S1, S3, S5, S6, S9, S11, S12, S15), TEACHER mode, acquisition only.
- **Selection:** the highest count of targets learned exactly (STUDENT-verified, program equal to gold); ties go to the lower token cost.
- **Freeze:** the chosen setting is frozen before the full DEV run.
- Preflight responses are cached like all others.

## A4. Mandatory baseline fixes (§9), implemented in `student/` (the frozen NL_TEACH V1.2 frontend + these changes only)
- **9.1:** an instruction containing an apparent sequencing connector (strong or weak) whose clause decomposition does not validate is **CLARIFY**. There is no whole-sentence fallback.
- **9.2:** evidence sufficiency is checked before *every* abstraction (`:endteach`, `:learn`, `:propose`) against the registered target signature (`:target name(p:T, …)`).
  - Each input must be hinted by a declared example value, or vary across at least 2 demonstrations. Otherwise the outcome is `REQUIRE_SECOND_DEMONSTRATION`.
  - The parent's one-shot "value occurs in N slots" rejection maps to the same status.
- **Cross-demonstration consistency:** see A2.
- **Pre-freeze student safety rule (added after the SET_STATUS gap was found while designing INVALID_VALUE):** a status can be SET only when the instruction contains a cue word of that status family. So "mark them as archived" gives CLARIFY instead of silently mapping to CLOSED.

## A5. Protocol (§16–§22)
- **Capability card:** `teacher/protocol.py`, generated from the frozen primitive inventory and ontology.
  - Its phrasing examples use only MESSAGE / NOTE / PLAN.
  - It never contains a gold AST or trace, an expected action sequence, verifier cases or locked annotations.
- **Teacher inputs:** the goal, the target signature, the student's ACTIVE skills (with their registered goals), a **teacher value pool**, and the style instruction (A–E).
- **Value pool:** the pool is disjoint from the post-handoff evaluation values. Post-handoff arguments are therefore never-demonstrated by construction (§40); novelty is still checked against the values the teacher actually used.
- **Student questions** are fixed templates:
  - rephrase request;
  - reference question (`ANSWER:`);
  - another-demonstration request, for insufficient evidence or inconsistency;
  - "not returned yet".
- **Accept:** the evaluator issues `:accept` only on VERIFIED (§18.14).
- **Budgets (§19):** 8 teacher turns per demonstration, 2 clarifications per instruction, 3 demonstrations per target.

## A6. Controls and arms (§29–§31)
- **GOLD_TRACE and FORMAL_TEACH:** registered pool values.
- **SCRIPTED_TEACHER:** registered lessons from the NL_TEACH DEV template bank for DEV. LOCKED uses a NEW blind template file, because the NL_TEACH LOCKED materials stay untouched (§58).
- **TEACHER:** the primary arm.
- **LOCAL_NL_V1_FINAL (§51):** the historical NL_TEACH V1.2 DEV result is reported as-is. SCRIPTED_TEACHER is its comparable arm on this experiment's scenarios.
- **DIRECT_TEACHER_AST:** a descriptive diagnostic (§31, §64).

## A7. Metrics definitions (registered)
- **STUDENT_TRACE_EXACT:** a demonstration's executed trace equals the gold body with any values at parameter slots and every constant matching. Demonstrations with a legal-bad injection are excluded.
- **WRONG_TEACHER_ACTION_EXECUTED:** a completed (RETURNed) demonstration whose trace is not exact, excluding legal-bad injected demonstrations.
  - Whether the fault lies with the teacher or the student is assigned by the failure taxonomy.
  - This is strict: an alternative, behaviourally equivalent program still counts as wrong. Behavioural distillation is reported separately (DISTILLED_SKILL_EXACT).
- **VERIFY_FALSE_ACCEPT:** registered probes. For every ACTIVE learned target, the frozen-value and dropped-constant-filter variants are proposed against the same evidence and must be REJECTED.
- **POST_HANDOFF_TEACHER_CALLS:** non-loopback connection attempts logged by the network guard in any reuse process, plus teacher-cache writes after handoff.
- **TEACHER_REMOVAL_AUDIT_CLEAN:** every reuse process has the guard active, no teacher environment variables, no teacher modules loaded, and no `learn/` directory. Teaching transcripts, examples and snapshots are moved out at handoff.
- **DISTILLED_SKILL_EXACT (per skill):** ACTIVE after acquisition, every post-handoff invocation of the skill exact, and the audit clean.
