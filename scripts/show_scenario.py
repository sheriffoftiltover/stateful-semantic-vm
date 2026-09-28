"""Convenience wrapper: readable view of one RCI scenario (and optionally what an arm did).

python scripts/show_scenario.py dev_a/dev_a-022-S15 [--arm D]
Paths are relative to experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1/scenarios/ (".json" optional)."""
import os, sys, subprocess

EXP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1")
a = sys.argv[1:]
if a and not a[0].startswith("-"):
    p = a[0] if a[0].endswith(".json") else a[0] + ".json"
    a[0] = p if os.path.exists(p) else os.path.join(EXP, "scenarios", p)
sys.exit(subprocess.call([sys.executable, os.path.join(EXP, "show_scenario.py")] + a, cwd=EXP))
