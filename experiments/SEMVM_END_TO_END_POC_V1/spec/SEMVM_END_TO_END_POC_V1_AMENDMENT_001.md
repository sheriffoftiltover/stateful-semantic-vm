# SEMVM_END_TO_END_POC_V1: Amendment 001 (input-language boundary)

**Registered:** 2026-09-26, by the user's ruling, **before any implementation**. The machine-readable contract is `spec/SEMVM_POC_LANGUAGE_V1.json`.

## Why
The frozen binder (A-005 R20, seed 17, epoch 40, sha `3f23d13c…`) reads only its trained controlled language. It does **not** read English:
- its 117-token vocabulary lacks "me", "tomorrow", "Friday", "office", "Who", "Actually" and similar words;
- parent attachment is signalled by **coindexation tags**, because every modifier names its parent's tag;
- it covers exactly one outer and one inner event, with at most two modifiers.

The English examples in the V1 spec (§5.4, §14, §15, §41–§45) are therefore **not** supported inputs.

## SEMVM_POC_LANGUAGE_V1: two input surfaces
**A. CONTROLLED ASSERTION LANGUAGE → frozen neural binder → canonical IR.**
- **Strings:** exactly those the locked generator (`mr_generate.render`) produces. There are:
  - 32 single-modifier layouts, the P0 envelope with no before-both slots;
  - 4 two-modifier `straddle_o` layouts, the P2 envelope;
  - phrase formats fa / fb;
  - (relation, OUTER, INNER) restricted to the 29 triples where the relation is valid on both events.
- **The tags are part of the input,** exactly as in training. **No deterministic component infers or inserts tags or decides attachment.**
- **Envelope check:** the layout is identified from the function-word skeleton only. The check never looks at which tag a modifier carries.

**B. DETERMINISTIC COMMAND / QUERY LANGUAGE (SEMVM_CMD_V1) → deterministic parser → VM.** It is never neural.
```
QUERY <REL> OF <TARGET> [WHERE <SCOPE>.<REL>=<VALUE>]*    SCOPE ∈ SELF | PARENT | CHILD
UPDATE <REF> <REL>=<VALUE> [<REL>=<VALUE>]*               functional replace, one transaction
RETRACT <REF> <REL>
DELETE <REF>
NEW PERSON <NAME>                                          explicit creation of a distinct same-alias person
TARGET = event type (all active events of that type) | REF
REF    = LAST_<EVENT_TYPE>                                 most recently created active event of that type
```

## Unsupported (→ `UNSUPPORTED_INPUT`, no mutation, no transformation)
Unsupported inputs are:
- ordinary English;
- more than 2 modifiers;
- more than 2 events;
- unknown vocabulary;
- unsupported relations or relation × constructor combinations;
- layouts outside the envelope, including BEFORE_BOTH and format fc;
- arbitrary discourse / pronoun syntax.

**No English → controlled rewriter is used.** It would have to insert the tags, i.e. perform the binding itself.

## Literal examples (from the locked generator, **envelope-checked**)
**Correction (2026-09-26, after the POC run, found while building `repl.py`).** The first version of this table used WHEN on REMINDER. That is a V1 withheld cell, so it lies outside the supported triples, and the envelope correctly rejects those strings. The examples were rendered by the generator but not envelope-checked. They are replaced below with strings produced by `scenarios/generate.py` `Gen.assertion` (which enforces the envelope), and each was verified to pass `envelope.check`. **No scenario, result or registered rule was affected;** the DEV / LOCKED suites were always envelope-checked at generation.

| ENGLISH GLOSS (NOT MODEL INPUT) | ACTUAL POC ASSERTION INPUT |
|---|---|
| "Request a call with Alice" (WHO → CALL) | `call epsilon ; and then , by Alice per epsilon , request theta` |
| "Request at 5 that someone calls" (WHEN → REQUEST) | `request zeta : so then again soon , call theta ; at 5 re zeta` |
| "Bob requests at noon that someone calls" (WHEN, WHO → REQUEST) | `request epsilon at noon per epsilon , and after that then , call gamma and by Bob re epsilon` |
| "Request at 3 a call with Alice" (WHEN → REQUEST, WHO → CALL; mixed OI) | `request theta : at 3 re theta ; so then again soon , call alpha ; by Alice per alpha` |
| same semantics, other slot order (WHO → CALL, WHEN → REQUEST; mixed IO) | `request eta by Alice re beta , and after that then , call beta and at 3 re eta` |

| ENGLISH GLOSS (NOT INPUT) | ACTUAL COMMAND |
|---|---|
| "Who is the call with (for the request at 3)?" | `QUERY WHO OF CALL WHERE PARENT.WHEN=3` |
| "Actually make that noon." | `UPDATE LAST_REQUEST WHEN=noon` |
| "Forget who the call is with." | `RETRACT LAST_CALL WHO` |
| "Delete that request." | `DELETE LAST_REQUEST` |

## RESULT-E: English interface gap (descriptive only)
A small set of ordinary-English paraphrases of supported semantics is fed to the frozen binder **without preprocessing**. The report records OOV behaviour, parse success / failure, IR exact, and binding where meaningful. The result does not count against the POC, and nothing is tuned after it.

## Revised claim (V1)
> A frozen small neural binder can translate its trained controlled compositional language into canonical semantic state, including multiple independent relation bindings, and that state can participate in persistent deterministic computation across turns.

V1 does **not** claim general English understanding, natural-language querying, or arbitrary discourse understanding.

## Other registered implementation choices (made before scenarios exist)
- **TIME** values are the binder's clock and named values, normalized deterministically (digits → `HH:MM`, named → `NOON / MIDNIGHT / DAWN / DUSK`). A per-scenario reference timestamp is recorded, but V1 has no relative dates. The §10 date examples are unsupported.
- **Relation count (§19.1 S5):** "three or more simultaneous relations" is realized as TODO plus two modifiers across the two events. Four modifiers (WHO + WHEN + WHERE + TOPIC) in one assertion are outside the envelope, so that version of S5 is **UNSUPPORTED** (a deviation).
- **Entities:** persons are resolved by exact alias:
  - 0 matches → create;
  - 1 match → reuse;
  - ≥ 2 matches → `RESOLUTION_AMBIGUOUS`, with no mutation.
- **Scalars:** TIME, PLACE and TOPIC values are scalars with deterministic natural keys.
- **Events:** each assertion creates a new outer and a new inner event.
- **P3 / BEFORE_BOTH (§26):** a separate optional diagnostic. It is not run unless time permits, and it is never part of acceptance.
- **Gates:** the acceptance gates, GOLD_IR control, DEV / LOCKED_TEST discipline, restart, rollback and trace requirements are **unchanged** from the V1 spec.
