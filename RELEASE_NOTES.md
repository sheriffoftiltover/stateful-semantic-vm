# Release notes

## v1.0.1 (2026-09-28): review revisions

Changes made in response to an external critique. No experiment was rerun and no reported number changed.

- **New `docs/verification_audit.md`.** A read-only audit of every gate-deciding check:
  - the permissive teardown class occurs in two helpers (PDX, HTG/TTP/RCI), and its permissive path was taken once (RCI LOCKED);
  - "hosted calls" and "network attempts" are one measurement from an in-process guard;
  - two aggregate checks would pass on empty input, but never received empty input;
  - the oracle shares its parsing and hashing code with the runtime;
  - completeness is relative to the lesson, not to the goal.
- **Paper changes:**
  - the abstract and introduction name the three roles (the library is the capability, the 120B is the acquirer, the 1.5B is a fixed retrieval front end);
  - new subsection "Verifying the verification code";
  - the network guard is described as instrumentation;
  - the DEV draws are stated as carrying the causal claim;
  - the single-author / no-replication limitation moves to the top of the list, and three explicit limitation sentences are added;
  - future work is reordered: scaling, open-English reuse and cross-domain acquisition come first, alongside the cheap LOCKED replication, plus a boundary experiment where the teacher must invent the decomposition.
- **Docs:** README, limitations and architecture are updated to match.
- **Title unchanged** ("External Procedural Distillation …"); a retitle is under consideration.

## v1.0.0 (2026-09-28): initial public release

This is a clean, sanitized repository. It was curated from the author's internal experiment tree by `scripts/build_release.py`, and the internal git history is not included.

### Contents
- **Paper:** `paper/SEMVM_PREPRINT.pdf`, built from `paper/main.tex` and `paper/references.bib`, with TikZ and matplotlib figures and tables generated from the released JSONs.
- **Seven as-run experiments** (`experiments/`), each with its preregistration and amendments, locks, scenarios, results, engineering log and raw evidence:
  - END_TO_END_POC_V1
  - PROCEDURE_DISCOVERY_POC_V1
  - NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1
  - LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1
  - HOSTED_TEACHER_GROUNDER_V1
  - TRANSACTIONAL_TEACHING_PROTOCOL_V1
  - RECOVERY_CAPACITY_ISOLATION_V1
- **Worked example** `examples/close_oldest_open_request/`, plus `scripts/dump_case.py` / `scripts/show_scenario.py` for any RCI scenario.
- **Docs:** architecture, lineage, worked example, limitations, reproduction, artifact map, project history.

### Headline result (unchanged from the experiment records)
- RCI Arm D, pooled over two DEV draws: 70/72 learned, 58/60 scenarios, 62/64 distilled, 71/71 grounding; 0 wrong committed actions.
- The sealed LOCKED evaluation passed every behavioral acquisition, grounding, safety, and reuse criterion. It failed the preregistered proof-of-teacher-disconnection condition, because teardown was probed before the hosted endpoint had fully disappeared (HTTP 401 instead of 404). LOCKED is **not a clean pass** and is not rerun.

### Verified for this release
All verification ran on the release tree. The results are in `release_tests/`.
- `scripts/run_tests.sh`: 127/127 unit tests.
- `scripts/verify_rci_rescore.py`: every RCI metric recomputed from released records, 0 differences in 2530 values.
- `dump_case.py`: reproduces the checked-in dev_a-022-S15 dump byte-identically.
- Two-pass secret scan: clean (`RELEASE_SECURITY_AUDIT.md`).

### Changes relative to the internal tree
- Absolute paths were replaced with placeholders in 1170 text files. Original and released sha256 values are in `PROVENANCE_SANITIZATION.json`.
- One portability edit, recorded in the same file: the evaluators' hard-coded interpreter path became the `SEMVM_LLM_PYTHON` environment variable.
- Transient work directories, world snapshots, service logs and pid files were dropped. For RCI, the per-scenario acquisition records, procedure stores and reuse turns were kept.
- The contents of never-run sealed LOCKED sets (NL_TEACH, PDX, HTG/TTP) are withheld; their manifests are kept.

### Known issues
- Frozen-file hashes match their freeze manifests except for four documented post-run edits:
  - TTP `teacher/transactional.py` and `tests/test_ttp.py` (Amendment 003);
  - HTG `evaluator/behavior.py` (evaluator repair);
  - RCI `htg_evaluate.py` (post-RCI teardown fix, not used by any RCI run).
- The released config fingerprint therefore differs from the frozen `dacd7a90…`.
- **No license has been chosen**, so the repository has no LICENSE file.
