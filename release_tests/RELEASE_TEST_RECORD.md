# Release test record

All checks below ran on this repository's release tree before the initial commit. The content of that tree is exactly the initial release commit; its hash is recorded at the end of this file by a follow-up commit.

## Environment

| Item | Value |
|---|---|
| OS | Linux 6.16.3 x86_64 |
| Python | 3.10.12 (a local venv with torch 2.5.1+cu121, numpy 2.2.6, matplotlib 3.10.9, transformers 5.12.1); system `python3` for the stdlib-only scripts |
| Hosted models | none used; no network access needed |
| Date | 2026-09-28 |

## Results

| Check | Command | Result |
|---|---|---|
| Unit suites (8) | `scripts/run_tests.sh <venv python>` | **127 passed / 0 failed** of 127. E2E runtime 17/17, PDISC procedures 18/18, RCI-tree htg 15/15, nl_teach 18/18, pdx 10/10, procedures 18/18, rci 13/13, ttp 18/18 (`SUMMARY.json`) |
| RCI rescore from records | `python3 scripts/verify_rci_rescore.py` | **RESCORE_REPRODUCED**: dev_a 1049, dev_b 1049, locked_test 432 values; 0 differences |
| Worked-example dump | `python3 scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D` | byte-identical to `results/examples/dev_a-022-S15_D.md` |
| Paper numbers / tables / figures | `scripts/make_figures_tables.py` (venv python) | regenerated; `paper/SEMVM_PREPRINT.pdf` built with Tectonic 0.15.0 (23 pages) |
| Secret scan (two passes) | `python3 scripts/release_scan.py --known …` | **SCAN_CLEAN** (see `RELEASE_SECURITY_AUDIT.md`) |

Not run for this release: any hosted-model (tier 2) run, and full acquisition re-execution against the response caches (tier 3). See `docs/reproduction.md`.
