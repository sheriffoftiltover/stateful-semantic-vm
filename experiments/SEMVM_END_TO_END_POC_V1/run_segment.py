"""Runs turns [start, end) of one scenario in a FRESH process against an existing / new SQLite world model (restart persistence, spec §30).
Assertion neural outputs come from the frozen-parser cache (spec §25); this process never loads the neural model.
python run_segment.py --scenario <json> --db <sqlite> --mode FULL|GOLD_IR --cache <json> --start i --end j --out <json>"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT)
import pipeline as PL


def main():
    ap = argparse.ArgumentParser()
    for k in ("--scenario", "--db", "--mode", "--cache", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--start", type=int, required=True); ap.add_argument("--end", type=int, required=True); a = ap.parse_args()
    sc = json.load(open(a.scenario)); cache = json.load(open(a.cache)); s = PL.Session(a.db, a.mode, binder=None, cache=cache); out = []
    for i in range(a.start, a.end):
        t = sc["turns"][i]
        out.append({"turn": i, "pid": os.getpid(), **s.process(f"{sc['scenario_id']}:{i}", t, f"{sc['reference_time']}#t{i:03d}")})
    s.close(); json.dump(out, open(a.out, "w"), default=str)


if __name__ == "__main__":
    main()
