# SEMVM_END_TO_END_POC_V1

This is a frozen neural binder (A-005 R20) plus a deterministic persistent semantic VM. The input language is `spec/SEMVM_POC_LANGUAGE_V1.json` (Amendment 001).

**Python:** use the interpreter built from `environment/requirements-lock.txt`.

```
python repl.py [--db my_world.sqlite]        # interactive shell: type assertions / commands; :example OI for a valid assertion
python tests/test_runtime.py                     # deterministic runtime unit suite (17 tests)
python tests/neural_regression.py                # binder regression vs the source A-005 evaluation (needs the source experiment)
python evaluate.py --suite dev                   # neural pass + FULL / GOLD_IR replay + metrics -> results/dev/EVAL.json, traces/dev/
python tests/result_e_english_probe.py           # RESULT-E (descriptive)
python3 launch.py --backend local|modal --job poc-eval --suite dev
```
- **LOCKED_TEST** (`scenarios/locked_test/`) was run once, at M7. Do not re-run it for development.
- **The report** is `results/SEMVM_END_TO_END_POC_V1_REPORT.md`.
