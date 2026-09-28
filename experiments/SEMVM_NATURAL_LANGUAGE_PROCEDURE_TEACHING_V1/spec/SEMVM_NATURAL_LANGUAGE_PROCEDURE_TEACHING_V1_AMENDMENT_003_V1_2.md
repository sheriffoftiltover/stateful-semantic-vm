# Amendment 003 — V1.2 reference-validity and output-obligation invariants (FINAL DEV iteration)

**Date:** 2026-09-27.

**Trigger:** the V1.1 DEV run executed 2 wrong teaching actions (gate: 0).
- "Count them" with no antecedent in context: the frontend invented FIND REMINDER.
- "Tell me how many there are": the plan was COUNT with no RETURN.

**Records kept:** the V1 results (`results/dev_run1/`) and the V1.1 results (`results/dev_run2_v1_1/`) are kept as reported results.

## New deterministic invariants
All three are registered in `NL_TEACH_LANGUAGE_V1`.
1. **Event searches must be named.** FIND and FIND_LAST are available only for event types that the clause names with a registered type noun. This is enforced both in the grammar options and in static validation.
2. **Antecedent validity.** A clause containing an anaphor must reference an already-defined result. If no valid grounding remains, the result is CLARIFY. An antecedent is never reconstructed implicitly.
3. **Output obligation.** An utterance carrying an OUTPUT_REQUEST cue must yield a plan ending in RETURN. When the requested kind of result is named, R4 requires the RETURN to deliver that kind.

## Unchanged
- The LLM, prompt, few-shot, MARGIN (1.0), beam, scenarios and gates.
- All V1.1 rules.

## Protocol
- The full DEV is rerun from scratch.
- V1.2 is the final DEV iteration: no further tuning afterwards.
- LOCKED_TEST unlocks only if every registered gate passes as written. Otherwise LOCKED stays untouched and the experiment is written up.
