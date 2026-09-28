# Limitations

These are the limitations of what was observed. Future work, which is not a result, is listed separately at the end.

## Limitations

- **Synthetic, bounded domain.**
  - One personal-organizer world and a 21-primitive step language.
  - Curricula are drawn from 13–15 procedure families plus composites.
  - Reuse requests are controlled paraphrases, not open English.
- **Small samples.**
  - 36 targets per DEV draw and 23 in LOCKED.
  - A perfect LOCKED score is consistent with an error rate of a few percent per target. Intervals quoted anywhere are descriptive only; no significance tests.
- **LOCKED is not a clean pass.** The preregistered proof-of-teacher-disconnection condition failed: the probe returned HTTP 401 instead of 404. Under the strict rule, DISTILLED_SKILL_EXACT and TEACHER_DISCONNECT_REUSE are 0. LOCKED is not rerun.
- **Strict structural metric.**
  - LEARNED_PROCEDURE_EXACT requires hash identity with a reference program.
  - Behaviorally equivalent alternatives therefore count as failures.
- **Where the understanding sits.**
  - In the final configuration the hosted 120B model both teaches and grounds lesson lines during acquisition.
  - The frozen 1.5B model interprets requests after handoff, behind deterministic checks.
  - Nothing here shows that the 1.5B model understands lessons. NL_TEACH, where it did the grounding, failed its gates.
- **Teacher dependence.** Growing the library requires a teacher or another source of usable demonstrations; the student cannot produce a demonstration for a skill it lacks.
- **One hosted model family.** The teacher, grounder and judge are one frozen checkpoint in separate roles.
- **Serving is not bitwise repeatable.** vLLM at temperature 0 does not reproduce responses bit for bit, so the response caches are the experimental record.
- **DEV reuse.**
  - DEV sets were used for engineering within experiments, notably NL_TEACH's three iterations. DEV numbers there are optimistic.
  - RCI used two fresh draws with no change between them.
- **Worked-example caveats (dev_a-022-S15).**
  - Frank had only one open request, so the clarification supplied identifying information that behavioral evidence could not.
  - Only Trent was a positive reuse case, so ordering at reuse time is untested.
- **Released blind sets.**
  - HTG and TTP share a sealed LOCKED set that was never run; its contents are withheld.
  - That set was generated from the same template file as the RCI LOCKED set, which is released. Treat it as no longer blind.
- **Scale and replication.**
  - Single-author research.
  - Hosted spend was about $14.6 in total across four experiments.
  - No external replication yet.

## Future work (hypotheses and plans only)

1. A clean LOCKED replication on a newly sealed set, using the corrected teardown helper.
2. A behavioral learned-exact metric, registered before a fresh DEV.
3. Evidence-diversity requirements, e.g. multi-element witnesses for SORT/FIRST skills.
4. Other teacher sources: humans, other models, documentation.
5. Larger, less templated domains and English requests.
6. Library scaling: retrieval among hundreds of procedures, re-teaching and versioning, and deeper composition.
