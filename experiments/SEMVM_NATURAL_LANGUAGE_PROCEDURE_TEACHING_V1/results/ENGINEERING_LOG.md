# NL_TEACH engineering log

Each entry records a DEV-time change (spec §76). All changes are general runtime / frontend changes; they apply identically to the eventual
single LOCKED_TEST run. The parent runtime (core/, procedure/) is byte-identical to SEMVM_PROCEDURE_DISCOVERY_POC_V1 (locks/PARENT_FROZEN_COMPONENTS.json);
no entry below modifies it.

## #0 — pre-DEV prototype (2026-09-26): free generation -> grammar-constrained ranking
- A free greedy-generation prototype of the frontend (JSON action lines, parent-style few-shot) was tried on 25 ad-hoc instructions (not DEV
  scenarios). It copied few-shot continuation patterns (e.g. "Count them." -> SET_STATUS + COUNT + RETURN), dropped mentioned values,
  hallucinated extra actions and scopes: roughly half correct.
- Replaced by grammar-constrained beam search in which the frozen LLM only RANKS legal typed options (spec §9.2 "rank candidate actions",
  "select a primitive", "extract candidate arguments"). Two scoring defects found and fixed while prototyping:
  (a) the /choose score must be log P(tok(prompt+option)) - log P(tok(prompt)) (tokenization-boundary exact) — the first version fell back to
      a full-vocabulary forward that ran out of GPU memory;
  (b) options that end mid-token (e.g. `"FIND"` before `,` which tokenizes as `",`) get artificially low probability: every option now ends
      with its JSON delimiter; per-decision scores are renormalized over the legal options.

## #1 — DEV probe v0 -> v1 (teacher-forced grounding 93/136 -> 110/136)
Teacher-forced probe = GOLD_TRACE run in which each DEV utterance is additionally grounded (never executed) in its correct context.
Failures of v0: few-shot recency/type bias (VISIT -> MESSAGE, spurious status OPEN, WHO vs RECIPIENT), UNSUPPORTED/CLARIFY chosen for long
instructions, and the margin rule comparing hypotheses that are identical after the deterministic checks (e.g. `{"WHO":..,"WHEN":..}` vs
`{"WHEN":..,"WHO":..}`, or `RETURN r2` vs `RETURN r1` when the reference grammar licenses only one).
Changes:
- few-shot rewritten: 32 balanced examples (all 8 event types, fewer status examples, more multi-action, CLARIFY / UNSUPPORTED not last);
  still no catalogue family combination and no DEV template string.
- EVENT_TYPE values are restricted to the registered type nouns named in the instruction (same principle as PERSON / TIME / PLACE values:
  a literal must occur in the instruction; all types are offered if none is named).
- every complete hypothesis passes the same deterministic checks; hypotheses with an identical canonical outcome are one candidate
  (log-sum-exp); the margin is measured between DISTINCT canonical outcomes (as in parent ENGINEERING_LOG #4: a score gap is never evidence of
  equivalence; equivalence is structural).

## #2 — DEV probe v1 -> v2
Failures of v1 that EXECUTED (unsafe): value-coverage used as a decoding constraint made the beam append junk actions to consume a leftover
value ("... requests Laura made for midnight and then count them" -> FIND without WHEN, COUNT, RETURN, FIND again); status OPEN hallucinated
with no status word ("Look up all of my emails"); a named procedure ignored ("use count_calls_with on that person and then give it back" ->
RETURN only); two RETURNs.
Changes:
- coverage (PERSON / TIME / PLACE values AND named ACTIVE procedures) is no longer a decoding constraint; a complete hypothesis that violates
  it is a COVERAGE CLARIFY outcome that competes as a candidate and is never executed.
- a status constraint is offered only if the instruction contains a status cue word (registered roots, NL_TEACH_LANGUAGE_V1.status_cue_roots).
- RETURN is terminal (nothing may follow it in an instruction).
- five few-shot examples added (CALL with WHO + TOPIC; compact FIND+COUNT; compact FIRST+GET; compact COUNT+RETURN; two constraints on one
  outer event).

## #3 — DEV probe v2 (120/136) -> v3
Remaining EXECUTED errors of v2: a spurious COUNT inserted between FIND and "close each of them" (x2, unused result); "Please return how many
there are" -> RETURN of the list (no count exists); "Tell me how many there are" -> COUNT only (RETURN dropped; left as a known limitation).
Changes (registered in NL_TEACH_LANGUAGE_V1):
- R4: a RETURN whose instruction names result / type nouns, none of which matches any compatible result, is CLARIFY.
- dangling-result rule: an intermediate result produced by an instruction must be used by a later action of the same instruction.
- fix (same entry): the exemption is for the result of the instruction's LAST ACTION (v3 exempted the last producing action, letting FIND, COUNT, SET_STATUS through).

## #4 — first full DEV NL_TEACH run (results/dev_run1/) -> changes
First full DEV run (code as of #3): controls GOLD_TRACE / FORMAL_TEACH 1.0 on every metric; NL_TEACH scenario exact 0.733 (first pass 0.60),
WRONG_LLM_ACTION_EXECUTED 9, band D (compact multi-action) utterance exact 0.50 vs A/B/C 0.95-1.0.
Diagnosis: (i) cascade — every CLARIFY kept the instruction pending, so after a failed restatement the NEXT scripted utterance was appended to
the old instruction as an "answer" and re-grounded the whole earlier clause (most wrong executions happened inside these cascades);
(ii) truncation — the 1.5B frontend often grounds only the first clause of "X and Y" instructions (e.g. FIND without the close), and beam 3
loses the complete plan.
Changes:
- only a REFERENCE clarification ("which one do you mean?") keeps the instruction pending; low-margin / coverage / frontend CLARIFY asks for a
  rephrase and the next utterance is a new instruction.
- registered sequencing rule (spec §11 "simple conjunctions / sequencing words", §33): instructions are split at registered connectors; each
  clause is grounded by the frontend in order with earlier clauses' planned results as in-instruction context (R1); the combined plan must pass
  liveness, coverage and RETURN-last; if any clause is not OK the whole instruction is grounded as one.

## V1.1 — post-DEV engineering amendment (spec/SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1_AMENDMENT_002_V1_1.md)
The first full DEV run (results/dev_run1/, code of #3) triggered the hard safety condition: WRONG_LLM_ACTION_EXECUTED = 9 (gate = 0). Those
numbers are kept permanently as the V1 DEV result. #4's changes were refined (per review) into a V1.1 multi-clause plan compiler; the full
DEV is then rerun from scratch. LOCKED_TEST remains untouched (never run, never opened).
- candidate segmentation (strong markers vs weak plain 'and'); every clause grounded to a NON-EXECUTABLE plan fragment; finest segmentation
  whose combined plan validates wins; a weak 'and' that does not yield valid clauses is not a boundary;
- whole-plan validation with the same authority on every path (clause-wise or whole-utterance fallback): defined-before-use (grammar +
  validation + R4), DEAD_PURE_RESULT liveness (pure results only; stateful ops exempt; the last action's result is live-out to later
  instructions), value + named-procedure coverage, RETURN last, CLAUSE_COVERAGE (#actions >= #clauses);
- the whole-utterance reading is also grounded; if it validates, covers every clause and differs from the clause-wise plan -> CLARIFY
  (SEGMENTATION uncertain);
- structured pending clarification {kind REFERENCE, source_utterance_id, unresolved_slot, legal_answers}; only an utterance naming exactly one
  legal answer consumes it; otherwise it is cleared and the utterance is grounded normally;
- only the complete validated plan executes, as ONE transaction (unchanged).
- metrics added: INPUT_CLAUSE_COUNT, GROUNDED_CLAUSE_COUNT, CLAUSE_COVERAGE, SEGMENTATION_DISAGREE, DATAFLOW_DEAD_PURE_RESULT_BLOCKED,
  DATAFLOW_USE_BEFORE_DEFINITION_BLOCKED, clarification consumed / cleared counts.

## V1.2 — reference + output-obligation amendment (FINAL DEV iteration; spec/..._AMENDMENT_003_V1_2.md)
V1.1 DEV (results/dev_run2_v1_1/): WRONG_LLM_ACTION_EXECUTED 2 (gate 0), NL_TEACH_SCENARIO_EXACT .933, first pass .667; kept as the V1.1 result.
The two unsafe executions were: "Count them" with no list in context -> the frontend invented FIND REMINDER + COUNT; "Tell me how many there
are" -> COUNT without RETURN. Both are expressed as general static invariants (no string rule, no prompt change, MARGIN unchanged):
- event_search_rule: FIND / FIND_LAST only for event types NAMED in the clause (option set AND static validation) -> no invented antecedent;
- antecedent_rule: a clause containing an anaphor (them / they / those / these / it / its / each of them / ...; relative 'that' and 'the ones'
  are not anaphors) must reference an existing result, else it is not a candidate (-> CLARIFY if nothing remains);
- output_obligation_rule: an OUTPUT_REQUEST cue (return / give|hand ... back / hand over / report back / tell me|let me know + a quantity)
  obliges a plan ending in RETURN; the RETURNed result must match a named requested kind (R4). Checked per hypothesis and in whole-plan
  validation.
After V1.2: no further tuning; LOCKED_TEST only if every registered gate passes as written.
