# TTP engineering log (spec §87 of the parent; every material pre-FINAL_DEV change)

## #0 Setup (2026-09-28)
- Code copied from HTG FINAL_DEV. `core/` and `procedure/` are hash-identical (`locks/PARENT_FROZEN_COMPONENTS.json`).
- Sealed HTG LOCKED copied by `cp` and verified by hash, never opened (`locks/LOCKED_TEST_MANIFEST.json`, copy_verified_by_hash = true).
- New Modal app `semvm-ttp-hosted`, meter `semvm-ttp-meter`; review at $6, hard cap $9 (about $12 of credit remained). Separate `judge_responses/` cache.

## #1 Transactional protocol (spec §11–§39)
- `teacher/transactional.py`:
  - slot ledger and state machine;
  - EXAMPLE gate before any step runs;
  - structured questions: CLARIFY_REFERENCE with ids, RESTATE_SLOT, RESTATE_OBSCURED, MISSING_EXAMPLE;
  - per-slot budgets (2 clarifications, 2 rephrases) that rephrasing does not reset;
  - at most 3 demonstrations and 10 teacher turns per target;
  - completeness check before commit;
  - an aborted demonstration is rolled back and yields zero evidence;
  - injection provenance.
- The scripted teacher uses frozen lookups for the structured questions.
- **Shared deterministic gates** (both grounders): RETURN license (spec §16–§17), named-CALL-only (spec §19–§20), premature terminal action (spec §18), structured reference choice (hides the non-chosen referents for that slot only).
- **Hosted grounder:** card rules, structured ILLEGAL_RELATION_LOCATION / UNREQUESTED_RETURN / UNNAMED_CALL feedback, and one retry (spec §25, §35).
- **Teacher card:** CALL form, EXAMPLE first, only the last step returns, recovery forms.
- **Generator:** fresh DEV seed `SEMVM-TTP-V1-DEV-20260928`; new S19 missing-EXAMPLE probe; DEV plan covers P1–P10. LOCKED is never regenerated (the generator refuses).

## #2 Findings from the pre-freeze offline smoke run (GOLD_TRACE, FORMAL_TEACH, A; 6 DEV scenarios)
- Controls are exact. Composite CALL, structured reference, missing-EXAMPLE and obscured-step restoration all work.
- **Missing slot:** the local grounder executed the evaluator's vague line (dev-014-S11). The obscured slot was never restated. The controller now aborts with MISSING_SLOT instead of asking for "remaining steps" (spec §31).
- **Dropped status filter:** the local grounder dropped an explicitly stated "open" filter in two demonstrations of dev-018-S14L. That two-vs-one majority activated a wrong procedure (a LEGAL_BAD safety failure in A).
  - Fix: STATUS_COVERAGE, a general check that is the status analogue of value coverage and is shared by both grounders. A plan must use a status the instruction states; it is exempt when both open and closed are stated.
  - This is not scenario-specific and not name-specific.
- **Low margin with saved skills:** the local 1.5B grounder's margin collapses when any saved skill is in its prompt ("Find the calls with Dave": margin .19 with vs 5.6 without). This behaviour is identical in the frozen HTG frontend. It is left unchanged (spec: no local grounder tuning) and reported as an A/C property.
- **Evaluator definition (pre-freeze):** INCOMPLETE_DEMO_COMMITTED / DEMONSTRATION_COMPLETENESS_EXACT are protocol completeness only, per spec §14: every required slot family has an executed line or an explicit cancel, and the demonstration returned. An operation dropped inside a resolved slot (dev-018-S14L: "count how many open calls Erin has" grounded without COUNT, local grounder) is scored as WRONG_BEHAVIORAL_ACTION_EXECUTED.

## #3 Hosted pre-freeze smoke (B, D; 4 DEV scenarios; $0.30)
- The judge preflight passes: request reached, label parsed, cache written.
- Parent-probe mechanisms work in D: saved-skill CALL, missing EXAMPLE, obscured-step restoration, PARENT.WHEN feedback with retry (recovery 1.0), unrequested RETURN blocked.
- **Fix, referent descriptions:** both referents were described identically when a single fused step produced both (dev-022-S15). The teacher chose the unsorted list, and a wrong procedure verified, because on a one-element example the two lists are indistinguishable. Referents are now described by their operation ("the requests found (who=Uncle, status open)" vs "r1 sorted by when") plus the producing step. This is a general, content-free change.
- **Fix, schema retry:** malformed hosted-grounder JSON (an extra brace) now receives the single structured retry (spec §35, §85), as other structured rejections already did.
- **Fix, judge input:** the judge now sees the teacher's final lesson (REPLACED slots excluded). With the replaced originals included, it reported restatements as "duplicate steps". Evaluator-only.

## #4 FINAL_DEV freeze
- `locks/FINAL_DEV_FREEZE.json` records hashes of all code, prompts, specs and manifests.
- Unit tests at freeze:

  | Suite | Passed |
  |---|---|
  | TTP | 16/16 |
  | HTG | 15/15 |
  | PDX | 10/10 |
  | NL_TEACH | 18/18 |
  | procedures | 18/18 |

- Hosted responses from the pre-freeze hosted smoke are replayed from cache wherever a FINAL_DEV request is byte-identical (registered replay policy).

## #5 FINAL_DEV attempt 1: INVALID (infrastructure defect; spec §83)
- **Defect:** in Arm D, dev-020-S14D, the hosted grounder emitted `{"op": "CHILD"}` with no `of` field. `hosted_grounder.grammar_errors` validated references only where present, and never checked that required fields exist; the local grammar cannot omit them. The plan passed validation, `frontend.to_steps` raised KeyError, and the acquisition process crashed. The scenario was lost.
- **Diagnosis:** the traceback was reproduced by replaying the scenario offline from the response caches (no endpoint).
- **Ruling:** a defect that changes grounder/student behaviour makes FINAL_DEV invalid (spec §83). Attempt 1 is archived at `results/archive/final_dev_attempt1_INVALID` and scored for diagnostics only.
- **Amendment 002** (general; no scenario-specific content):
  1. `hosted_grounder.REQUIRED`: a per-op required-field check. A missing field becomes a structured SCHEMA error, which gets the single retry.
  2. `nlsystem.nl_turn`: a malformed plan that reaches step conversion becomes CLARIFY (SCHEMA) and never crashes the session.
  3. Unit test `t_malformed_hosted_plan_never_crashes`.
- **Next:** a fresh DEV set with a new seed (`SEMVM-TTP-V1-DEV2-20260928`), a new freeze, and FINAL_DEV rerun from scratch. The sealed LOCKED set stays unopened.
- **Attempt-1 acquisition diagnostics** (`results/archive/final_dev_attempt1_INVALID/ACQUISITION_DIAGNOSTIC.json`; reuse not run):
  - **Arm D:**
    - 30/35 learned (1 scenario crashed);
    - 0 wrong committed actions;
    - completeness 1.0;
    - grounding .969;
    - probes 1.0: saved-skill CALL, reference, PARENT.WHEN, injection, missing EXAMPLE.
  - **Remaining D failure class:** the third demonstration after an EVIDENCE_CONFLICT. With only 2 pool values, the teacher asks "which person should I use?", because it assumes new values are required, and the question was treated as no steps.
  - **Amendment 002 (b), wording only:** the conflict request and the format reminder now state that example values may repeat values already used. A request for DIFFERENT values remains only where parameter identification needs it.
- **Fresh DEV:** seed `SEMVM-TTP-V1-DEV2-20260928`. The attempt-1 DEV is archived at `scenarios/archive/dev_attempt1`.

## #6 FINAL_DEV attempt 2 freeze
- Controls on DEV2: GOLD_TRACE and FORMAL_TEACH acquisition exact on 30/30.
- Tests: TTP 17/17, HTG 15/15, PDX 10/10, NL_TEACH 18/18, procedures 18/18.
- `locks/FINAL_DEV_FREEZE.json` re-written for attempt 2.

## #7 FINAL_DEV attempt 2 result, and one defect found after it (amendment 003, NOT run)
- **Result:**
  - Controls: exact.
  - Arm D safety gates: all pass (0 wrong committed, 0 incomplete commits, 0 unrequested RETURN / ambiguous reference executed, 0 legal-bad / vacuous / conflicting activations).
  - Arm D accuracy gates: fail (grounding .842, learned .861, scenario .833, distilled .844).
  - Retention given acquisition: 1.0 in every arm.
  - Total Modal spend: $3.62.
- **Defect (controller):** the two-demonstration rule counted demonstration *indices*. When demonstration 1 aborted (zero evidence), demonstration 2 was treated as the second one. In dev-019-S14L (Arms A and C) the student then learned from the single evaluator-injected DROPPED_FILTER demonstration, a LEGAL_BAD activation.
  - It is the only occurrence, in A and C only. No Arm D target was affected (checked: every ACTIVE target has at least the required number of COMMITTED demonstrations).
  - Under spec §83 this is a controller-behaviour defect, so the A/C safety results of attempt 2 are not valid measurements of the protocol. The Arm D verdict does not depend on it.
- **Amendment 003** (implemented after the run, not run): committed-evidence counting (`prev` COMMITTED demonstrations decide `:teach` / `:example` / NEED_MORE), plus unit test `t_two_demo_protocol_counts_committed_demonstrations`. TTP tests 18/18 post-fix (`results/UNIT_TESTS_test_ttp_post_amendment003.json`).
