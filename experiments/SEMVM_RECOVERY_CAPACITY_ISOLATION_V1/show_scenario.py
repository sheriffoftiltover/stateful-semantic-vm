"""Readable view of one RCI scenario, optionally with what an arm actually did.
python show_scenario.py scenarios/dev_a/dev_a-022-S15.json            # the scenario itself
python show_scenario.py scenarios/dev_a/dev_a-022-S15.json --arm D   # + the teaching dialogue and outcome of arm D"""
import json, sys, os, argparse
ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--arm", default=None); a = ap.parse_args()
    sc = json.load(open(a.path)); sid = sc["scenario_id"]
    print(f"== {sid}   stratum {sc['stratum']}: {sc['stratum_name']}   (lesson style {sc['style']})\n")
    print("TEACHER VALUE POOL (values the teacher may demonstrate with):")
    for k, v in sc["teacher_pool"].items(): print(f"   {k:8s} {', '.join(v)}")
    print("EVAL POOL (unseen values used after handoff):")
    for k, v in sc["eval_pool"].items(): print(f"   {k:8s} {', '.join(v)}")
    print(f"\nWORLD: {sum(1 for t in sc['fixture'] if t['kind'] == 'ASSERT')} events asserted, {sum(1 for t in sc['fixture'] if t['kind'] == 'STEP')} setup steps")
    for it in sc["curriculum"]:
        sig = ", ".join(f"{p}:{t}" for p, t in it["sig"].items())
        print(f"\n-- SKILL TO TEACH: {it['name']}({sig})")
        print(f"   goal: {it['goal']}")
        if it.get("injection"): print(f"   evaluator injection: {it['injection']}")
        print("   reference procedure:"); [print("      " + l) for l in it["gold"].splitlines()]
        s = sc["scripted"].get(it["name"])
        if s:
            print("   scripted lesson (demonstration 1):")
            d = s["demos"][0]; print("      EXAMPLE: " + ", ".join(f"{k}={v}" for k, v in d["example"].items()))
            for l in d["lines"]: print("      STEP: " + l)
    print("\n-- AFTER HANDOFF (teacher gone; student alone):")
    for t, e in zip(sc["post_turns"], sc["post_expected"]):
        if t["kind"] == "RESTART": print("   [student restarted]"); continue
        ret = (e or {}).get("return") if e else None
        print(f"   {t['text']}" + (f"   -> expected {json.dumps(ret)}" if ret is not None else f"   -> expected {e.get('status') if e else ''}"))
    if a.arm:
        suite = sc["suite"]; tr = os.path.join(ROOT, "teaching_traces", suite, a.arm, sid + ".json"); acq = os.path.join(ROOT, "results", suite, "work", a.arm, sid, "acq.json")
        if os.path.exists(tr):
            T = json.load(open(tr))
            for tg in T["targets"]:
                print(f"\n== ARM {a.arm} teaching dialogue for {tg['name']}   (final status {tg['status']})")
                for m in tg["transcript"][2:]:
                    who = "TEACHER" if m["role"] == "assistant" else "STUDENT"
                    print(f"   {who}: " + m["content"].replace("\n", "\n            "))
        if os.path.exists(acq):
            A = json.load(open(acq))
            for O in A["targets"]:
                print(f"\n== ARM {a.arm} demonstrations for {O['name']}: {O['status']}")
                for D in O["demos"]:
                    print(f"   demo {D['index'] + 1}: {D['end']}" + (f" / learn {D['learn']}" if D.get("learn") else ""))
                    for r in D["results"]:
                        steps = " ; ".join(s["op"] for s in r["executed_steps"]) or "-"
                        print(f"      [{r['status']:9s}] {r['line']}   => {steps}")


if __name__ == "__main__":
    main()
