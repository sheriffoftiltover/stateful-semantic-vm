"""Procedure-learning scenario suites P1-P12 (spec §41-§42, §71). DEV and LOCKED_TEST use separate seeds AND disjoint paraphrase templates.
Every scenario: a randomized world fixture (gold-IR facts + setup steps), teaching turns (concrete steps = gold procedure with example values,
random variable names), lifecycle turns with DESIGNED expected outcomes (VERIFIED / REJECTED_* / CLARIFY ...), invocations (RUN / REQUEST with
never-demonstrated arguments), restarts. Expected results for every turn (status, return, full world state) come from the independent oracle.
Usage: python scenarios/generate.py --suite dev|locked_test"""
import os, sys, json, random, argparse, hashlib, glob, copy
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "core", "ir"), os.path.join(ROOT, "core", "neural", "vendor")]
import mr_config as K, ir as IR, lang as L, catalog as CAT, oracle as OR
VOCAB = {"PERSON": set(K.PERSONS), "TIME": set(K.TIMES), "PLACE": set(K.PLACES), "TOPIC": set(K.TOPICS), "EVENT_TYPE": set(L.EVENT_TYPES), "STATUS": set(L.STATUSES)}
SEEDS = {"dev": "SEMVM-PD-V1-DEV-20260926", "locked_test": "SEMVM-PD-V1-LOCKED-V2-20260926-independent"}   # locked v1 seed archived (invalidated before run)
PLAN = {"dev": {"P1": 4, "P2": 3, "P3": 2, "P4": 2, "P5": 3, "P6": 2, "P7": 3, "P8": 2, "P9": 2, "P10": 2, "P11": 2, "P12": 3},
        "locked_test": {"P1": 2, "P2": 2, "P3": 1, "P4": 2, "P5": 2, "P6": 1, "P7": 2, "P8": 2, "P9": 1, "P10": 1, "P11": 1, "P12": 3}}
VC = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}
ONE_PARAM = ["calls_with", "count_open_calls_with", "close_calls_with", "move_last_reminder_and_return_call_person", "retarget_last_email", "replace_visit_location",
             "call_people_at", "person_on_call_at", "count_calls_with", "close_open_emails_to"]


def fact_ir(f):
    occs = [(f["outer"], None, 0), (f["inner"], None, 1)] + [(VC[r], v, 2 + k) for k, (r, v, _) in enumerate(f["mods"])]
    return IR.from_graph(occs, [("TODO", occs[0], occs[1])] + [(r, occs[0] if a == "outer" else occs[1], occs[2 + k]) for k, (r, v, a) in enumerate(f["mods"])])


class Gen:
    def __init__(self, rng, suite): self.r = rng; self.suite = suite

    def world(self):
        r = self.r; P = r.sample(K.PERSONS, 7); T = r.sample(K.TIMES, 5); PL = r.sample(K.PLACES, 4); TO = r.sample(K.TOPICS, 4)
        F = []
        F += [{"outer": "REMINDER", "inner": "EMAIL", "mods": [("RECIPIENT", P[1], "inner"), ("TOPIC", TO[0], "inner")]},
              {"outer": "REQUEST", "inner": "EMAIL", "mods": [("RECIPIENT", P[4], "inner"), ("TOPIC", TO[1], "inner")]},
              {"outer": "REMINDER", "inner": "EMAIL", "mods": [("RECIPIENT", P[1], "inner"), ("TOPIC", TO[2], "inner")]},
              {"outer": "REQUEST", "inner": "EMAIL", "mods": [("RECIPIENT", P[5], "inner"), ("TOPIC", TO[3], "inner")]},
              {"outer": "REMINDER", "inner": "VISIT", "mods": [("WHERE", PL[0], "inner")]},
              {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHERE", PL[1], "inner")]},
              {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[2], "outer"), ("WHEN", T[0], "outer")]},
              {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[5], "outer"), ("WHEN", T[1], "outer")]},
              {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[2], "outer"), ("WHEN", T[1], "outer")]}]
        for k in range(6): F.append({"outer": "REMINDER", "inner": "CALL", "mods": [("WHEN", T[k % 5], "outer"), ("WHO", P[[0, 1, 3, 0, 6, 3][k]], "inner")]})
        setup = ["$s0 = FIND CALL WHERE SELF.WHO=" + P[3], "FOR $s1 IN $s0 : SET_STATUS $s1 CLOSED", "$s2 = FIND EMAIL WHERE SELF.TOPIC=" + TO[2], "FOR $s3 IN $s2 : SET_STATUS $s3 CLOSED"]
        return {"P": P, "T": T, "PL": PL, "TO": TO}, F, setup

    def values_for(self, fam, V):
        """example + counterfactual values that are meaningful in the fixture (never equal)"""
        ps = CAT.FAMILIES[fam]["params"] if fam in CAT.FAMILIES else CAT.COMPOSITE["params"]; out = []
        pools = {"PERSON": {"calls_with": [V["P"][0], V["P"][1], V["P"][3], V["P"][6]], "count_open_calls_with": [V["P"][0], V["P"][3], V["P"][1], V["P"][6]], "close_calls_with": [V["P"][0], V["P"][1], V["P"][6]],
                            "retarget_last_email": [V["P"][5], V["P"][6], V["P"][2]], "count_calls_with": [V["P"][0], V["P"][3], V["P"][1], V["P"][6]], "close_open_emails_to": [V["P"][1], V["P"][4], V["P"][5]],
                            "count_requests_by_at": [V["P"][2], V["P"][5]]},
                 "TIME": {"_": [V["T"][0], V["T"][1], V["T"][2], V["T"][3], V["T"][4]], "count_requests_by_at": [V["T"][1], V["T"][0]]}, "PLACE": {"_": [V["PL"][2], V["PL"][3], V["PL"][0]]}}
        for p, c in ps.items():
            pool = list(pools[c].get(fam, pools[c].get("_", [])))
            if fam == "count_requests_by_at": out.append((p, pool)); continue
            self.r.shuffle(pool); out.append((p, pool))
        return out

    def teach_steps(self, gold_text, vals):
        g = L.parse_procedure(gold_text); letters = self.r.sample("abcdefghjkmnpqrstuwxyz", 8); ren = {}
        def fix(o):
            if isinstance(o, dict):
                if set(o) == {"param"}: return {"const": vals[o["param"]]}
                if set(o) == {"var"}: return {"var": ren.setdefault(o["var"], letters[len(ren)])}
                out = {}
                for k, v in o.items():
                    out[k] = ren.setdefault(v, letters[len(ren)]) if k in ("bind", "as") else fix(v)
                return out
            if isinstance(o, list): return [fix(x) for x in o]
            return o
        return [L.fmt_step(fix(s)) for s in g["body"]]

    def tmpl(self, fam, vals):
        spec = CAT.FAMILIES.get(fam, CAT.COMPOSITE); t = self.r.choice(spec["dev" if self.suite == "dev" else "locked"]); return t.format(**vals)


def T(kind, text=None, **kw): return dict({"kind": kind, "text": text}, **kw)


def build(g, cat):
    V, facts, setup = g.world(); turns = [T("ASSERT", "<fixture>", facts=f, gold_ir=fact_ir(f)) for f in facts] + [T("STEP", s) for s in setup]; r = g.r
    def teach(fam, vals, mode=":teach", name=None, expect="VERIFIED"):
        name = name or fam; gold = CAT.FAMILIES[fam]["gold"] if fam in CAT.FAMILIES else CAT.COMPOSITE["gold"]
        hdr = f"{mode} {name}(" + ", ".join(f"{k}={v}" for k, v in vals.items()) + ")" if (mode != ":example" and vals) else f"{mode} {name}" + (f"({', '.join(f'{k}={v}' for k, v in vals.items())})" if vals and mode == ":example" else "")
        out = [T("CMD", hdr)] + [T("STEP", s, teaching=name) for s in g.teach_steps(gold, vals)]
        end = {":teach": ":endteach", ":example": ":endexample", ":revise": ":endrevise"}[mode]
        out.append(T("CMD", end, expect=None if mode == ":example" else expect, family=fam, name=name)); return out
    def accept(fam, name=None, gold=None): return [T("CMD", f":accept {name or fam}", expect="OK", gold=gold or (CAT.FAMILIES[fam]["gold"] if fam in CAT.FAMILIES else CAT.COMPOSITE["gold"]), name=name or fam)]
    def run(fam, vals, name=None): return [T("RUN", f"RUN {name or fam} " + " ".join(f"{k}={v}" for k, v in vals.items()), plan={"call": name or fam, "args": dict(vals)}, family=fam)]
    def req(fam, vals, plan=None): return [T("REQUEST", "REQUEST " + g.tmpl(fam, vals), plan=plan or {"call": fam, "args": dict(vals)}, family=fam)]
    def pick(fam, k=3):
        vs = g.values_for(fam, V); return [{p: pool[i % len(pool)] for p, pool in vs} for i in range(k)]
    if cat in ("P1", "P5", "P6"):
        fam = r.choice(ONE_PARAM + (["email_topic_report"] if cat == "P1" else [])); v = pick(fam, 3) if CAT.FAMILIES[fam]["params"] else [{}, {}, {}]
        turns += teach(fam, v[0]) + accept(fam)
        if cat == "P5": turns += [T("RESTART")] + req(fam, v[1]) + run(fam, v[2])
        else: turns += run(fam, v[1]) + req(fam, v[2])
    elif cat in ("P2", "P4"):
        fam = r.choice(["calls_with", "count_calls_with", "call_people_at", "retarget_last_email", "replace_visit_location"] if cat == "P2" else ["count_open_calls_with", "close_open_emails_to"])
        v = pick(fam, 3); turns += teach(fam, v[0], ":example") + teach(fam, v[1], ":example") + [T("CMD", f":learn {fam}", expect="VERIFIED", family=fam, name=fam)] + accept(fam) + req(fam, v[2]) + run(fam, v[0])
    elif cat == "P3":
        fam = "count_requests_by_at"; V2 = [V["P"][2], V["P"][5], V["P"][2]]; T2 = [V["T"][0], V["T"][1], V["T"][1]]
        turns += teach(fam, {"person": V2[0], "time": T2[0]}, ":example") + teach(fam, {"person": V2[1], "time": T2[1]}, ":example")
        turns += [T("CMD", f":learn {fam}", expect="VERIFIED", family=fam, name=fam)] + accept(fam) + run(fam, {"person": V2[2], "time": T2[2]}) + req(fam, {"person": V["P"][5], "time": V["T"][0]})
    elif cat == "P7" or cat == "P12":
        t = pick("person_on_call_at", 3); p = pick("count_calls_with", 2)
        turns += teach("person_on_call_at", t[0]) + accept("person_on_call_at") + teach("count_calls_with", p[0]) + accept("count_calls_with") + [T("RESTART")]
        comp_plan = {"call": "count_calls_with", "args": {"person": {"call": "person_on_call_at", "args": {"time": t[1]["time"]}}}}
        turns += [T("REQUEST", "REQUEST " + g.tmpl("__composite", {"time": t[1]["time"]}), plan=comp_plan, family="__composite", composition="L1")]
        name = CAT.COMPOSITE["name"]
        turns += [T("CMD", f":save-last-as {name}(time={t[1]['time']})", expect="VERIFIED", family="__composite", name=name, composition="L2")] + accept("__composite", name)
        turns += [T("RESTART")] + run("__composite", {"time": t[2]["time"]}, name)
        if cat == "P12": turns += [T("REQUEST", "REQUEST " + g.tmpl("__composite", {"time": t[0]["time"]}), plan={"call": name, "args": {"time": t[0]["time"]}}, family="__composite")]
    elif cat == "P8":
        fam = "count_open_calls_with"; v = pick(fam, 3); turns += teach(fam, v[0], ":example") + teach(fam, v[1], ":example")
        bads = {"frozen_value": f"PROCEDURE {fam}() ; $v0 = FIND CALL WHERE SELF.WHO={v[0]['person']} STATUS=OPEN ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                "param_constant": f"PROCEDURE {fam}(person:PERSON, status:STATUS) ; $v0 = FIND CALL WHERE SELF.WHO={{person}} STATUS={{status}} ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                "dropped_constant_filter": f"PROCEDURE {fam}(person:PERSON) ; $v0 = FIND CALL WHERE SELF.WHO={{person}} ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                "wrong_relation": f"PROCEDURE {fam}(person:PERSON) ; $v0 = FIND CALL WHERE PARENT.WHO={{person}} STATUS=OPEN ; $v1 = COUNT $v0 ; RETURN $v1 ; END"}
        for k in r.sample(sorted(bads), 3): turns.append(T("CMD", f":propose {fam} <<{bads[k]}>>", expect="REJECTED", family=fam, name=fam, bad=k))
        turns += [T("CMD", f":learn {fam}", expect="VERIFIED", family=fam, name=fam)] + accept(fam) + run(fam, v[2])
    elif cat == "P9":
        a, b = "count_calls_with", "count_open_calls_with"; pa, pb = pick(a, 2), pick(b, 2)
        turns += teach(a, pa[0]) + accept(a) + teach(b, pb[0]) + accept(b) + [T("CMD", f":alias {a} call count", expect="OK"), T("CMD", f":alias {b} call count", expect="OK")]
        turns += [T("REQUEST", f"REQUEST what is the call count for {pa[1]['person']}", plan=None, expect="CLARIFY", family="__ambiguous")] + run(a, pa[1])
    elif cat == "P10":
        fam = "count_calls_with"; v = pick(fam, 3); turns += teach(fam, v[0]) + accept(fam) + run(fam, v[1])
        turns += teach("count_open_calls_with", v[0], ":revise", name=fam) + accept(fam, fam, CAT.FAMILIES["count_open_calls_with"]["gold"].replace("count_open_calls_with", fam)) + run(fam, v[1])
        turns += [T("CMD", f":procedure {fam}", expect="OK", versions=["RETIRED", "ACTIVE"], name=fam)]
    elif cat == "P11":
        fam = "move_visit_and_parent"; v = pick(fam, 3)     # DEV v2: two examples (the parameter occurs in 2 slots -> one-shot is ambiguous by the registered rule)
        turns += teach(fam, v[0], ":example") + teach(fam, v[1], ":example") + [T("CMD", f":learn {fam}", expect="VERIFIED", family=fam, name=fam)] + accept(fam)
        f = {"outer": "PLAN", "inner": "VISIT", "mods": [("WHEN", V["T"][2], "outer")]}; turns += [T("ASSERT", "<fixture>", facts=f, gold_ir=fact_ir(f))] + run(fam, v[1]) + req(fam, v[2])
    return turns


def mark_novelty(turns):
    """invocation turns get novel_args = True iff some literal argument value was never used as a teaching example value for that procedure"""
    demo = {}; cur = None
    for t in turns:
        if t["kind"] == "CMD" and t["text"].split()[0] in (":teach", ":example", ":revise", ":save-last-as"):
            hdr = t["text"].split(" ", 1)[1]; nm = hdr.split("(")[0].strip(); vals = hdr[hdr.index("(") + 1:hdr.rindex(")")].split(",") if "(" in hdr else []
            demo.setdefault(nm, set()).update(v.split("=", 1)[1].strip() for v in vals if "=" in v)
        if t["kind"] in ("RUN", "REQUEST") and t.get("plan"):
            def lits(pl): return [v for v in pl["args"].values() if isinstance(v, str)] + [x for v in pl["args"].values() if isinstance(v, dict) for x in lits(v)]
            t["novel_args"] = any(v not in demo.get(t["plan"]["call"], set()) for v in lits(t["plan"]))
    return turns


def expected(turns):
    W = OR.World(VOCAB); lib = {}; env = {}; teaching = None; exp = []; verified = {}
    for t in turns:
        k = t["kind"]
        if k == "RESTART": exp.append(None); env = {}; continue
        if k == "ASSERT": W.assertion(t["facts"]); e = {"status": "OK"}
        elif k == "STEP":
            st, ret = W.run_step_text(t["text"], env, lib); e = {"status": st}
        elif k == "CMD":
            c = t["text"].split()[0]
            if c in (":teach", ":example", ":revise"): env = {}; e = {"status": "OK"}
            elif c in (":endteach", ":endrevise", ":learn", ":save-last-as") or c.startswith(":propose"):
                e = {"status": t["expect"]}
                if t.get("expect") == "VERIFIED": verified[t["name"]] = True
            elif c == ":endexample": e = {"status": "OK"}
            elif c == ":accept":
                lib[t["name"]] = L.parse_procedure(t["gold"]) if t["name"] in verified else lib.get(t["name"]); e = {"status": "OK"}
            else: e = {"status": t.get("expect", "OK")}
        elif k in ("RUN", "REQUEST"):
            if t.get("expect") == "CLARIFY": e = {"status": "CLARIFY"}
            else: st, ret = W.invoke(OR.plan_proc(t["plan"]), {}, lib); e = {"status": st, "return": ret}
        e["state"] = W.state(); exp.append(e)
    return exp


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=sorted(SEEDS)); a = ap.parse_args()
    rng = random.Random(SEEDS[a.suite]); g = Gen(rng, a.suite); d = os.path.join(HERE, a.suite); os.makedirs(d, exist_ok=True); k = 0; out = []
    for cat, n in PLAN[a.suite].items():
        for _ in range(n):
            k += 1; turns = mark_novelty(build(g, cat)); sc = {"scenario_id": f"{a.suite}-{k:03d}-{cat}", "suite": a.suite, "category": cat, "turns": turns, "expected": expected(turns)}
            json.dump(sc, open(os.path.join(d, f"{sc['scenario_id']}.json"), "w"), indent=1); out.append(sc)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    man = {"suite": a.suite, "seed": SEEDS[a.suite], "n": len(out), "categories": PLAN[a.suite], "templates": "dev" if a.suite == "dev" else "locked (disjoint)",
           "files_sha256": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files}}
    json.dump(man, open(os.path.join(HERE, f"{a.suite.upper()}_MANIFEST.json"), "w"), indent=1); print({k: v for k, v in man.items() if k != "files_sha256"})


if __name__ == "__main__":
    main()
