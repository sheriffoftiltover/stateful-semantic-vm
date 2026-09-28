# Project history (background, not evidence for the paper's claims)

The seven experiments in `experiments/` are the paper's evidence. Before them came about six weeks of preregistered experiments (2026-08-13 to 2026-09-26) that shaped the architecture. **Their code and results are not part of this release.**

This page summarizes them so a reader can see where the design came from. It is compiled from two sources:
- the author's consolidated state report of 2026-09-21, which covers about 115 specifications and 90 result reports;
- for Phase 12, the individual result reports. Several numbers from the consolidated report were checked against the original reports and are corrected where they differed (v2.2, v6C.2).

Numbers are quoted as those reports give them. They have not been re-verified against released artifacts, because those artifacts are not released. Treat everything here as background.

## The thesis that emerged

The programme started with a narrow question: can a small autoregressive model store a reusable reasoning procedure in few parameters, and spend inference compute instead? The early experiments showed that "reasoning failure" hides many different failures:
- semantic interpretation;
- reference binding;
- retrieval;
- exact state carry;
- identity resolution;
- completion detection;
- control flow;
- operator availability.

The experiments that followed separated these one at a time. The same pattern recurred at least six times: whenever a learned component was asked to do exact bookkeeping implicitly, it failed or shortcut; when that bookkeeping was made explicit and deterministic, the same or a smaller model succeeded.

This produced the thesis behind SEMVM:
- durable state, retrieval bookkeeping, dereferencing, composition and execution belong in an explicit deterministic runtime;
- neural components should be confined to interpretation;
- reusable knowledge can live in external memory rather than in weights.

## Phases

| Phase | Dates | What was asked | What was found (as reported) |
|---|---|---|---|
| 1. Synthetic autoregressive reasoning | 08-13 | Can a small model trade inference compute for parameters by generating an executable derivation? | Transition competence ≠ execution horizon; a token budget is permission to compute, not a policy for using it |
| 2. External associative memory | 08-27 to 08-30 | Can knowledge live in a hashed memory beside a small Transformer? | Concepts and transformations externalize as readable stored knowledge; part of the early advantage was lexical binding, and the controlled advantage is real but smaller |
| 3. Control / geometry / optimization ladder (V6-A to V12.2) | 08-31 | Why does in-episode derivation fail? | Attention supervision saturated with no execution gain; scaling degraded under a fixed recipe; the V9–V12 ceiling was undertraining (held-out triples 0.85 at 50 epochs; the replication was seed-variable) |
| 4. Macro-core, ml_next suite, neural instruction programme | 09-06 to 09-07 | Where do real-benchmark traces fail? | GSM8K free 0.376 vs oracle-state 0.990: state carry dominates. Knowledge scales with memory bytes, and reasoning saturates at the smallest core. A cross-namespace residual was localized to destination allocation, which is external bookkeeping |
| 5. Semantic front-end on GSM8K quantities | 09-09 to 09-10 | Can a small front-end map language onto a frozen symbolic operator set? | OP selection plateaued near 0.56; the grounding of real text, not symbolic execution, was the frontier |
| 6. Synthetic Stateful Semantic VM (v0–v4C.3) | 09-11 to 09-12 | Can a small controller act over explicit, durable state? | See [Query-mediated state](#query-mediated-state-the-direct-precursors) |
| 7. Human language and external knowledge (v5A) | 09-12 to 09-13 | Wikidata-scale knowledge behind a linker | Knowledge decoupling passed: 300 facts taught after freezing were queried and survived restart at 1.0 with zero optimizer steps. Read-path predicate grounding failed (0.20) |
| 8. Frozen code LLMs on SWE-bench (v6A–v6B.4) | 09-13 to 09-15 | Can frozen 0.5B–3B code models revise beliefs from evidence? | Evidence revision failed at every size; polarity was not legible from bounded strings, even to hosted 27B/120B judges |
| 9. Epistemic gaps, runtime predicates, real code (v6C–v6D) | 09-15 to 09-16 | Can a controller know when it is done? | Runtime completion/progress predicates lifted depth 5–12 episode success from 0.063 (v6C; 0.190 with semantic queries) to 1.0. BugsInPy navigation was 1.0 on held-out projects, but localization was partial |
| 10. Semantic compilation (v6E series) | 09-16 to 09-17 | Can language be compiled to canonical records that compose? | Identity and semantics are separable defects. Composition (S5) stayed at 0 across encoders, capacities and teacher data. Property satisfaction is a deterministic table once facts are canonical |
| 11. Latent-parser sequence (toy, real teacher prose, Corpus B) | 09-17 to 09-21 | Can a parser over frozen Qwen features learn typed records from records alone? | The toy language was solved by a chart parser (64/64 withheld). On real prose, fit was achieved (811/844 TRAIN), but semantic interpretation did not transfer to new language (withheld 0/59) |
| 12. Typed frontend, query-mediated state, binding (up to E2E) | 09-22 to 09-26 | See [Phase 12](#phase-12-2026-09-22-to-09-26) | Mid-layer typed readout transfers partially; query-mediated state is flat in store size; novel attachment is the residual; replay-trained binder handed to E2E |

## Query-mediated state: the direct precursors

These synthetic-phase results (Phase 6) are the most direct precursors of the paper's architecture. As reported in the 2026-09-21 state report:

- **v2: durable state at constant neural context.**
  - A SQLite store scaled from 1K to 1M records, with a learned retrieval planner (247K parameters) and a bounded-view binder (328K).
  - Final-state exactness was 1.000 at every scale, as a 3-seed mean; some controls and ablations are seed 0 only.
  - The round ablation showed iterative retrieval was necessary: 1 round → 0.25, 2 → 0.75, 3 → 1.00.
  - Caveat: the utterances were delexicalized.
- **v2.2: externalized retrieval bookkeeping.** Explicit runtime requirement state, with 0 new parameters, lifted 3-op all-required at 1M records from 0.929 to 1.000 (3-seed mean). The consolidated report's "0.51 → 1.00" does not appear in the v2.2 report and is corrected here.
- **v4B.1: typed queries.** Relational answers were 0.00 under a counterfactual switch. An explicit QUERY alone did not help; typed relation matching fixed it, and deterministic projection made it exact (0.00 → 1.00, 3 seeds, 256,932 parameters).
- **v4C: closed loop.** Query–response stayed at 1.0 for 64 turns, with the neural context bounded at about 24 tokens while the equivalent transcript grew to 1,306.
- **v4C.2.** Deterministic dereference of a focus handle fixed discourse reference, which had been at chance.

## Phase 12 (2026-09-22 to 09-26)

These are compiled from the individual result reports under the internal `decomposed_reasoning/results/` and `experiments/` trees, which are not released. Numbers are as reported.

### 12a. Qwen typed semantic frontend (09-22 to 09-23)

- **Eval corpus v2.** Frozen at 176 rows, all verifier-accepted.
- **Typed-query localization.**
  - Frozen Qwen2.5-Coder-0.5B block 11 (of 24) exposed the semantic fields to a typed-query decoder: 56–58/96 equivalent on fresh language, against 19/96 for the host parser.
  - The last layer gave 12–20.
- **Integration into the host parser.**
  - Full records rose from 12 to 39–40/96, and the envelope blocked the rest.
  - Record type accounted for 52% of that headroom. A deterministic modality→record-type map closed it (48/46/48, equal to the gold oracle).
  - Identifier copy failed on unseen suffixes. A start+continue copy matched the gold-name oracle (56/54/55).
- **Remaining semantic misses.** These were mostly in the property field.
  - Tuple-constrained decoding showed headroom (75–79).
  - A pairwise structured decoder, consistency losses and external paraphrase pretraining gave no fresh-language gain.
  - An LLM paraphrase-augmentation run was stopped by the user (provider token caps).
  - A compiler-scaling study stopped at its review gate (about 18 days of compute estimated).

### 12b. Query-mediated external world state (09-23 to 09-24)

- **Setup:** frozen Qwen-0.5B (block 12, about 315M active) plus a 3.24M typed-operation head reads and writes an external store through typed queries.
- **Results:**
  - End-to-end exact 0.985 (one seed).
  - A 512-entity store at 29.2 tokens/turn, against a context-stuffing baseline at 0.005 and 20,352 tokens. The report's correction notes that the baseline collapse is confounded with out-of-distribution length.
  - Delayed reads exact at 100 turns.
  - Held-out phrasing 0.367.
- **Phrasing-diversity follow-up.** It raised held-out phrasing from 0.49 to 0.82 (two seeds; some seed-29 fits below the original gate). It did not fix two-role pointer duplication (R10) or trajectory compounding.

### 12c. MTOP and attachment (09-24)

- **Typed span decomposition on MTOP English:**
  - tree exact 0.696, against flat baselines at 0.512 / 0.412;
  - novel combinations 0.167, against 0.711 seen.
- **Localization.** The residual is parent attachment under novel nesting (NEW 0.699 vs seen 0.98). It was flat across Qwen depth.
- **Interventions.** LoRA left NEW at 0.796, as did rare-pair oversampling and counterfactual recombination. An explicit dot-product binder was worse (0.657).

### 12d. Typed local structure and latent composition (09-24 to 09-25)

- **Oracle structure.** Oracle local types and supertags assemble exactly (Stage 0 tautology caveat noted). Learned local predictors failed their fit gates (L-C, SVA-C, SCM-C).
- **Latent typed composition:**
  - an explicit compositional interface beat a lexicalized one (0.690 vs 0.354); hard alignment reached 0.819;
  - the latent posterior collapsed to the all-singleton factorization;
  - temperature effects were seed-dependent;
  - the branch stopped (EARLY-IMPRINT-MIXED).

### 12e. Multi-relation identifiability and parent binding (09-25 to 09-26)

- **MRSI V1.** Stopped at its fit gate (ID_VAL 0.841–0.880 vs 0.95).
  - Localization: at least 99% of errors were attachment-parent, concentrated in mixed-attachment two-modifier items and before-both frames.
  - V1.1 corpus revision: no eligible candidate.
- **Parent-binding mechanism.**
  - The single-modifier fit failure was partly an early-stopping artifact on an ln 2 plateau.
  - A-002: SEED_DEPENDENT 2/3.
  - A-003Z: a P0-trained binder makes one sentence-level choice for both modifiers.
  - A-004: P2 fine-tuning learns independent binding with P0 forgetting.
  - A-005: 10–30% P0 replay preserves both (OUTCOME A, one seed).
- **Handoff to E2E.** The A-005 R20, seed 17, epoch 40 checkpoint became the frozen binder of END_TO_END_POC_V1. This is confirmed in that experiment's report, and the E2E experiment is included in this release.

## Cross-cutting findings carried into SEMVM

1. Make identity and bookkeeping explicit; keep semantics learned.
2. Reusable knowledge can live outside weights, but knowledge retrieval ≠ binding ≠ composition.
3. Inference compute is not a substitute for a control policy, and depth extrapolation is a question of where a representation is placed, not of capacity.
4. Measurement hygiene decided several verdicts:
   - symmetric foils and shortcut probes;
   - three-tier evidence rules;
   - dataset validity gates;
   - bit-exact resume checks;
   - correcting the executor's own claims.
