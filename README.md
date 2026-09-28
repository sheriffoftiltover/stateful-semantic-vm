# Stateful Semantic VM (SEMVM): external procedural distillation into verified procedural memory

**Headline.** A temporary gpt-oss-120b teacher taught procedures that were verified and stored in an external library. After the teacher was destroyed, a system whose only resident model is a frozen Qwen2.5-Coder-1.5B reused them, with no change to any neural weights. Across two independent development draws it exactly learned **70/72** target procedures with **0** wrong committed actions. The sealed LOCKED evaluation passed every behavioral acquisition, grounding, safety, and reuse criterion (**23/23** learned, **20/20** scenarios), but it failed the preregistered proof-of-teacher-disconnection condition: teardown was probed before the hosted endpoint had fully disappeared (HTTP 401 instead of the required 404). LOCKED is therefore **not a clean pass**.

| Question | Short answer |
|---|---|
| **What is this?** | Research code, preregistrations and raw evidence for SEMVM. It is a small frozen language model inside a deterministic runtime (SQLite world model + VM + procedure library). Neural models only *propose*; deterministic code *decides* what executes, what counts as evidence, and what gets activated. |
| **What was shown?** | Natural-language lessons from a hosted teacher were turned into sandboxed, committed traces. A deterministic anti-unifier then produced programs from those traces, and an evidence verifier checked each one. Only verified programs were activated in `procedures.sqlite`. They were then reused exactly after restarts, with new wording and unseen arguments, and with the teacher gone. See [paper](paper/SEMVM_PREPRINT.pdf) §5–§7. |
| **What is the caveat?** | LOCKED's teardown-verification gate failed as registered (401 race, §6 of the paper). LOCKED was not and will not be rerun. The domain is synthetic and bounded. |
| **Who does what?** | The verified procedure library *is* the capability. The temporary 120B model is the *acquirer*: it writes lessons and grounds each lesson line. The frozen 1.5B model is a fixed *retrieval front end*: after handoff it ranks procedure names and writes argument text behind deterministic checks. |
| **What is *not* claimed?** | The 1.5B model did not learn the 120B model's knowledge. This is not weight distillation. It is not open-domain continual learning, autonomous self-improvement, arbitrary program synthesis, indefinite scaling, or human-level generality. Library growth still needs a teacher. |
| **Where is the evidence?** | [`experiments/`](experiments/): seven as-run experiments with specs, locks, result JSONs, engineering logs and raw teacher/grounder/judge responses. [`examples/close_oldest_open_request/`](examples/close_oldest_open_request/) is one worked case, end to end. |
| **How do I run it?** | `scripts/run_tests.sh` (127 tests, no hosted model); `python scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D`. See [docs/reproduction.md](docs/reproduction.md). |
| **License / citation?** | **No license has been chosen yet**, so no LICENSE file is included and default copyright applies. To cite, see [CITATION.cff](CITATION.cff). |

The core claim, stated exactly: *the SEMVM system can accumulate externally stored procedural capability, acquired with assistance from a temporary teacher, without modifying the frozen student's neural weights. Continued growth of that library currently depends on access to a teacher or other source capable of supplying usable demonstrations.* The teacher is part of the acquisition causal chain, not the execution causal chain.

---

## Contents

- [Paper](#paper)
- [How it works (one paragraph)](#how-it-works-one-paragraph)
- [Results at a glance](#results-at-a-glance)
- [Quick start](#quick-start)
- [Repository layout](#repository-layout)
- [Integrity notes](#integrity-notes)
- [Citation](#citation)

## Paper

[`paper/SEMVM_PREPRINT.pdf`](paper/SEMVM_PREPRINT.pdf) is built from `paper/main.tex`. Every number, table and data figure in it is generated from the released JSON files by `scripts/make_figures_tables.py` (see `paper/generated/`).

## How it works (one paragraph)

1. **Teaching.** A hosted teacher writes a lesson: an `EXAMPLE:` line and `STEP:` lines.
2. **Grounding.** A transactional controller sends each line, one at a time, to a hosted grounder, which returns a typed plan. Deterministic checks validate the plan, and the controller executes it inside a sandboxed transaction.
3. **Clarification.** The controller asks structured questions when a reference is ambiguous or a line cannot be grounded.
4. **Commit.** A demonstration is committed only if it is complete. Aborted demonstrations contribute zero evidence.
5. **Learning.** From committed traces, a deterministic anti-unifier proposes candidate programs. A verifier tests each one: replay, counterfactual argument substitution, state perturbation, negative cases, rollback injection and determinism. Only a VERIFIED candidate, explicitly accepted, becomes ACTIVE.
6. **Handoff.** The hosted app is stopped, transcripts are removed, and credentials are scrubbed. A network guard blocks egress, and the student is restarted.
7. **Reuse.** New requests are ranked against ACTIVE procedures by the frozen 1.5B model, with argument and type checks. They are executed by the VM.

See [docs/architecture.md](docs/architecture.md).

## Results at a glance

| Experiment | Question | Result |
|---|---|---|
| END_TO_END_POC_V1 | frozen binder + deterministic runtime | RESULT A: LOCKED 20/20, DEV 29/30 (controlled language only) |
| PROCEDURE_DISCOVERY_POC_V1 | induce + verify + persist procedures | RESULT A: LOCKED_v2 20/20; the 1.5B model's direct proposals added nothing (0 of 32 discoveries) |
| NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1 | 1.5B grounds natural-language lessons | RESULT B + safety stop: learned .914, 1 wrong executed; LOCKED not run |
| LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1 | hosted 120B teacher | retention 54/54 given exact acquisition; teacher 24/36 vs scripted 33/36; LOCKED not run |
| HOSTED_TEACHER_GROUNDER_V1 | teacher × grounder 2×2 | Arm D 27/36, grounding 1.0, 2 wrong; "consistent evidence ≠ complete evidence"; LOCKED not run |
| TRANSACTIONAL_TEACHING_PROTOCOL_V1 | teaching as a transaction | Arm D 31/36, 0 wrong, every safety gate; RESULT D; LOCKED not run |
| **RECOVERY_CAPACITY_ISOLATION_V1** | pool 2→4, teacher tokens 4096→8192 | Arm D **70/72** pooled (36/36, 34/36); LOCKED 23/23 behaviorally, **teardown proof failed (401)** |

See [docs/experiment_lineage.md](docs/experiment_lineage.md) and [docs/limitations.md](docs/limitations.md).

## Quick start

```bash
git clone https://github.com/sheriffoftiltover/stateful-semantic-vm && cd stateful-semantic-vm
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt   # torch only needed for one suite
scripts/run_tests.sh "$(which python)"                                             # tier 1: 127 unit tests, no network
python scripts/show_scenario.py dev_a/dev_a-022-S15 --arm D                       # read one scenario and what arm D did
python scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D         # full evidence dump (identical to the checked-in one)
python scripts/make_figures_tables.py                                              # regenerate every paper number / table / figure
```

Tiers 2 and 3 (hosted teacher integration, and exact historical results from response caches) are described in [docs/reproduction.md](docs/reproduction.md).

## Repository layout

| Path | Contents |
|---|---|
| `paper/` | `main.tex`, `references.bib`, TikZ and matplotlib figures, generated tables, `SEMVM_PREPRINT.pdf` |
| `docs/` | architecture, experiment lineage, worked example, limitations, reproduction, artifact map, verification audit, project history |
| `experiments/<EXPERIMENT>/` | as-run code, `spec/` (preregistration + amendments), `locks/`, `scenarios/`, `results/`, raw evidence directories |
| `examples/close_oldest_open_request/` | the worked example (dev_a-022-S15, Arm D) as small text files |
| `scripts/` | `build_release.py` (how this tree was curated), `run_tests.sh`, `make_figures_tables.py`, `make_example_bundle.py`, `dump_case.py`, `show_scenario.py` |
| `release_tests/` | the release test record |
| `PROVENANCE_SANITIZATION.json` | original and released sha256 of every file whose text was changed for release |
| `RELEASE_SECURITY_AUDIT.md`, `RELEASE_NOTES.md`, `CITATION.cff` | release metadata |

The code under `experiments/` is **as run**, one copy per experiment. It is deliberately not refactored into a shared package, so that every freeze-manifest hash remains checkable. See [docs/artifact_map.md](docs/artifact_map.md).

## Integrity notes

- **Invalid and superseded runs are kept.** This includes TTP FINAL_DEV attempt 1 (`results/archive/final_dev_attempt1_INVALID`), the PDX and PDISC superseded DEV attempts, and the RCI Stage 0C wrong-app teardown. See paper §8.
- **Four frozen files carry documented post-run edits.** These are TTP Amendment 003 (two files), an HTG evaluator repair, and the post-RCI teardown fix. Every other frozen file matches its freeze manifest, and path sanitization is recorded file by file.
- **Sealed LOCKED sets that were never run have their contents withheld.** Their hash manifests are included.
- **The gate-deciding checks were audited** ([docs/verification_audit.md](docs/verification_audit.md)). The permissive-teardown class of bug occurs in two helpers; the permissive path was taken once (RCI LOCKED). "0 hosted calls" and "0 network attempts" are one measurement from an in-process network guard, which is instrumentation, not isolation. Two aggregate checks would pass on empty input, but never received empty input. No released number changes.

## Citation

```bibtex
@misc{anderson2026semvm,
  title  = {External Procedural Distillation: Natural-Language Teaching into Verified Procedural Memory with a Frozen Student},
  author = {Anderson, Matthew},
  year   = {2026},
  note   = {Preprint},
  url    = {https://github.com/sheriffoftiltover/stateful-semantic-vm}
}
```
