"""Runs turns [start, end) of one scenario in a FRESH process against persistent WORLD + LIBRARY databases (restart = new process).
Modes: GOLD_TRACE (gold actions per utterance), FORMAL_TEACH (parent step language; scenario['formal_turns']), NL_TEACH (natural language).
NL_TEACH simulated user (ASSISTED protocol, registered; at most ONE rescue per utterance; the user knows only their own intent = the gold
outcome of the utterance): unexpected CLARIFY / UNSUPPORTED / failure on an executable utterance -> the registered band-A restatement
("I mean: ..."); a wrong executed action -> "No, <restatement>" (correction); an action executed where the user expected a clarification /
rejection -> ":undo". Every first-pass result is kept; FIRST_PASS metrics never count rescued turns as correct.
python run_segment.py --scenario <json> --dir <work dir> --mode MODE --start i --end j --out <json>"""
import os, sys, json, argparse, copy
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "nlteach"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import nlsystem as NS, nllm, llm as PLM


def same_steps(a, b): return json.dumps(NS.canon_steps(a), sort_keys=True) == json.dumps(NS.canon_steps(b), sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--scenario", "--dir", "--mode", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--start", type=int, required=True); ap.add_argument("--end", type=int, required=True); ap.add_argument("--probe", action="store_true"); a = ap.parse_args()
    sc = json.load(open(a.scenario)); d = a.dir; turns = sc["formal_turns"] if a.mode == "FORMAL_TEACH" else sc["turns"]
    S = NS.NLSystem(os.path.join(d, "world.sqlite"), os.path.join(d, "procedures.sqlite"), os.path.join(d, "learn"), mode=a.mode, probe=a.probe); out = []
    for i in range(a.start, a.end):
        t = turns[i]; uid = f"{sc['scenario_id']}:{i}"; ts = f"2026-09-26T21:00:00#t{i:03d}"
        if t["kind"] == "ASSERT": r = S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": t["gold_ir"]}, uid, ts)
        elif t["kind"] == "NL":
            g = t["gold"]
            if a.mode == "GOLD_TRACE": r = S.process({"kind": "NL", "text": t["text"], "gold_outcome": g}, uid, ts)
            else:
                r = S.process({"kind": "NL", "text": t["text"]}, uid, ts); first = copy.deepcopy(r); rescue = None
                if g["status"] == "OK":
                    if r["status"] == "OK" and not same_steps(r.get("executed_steps") or [], g["steps"]):
                        rescue = "No, " + t["rephrase"][len("I mean: "):]
                    elif r["status"] != "OK": rescue = ("No, " + t["rephrase"][len("I mean: "):]) if g.get("undo") else t["rephrase"]
                elif r["status"] == "OK": rescue = ":undo"
                if rescue:
                    r2 = S.process({"kind": "NL", "text": rescue}, uid + "#rescue", ts + "r"); r2["first_pass"] = first; r2["rescue_text"] = rescue; r = r2
                else: r["first_pass"] = None
        else: r = S.process({"text": t["text"]}, uid, ts)
        r["STATE"] = S.world.canonical_state(); r["pid"] = os.getpid(); r["turn"] = i
        c = (t.get("text") or "").split()[:1]
        if t["kind"] == "CMD" and c and c[0] == ":procedure" and r.get("explain"): r["versions"] = [v["status"] for v in r["explain"]["version_history"]]
        out.append(r)
    info = {"lib_bytes": S.lib.library_bytes(), "world_bytes": os.path.getsize(os.path.join(d, "world.sqlite")), "active": S.lib.list_active(), "nl_llm_calls": nllm.CALLS, "retrieval_llm_calls": PLM.CALLS}
    S.close(); json.dump({"turns": out, "info": info}, open(a.out, "w"), default=str)


if __name__ == "__main__":
    main()
