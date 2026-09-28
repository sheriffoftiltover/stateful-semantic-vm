# DEV engineering log (spec §60: engineering fixes that preserve registered semantics, logged)
1. **Before any scenario existed:** `vm.compile_command` could create a *new* person twice when one UPDATE named it twice (e.g. `WHO=Bob RECIPIENT=Bob`). Fixed by reusing the register. Unit test `update_same_new_person_once` was added.
2. **DEV run 1 (2026-09-26):**
   - All registered gates passed.
   - `RENDER_EXACT` (.9846) had been defined as the response vs the oracle's expected answer, so it also counted *upstream* errors. Both mismatches were in `dev-008-S3`, caused by its N_BIND error.
   - Redefined as **render correctness of the actual returned result**. Added `RESPONSE_EXACT` (end-to-end answer vs the oracle).
   - This is a metric-definition change only. No runtime code changed, no registered gate or semantics changed. DEV was re-evaluated from the cached neural outputs.
3. **Post-run documentation correction (found while building `repl.py`):**
   - The Amendment 001 literal-example table used WHEN on REMINDER. That is a V1 withheld cell, outside the supported triples, so the envelope rejects it.
   - The examples were replaced with envelope-checked generator output. The REPL help example was replaced too.
   - No scenario or result was affected: the suites were always envelope-checked at generation.
