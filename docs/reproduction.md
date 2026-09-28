# Reproduction

There are three tiers. Only tier 1 was re-executed for this release. What was run, and its results, is recorded in `release_tests/`.

## Tier 1 — fully local (no hosted model, no network, CPU is enough)

| Command | What it checks | Release result |
|---|---|---|
| `scripts/run_tests.sh [python]` | 8 unit suites: E2E runtime 17, PDISC procedures 18, and in the RCI tree htg 15, nl_teach 18, pdx 10, procedures 18, rci 13, ttp 18 | **127/127** (`release_tests/SUMMARY.json`) |
| `python scripts/verify_rci_rescore.py` | Recomputes every RCI metric from the released per-scenario records (acquisition records, procedure stores, reuse turns, judge labels) and diffs them against the released `RCI_SUMMARY.json` for DEV-A, DEV-B and LOCKED | **0 differences in 2530 values** |
| `python scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D` | Regenerates the worked-example dump from records | byte-identical to `results/examples/dev_a-022-S15_D.md` |
| `python scripts/make_example_bundle.py` | Rebuilds `examples/close_oldest_open_request/` | — |
| `python scripts/make_figures_tables.py` | Regenerates `paper/generated/*.tex`, `docs/generated_numbers.json` and the two data figures from the released JSONs | — |
| `cd paper && tectonic main.tex` | Builds the paper (any LaTeX distribution with TikZ, natbib and hyperref also works) | — |

Environment:
- The released numbers above were produced with Python 3.10.12, torch 2.5.1, numpy 2.2.6 and matplotlib 3.10.9 on Linux.
- Only the E2E binder test needs torch; the procedure and teaching suites use the standard library.

Two caveats for rescoring:
- **Config fingerprint.** It differs from the frozen value (`dacd7a90…`), because released files are path-sanitized and `htg_evaluate.py` carries the post-RCI teardown fix. `PROVENANCE_SANITIZATION.json` gives the original sha256 of every changed file, and those match the freeze manifests. The exceptions are four documented post-run edits: TTP `teacher/transactional.py` and `tests/test_ttp.py` (Amendment 003), HTG `evaluator/behavior.py` (the evaluator repair), and RCI `htg_evaluate.py` (the teardown fix).
- **LOCKED summary.** The rescored LOCKED summary is the *as-recorded* one. The strict teardown rescore that makes LOCKED not a clean pass is `results/LOCKED_TEST.json`.

## Tier 2 — teacher / grounder integration (hosted model required)

1. Serve **gpt-oss-120b** behind an OpenAI-compatible endpoint. The runs used:
   - checkpoint sha256 `0fc58fd2…` (per-file hashes in `SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1/locks/TEACHER_WEIGHTS_MANIFEST.json`);
   - vLLM 0.11.0 on one H100 via Modal, `max_model_len` 32768;
   - teacher reasoning high, T=0, `max_tokens` 8192; grounder reasoning low, 4096.
2. Download **Qwen/Qwen2.5-Coder-1.5B** for the local student service. Its weights hash is checked against the recorded `9b3db05b…`.
3. Set `TEACHER_URL` / `TEACHER_API_KEY` (never commit them), and optionally `SEMVM_LLM_PYTHON` for the student-service interpreter.
4. Run `rci_evaluate.py --suite <new suite>` on a newly generated scenario set.

The teardown helper in the released `htg_evaluate.py` is the corrected one: it polls until a real 404. The Modal deployment scripts assume a Modal account; adapt `teacher/modal_teacher.py` for other hosts.

Expect different responses: vLLM at temperature 0 is not bitwise repeatable. A new run is a replication, not a re-execution.

## Tier 3 — exact historical results

The experimental record is the set of role-scoped response caches, keyed by request hash:
- `initial_teacher_responses/`
- `recovery_teacher_responses/`
- `grounder_responses/`
- `judge_responses/`

plus the per-scenario records. Tier 1's rescore reproduces every reported metric from those records.

The client (`teacher/client.py`) replays a cached response whenever an identical request recurs. A full acquisition re-execution against the caches is therefore possible in principle, but it was **not** attempted for this release. It would also need the local student service on comparable hardware (the runs used an RTX 3060, fp16).

## Sealed sets

- **Withheld:** the contents of sealed LOCKED sets that were never run (NL_TEACH, PDX, HTG/TTP). Their manifests remain.
- **Released:** the RCI LOCKED set, which was run once. It shares the HTG template file (`scenarios/templates_htg_locked.json`), so the HTG/TTP sealed set should no longer be treated as blind.
- **Do not rerun LOCKED** for any experiment.
