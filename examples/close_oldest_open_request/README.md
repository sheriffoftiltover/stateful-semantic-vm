# Worked example: `close_oldest_open_request` (dev_a-022-S15, RCI Arm D)

A hosted gpt-oss-120b teacher taught this skill in natural language. The system learned it as a verified procedure and reused it after the teacher was destroyed. All files here are generated from the released records by `scripts/make_example_bundle.py`.

| File | Contents |
|---|---|
| `teacher_dialogue.txt` | The visible teacher dialogue: the lesson, the structured referent question, and the answer `REFERENT: r2` |
| `committed_trace.txt` | The one committed demonstration (the learning evidence) |
| `learned_procedure.txt` | The VERIFIED, ACTIVE program |
| `verifier_summary.json` | All three candidates with every verifier test; `active_pointer`; the library lifecycle log |
| `reuse_summary.txt` | Post-handoff requests across two restarts, compared with the oracle |

To see everything, including the raw grounder JSON, slot ledger, transaction record and every DB table, run:

```bash
python scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D
```

The same dump is checked in at `experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1/results/examples/dev_a-022-S15_D.md`.

**Caveats:**
1. Frank had only one open request, so the clarification supplied identifying information that behavioral evidence could not.
2. Only Trent was a positive reuse case, so ordering at reuse time is untested.

See [docs/worked_example.md](../../docs/worked_example.md).
