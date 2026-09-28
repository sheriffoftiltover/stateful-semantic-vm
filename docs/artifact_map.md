# Artifact map

Everything under `experiments/` is as run (see `scripts/build_release.py` for the curation policy). Directory names match each experiment's preregistration.

| Experiment | Spec | Report | Key result files |
|---|---|---|---|
| `SEMVM_END_TO_END_POC_V1` | `spec/SEMVM_END_TO_END_POC_V1*.md` | `results/SEMVM_END_TO_END_POC_V1_REPORT.md` | `results/SEMVM_END_TO_END_POC_V1_RESULTS.json`, `traces/`, `results/example_traces/` |
| `SEMVM_PROCEDURE_DISCOVERY_POC_V1` | `spec/SEMVM_PROCEDURE_DISCOVERY_POC_V1*.md` | `results/PROCEDURE_DISCOVERY_REPORT.md` | `results/PROCEDURE_LOCKED_TEST.json`, `results/PROCEDURE_DEV.json` |
| `SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1` | `spec/` (+ amendments 001–003) | `results/NL_TEACH_REPORT.md` | `results/NL_TEACH_DEV.json`, `results/NL_TEACH_LOCKED_TEST.json` (manifest only) |
| `SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1` | `spec/` (+ amendment 001) | `results/GROQ_DISTILLATION_REPORT.md` | `results/GROQ_DISTILLATION_DEV.json`, `teacher_responses/`, `results/dev_run1_design_defect/`, `results/dev_run2_teacher_truncated/` |
| `SEMVM_HOSTED_TEACHER_GROUNDER_V1` | `spec/SEMVM_HOSTED_TEACHER_GROUNDER_V1.md` | `results/REPORT.md` | `results/DEV_FACTORIAL.json`, `teacher_responses/` (teacher + judge), `grounder_responses/`, `behavioral_equivalence/` |
| `SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1` | `spec/` | `results/REPORT.md` | `results/DEV_FACTORIAL.json`, `results/archive/final_dev_attempt1_INVALID/`, `slot_ledgers/`, `teaching_transactions/` |
| `SEMVM_RECOVERY_CAPACITY_ISOLATION_V1` | `spec/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1.md` + registered JSON specs | `results/REPORT.md` | `results/DEV_POOLED.json`, `results/{dev_a,dev_b,locked_test}/RCI_*.json`, `results/LOCKED_TEST.json`, `results/RECOVERY_CEILING_DIAGNOSTIC.json`, `results/examples/` |

Common subdirectories:
- **`locks/`:** freeze manifests with file sha256s, the config fingerprint, sealed-set manifests and the hosted checkpoint manifest.
- **`scenarios/`:** the generator, oracle, templates and the scenario sets that were run.
- **`*_responses/`:** cached hosted responses, keyed by request hash. These are the experimental record.
- **`teaching_traces/`, `slot_ledgers/`, `teaching_transactions/`, `recovery_events/`:** acquisition dialogue and controller state.
- **`procedure_verification/`, `procedure_store_snapshots/`:** candidates, verifier tests and library snapshots.
- **`handoff_audit/`, `network_audit/`:** teardown probes and network-guard logs.
- **`results/<suite>/work/<arm>/<sid>/`** (RCI only): `acq.json`, `procedures.sqlite` and `reuse_*.json`, which `dump_case.py` and the rescore read.
- **`results/<suite>/acq_artifacts/<arm>/<sid>/`** (RCI only): committed examples, candidates and student teaching traces.

**Not released:** transient work directories of the other experiments, world snapshots, student-service logs, pid files, and the contents of never-run LOCKED sets.
