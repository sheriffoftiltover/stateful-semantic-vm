"""Convenience wrapper: full evidence dump for one RCI scenario x arm from the released records (read-only).

python scripts/dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D [--out FILE]

Runs experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1/dump_case.py (the as-run tool). Without --out it prints to stdout
instead of overwriting the checked-in dump in results/examples/."""
import os, sys, subprocess, tempfile

EXP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1")
args = sys.argv[1:]
if "--out" in args:
    sys.exit(subprocess.call([sys.executable, os.path.join(EXP, "dump_case.py")] + args))
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "dump.md"); rc = subprocess.call([sys.executable, os.path.join(EXP, "dump_case.py")] + args + ["--out", out], stdout=subprocess.DEVNULL)
    if rc == 0: sys.stdout.write(open(out).read())
    sys.exit(rc)
