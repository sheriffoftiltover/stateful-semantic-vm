"""Interactive SEMVM POC shell. Controlled assertions go through the frozen binder; SEMVM_CMD_V1 commands go to the deterministic VM.
python repl.py [--db my_world.sqlite]      (state persists in the SQLite file across sessions)
Meta commands:
  :example [O|I|OO|II|OI|IO]   print a fresh valid controlled assertion (from the locked generator) + its English gloss
  :state                       show the persistent world state      :trace   toggle full per-turn traces
  :help                        help                                 :quit    exit"""
import os, sys, json, random, argparse, itertools
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scenarios"))
import pipeline as PL
HELP = """Assertions (controlled language; the tag after a modifier names its parent event), e.g.
    request theta : at 3 re theta ; so then again soon , call alpha ; by Alice per alpha
    (or type :example OI for a fresh one)
Commands:
    QUERY <REL> OF <TYPE|LAST_TYPE> [WHERE SELF|PARENT|CHILD.<REL>=<VALUE> ...]
    UPDATE LAST_<TYPE> <REL>=<VALUE> ...   RETRACT LAST_<TYPE> <REL>   DELETE LAST_<TYPE>   NEW PERSON <NAME>
REL: WHO WHEN WHERE RECIPIENT TOPIC     TYPE: REMINDER PLAN REQUEST NOTE / CALL EMAIL VISIT MESSAGE
Meta: :example [O|I|OO|II|OI|IO]  :state  :trace  :help  :quit"""


def gloss(f):
    at = {"outer": f["outer"], "inner": f["inner"]}
    return f"{f['outer']} → TODO → {f['inner']}; " + "; ".join(f"{r}({at[a]}) = {v}" for r, v, a in f["mods"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--db", default=os.path.join(ROOT, "repl_world.sqlite")); a = ap.parse_args()
    import binder as BN, generate as GEN
    print("loading frozen binder ..."); b = BN.Binder(); s = PL.Session(a.db, "FULL", binder=b); gen = GEN.Gen(random.Random(), set()); trace = False; n = itertools.count(1)
    print(f"world model: {a.db}\n{HELP}\n")
    while True:
        try: line = input("semvm> ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not line: continue
        if line in (":quit", ":q", "exit"): break
        if line == ":help": print(HELP); continue
        if line == ":trace": trace = not trace; print("trace", "on" if trace else "off"); continue
        if line == ":state": print(json.dumps(s.store.canonical_state(), indent=1)); continue
        if line.startswith(":example"):
            pat = (line.split() + ["OI"])[1] if len(line.split()) > 1 else random.choice(["O", "I", "OO", "II", "OI", "IO"])
            ex = gen.assertion(pat); print(f"  {ex['text']}\n  gloss (NOT input): {gloss(ex['facts'])}"); continue
        kind = "COMMAND" if PL.VM.is_command(line) else "ASSERT"
        t = s.process(f"repl:{next(n)}", {"kind": kind, "text": line}, "repl")
        if kind == "ASSERT" and t.get("CANONICAL_IR"):
            ir = t["CANONICAL_IR"]; typ = {o["local_id"]: o["type"] for o in ir["objects"]}; sur = {o["local_id"]: o.get("surface") for o in ir["objects"]}
            print("  parsed:", "; ".join(f"{r['predicate']}({typ[r['subject']]}, {sur[r['object']] or typ[r['object']]})" for r in ir["relations"]))
        if t.get("STATE_DIFF"): print("  diff:  ", "  ".join(" ".join(map(str, d)) for d in t["STATE_DIFF"]))
        print(f"  [{t['status']}] {t['RESPONSE']}" + (f"  ({t.get('reason')})" if t["status"] != "OK" and t.get("reason") else ""))
        if trace: print(json.dumps({k: v for k, v in t.items() if k != "STATE_CANONICAL_AFTER"}, indent=1, default=str))
    b.assert_frozen(); s.close(); print("bye (binder still frozen; state saved)")


if __name__ == "__main__":
    main()
