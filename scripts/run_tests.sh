#!/usr/bin/env bash
# Run the unit-test suites of the final system (RCI directory, which carries the inherited suites) and of the two
# early proof-of-concept experiments, writing JSON results to release_tests/. No hosted model is needed.
# Usage: scripts/run_tests.sh [python]      (python defaults to python3; the EEP binder test needs torch)
set -u
PY=${1:-python3}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/release_tests"; mkdir -p "$OUT"
run () {  # dir suite
  local d="$ROOT/experiments/$1"; local s="$2"
  ( cd "$d" && timeout 1800 "$PY" "tests/$s.py" --out "$OUT/$1__$s.json" > "$OUT/$1__$s.log" 2>&1 ); echo "$1/$s -> rc $?"
}
for s in test_rci test_ttp test_htg test_pdx test_nl_teach test_procedures; do run SEMVM_RECOVERY_CAPACITY_ISOLATION_V1 "$s"; done
run SEMVM_PROCEDURE_DISCOVERY_POC_V1 test_procedures
run SEMVM_END_TO_END_POC_V1 test_runtime
"$PY" - "$OUT" <<'EOF'
import json, glob, os, sys
rows = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    if f.endswith("SUMMARY.json"): continue
    d = json.load(open(f)); n = d.get("n", d.get("total")); p = d.get("passed")
    fails = [k for k, v in (d.get("tests") or {}).items() if v not in ("PASS", True)]
    rows.append({"suite": os.path.basename(f)[:-5], "passed": p, "n": n, "failed": fails})
json.dump(rows, open(os.path.join(sys.argv[1], "SUMMARY.json"), "w"), indent=1)
for r in rows: print(f"{r['passed']:>3}/{r['n']:<3} {r['suite']}" + (f"  FAILED: {r['failed']}" if r["failed"] else ""))
print("TOTAL", sum(r["passed"] for r in rows), "/", sum(r["n"] for r in rows))
EOF
