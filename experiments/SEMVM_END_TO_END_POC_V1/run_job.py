#!/usr/bin/env python3
"""Single entry point for every backend (spec §28): python run_job.py --spec-json '<JobSpec>' --output <dir> [--backend-label local|modal]
Job types: poc-eval {suite: dev} -> evaluate.py --suite <suite> --work <output>   (LOCKED_TEST is run once, locally, at M7; never re-run here)
           poc-unit {}          -> tests/test_runtime.py --out <output>/UNIT_TESTS.json
No semantic branching on the backend; the label is provenance only."""
import os, sys, json, time, subprocess, argparse, hashlib, glob, platform
HERE = os.path.dirname(os.path.realpath(__file__))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--spec-json", required=True); ap.add_argument("--output", required=True); ap.add_argument("--backend-label", default="local"); a = ap.parse_args()
    spec = json.loads(a.spec_json); out = os.path.abspath(a.output); os.makedirs(out, exist_ok=True); t0 = time.time(); A = spec["args"]
    if spec["job_type"] == "poc-eval":
        if A["suite"] != "dev": raise SystemExit("STOP — only DEV may be run through backend jobs (LOCKED_TEST: run once at M7)")
        cmd = [sys.executable, os.path.join(HERE, "evaluate.py"), "--suite", "dev", "--work", out]
    elif spec["job_type"] == "poc-unit": cmd = [sys.executable, os.path.join(HERE, "tests", "test_runtime.py"), "--out", os.path.join(out, "UNIT_TESTS.json")]
    else: raise SystemExit(f"unknown job_type {spec['job_type']}")
    r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    man = {"job_id": spec["job_id"], "job_type": spec["job_type"], "args": A, "backend": a.backend_label, "rc": r.returncode, "wall_s": round(time.time() - t0, 1), "python": platform.python_version(), "machine": platform.machine(),
           "stdout_tail": r.stdout[-3000:], "stderr_tail": r.stderr[-3000:]}
    files = sorted(p for p in glob.glob(os.path.join(out, "**", "*"), recursive=True) if os.path.isfile(p))
    man["artifacts_sha256"] = {os.path.relpath(p, out): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files if not p.endswith(".sqlite")}
    json.dump(man, open(os.path.join(out, "RUN_MANIFEST.json"), "w"), indent=1); print("RUN_JOB_DONE", json.dumps({k: man[k] for k in ("job_id", "rc", "wall_s")})); sys.exit(r.returncode)


if __name__ == "__main__":
    main()
