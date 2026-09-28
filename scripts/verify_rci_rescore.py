"""Tier-1 check: recompute every RCI metric from the released records and compare with the released summaries.

python scripts/verify_rci_rescore.py

Copies experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1 to a temporary directory (the evaluator writes into its own tree),
runs `rci_evaluate.py --suite <s> --rescore` for dev_a, dev_b and locked_test (GOLD_TRACE, FORMAL_TEACH, D), and diffs every
per-arm value of RCI_SUMMARY.json. No hosted model, GPU or network is used. The config fingerprint is expected to differ from
the frozen one (dacd7a90...) because released files are path-sanitized and htg_evaluate.py carries the post-RCI teardown fix;
see PROVENANCE_SANITIZATION.json. The LOCKED summary is the as-recorded one; the strict teardown rescore is results/LOCKED_TEST.json."""
import os, sys, json, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "experiments", "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1")
SUITES = {"dev_a": None, "dev_b": None, "locked_test": "GOLD_TRACE,FORMAL_TEACH,D"}


def main():
    ok = True
    with tempfile.TemporaryDirectory() as d:
        cp = os.path.join(d, "rci"); shutil.copytree(SRC, cp, ignore=shutil.ignore_patterns("__pycache__"))
        for su, arms in SUITES.items():
            orig = json.load(open(os.path.join(SRC, "results", su, "RCI_SUMMARY.json")))
            cmd = [sys.executable, "rci_evaluate.py", "--suite", su, "--rescore"] + (["--arms", arms] if arms else [])
            rc = subprocess.call(cmd, cwd=cp, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            new = json.load(open(os.path.join(cp, "results", su, "RCI_SUMMARY.json")))
            n, diffs = 0, []
            for arm, M in orig["arms"].items():
                for k, v in M.items():
                    if k == "seconds": continue
                    n += 1
                    if json.dumps(v, sort_keys=True, default=str) != json.dumps(new["arms"].get(arm, {}).get(k), sort_keys=True, default=str): diffs.append(f"{arm}.{k}")
            ok &= rc == 0 and not diffs
            print(f"{su:12s} rc {rc}  values compared {n}  differences {len(diffs)} {diffs[:5]}")
    print("RESCORE_REPRODUCED" if ok else "RESCORE_MISMATCH"); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
