# HTG Amendment 001 — implementation registration (before the grounder preflight and before FINAL_DEV)

Registered 2026-09-28. No DEV arm has been run with a hosted model when this document was written. The parent LOCKED sets (NL_TEACH LOCKED and PDX LOCKED v2) were not opened, copied or reused.

## A1 Parent freeze
`locks/PARENT_FROZEN_COMPONENTS.json` records 62 files that are identical to the PDX final DEV code: runtime, executor, anti-unifier, verifier, procstore, retrieval, local frontend and student service. The local 1.5B grounder, i.e. the PDX final frontend, is unchanged (spec §60).

## A2 Hosted checkpoint
The HTG reuses the same checkpoint as PDX: the Modal Volume `semvm-pdx-gptoss120b` holding `openai/gpt-oss-120b`.
- HF revision: `b5c939de…`
- checkpoint sha256: `0fc58fd2…`
- manifest: `locks/HOSTED_CHECKPOINT_MANIFEST.json`

It is served by vLLM 0.11.0 on one H100 under a new app, `semvm-htg-hosted`, with its own cost meter `semvm-htg-meter`. Spend is reviewed at $8 and hard-capped at $12. The teacher and grounder roles share the checkpoint only: they have separate system prompts, separate requests, separate caches (`teacher_responses/`, `grounder_responses/`, `evaluator/judge_responses/`) and role-scoped request keys.

## A3 Arms and execution order (spec §6, §57)
- **Acquisition:**
  1. GOLD_TRACE, FORMAL_TEACH and A run first, with no hosted model up.
  2. The endpoint is deployed.
  3. B, C and D acquire concurrently, in separate processes and directories. C runs on the local GPU workers; B and D run on hosted-only threads.
  4. The evaluator-side lesson judge labels the C and D lessons.
- **Handoff:** one handoff covers every arm:
  - `modal app stop --yes` must return rc 0;
  - an endpoint probe must fail;
  - every arm's `learn/` directory is moved out.
- **Reuse:** runs in arm order, with a fresh student process and a restarted student service at every RESTART, the network guard on, and secrets scrubbed from the environment.
- **Teacher cache sharing:** teacher requests that are byte-identical between C and D (in particular each target's first LESSON request) are served from the shared teacher cache, by the registered replay policy (spec §48, §86). C and D therefore see the same first lesson for every target.

## A4 Hosted grounder (spec §13, §14, §61)
The grounder is `student/hosted_grounder.py`, frozen in `spec/HOSTED_GROUNDER_PROTOCOL.json`:
- One isolated request per line.
- Output is a typed envelope: PLAN, CLARIFY or UNSUPPORTED.
- A plan passes the local grammar's option constraints (rewritten as checks) and then every inherited deterministic check.
- There is no margin rule, because the hosted grounder has no calibrated scores.
- A grounder CLARIFY is routed to the teacher as the same templated student question the local grounder produces.

Reasoning effort is chosen by the registered preflight (`preflight_grounder.py`, rule in its docstring, result in `results/PREFLIGHT.json`) from {low, medium}. The preflight runs Arm B only on 8 DEV scenarios.

## A5 Teacher (spec §16, §59)
The only teacher change is the goal-faithfulness contract added to the capability card. Teacher reasoning is high, max_tokens is 4096, and temperature is 0.

## A6 Truncation (spec §49)
A reply with `finish_reason=length`, or with empty content, is never parsed or cached. It is re-requested once; after a second truncation it becomes PROVIDER_FAILURE. This applies to both roles and to the judge.

## A7 Evidence non-vacuity and conflict (spec §19–§23)
Both checks are in `student/nlsystem.py` and frozen in `spec/EVIDENCE_NONVACUITY_V1.json` and `spec/EVIDENCE_CONFLICT_V1.json`:
- The non-vacuity check replays each demonstration on its start snapshot. It requires every constrained search to be witnessed: non-empty in at least one demonstration, and distinguishable from its registered contrasts (status dropped; WHO↔RECIPIENT).
- The status that PDX called DEMONSTRATIONS_INCONSISTENT is renamed EVIDENCE_CONFLICT.
- A non-signature class that varies within the used group also gives EVIDENCE_CONFLICT.
- The frozen verifier is never called on a conflicting set.

**Inherited unit-test adaptations:**
- `test_pdx.t_cross_demonstration_consistency` gains a CLOSED witness call, because its old world has none and the non-vacuity rule now correctly refuses to verify without one. It also accepts the new status name.
- `test_pdx.t_client_cache_and_budget_stop` uses the role-scoped cache key.

## A8 Behavioural equivalence and metrics (spec §24–§28, §66)
- **Implementation:** `evaluator/behavior.py` runs on the independent oracle interpreter over 5 registered worlds and is frozen in `spec/BEHAVIORAL_EQUIVALENCE_V1.json`. It also holds the metric definitions, including GROUNDING_BEHAVIORAL_EXACT.
- **Demonstration-level grounding:** grounding exactness is measured over non-injected demonstrations whose lesson is faithful. Hosted lines have no per-line gold, so for C and D the grounding metric is necessarily measured on the demonstration.
- **Line-level grounding:** scripted arms additionally report LINE_GROUNDING_STRUCTURAL_EXACT, and A and B are paired line by line on identical registered lines (spec §62).
- **COUNTERFACTUAL_EXACT:** the pass rate of the verifier's counterfactual and perturbation tests on VERIFIED candidates (an acquisition metric, spec §34). The PDX post-handoff "novel argument" metric is reported as POST_HANDOFF_UNSEEN_ARGUMENT_EXACT_ALL. Retention metrics are reported both unconditionally and given exact acquisition (spec §35, §74).
- **Lesson judge:** `evaluator/judge.py` is the same checkpoint in an evaluator-only role. It sees the goal, the gold procedure and the lesson, and never feeds back into any arm. It labels TEACHER_LESSON_BEHAVIORAL_EXACT. TEACHER_UNREQUESTED_CONSTRAINT_RATE uses a deterministic lexical rule only.

## A9 Scenarios (spec §53–§55, §75–§82)
- **Generator:** the same generator, with new seeds and three new strata:
  - S16: relation-sensitive (RECIPIENT, TOPIC, WHERE);
  - S17: over-constraint;
  - S18: vacuity probe, a RELATION_SWAP injection.
- **New families:** all_requests_by, count_emails_to, emails_about, count_visits_in.
- **Fixture additions:** visits at pool places; a CLOSED call and a CLOSED request for teacher-pool person 0; topic pools.
- **DEV:** 30 scenarios, 36 targets, 2 L1 and 2 L2 composition cases, 10 post-handoff composite invocations.
- **LOCKED:** 20 scenarios, generated from blind templates written by an independent agent that read no parent LOCKED file. The LOCKED set stays unopened.
