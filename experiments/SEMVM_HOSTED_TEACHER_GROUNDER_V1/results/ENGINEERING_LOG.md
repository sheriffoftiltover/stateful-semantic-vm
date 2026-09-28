# HTG engineering log (spec §87)

## #0 Setup (2026-09-28)
- **Parent freeze:**
  - PDX final DEV code copied; 62 files hash-identical to the parent (`locks/PARENT_FROZEN_COMPONENTS.json`).
  - Parent LOCKED sets not copied or opened.
- **Hosted endpoint:** new Modal app `semvm-htg-hosted` with its own meter `semvm-htg-meter`, on the same checkpoint Volume. Spend is reviewed at $8 and hard-capped at $12.
- **client.py:** role-scoped caches (teacher / grounder / judge) and role-scoped request keys. The truncation rule treats `finish_reason=length` or an empty reply as HOSTED_TRUNCATION: never parsed or cached, re-requested once, then PROVIDER_FAILURE.
- **Teacher card:** goal-faithfulness contract added (spec §16).

## #1 Build (all before any hosted DEV run)
- **Hosted grounder** (`student/hosted_grounder.py`) and a pluggable grounder in NLSystem.
- **Evidence checks in NLSystem:** non-vacuity and conflict prechecks.
- **Episode:** EVIDENCE_CONFLICT / vacuity handling, the RELATION_SWAP injection, lesson lines kept before injection, and grounder provider failures caught.
- **Behavioural evaluator** (`evaluator/behavior.py`) and the lesson judge (`evaluator/judge.py`).
- **Factorial evaluator** (`htg_evaluate.py`).
- **Generator:**
  - new seeds;
  - strata S16–S18 (probe families cycle deterministically);
  - HTG families;
  - fixture witnesses;
  - scripted-line → gold-unit map.
- **Inherited-test adaptations** (Amendment 001 A7):
  - `t_cross_demonstration_consistency` now gets a CLOSED witness;
  - the role-scoped cache key is used.
- **Test results:**
  - HTG 15/15
  - PDX 10/10
  - NL_TEACH 18/18
  - procedures 18/18
- **Offline smoke** (4 DEV scenarios; GOLD_TRACE, FORMAL_TEACH and A):
  - all exact;
  - probe metrics populated;
  - the S14L DROPPED_FILTER demonstration → EVIDENCE_CONFLICT → a third demonstration → VERIFIED with 1 discarded;
  - S18: the local grounder read "with" as RECIPIENT, so the vacuity probe was not triggered.

## #2 Blind LOCKED
- An independent agent wrote `scenarios/templates_htg_locked.json` (sha `185cefcb…`) and generated 20 scenarios (manifest sha `fb695df0…`), sealed in `locks/LOCKED_TEST_MANIFEST.json`.
- Wording overlap with DEV: 0. There are 4 shared structural tokens: `""`, `"."`, and the `failing` type codes PLAN and NOTE.
- The experimenter did not inspect the contents.

## #3 Grounder preflight (results/PREFLIGHT.json)
- **Setup:** Arm B, 8 DEV scenarios, low vs medium reasoning.
- **Results:**

  | Setting | LINE_GROUNDING_STRUCTURAL_EXACT | WRONG_BEHAVIORAL | Mean output tokens | Truncations |
  |---|---|---|---|---|
  | low | .905 (21 lines) | 0 | 68 | 0 |
  | medium | .563 (16 lines) | 1 | 271 | 0 |

- **Selected:** low, by the frozen rule.
- **Inexact low lines (genuine grounder behaviour):**
  - an output-obligation block on a SELECT without the requested RETURN, rescued by the scripted rephrase;
  - COUNT fused with an early RETURN (behaviourally equivalent).

## #4 FINAL_DEV freeze
`locks/FINAL_DEV_FREEZE.json` records the hashes of all code, prompts, specs and manifests. No engineering changes are allowed during FINAL_DEV.

## #5 FINAL_DEV judge defect (evaluator-only; found after FINAL_DEV completed)
- **Defect:** `htg_evaluate.run_judge` ran inside the evaluator's main process. The endpoint URL and key are injected only into subprocess environments, so every judge call failed with a KeyError before any request was sent. 73 labels are `{faithful: None}`, and TEACHER_LESSON_* and the C/D GROUNDING_BEHAVIORAL_EXACT come out null.
- **Unaffected:** no arm, student, teacher, grounder or reuse data.
- **Repair** (no code or prompt change to any arm):
  1. After all reuse phases, the endpoint was redeployed for the evaluator-only judge role.
  2. The saved C/D lessons were labelled with the frozen judge prompt.
  3. The endpoint was torn down again and the 404 re-verified (`handoff_audit/teardown_judge_repair.json`).
  4. Results were rescored with `--rescore`.
- **Handoff guarantees:** unchanged. Every student reuse process had already finished under the network guard before the redeploy.

## #6 Evaluator defect: parameterless reference (found while reading FINAL_DEV results)
- **Defect:** `behavior.reference_steps` returned None whenever the example dict was empty. The parameterless family `email_topic_report` therefore had no reference, and every arm counted one spurious WRONG_BEHAVIORAL action and one non-exact demonstration, even though the procedure was learned exactly.
- **Fix:** an empty example is valid when the signature is empty. This is an implementation defect, not a redefinition: the registered reference is "gold family steps for the demonstration's own EXAMPLE values", and it exists when there are no parameters.
- **Scope:** results rescored from the saved data. Values before the fix are in results/REPORT.md.

## #7 Attribution caveat (reported, not changed)
- The judge sees the lines the student CONSUMED. When a grounder RETURN ends a demonstration early, the teacher's remaining lesson lines are never consumed, so the judge can blame the teacher for a missing step.
- One Arm D case: dev-011-S9, where the hosted grounder added an unrequested RETURN. The earliest-cause label there is corrected by hand in the report; the metric code is unchanged.
