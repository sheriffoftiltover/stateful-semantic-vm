# Experiment lineage

Seven preregistered experiments. Each ran from a spec with gates, stop rules and a sealed LOCKED set, and each stopped at its registered decision point.

- Numbers are copied from each experiment's `results/` report and JSON.
- The paper's `paper/generated/numbers.tex` is produced from the same JSONs by `scripts/make_figures_tables.py`.
- Categories are kept separate throughout: **observed**, **registered outcome**, **interpretation**, **invalid / defect**, and **next question**.

## 1. END_TO_END_POC_V1 — `experiments/SEMVM_END_TO_END_POC_V1`

- **Added:** a frozen neural binder, a canonical IR, a resolver, and a SQLite world model plus VM. Input was a controlled, tag-coindexed language (Amendment 001).
- **Observed:**
  - LOCKED 20/20 scenarios exact; DEV 29/30, where the one miss was a single neural parent-binding error.
  - GOLD_IR control: 1.0 on both suites.
  - Local vs Modal backend equivalence: 60/60 traces identical.
- **Registered outcome:** RESULT A, within the controlled-language regime.
- **Interpretation:** the deterministic runtime is exact given correct semantics. English is outside the envelope: 0/8 exact, and all 8 were rejected by the envelope check.
- **Next:** procedures.

## 2. PROCEDURE_DISCOVERY_POC_V1 — `experiments/SEMVM_PROCEDURE_DISCOVERY_POC_V1`

- **Added:** the procedure library, deterministic anti-unification, and the evidence verifier. Teaching used a formal step language; retrieval used controlled paraphrase.
- **Observed:**
  - LOCKED_v2 20/20 with every gate at 1.0.
  - 0 of 6 deliberately bad LOCKED candidates accepted.
  - The 1.5B model's procedure proposals: LLM-only verified discoveries were 0 of 32 on LOCKED. Where both paths verified, the programs were canonically identical 25/25 times.
- **Registered outcome:** RESULT A.
- **Defects:**
  - A verifier false accept (a dropped constant filter) was found by the unit suite before DEV and fixed with state perturbation.
  - DEV v1 had a scenario-design defect, so LOCKED v1 was archived unopened and LOCKED_v2 was sealed.
- **Next:** natural-language teaching.

## 3. NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1 — `experiments/SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1`

- **Added:** the frozen 1.5B model grounds each lesson clause through grammar-constrained ranking, followed by a deterministic multi-clause plan compiler.
- **Observed (V1.2, final):**
  - Learned .914; scenario .867.
  - Wrong LLM actions: 22 raw proposals were wrong, 16 were blocked or repaired, and 1 wrong action was executed (down from 9 in V1).
  - 1 verifier false accept, caused upstream by a lost second demonstration.
  - Trace-mediated learning 86.1% vs direct program writing 5.6%.
- **Registered outcome:** RESULT B with a safety stop. LOCKED not run (author ruling).
- **Next:** a stronger teacher.

## 4. LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1 (PDX) — `experiments/SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1`

- **Added:** a hosted gpt-oss-120b teacher (Modal H100, vLLM), and the handoff with verified teardown.
- **Observed:**
  - Retention 54/54 given exact acquisition.
  - The TEACHER arm learned 24/36, against 33/36 for SCRIPTED lessons.
  - 12 wrong executed demonstrations, about half teacher-side (unrequested constraints) and half student-side mis-grounding.
  - 1 false accept on vacuous evidence.
- **Registered outcome:** RESULT E/F conditions; LOCKED not run.
- **Superseded attempts:**
  - `results/dev_run1_design_defect`: a scenario-design defect.
  - `results/dev_run2_teacher_truncated`: 32/98 teacher replies truncated at 1200 tokens.
- **Next:** is the teaching channel limited by grounding?

## 5. HOSTED_TEACHER_GROUNDER_V1 (HTG) — `experiments/SEMVM_HOSTED_TEACHER_GROUNDER_V1`

- **Added:** a hosted 120B grounder; a 2×2 of teacher × grounder; non-vacuity and conflict checks.
- **Observed (Arm D, hosted × hosted):** learned 27/36 (.750); grounding 1.0; 2 wrong actions.
- **The two wrong actions:**
  - An unrequested RETURN truncated a demonstration.
  - An injected vague step was never restored.
  - Both procedures verified against evidence that was *consistent* but *incomplete*.
- **Registered outcome:** RESULT G (safety stop) together with RESULT E. LOCKED not run.
- **Evaluator-only defects:** the judge had no credentials, and a parameterless-reference scoring bug. Both were repaired and rescored; the Arm D decision is unchanged.
- **Interpretation:** consistent evidence is not necessarily complete evidence. The bottleneck is the clarification protocol.

## 6. TRANSACTIONAL_TEACHING_PROTOCOL_V1 (TTP) — `experiments/SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1`

- **Added:** a demonstration is a transaction, with a slot ledger, commit/abort, structured referent choice, RETURN licensing, named-CALL-only, PARENT.WHEN feedback, and injection provenance.
- **Observed (Arm D):**
  - Every safety gate passed: 0 wrong actions, completeness 1.0, 5 unrequested RETURNs blocked.
  - Learned 31/36 (.861); scenario .833; grounding .842.
  - B (scripted × hosted grounder) cleared the accuracy thresholds descriptively: learned .944.
- **Registered outcome:** RESULT D. LOCKED not run.
- **Invalid:** FINAL_DEV attempt 1 (a malformed CHILD crashed an acquisition). Archived at `results/archive/final_dev_attempt1_INVALID`; fixed by Amendment 002; rerun on a fresh DEV2 seed.
- **Post-run defect, Amendment 003:** the rule counted demonstration indices, not committed demonstrations. The A/C safety results are invalid; D is unaffected. The fix was unit-tested but not rerun.
- **Residual:** recovery capacity (truncation at 4096, a two-value pool, a turn budget).

## 7. RECOVERY_CAPACITY_ISOLATION_V1 (RCI) — `experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1`

### Stage 0
- **LOCKED parity:** Outcome N, so a successor LOCKED set was sealed.
- **Taxonomy:** frozen.
- **Ceiling diagnostic:** 4/5 parent failures recovered → GO.
- **Defect:** the Stage 0C teardown targeted the wrong app. It was repaired and 404 verified; the run was acquisition-only.

### Stage 1
- **Intervention:** only the value pool (2 → 4) and teacher `max_tokens` (4096 → 8192) changed. The serving context was raised to 32768 so these budgets fit. Amendment 003 is the baseline.

### Observed

**Arm D:**

| Metric | DEV-A | DEV-B | Pooled |
|---|---|---|---|
| Learned | 36/36 | 34/36 | 70/72 |
| Scenario | 30/30 | 28/30 | 58/60 |
| Distilled | 32/32 | 30/32 | 62/64 |
| Grounding | 36/36 | 35/35 | 71/71 |

- 0 wrong actions in both draws.
- Truncations 9 → 0.

**Factorial, learned (pooled):** B 71/72, E 72/72, F 68/72, D 70/72.
- Contrast signs do not replicate across draws, so no ranking.
- Scripted recovery grounded 0/14 recovery slots.
- The hosted recovery teacher resolved 12/12 events in E.

**LOCKED (run once):**
- 23/23 learned, 20/20 scenarios, grounding 22/23, with 0 wrong / incomplete / hosted calls / network attempts.
- The teardown probe returned **401**, which does not satisfy the registered 404 proof. Under the strict rule, teardown-verified, teacher-disconnect reuse and distilled-skill are all 0.
- **Not a clean pass.**

**Spend:** $3.57.
