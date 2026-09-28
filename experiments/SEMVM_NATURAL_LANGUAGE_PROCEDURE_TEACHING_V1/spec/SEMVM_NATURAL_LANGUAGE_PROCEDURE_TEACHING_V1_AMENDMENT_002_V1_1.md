# Amendment 002 — V1.1 multi-clause plan compiler (post-DEV, pre-LOCKED)

**Date:** 2026-09-27.

**Trigger:** the first complete DEV run (V1) executed 9 wrong teaching actions (gate: 0). It also scored first-pass scenario exact 0.60 and band-D (compact multi-action) utterance exact 0.50, against 0.95–1.0 for bands A, B and C.

**V1 record:** the V1 DEV numbers are archived unchanged in `results/dev_run1/` and reported as the V1 result.

**Diagnosis** (results/ENGINEERING_LOG.md #4):
- cascades from pending clarification state;
- truncation of multi-clause plans by the 1.5B frontend and the beam.

The primitive semantics are grounded well; clause composition is the defect.

## Change: an explicit multi-clause semantic / dataflow compiler layer between the frontend and execution

1. **Candidate clause segmentation.** Strong boundaries are explicit sequencing markers; plain `and` is a weak boundary (`NL_TEACH_LANGUAGE_V1`).
2. **Grounding.** Each clause is grounded by the frozen frontend to a non-executable plan fragment. Earlier clauses' planned results are in-instruction context.
3. **Combination** with cross-clause reference and dataflow resolution (reference rules R0–R4).
4. **Whole-plan validation.** The same checks apply to every path:
   - operation and type validity;
   - defined-before-use;
   - DEAD_PURE_RESULT liveness;
   - value and named-procedure coverage;
   - RETURN last;
   - CLAUSE_COVERAGE = 1 (at least as many actions as clauses).
   The whole-utterance fallback has no relaxed authority.
5. **Segmentation disagreement.** If the clause-wise and whole-utterance plans are both valid and cover every clause but differ, the result is CLARIFY (spec §33).
6. **Execution.** Only the complete validated plan executes, as one transaction.
7. **Structured clarification state.** A pending REFERENCE clarification is consumed only by an utterance that names exactly one legal answer.

## Unchanged
- The frozen parent runtime.
- The LLM, prompt, few-shot, MARGIN and grammar of the per-clause frontend.
- The scenarios, the DEV and LOCKED sets, and the gates.

## Protocol
- The full DEV is rerun from scratch under V1.1.
- LOCKED_TEST is not run until the user authorizes it.
