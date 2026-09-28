"""REUSE phase (post-handoff) segment in a FRESH process: teacher gone (no TEACHER_* / GROQ_API_KEY in the environment; network guard
blocks every non-loopback connection), teaching transcript / examples / snapshots removed from the student's directory; only WORLD +
LIBRARY (+ provenance hashes) remain. python run_reuse.py --scenario S.json --dir WORK --start i --end j --out OUT.json"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "student"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import nlsystem as NS, llm as PLM


def main():
    ap = argparse.ArgumentParser()
    for k in ("--scenario", "--dir", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--start", type=int, required=True); ap.add_argument("--end", type=int, required=True); a = ap.parse_args()
    audit = {"netguard_active": os.environ.get("PDX_NETGUARD_ACTIVE") == "1", "teacher_env_present": [k for k in ("TEACHER_URL", "TEACHER_API_KEY", "GROQ_API_KEY") if os.environ.get(k)],
             "teacher_modules_loaded": [m for m in ("client", "episode", "protocol") if m in sys.modules], "learn_dir_present_at_start": os.path.exists(os.path.join(a.dir, "learn", "teaching_traces"))}
    sc = json.load(open(a.scenario)); d = a.dir
    S = NS.NLSystem(os.path.join(d, "world.sqlite"), os.path.join(d, "procedures.sqlite"), os.path.join(d, "learn_reuse"), mode="GOLD_TRACE"); out = []
    for i in range(a.start, a.end):
        t = sc["post_turns"][i]; r = S.process({"text": t["text"]}, f"{sc['scenario_id']}:p{i}", f"2026-09-27T22:00:00#p{i:03d}")
        r["STATE"] = S.world.canonical_state(); r["turn"] = i; out.append(r)
    info = {"lib_bytes": S.lib.library_bytes(), "active": S.lib.list_active(), "retrieval_llm_calls": PLM.CALLS, "audit": audit,
            "teacher_modules_loaded_at_end": [m for m in ("client", "episode", "protocol") if m in sys.modules]}
    S.close(); json.dump({"turns": out, "info": info}, open(a.out, "w"), default=str)


if __name__ == "__main__":
    main()
