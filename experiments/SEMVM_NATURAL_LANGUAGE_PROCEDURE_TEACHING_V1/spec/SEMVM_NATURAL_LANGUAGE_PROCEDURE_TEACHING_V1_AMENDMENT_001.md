# SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1 — Amendment 001 (registered design decisions)

**Date:** 2026-09-26 (before any DEV run; items marked *DEV* were added during DEV engineering and are logged in `results/ENGINEERING_LOG.md`).
**Status:** binding for DEV and the one-time LOCKED_TEST run.

The spec leaves several implementation choices open. This amendment fixes each of them. None of them changes the frozen parent runtime.

## A1 — Frozen parent components
- `core/`, `procedure/`, `scenarios/oracle.py`, `scenarios/catalog.py` and the parent unit tests are copied byte-identically from `SEMVM_PROCEDURE_DISCOVERY_POC_V1`.
- The copy is hash-verified: `locks/PARENT_FROZEN_COMPONENTS.json`, 35 files, `identical_to_parent: true`.
- The parent unit tests pass in the copy.
- All new behaviour lives in `nlteach/`.

## A2 — Procedure abstraction is deterministic only (spec §1)
- The parent `System` runs with `use_llm=False`, so the frozen anti-unifier is the only procedure proposer.
- The LLM never proposes a procedure.

## A3 — Neural component and service (spec §9)
- **Model:** frozen `Qwen/Qwen2.5-Coder-1.5B` (base), fp16, eval mode, no optimizer. The same weight files as the parent; parameter hash `80aead4b…`.
- **Service:** `nlteach/nl_llm_service.py` is the parent service with its `/generate` and `/score` code byte-identical, so the parent retrieval stack is unchanged. It adds two read-only endpoints:
  - `/choose`: log P(option | prompt), exact under canonical tokenization, with a prompt KV-cache used for speed only;
  - `/generate_stop`: greedy decoding with an early stop.
- The service is stateless across requests in the sense that matters: results do not depend on cache state beyond fp16 noise.

## A4 — Role of the LLM in teaching: ranking legal typed options (spec §9.2, §13)
- Grounding is grammar-constrained beam search over `spec/NL_TEACH_ACTION_SCHEMA.json` (beam 3).
- The option set at every field is generated deterministically from four sources:
  - the frozen primitive inventory and ontology legality;
  - vocabulary values and registered type nouns that occur in the instruction;
  - type-compatible prior results of the current demonstration;
  - the ACTIVE procedure signatures.
- The LLM scores the options. The resulting best action list is the raw LLM proposal.
- A free-generation variant was tried as a prototype and rejected before DEV (ENGINEERING_LOG #0).
- The LLM can never:
  - emit an op outside the inventory;
  - emit a value that is not in the instruction;
  - mutate state, activate, or verify.

## A5 — Deterministic post-checks (spec §14, §15, §19, §69)
- The checks are:
  - static validation;
  - the registered reference grammar R0–R3 (`spec/NL_TEACH_LANGUAGE_V1.json`);
  - coverage (every mentioned PERSON / TIME / PLACE value and every named ACTIVE procedure must be used);
  - a margin test.
- Complete hypotheses with identical canonical outcomes are merged (log-sum-exp).
- If the best and the next *distinct* canonical outcome are within **MARGIN = 1.0 nats**, the result is CLARIFY. MARGIN was registered before DEV and is not tuned.
- A plural pronoun with at least two compatible lists is always CLARIFY. A singular pronoun resolves to the most recent compatible singular result (rule R3).

## A6 — Teaching session behaviour (spec §16–§18, §21, §42–§44, §50)
- **One transaction per utterance.** Only successfully executed steps enter the trace. Failed, clarified, unsupported and undone proposals remain provenance only.
- **Clarification.** A CLARIFY keeps the instruction pending. The next utterance is either:
  - an answer, which is appended to the instruction; or
  - a restatement starting with `I mean:`, which replaces it.
- **Correction.** Markers such as `No,` undo the previous grounded instruction (world restored from its snapshot) and ground the rest. `:undo` undoes only.
- **Teaching sandbox (spec §43, adopted).** At `:endteach` / `:endexample` / `:endrevise` the world is restored to the demonstration's start snapshot. This applies identically in GOLD_TRACE, FORMAL_TEACH and NL_TEACH, and in the oracle.
- **Second demonstration (spec §21).** An UNHINTED one-shot demonstration whose trace contains a PERSON / TIME / PLACE / TOPIC literal returns `REQUIRE_SECOND_DEMONSTRATION`. The trace is kept as example 1; the user continues with `:example` … `:endexample` and then `:learn`.
- **Provenance (spec §44).** Written per demonstration to `learn/teaching_traces/`: utterances, grounding, repairs, steps, state hashes, start-snapshot hash and trace hash.

## A7 — Name and hint leakage (spec §34, §65, §66)
- The grounding prompt never contains:
  - the name of the procedure being taught;
  - its header or hints;
  - the gold program or future demonstrations.
- So NAMED and OPAQUE grounding are identical by construction. The two strata can differ only through retrieval.
- **OPAQUE retrieval limitation.** The frozen parent retrieval ranks procedure names, so OPAQUE procedures are used only in single-procedure scenarios. There, retrieval is decided by a single candidate. This is reported, not hidden.
- HINTED and UNHINTED are separate strata. UNHINTED parameterization comes only from anti-unification over two traces.

## A8 — Evaluation modes (spec §53)
- **GOLD_TRACE:** each utterance's gold actions are executed through the same NL execution path (grounding bypassed).
- **FORMAL_TEACH:** the parent step language (`formal_turns`) through the parent step path.
- **NL_TEACH:** the full system.
- All three use the same frozen learner, verifier, store and retrieval.
- **Restarts.** In NL_TEACH, every RESTART kills and restarts both the scenario process and the LLM service (spec §46). In the two controls the scenario process is restarted; the LLM service, used there only for retrieval, is not.

## A9 — ASSISTED protocol and strict definitions (spec §41, §58, §60)
- **Simulated user.** It knows only the gold outcome of each utterance, which is its own intent. It gives at most ONE rescue per utterance:
  - an unexpected CLARIFY, UNSUPPORTED or failure gets the registered band-A restatement (`I mean: …`);
  - a wrong executed action gets `No, <restatement>`;
  - an execution where a clarification or rejection was expected gets `:undo`.
- **FIRST_PASS** counts nothing that needed a rescue.
- **Strict first-pass metrics:**
  - TEACH_TRACE_EXACT (per demonstration, no rescue);
  - ACTION_OP_EXACT and ACTION_ARGUMENT_EXACT_RAW (the raw LLM proposal);
  - ACTION_ARGUMENT_EXACT_AFTER_REPAIR (first-pass executed steps).
- **As-achieved metrics:**
  - LEARNED_PROCEDURE_EXACT (learned `program_hash` equals the gold program's);
  - NL_TEACH_SCENARIO_EXACT (the ASSISTED level; `_FIRST_PASS` is reported next to it).
- **WRONG_LLM_ACTION_EXECUTED (strict).** Counts every executed teaching step that differs from the gold action, whether in the first pass or in a rescue, and every execution where the gold was CLARIFY / UNSUPPORTED. Gate = 0. It is not restricted to wrongness the validator could have detected.

## A10 — LOCKED_TEST construction (spec §30, §62)
- LOCKED templates (`scenarios/templates_locked.json`) were written by an independent agent before DEV tuning. The experimenter never opened them or the generated LOCKED scenarios.
- They follow the same schema and language contract. The same agent's audit (`scenarios/LOCKED_TEMPLATE_AUDIT.json`, aggregate numbers only) found 0 of 172 strings overlapping DEV.
- LOCKED uses a separate seed and the parent's disjoint LOCKED request templates.
- If the generator changes during DEV, LOCKED is regenerated without inspection and re-frozen.

## A11 — Domain (spec §7)
- The parent world is used exactly, with the 13 parent procedure families plus the parent composite.
- No new entities, relations, primitives or effects.
- The domain convention that inner-event times live on the outer event (`PARENT.WHEN`) is encoded in the action grammar, registered in NL_TEACH_LANGUAGE_V1.
