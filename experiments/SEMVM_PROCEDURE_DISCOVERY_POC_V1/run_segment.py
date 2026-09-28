"""Runs turns [start, end) of one scenario in a FRESH process against persistent WORLD + LIBRARY databases (spec §29-§30).
python run_segment.py --scenario <json> --dir <scenario work dir> --mode DISCOVERED|GOLD_PROC --start i --end j --out <json>"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import system as SY, llm as LM


def main():
    ap = argparse.ArgumentParser()
    for k in ("--scenario", "--dir", "--mode", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--start", type=int, required=True); ap.add_argument("--end", type=int, required=True); a = ap.parse_args()
    sc = json.load(open(a.scenario)); d = a.dir
    S = SY.System(os.path.join(d, "world.sqlite"), os.path.join(d, "procedures.sqlite"), os.path.join(d, "learn"), mode=a.mode, use_llm=(a.mode == "DISCOVERED")); out = []
    for i in range(a.start, a.end):
        t = sc["turns"][i]; uid = f"{sc['scenario_id']}:{i}"; ts = f"2026-09-26T21:00:00#t{i:03d}"; c = (t.get("text") or "").split()[:1]
        if a.mode == "GOLD_PROC" and t["kind"] == "CMD" and (c[0] in (":endteach", ":endrevise", ":learn", ":save-last-as") or c[0] == ":propose"):
            S.teach = None; r = {"status": "GOLD_BYPASS", "response": "discovery bypassed (GOLD_PROC)"}
        elif a.mode == "GOLD_PROC" and t["kind"] == "CMD" and c[0] == ":accept":
            if t["name"] in [n for n, e in _expected_verified(sc, i)]: S.install_gold(t["name"], t["gold"]); r = {"status": "OK", "response": "gold installed"}
            else: r = {"status": "NOTHING_TO_ACCEPT", "response": ""}
        elif t["kind"] == "ASSERT": r = S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": t["gold_ir"]}, uid, ts)
        elif t["kind"] == "REQUEST" and a.mode == "GOLD_PROC": r = S.process({"text": t["text"], "gold_plan": t.get("plan")}, uid, ts)
        else: r = S.process({"text": t["text"]}, uid, ts)
        r["STATE"] = S.world.canonical_state(); r["pid"] = os.getpid(); r["turn"] = i
        if t["kind"] == "CMD" and c and c[0] == ":procedure" and r.get("explain"): r["versions"] = [v["status"] for v in r["explain"]["version_history"]]
        out.append(r)
    info = {"lib_bytes": S.lib.library_bytes(), "world_bytes": os.path.getsize(os.path.join(d, "world.sqlite")), "active": S.lib.list_active(), "llm_calls": LM.CALLS}
    S.close(); json.dump({"turns": out, "info": info}, open(a.out, "w"), default=str)


def _expected_verified(sc, upto):
    return [(t.get("name"), True) for t in sc["turns"][:upto] if t["kind"] == "CMD" and t.get("expect") == "VERIFIED"]


if __name__ == "__main__":
    main()
