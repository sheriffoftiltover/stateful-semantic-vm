#!/usr/bin/env python3
"""Canonical launcher (spec §28): python3 launch.py --backend local|modal --job poc-eval|poc-unit [--suite dev]
Backend code controls only provisioning / mounting / lifecycle / artifact transfer (backends/). Modal runs are CPU-only (profile cpu-small)."""
import os, sys, json, glob, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, os.path.join(ROOT, "backends"))
from jobspec import JobSpec
PROFILES = json.load(open(os.path.join(ROOT, "backends", "profiles.json")))["profiles"]
RATES = {"gpu": {}, "cpu_core": 0.0000131, "mem_gib": 0.00000222}


def next_id(prefix):
    n = len(glob.glob(os.path.join(ROOT, "results", "jobs", prefix + "_attempt_*"))) + 1; return f"jobs/{prefix}_attempt_{n:03d}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", choices=["local", "modal"], default="local"); ap.add_argument("--job", required=True, choices=["poc-eval", "poc-unit"]); ap.add_argument("--suite", default="dev"); a = ap.parse_args()
    spec = JobSpec(job_id=next_id(f"{a.job}_{a.suite}_{a.backend}" if a.job == "poc-eval" else f"{a.job}_{a.backend}"), job_type=a.job, args={"suite": a.suite} if a.job == "poc-eval" else {}, profile="cpu-small")
    if a.backend == "local":
        from backends.local import LocalBackend
        res = LocalBackend(ROOT, PROFILES).map([spec])
    else:
        from backends.modal_backend import ModalBackend
        be = ModalBackend(ROOT, PROFILES, "semvm-poc-v1", "semvm-poc-v1-results", RATES)
        with be: res = be.map([spec])
        be.collect([spec.job_id])
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
