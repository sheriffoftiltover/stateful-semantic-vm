# PDX engineering log

The parent runtime (core/, procedure/) is byte-identical to the NL_TEACH copy of SEMVM_PROCEDURE_DISCOVERY_POC_V1
(locks/PARENT_FROZEN_COMPONENTS.json). student/ starts from the frozen NL_TEACH V1.2 frontend; every student change is listed here.

## #0 (pre-DEV, 2026-09-27) — registered baseline + infrastructure
- Amendment 001 (Modal self-hosted gpt-oss-120b teacher; bad-suggestion scoring by detectability; preflight; baseline fixes).
- student: fix 9.1 (connector + failed decomposition -> CLARIFY, no whole fallback); fix 9.2 (evidence sufficiency before every abstraction against the
  registered :target signature; parent one-shot rejection -> REQUIRE_SECOND_DEMONSTRATION); cross-demonstration consistency (strict majority >= 2).
- student safety rule: SET_STATUS values only with a cue word of that status family (found while designing the INVALID_VALUE injection:
  "mark them as archived" would otherwise have been grounded as CLOSED).
- teacher: capability-card line about where times are stored replaced after the first smoke test (the teacher looked for "open reminders at 5:45"
  instead of calls); EXAMPLE line parser tolerant of "EXAMPLE=" (seen in the smoke test).

## #1 (pre-DEV) — local subset test (GOLD_TRACE + SCRIPTED, 9 scenarios, no teacher cost)
GOLD_TRACE 1.0 on every metric (14 false-accept probes rejected, removal audit clean, 0 network attempts, neural hash invariant).
SCRIPTED revealed three defects, all fixed:
- controller: an episode aborted by a budget left the student's demonstration OPEN; the next target's lesson was then grounded inside it
  (spurious reference ambiguity loops). Aborted demonstrations are now closed without learning and the sandbox restored.
- student (latent NL_TEACH bug): a result whose runtime value is NONE (e.g. GET WHO of the first call when there is no call) was typed NONE, so a
  following "Return the person." failed R4. Results now keep the static kind of their operation.
- scripted teacher: demonstration 3 reused demonstration 1's value (majority group could not vary) -> uses the other pool value.
- VAGUE_STEP injection text made reliably ungroundable ("..., like we did for Kevin."): the original text "Now do the usual thing with it." was
  executed as RETURN by the student — reported as a student weakness (a vague instruction can execute); the injection's purpose (a guaranteed
  rephrase request, spec §42) needs a line the student must reject.

## #2 (pre-DEV) — teacher-selection preflight (results/TEACHER_PREFLIGHT.json)
gpt-oss-120b reasoning low / medium / high on 8 registered DEV scenarios (10 targets): learned-exact 6 / 9 / 9; tokens 40.8K / 48.2K / 41.5K;
student questions 24 / 23 / 13. SELECTED: high (tie on exact, fewer tokens). Cost $0.98. Frozen: reasoning_effort=high.
Defects found in the preflight transcripts (fixed before DEV):
- controller: the per-instruction clarification budget never triggered (each replacement line got a new id), so an unresolved step ("Sort them by
  when.") was eventually ABANDONED and the incomplete demonstration (FIND, FIRST, RETURN) was learned. Replacements now inherit the id of the
  instruction they replace; > 2 exchanges aborts the demonstration (TEACHER_EPISODE_FAIL, spec §19) — an incomplete demonstration can no longer
  become evidence.
- controller: a teacher reply to a rephrase request that contains a NEW demonstration (EXAMPLE + >= 2 STEPs) restarts the demonstration (the
  abandoned one is closed without learning); NOT_FOUND feedback now explains that an earlier step found nothing for the example values.
- student prompt (pre-freeze coverage fix): the frozen NL_TEACH few-shot had no SORT example although SORT is in the primitive inventory; one
  non-curriculum example added ("Sort them by place." over NOTE).

## #3 — first full DEV attempt STOPPED (results/dev_run1_design_defect/): scenario-design defect in the controls
GOLD_TRACE / FORMAL_TEACH were NOT exact: 2 VERIFY_FALSE_ACCEPT probes VERIFIED (close_open_emails_to, dropped status filter; dev-007, dev-008)
and 1 learning miss (dev-030, close_oldest_open_request). Cause: the PDX teacher value pool (introduced so post-handoff arguments are
never-demonstrated) contained values with NO matching events — a pool person with no emails (the evidence, even after the verifier's state
perturbation, has no email for that person, so "open emails" and "all emails" are indistinguishable: the verifier behaved per its evidence-only
contract; the scenario violated spec §63 "counterfactual cases executable / negative cases meaningful"), and pool people with no requests (the
S15 demonstration's "close it" fails NOT_FOUND even with gold steps). The TEACHER arm was stopped during acquisition (cost so far ~$2.0 total).
Fixes: every teacher-pool value now has matching events (two emails to pool person 0, one closed by the setup; four requests by the two pool people
at different times, one closed). Generator changed -> LOCKED v1 archived UNOPENED as INVALIDATED_BEFORE_RUN
(scenarios/archive/locked_test_v1_INVALIDATED_BEFORE_RUN/INVALIDATION.json); LOCKED v2 generated from the same blind template file with a NEW seed,
not inspected. DEV regenerated; full DEV rerun from scratch.
Also found: `modal app stop` requires --yes non-interactively — the evaluator's handoff teardown would have FAILED silently (recorded as
teacher_destroyed=false). Fixed; TEACHER-mode disconnect metrics now REQUIRE a verified teacher teardown.

## #4 — DEV attempt 2 (results/dev_run2_teacher_truncated/): SCRIPTED + TEACHER; controls exact (kept)
SCRIPTED: scenario .867, learned .914, distilled .903; all safety gates pass; reuse gates fail (counterfactual / restart .92, stored reuse .75).
TEACHER: scenario .60, learned .629, WRONG_TEACHER_ACTION_EXECUTED 4, VERIFY_FALSE_ACCEPT 2, 1 scenario crashed. NOT a valid measurement of the
teacher because of two infrastructure defects:
- teacher output cap: max_tokens 1200 truncated 32 / 98 teacher replies (finish_reason=length; 29 EMPTY — the hidden reasoning at effort=high used
  the budget) -> empty "demonstrations" -> TRACE_FAILED -> turn / demo budgets. max_tokens -> 4096. (The preflight also ran under the 1200 cap;
  reported as a caveat — high still won 9/10.)
- consistency rule too weak: skeletons ignore constant VALUES, so an injected CONSTANT_SWAP demonstration (STATUS=CLOSED) grouped with a
  correct one (STATUS=OPEN); anti-unification then made STATUS a PARAMETER and the frozen parent verifier crashed (cf_values: empty
  counterfactual pool once both STATUS values occur in the evidence — a latent PARENT bug, reported, not patched). Consistency now requires the
  same skeleton AND the same constants outside the registered signature's types; any failure inside the frozen learner is caught and fails the
  target as LEARNER_ERROR instead of crashing the scenario.
Also observed (reported, not fixed — student limitation): the frozen 1.5B student grounds "open emails to <P>" as SELF.WHO in some contexts;
with an empty WHO result the evidence is vacuous and 2 dropped-filter probes VERIFY (the false accepts above are of this kind).

## #5 — FINAL DEV (results/dev/) — no further tuning; LOCKED not run
TEACHER: learned .667, scenario .633, WRONG_TEACHER_ACTION_EXECUTED 12, VERIFY_FALSE_ACCEPT 1 (gates fail; spec §72 S3, S5).
SCRIPTED: learned .917, scenario .900, all safety gates pass; reuse gates .92 (misses = skills not learned exactly).
Controls: 1.0 on every metric. Retention given exact acquisition: 1.0 in every arm (TEACHER 54/54). Direct teacher AST .639 vs trace .667.
Teacher truncation after the 4096 cap: 1 / 78. Teacher destroyed at handoff (modal app stop rc 0, endpoint 404). Total Modal spend $4.78.
