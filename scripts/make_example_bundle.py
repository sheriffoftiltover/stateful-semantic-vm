"""Build examples/close_oldest_open_request/ from the released RCI records (read-only; no hosted model needed).

python scripts/make_example_bundle.py

Every file it writes is copied or re-formatted from these sources in experiments/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1/:
  teaching_traces/dev_a/D/dev_a-022-S15.json                     hosted teacher dialogue + call provenance
  results/dev_a/acq_artifacts/D/dev_a-022-S15/examples.json       committed trace
  results/dev_a/acq_artifacts/D/dev_a-022-S15/candidates/*.json   candidates and verifier tests
  results/dev_a/work/D/dev_a-022-S15/procedures.sqlite            ACTIVE record
  results/dev_a/RCI_D.json, results/dev_a/HANDOFF.json            post-handoff reuse
The full dump (grounder JSON, slot ledger, transaction, every DB table) is results/examples/dev_a-022-S15_D.md, produced by dump_case.py."""
import os, sys, json, glob, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "experiments", "SEMVM_RECOVERY_CAPACITY_ISOLATION_V1")
sys.path[:0] = [os.path.join(EXP, "procedure")]
import lang as L  # noqa: E402

SID, SU, ARM = "dev_a-022-S15", "dev_a", "D"
OUT = os.path.join(ROOT, "examples", "close_oldest_open_request")


def main():
    os.makedirs(OUT, exist_ok=True)
    R = os.path.join(EXP, "results", SU); ART = os.path.join(R, "acq_artifacts", ARM, SID); W = os.path.join(R, "work", ARM, SID)
    T = json.load(open(os.path.join(EXP, "teaching_traces", SU, ARM, SID + ".json")))
    # teacher dialogue (visible messages only; the teacher's hidden reasoning is not part of the protocol)
    lines = []
    for tg in T["targets"]:
        lines.append(f"# target {tg['name']}: final status {tg['status']}\n# system prompt = teacher card (teacher/protocol.py; sha in locks/FINAL_CONFIG_FREEZE.json)\n")
        for m in tg["transcript"][1:]:
            lines.append(("=== TEACHER" if m["role"] == "assistant" else "=== STUDENT -> TEACHER") + "\n" + m["content"].rstrip() + "\n")
        lines.append("# teacher-call provenance")
        for l in tg["teacher_log"]:
            pv = l.get("provenance") or {}
            lines.append(f"# {l['kind']}: role {pv.get('role')}, request {str(pv.get('request_hash'))[:16]}, tokens in/out {pv.get('input_tokens')}/{pv.get('output_tokens')}, finish {pv.get('finish_reason')}")
    open(os.path.join(OUT, "teacher_dialogue.txt"), "w").write("\n".join(lines) + "\n")
    # committed trace
    ex = json.load(open(os.path.join(ART, "examples.json"))); lines = []
    for name, trs in ex.items():
        for k, tr in enumerate(trs):
            lines.append(f"# {name}: committed example {k + 1}, declared {json.dumps(tr.get('declared'))}")
            lines += [L.fmt_step(s) for s in tr["steps"]]
            lines.append(f"# result at commit: {json.dumps(tr.get('result'))}")
    open(os.path.join(OUT, "committed_trace.txt"), "w").write("\n".join(lines) + "\n")
    # candidates + verifier
    summ = {"scenario": SID, "arm": ARM, "suite": SU, "candidates": []}; learned = None
    for f in sorted(glob.glob(os.path.join(ART, "candidates", "*.json"))):
        C = json.load(open(f)); ch = (C.get("paths") or {}).get(C.get("chosen") or "deterministic", {}); prog = ch.get("program") or C.get("program")
        tests = ch.get("tests") or []
        text = prog if isinstance(prog, str) else L.fmt_procedure(prog)
        summ["candidates"].append({"file": os.path.basename(f), "status": C.get("status"), "program": text,
                                   "tests_passed": sum(1 for t in tests if t[1]), "tests_run": len(tests),
                                   "tests": [{"id": t[0], "pass": bool(t[1])} for t in tests]})
        if C.get("status") == "VERIFIED": learned = text
    db = sqlite3.connect(f"file:{os.path.join(W, 'procedures.sqlite')}?mode=ro", uri=True)
    summ["active_pointer"] = [dict(zip(("name", "procedure_id", "enabled"), r)) for r in db.execute("select name, procedure_id, enabled from active_pointer")]
    summ["lib_log"] = [{"n": n, "event": e, "json": json.loads(j)} for n, e, j in db.execute("select n, event, json from lib_log order by n")]
    db.close()
    json.dump(summ, open(os.path.join(OUT, "verifier_summary.json"), "w"), indent=1)
    open(os.path.join(OUT, "learned_procedure.txt"), "w").write((learned or "(no VERIFIED candidate)").rstrip() + "\n")
    # reuse
    sc = json.load(open(os.path.join(EXP, "scenarios", SU, SID + ".json"))); HO = json.load(open(os.path.join(R, "HANDOFF.json")))
    RU = json.load(open(os.path.join(R, f"RCI_{ARM}.json")))["reuse"][SID]
    lines = [f"# handoff: app stop rc {HO.get('modal_app_stop_rc')}, endpoint after stop {HO.get('endpoint_after_stop')}, teacher destroyed {HO.get('teacher_destroyed')}"]
    for i, (t, e) in enumerate(zip(sc["post_turns"], sc["post_expected"])):
        if t["kind"] == "RESTART": lines.append("[RESTART: student process + local LLM service restarted; teaching transcripts absent]"); continue
        g = RU["turns"].get(str(i)) or {}
        ok = g.get("status") == e.get("status") and g.get("STATE") == e.get("state") and ("return" not in e or g.get("return") == e.get("return"))
        lines.append(f"{t['text']}\n    -> plan {g.get('plan')}; status {g.get('status')}; return {json.dumps(g.get('return'))}; expected {e.get('status')} {json.dumps(e.get('return'))}; world state {'==' if g.get('STATE') == e.get('state') else '!='} oracle: {'EXACT' if ok else 'MISMATCH'}")
    lines.append(f"# network-guard blocked attempts: {len(RU.get('netguard_blocked', []))}; student weight hashes: {sorted(set(RU.get('student_hashes', [])))}")
    open(os.path.join(OUT, "reuse_summary.txt"), "w").write("\n".join(lines) + "\n")
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
