"""Curate the public release tree from the internal experiment tree (run once by the author; kept for transparency).

python scripts/build_release.py --src <internal LLM-Experiment root> --dst <this repository root>

Policy (see RELEASE_SECURITY_AUDIT.md and docs/reproduction.md):
  * as-run code, specs, locks, tests, reports, engineering logs, summary / per-arm result JSON, scenario generators and the
    scenarios that were actually run, and the raw evidence directories (teacher / grounder / judge responses, slot ledgers,
    transactions, teaching traces, recovery events, verification records, procedure-store snapshots, handoff / network audits);
  * NOT: transient work directories, world snapshots, student-service logs, pid files, __pycache__;
  * NOT: the contents of sealed LOCKED sets that were never run (their hash manifests ARE included, so they stay usable as blind sets);
  * every text file has absolute machine paths replaced by placeholders; PROVENANCE_SANITIZATION.json records, per modified
    file, the original sha256 (the value the freeze manifests refer to), the released sha256 and the number of substitutions."""
import os, sys, json, shutil, hashlib, argparse, re, fnmatch

LINEAGE = ["SEMVM_END_TO_END_POC_V1", "SEMVM_PROCEDURE_DISCOVERY_POC_V1", "SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1",
           "SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1", "SEMVM_HOSTED_TEACHER_GROUNDER_V1", "SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1",
           "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1"]
RAW_DIRS = {"teacher_responses", "initial_teacher_responses", "recovery_teacher_responses", "grounder_responses", "judge_responses", "slot_ledgers",
            "teaching_transactions", "teaching_traces", "teacher_transcripts", "recovery_events", "procedure_verification", "procedure_store_snapshots",
            "handoff_audit", "network_audit", "behavioral_equivalence", "traces"}
CODE_DIRS = {"core", "procedure", "student", "teacher", "evaluator", "netguard", "environment", "spec", "locks", "tests", "nlteach", "neural", "ir", "vm",
             "state", "resolver", "render", "backends", "learning", "scenarios"}
DROP_NAMES = {"__pycache__", "work", "acq_artifacts", "jobs", "snapshots", "learn", "learn_reuse"}
DROP_GLOBS = ["*.pid", "student_service_*.log", "llm_service*.log", "repl_world.sqlite", "*.pyc", "db_FULL*", "db_GOLD_IR"]
# sealed LOCKED sets that were NEVER run: withhold contents (manifests stay)
NEVER_RUN_LOCKED = {
    "SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1": ["scenarios/locked_test", "scenarios/templates_locked.json"],
    "SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1": ["scenarios/locked_test", "scenarios/templates_pdx_locked.json", "scenarios/archive"],
    "SEMVM_HOSTED_TEACHER_GROUNDER_V1": ["scenarios/locked_test"],
    "SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1": ["scenarios/locked_test"],
}
# the only code edit made for the release: the evaluators' hard-coded interpreter path becomes an environment variable
PORTABILITY = (re.compile(r'^LLM_PY = "[^"]*"', re.M), 'LLM_PY = os.environ.get("SEMVM_LLM_PYTHON", sys.executable)  # release portability edit (was an absolute venv path)')
TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".log", ".txt", ".sh", ".cfg", ".toml", ".yaml", ".yml", ".tex", ".bib", ".csv", ".tsv", ""}


def subs_for(src):
    home = os.path.expanduser("~"); ml = os.path.dirname(src.rstrip("/"))
    return [(src.rstrip("/"), "$SEMVM_INTERNAL_ROOT"), (ml, "$ML_ROOT"), (home, "$HOME"),
            (re.compile(r"/tmp/claude-\d+/[^\s\"']*"), "$JOB_TMP"), (re.compile(r"/home/[a-z0-9_-]+/\.claude/jobs/[0-9a-f]+"), "$JOB_DIR")]


# RCI only: the per-scenario acquisition records that dump_case.py reads (no world snapshots, no student logs)
RCI = "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1"
RCI_WORK = ("acq.json", "procedures.sqlite")


def rci_evidence(parts):
    # results/<suite>/work/<arm>/<sid>/{acq.json, procedures.sqlite, reuse_*.json}
    if len(parts) == 6 and parts[0] == "results" and parts[2] == "work":
        return parts[5] in RCI_WORK or fnmatch.fnmatch(parts[5], "reuse_*.json")
    # results/<suite>/acq_artifacts/<arm>/<sid>/{examples.json, targets.json, candidates/*, teaching_traces/*}
    if parts[0] == "results" and len(parts) >= 6 and parts[2] == "acq_artifacts":
        return (len(parts) == 6 and parts[5] in ("examples.json", "targets.json")) or (len(parts) == 7 and parts[5] in ("candidates", "teaching_traces"))
    return False


def dropped(rel, exp):
    parts = rel.split("/")
    if exp == RCI and rci_evidence(parts): return False
    if any(p in DROP_NAMES for p in parts): return True
    if any(fnmatch.fnmatch(parts[-1], g) for g in DROP_GLOBS): return True
    for w in NEVER_RUN_LOCKED.get(exp, []):
        if rel == w or rel.startswith(w + "/"): return True
    top = parts[0]
    if len(parts) == 1: return not (parts[0].endswith((".py", ".md", ".json", ".txt")) and not parts[0].endswith(".sqlite"))
    if top in CODE_DIRS or top in RAW_DIRS: return False
    if top == "results":
        # results/<file>, results/<run>/<file>, results/<run>/<sub>/<file> for small evidence subdirs (examples, example_traces, preflight arms)
        if len(parts) <= 3: return False
        # archived (invalid / superseded) runs: keep their top-level summaries, diagnostics and logs, not their bulk work dirs
        if parts[1] == "archive" and len(parts) == 4: return False
        return parts[1] not in ("examples", "example_traces", "preflight")
    return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); ap.add_argument("--dst", required=True); a = ap.parse_args(); a.src = os.path.abspath(a.src); a.dst = os.path.abspath(a.dst)
    src_exp = os.path.join(a.src, "experiments"); dst_exp = os.path.join(a.dst, "experiments"); subs = subs_for(a.src)
    prov = {"policy": __doc__.split("Policy")[1].strip(), "files": {}, "withheld_never_run_locked": NEVER_RUN_LOCKED}; n_files = 0; n_bytes = 0
    for exp in LINEAGE:
        root = os.path.join(src_exp, exp)
        for dp, dns, fns in os.walk(root):
            in_rci_results = exp == RCI and os.path.relpath(dp, root).split("/")[0] == "results"
            dns[:] = [d for d in dns if d not in DROP_NAMES or (in_rci_results and d in ("work", "acq_artifacts"))]
            for fn in fns:
                full = os.path.join(dp, fn); rel = os.path.relpath(full, root)
                if dropped(rel, exp): continue
                out = os.path.join(dst_exp, exp, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
                raw = open(full, "rb").read(); ext = os.path.splitext(fn)[1]
                if ext in TEXT_EXT:
                    try: txt = raw.decode("utf-8")
                    except UnicodeDecodeError: txt = None
                    if txt is not None:
                        n = 0; port = False
                        if fn in ("evaluate.py", "pdx_evaluate.py"):
                            txt, k = PORTABILITY[0].subn(PORTABILITY[1], txt); n += k; port = bool(k)
                        for pat, rep in subs:
                            if isinstance(pat, str): n += txt.count(pat); txt = txt.replace(pat, rep)
                            else: txt, k = pat.subn(rep, txt); n += k
                        if n:
                            new = txt.encode("utf-8")
                            prov["files"][f"experiments/{exp}/{rel}"] = {"original_sha256": hashlib.sha256(raw).hexdigest(), "released_sha256": hashlib.sha256(new).hexdigest(), "substitutions": n}
                            if port: prov["files"][f"experiments/{exp}/{rel}"]["portability_edit"] = "LLM_PY absolute interpreter path -> SEMVM_LLM_PYTHON env var (default: current interpreter)"
                            raw = new
                open(out, "wb").write(raw); n_files += 1; n_bytes += len(raw)
        # the internal spec document for each experiment lives at the internal root
        spec = os.path.join(a.src, exp + ".md")
        if os.path.exists(spec) and not os.path.exists(os.path.join(dst_exp, exp, "spec", exp + ".md")):
            os.makedirs(os.path.join(dst_exp, exp, "spec"), exist_ok=True); shutil.copy(spec, os.path.join(dst_exp, exp, "spec", exp + ".md")); n_files += 1
    json.dump(prov, open(os.path.join(a.dst, "PROVENANCE_SANITIZATION.json"), "w"), indent=1)
    print(json.dumps({"files": n_files, "MB": round(n_bytes / 1e6, 1), "sanitized_files": len(prov["files"])}))


if __name__ == "__main__":
    main()
