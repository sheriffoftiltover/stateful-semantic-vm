"""PDX scenario suites (spec §47-§50, §56-§57; spec/GROQ_DISTILLATION_SCENARIO_SCHEMA.json). A scenario = a registered world fixture + a
curriculum of target skills (goal, signature, protocol, optional injection) + the TEACHER VALUE POOL (the only values a teacher may use for
demonstrations) + post-handoff turns whose arguments are drawn from OUTSIDE the pool (never-demonstrated by construction, spec §40) and
whose wording comes from registered request templates (disjoint from lessons, spec §41). Controls: gold / formal acquisition turn lists
(registered demonstration values from the pool) and scripted lessons (NL_TEACH template machinery). Expected outcomes: independent oracle.
python scenarios/pdx_generate.py --suite dev|locked_test"""
import os, sys, json, random, argparse, hashlib, glob, copy
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "core", "ir"), os.path.join(ROOT, "core", "neural", "vendor")]
import mr_config as K, lang as L, oracle as OR, pdx_catalog as PC
import nl_generate as NG
SEEDS = {"dev": "SEMVM-HTG-V1-DEV-20260928", "locked_test": "SEMVM-HTG-V1-LOCKED-20260928-independent"}
TEMPLATES = {"dev": "templates_dev.json", "locked_test": "templates_htg_locked.json"}
PLAN = {"dev": ["S1", "S2", "S3", "S4", "S4", "S5", "S6", "S7", "S8", "S9", "S9", "S10", "S10", "S11", "S11", "S12", "S12", "S13", "S14L", "S14L",
                "S14D", "S14D", "S15", "S16", "S16", "S16", "S17", "S17", "S18", "S18"],
        "locked_test": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14L", "S14D", "S15", "S16", "S16", "S17", "S18"]}
STRATUM = {"S1": "single-step read", "S2": "single-step state mutation", "S3": "multi-step linear", "S4": "filter + state update", "S5": "loop / FOR_EACH",
           "S6": "constant preservation", "S7": "multiple parameters", "S8": "report construction", "S9": "nested procedure call (teacher-taught composite)",
           "S10": "composition (post-handoff L1 / L2)", "S11": "clarification-required (induced rephrase)", "S12": "insufficient-evidence", "S13": "unsupported-operation (injected)",
           "S14L": "bad teacher suggestion — legal-but-wrong / evidence-conflict probe (injected in demonstration 2)", "S14D": "bad teacher suggestion — locally detectable (injected)", "S15": "sort (spec §23 example family)",
           "S16": "relation-sensitive query (RECIPIENT / TOPIC / WHERE)", "S17": "teacher over-constraint probe (all X, OPEN and CLOSED instances exist)", "S18": "evidence vacuity probe (relation swap injected in demonstration 1)"}
FAM = {"S1": ["calls_with"], "S2": ["retarget_last_email", "replace_visit_location"], "S3": ["person_on_call_at", "move_last_reminder_and_return_call_person", "count_calls_with"],
       "S4": ["close_open_emails_to"], "S5": ["close_calls_with"], "S6": ["count_open_calls_with"], "S7": ["count_requests_by_at"], "S8": ["email_topic_report"],
       "S11": ["count_calls_with", "person_on_call_at", "call_people_at"], "S12": ["move_visit_and_parent", "count_calls_with", "retarget_last_email"],
       "S13": ["count_calls_with", "close_calls_with", "replace_visit_location"], "S14L": ["count_open_calls_with", "close_open_emails_to"],
       "S14D": ["count_calls_with", "close_calls_with", "person_on_call_at"], "S15": ["close_oldest_open_request"],
       "S16": ["count_emails_to", "emails_about", "count_visits_in"], "S17": ["all_requests_by", "calls_with", "count_emails_to"], "S18": ["count_emails_to"]}
NG_FAMS = set(NG.CAT.FAMILIES) | {"__composite"}
LEGAL_BAD = ["DROPPED_FILTER", "CONSTANT_SWAP"]; DETECTABLE_BAD = ["UNSUPPORTED_PRIMITIVE", "PREMATURE_RETURN", "WRONG_ARGUMENT_TYPE", "INVALID_VALUE"]


def family_steps(fam, a):
    if fam == "close_oldest_open_request":
        P = a.get("person"); C = NG.C; V = NG.VAR
        return [("find_open_requests_by", NG.FIND("r1", "REQUEST", [("SELF", "WHO", P)], "OPEN")), ("sort_by_time", {"op": "SORT", "bind": "r2", "list": V("r1"), "rel": "WHEN"}),
                ("first", {"op": "FIRST", "bind": "r3", "list": V("r2")}), ("close_it", {"op": "SET_STATUS", "obj": V("r3"), "value": C("CLOSED")}), ("return_request", {"op": "RETURN", "value": V("r3")})]
    P, TO, PL = a.get("person"), a.get("topic"), a.get("place"); V = NG.VAR; ret = lambda x: {"op": "RETURN", "value": V(x)}; cnt = {"op": "COUNT", "bind": "r2", "list": V("r1")}
    if fam == "all_requests_by": return [("find_requests_by", NG.FIND("r1", "REQUEST", [("SELF", "WHO", P)])), ("return_requests", ret("r1"))]
    if fam == "count_emails_to": return [("find_emails_to", NG.FIND("r1", "EMAIL", [("SELF", "RECIPIENT", P)])), ("count", cnt), ("return_count", ret("r2"))]
    if fam == "emails_about": return [("find_emails_about", NG.FIND("r1", "EMAIL", [("SELF", "TOPIC", TO)])), ("return_emails", ret("r1"))]
    if fam == "count_visits_in": return [("find_visits_in", NG.FIND("r1", "VISIT", [("SELF", "WHERE", PL)])), ("count", cnt), ("return_count", ret("r2"))]
    return NG.family_steps(fam, a)


EXTRA_CLAUSES = {"dev": {"find_open_requests_by": {"A": ["find the open requests from {P}", "find {P}'s open requests"], "B": ["look up the requests {P} made that are still open"]},
                         "sort_by_time": {"A": ["sort them by time", "sort them by when they are"], "B": ["put them in order of time"]},
                         "close_it": {"A": ["close it", "mark it closed"], "B": ["set it to closed"]},
                         # HTG families (DEV wording; the LOCKED template file carries its own blind wording)
                         "find_requests_by": {"A": ["find all the requests from {P}", "find every request {P} made"], "B": ["look up all of {P}'s requests"]},
                         "find_emails_to": {"A": ["find the emails to {P}", "find all emails addressed to {P}"], "B": ["look up every email sent to {P}"]},
                         "find_emails_about": {"A": ["find the emails about {TO}", "find all emails on {TO}"], "B": ["look up every email about {TO}"]},
                         "find_visits_in": {"A": ["find the visits in {PL}", "find all visits at {PL}"], "B": ["look up every visit in {PL}"]}},
                 "returns": {"return_request": {"noun": {"A": ["return the request"], "B": ["give back the request"]}, "pronoun": ["return it"]},
                             "return_requests": {"noun": {"A": ["return the requests"], "B": ["give back those requests"]}, "plural_pronoun": ["return them"]}}}


class PGen(NG.Gen):
    """NL_TEACH generator with PDX value pools: TEACH pool (demonstrations) vs EVAL pool (post-handoff), disjoint"""
    def clause(self, pat, band, a, ret_forms=None):
        """NL_TEACH Gen.clause with the TOPIC placeholder {TO} (HTG families)"""
        T = self.tpl; fill = lambda s: s.format(P=a.get("person"), T=a.get("time"), PL=a.get("place"), TO=a.get("topic"))
        if pat in T["returns"]:
            R = T["returns"][pat]; forms = ret_forms or [f for f in ("noun", "pronoun", "plural_pronoun") if f in R]
            if band == "C": forms = [f for f in forms if f != "noun"] or forms
            f = self.r.choice(forms); lst = R[f][band if band in ("A", "B") else self.r.choice("AB")] if f == "noun" else R[f]
            return fill(self.r.choice(lst)), f
        c = T["clauses"][pat]; b = band if band in c else ("A" if band == "A" else self.r.choice([x for x in ("A", "B") if x in c]))
        return fill(self.r.choice(c[b])), None
    def pools_split(self, V):
        P, T, PLc = V["P"], V["T"], V["PL"]
        TO = V["TO"]
        return {"people": [P[0], P[1]], "times": [T[0], T[1]], "places": [PLc[2], PLc[3]], "topics": [TO[0], TO[1]]}, {"people": P[2:], "times": T[2:], "places": PLc[:2], "topics": TO[2:]}


def T(kind, text=None, **kw): return dict({"kind": kind, "text": text}, **kw)


def build(g, cat, k):
    r = g.r; V, facts, setup = g.world(); teach_pool, eval_pool = g.pools_split(V)
    # DEV-1 design fix (ENGINEERING_LOG #3): every TEACHER-POOL value has matching events for every family, so demonstrations are executable and the
    # verifier's counterfactual / perturbation cases are meaningful (spec §63): emails to pool person 0 (one closed by the setup), requests by both pool
    # people at two times each (one closed), so status filters and the time sort are observable.
    P, Tt, TO = V["P"], V["T"], V["TO"]
    facts = facts + [{"outer": "REMINDER", "inner": "EMAIL", "mods": [("RECIPIENT", P[0], "inner"), ("TOPIC", TO[0], "inner")]},
                     {"outer": "REQUEST", "inner": "EMAIL", "mods": [("RECIPIENT", P[0], "inner"), ("TOPIC", TO[2], "inner")]},
                     {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHO", P[0], "outer"), ("WHEN", Tt[3], "outer")]},
                     {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHO", P[0], "outer"), ("WHEN", Tt[0], "outer")]},
                     {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHO", P[1], "outer"), ("WHEN", Tt[4], "outer")]},
                     {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHO", P[1], "outer"), ("WHEN", Tt[1], "outer")]}]
    PLc = V["PL"]
    facts = facts + [{"outer": "REMINDER", "inner": "VISIT", "mods": [("WHERE", PLc[2], "inner")]}, {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHERE", PLc[3], "inner")]},
                     {"outer": "REMINDER", "inner": "VISIT", "mods": [("WHERE", PLc[2], "inner")]}]
    setup = setup + ["$s4 = FIND REQUEST WHERE SELF.WHEN=" + Tt[4], "FOR $s5 IN $s4 : SET_STATUS $s5 CLOSED",
                     "$s6 = FIND CALL WHERE PARENT.WHEN=" + Tt[3], "FOR $s7 IN $s6 : SET_STATUS $s7 CLOSED",          # HTG: a CLOSED call with pool person 0
                     "$s8 = FIND REQUEST WHERE SELF.WHEN=" + Tt[3], "FOR $s9 IN $s8 : SET_STATUS $s9 CLOSED"]         # HTG: a CLOSED request by pool person 0
    pre = [T("ASSERT", "<fixture>", facts=f, gold_ir=NG.fact_ir(f)) for f in facts] + [T("STEP", s) for s in setup]
    style = {"S9": "E"}.get(cat) or ["A", "B", "C", "D"][k % 4]
    def tvals(fam, n=2):
        ps = PC.spec(fam)["params"]; cls = {"PERSON": "people", "TIME": "times", "PLACE": "places", "TOPIC": "topics"}
        return [{p: teach_pool[cls[c]][i % len(teach_pool[cls[c]])] for p, c in ps.items()} for i in range(n)]
    def evals(fam, n=3):
        ps = PC.spec(fam)["params"]; cls = {"PERSON": "people", "TIME": "times", "PLACE": "places", "TOPIC": "topics"}; out = []
        pools = {c: r.sample(eval_pool[cls[c]], len(eval_pool[cls[c]])) for c in set(ps.values())}
        if fam == "count_requests_by_at": return [{"person": V["P"][2], "time": V["T"][1]}, {"person": V["P"][5], "time": V["T"][0]}, {"person": V["P"][2], "time": V["T"][3]}]
        for i in range(n): out.append({p: pools[c][i % len(pools[c])] for p, c in ps.items()})
        return out
    def item(fam, name=None, **proto):
        name = name or (PC.COMPOSITE["name"] if fam == "__composite" else fam); ps = PC.spec(fam)["params"]
        return {"name": name, "family": fam, "sig": ps, "goal": PC.GOALS[fam], "gold": PC.gold_text(fam, name), "demo_values": tvals(fam),
                "protocol": {"hint": proto.get("hint", True), "two_demo": proto.get("two_demo", False)}, "injection": proto.get("injection")}
    cur = []; post = [T("RESTART", handoff=True)]
    def req(fam, a, name):
        tp = PC.spec(fam)["dev" if g.suite == "dev" else "locked"]; post.append(T("REQUEST", "REQUEST " + r.choice(tp).format(**a), plan={"call": name, "args": dict(a)}, family=fam))
    def run(fam, a, name): post.append(T("RUN", f"RUN {name} " + " ".join(f"{k2}={v}" for k2, v in a.items()), plan={"call": name, "args": dict(a)}, family=fam))
    if cat in ("S9", "S10"):
        cur += [item("person_on_call_at"), item("count_calls_with")]
        te = evals("person_on_call_at"); pe = evals("count_calls_with")
        if cat == "S9":
            cur.append(item("__composite")); cn = PC.COMPOSITE["name"]
            run("__composite", te[0], cn); post.append(T("RESTART")); req("__composite", te[1], cn); req("count_calls_with", pe[0], "count_calls_with")
        else:
            cn = PC.COMPOSITE["name"]; comp = {"call": "count_calls_with", "args": {"person": {"call": "person_on_call_at", "args": {"time": te[0]["time"]}}}}
            post.append(T("REQUEST", "REQUEST " + r.choice(PC.COMPOSITE["dev" if g.suite == "dev" else "locked"]).format(time=te[0]["time"]), plan=comp, family="__composite", composition="L1"))
            post.append(T("CMD", f":save-last-as {cn}(time={te[0]['time']})", expect="VERIFIED", family="__composite", name=cn, composition="L2"))
            post.append(T("CMD", f":accept {cn}", expect="OK", gold=PC.gold_text("__composite", cn), name=cn))
            post.append(T("RESTART")); run("__composite", te[1], cn); req("__composite", te[2], cn)
    else:
        fam = r.choice(FAM[cat]); proto = {}
        if cat in ("S16", "S17"):                                # HTG probes: cycle the registered families (every relation / over-constraint family appears)
            g.occ = getattr(g, "occ", {}); j = g.occ.get(cat, 0); g.occ[cat] = j + 1; fam = FAM[cat][j % len(FAM[cat])]
        if cat == "S11": proto["injection"] = {"kind": "VAGUE_STEP", "demo": 0, "text": "Now do the usual thing with it, like we did for Kevin."}
        if cat == "S12": proto["hint"] = fam == "move_visit_and_parent"
        if cat == "S13": proto["injection"] = {"kind": "UNSUPPORTED_PRIMITIVE", "demo": 0, "text": "Also send the result to Kevin by Slack."}
        if cat == "S14L": proto.update(two_demo=True, injection={"kind": LEGAL_BAD[k % 2], "demo": 1})
        if cat == "S14D": proto.update(two_demo=True, injection={"kind": DETECTABLE_BAD[k % 4], "demo": 1})
        if cat == "S18": proto.update(injection={"kind": "RELATION_SWAP", "demo": 0})           # "to <P>" -> "with <P>" in demonstration 1: a vacuity probe
        cur.append(item(fam, **proto)); ev = evals(fam) if PC.spec(fam)["params"] else [{}, {}, {}]; nm = cur[-1]["name"]
        req(fam, ev[0], nm); run(fam, ev[1], nm); post.append(T("RESTART")); req(fam, ev[2], nm)
    return {"fixture": pre, "V": V, "teacher_pool": teach_pool, "eval_pool": eval_pool, "curriculum": cur, "post_turns": post, "style": style}


# ---------------- control acquisition turn lists (registered demonstration values from the teacher pool) ----------------
def acq_turns(sc_cur, formal, g):
    out = []
    for it in sc_cur:
        sig = ", ".join(f"{p}:{t}" for p, t in it["sig"].items()); out.append(T("CMD", f":target {it['name']}({sig})"))
        hdr = lambda a: "(" + ", ".join(f"{k}={v}" for k, v in a.items()) + ")" if a else ""
        two = it["protocol"]["two_demo"] or not it["protocol"]["hint"] or it["family"] == "move_visit_and_parent"
        for d in range(2 if two else 1):
            a = it["demo_values"][d]; steps = [s for _, s in family_steps(it["family"], a)]
            mode = ":example" if two else ":teach"
            out.append(T("CMD", f"{mode} {it['name']}{hdr(a) if it['protocol']['hint'] else ''}"))
            for s in steps: out.append(T("STEP", L.fmt_step(s), teaching=True) if formal else T("NL", "<gold>", gold={"status": "OK", "steps": [s]}))
            out.append(T("CMD", ":endexample" if two else ":endteach", expect="OK" if two else "VERIFIED", name=it["name"], family=it["family"]))
        if two: out.append(T("CMD", f":learn {it['name']}", expect="VERIFIED", name=it["name"], family=it["family"]))
        out.append(T("CMD", f":accept {it['name']}", expect="OK", gold=it["gold"], name=it["name"]))
    return out


def scripted_lessons(g, sc_cur, style):
    """SCRIPTED_TEACHER (spec §30): registered lessons from the template bank; lookup responses only (band-A restatements, 'people' answer)"""
    band = {"A": "A", "B": "D", "C": "A", "D": "B", "E": "A"}[style]; out = {}
    for it in sc_cur:
        demos = []
        for d in range(3):
            a = it["demo_values"][[0, 1, 1][d]]                    # demonstration 3 differs from demonstration 1 (majority groups must vary)
            if it["family"] in NG_FAMS: units, st = g.demo_units(it["family"], a, band)
            else:
                st = family_steps(it["family"], a); units = [([p], [i], g.sentence(g.clause(p, band if band in ("A", "B") else "A", a)[0])) for i, (p, _) in enumerate(st)]
            demos.append({"example": a, "lines": [u[2] for u in units], "rephrase": [g.rephrase(u[0], a, it["family"])[len(g.tpl["rephrase_prefix"]):] for u in units],
                          "units": [u[1] for u in units]})
        out[it["name"]] = {"demos": demos, "answer": g.r.choice(g.tpl["clarify_answers"]["people"])}
    return out


def expected(turns, lib_init=None):
    """oracle expectations; lib_init = gold procedures ACTIVE at handoff"""
    W = OR.World(NG.VOCAB); lib = dict(lib_init or {}); env = {}; exp = []; verified = {}; demo_start = None; last_ok = None
    for t in turns:
        k = t["kind"]
        if k == "RESTART": exp.append(None); env = {}; continue
        if k == "ASSERT": W.assertion(t["facts"]); e = {"status": "OK"}
        elif k == "STEP": st, ret = W.run_step_text(t["text"], env, lib); e = {"status": st}
        elif k == "NL": pre = (NG.snap(W), dict(env)); st, ret = NG.run_steps(W, t["gold"]["steps"], env, lib); e = {"status": st}
        elif k == "CMD":
            c = t["text"].split()[0]
            if c in (":teach", ":example", ":revise"): env = {}; e = {"status": "OK"}; demo_start = NG.snap(W)
            elif c in (":endteach", ":endrevise", ":learn", ":save-last-as", ":endexample"):
                e = {"status": t.get("expect", "OK")}
                if t.get("expect") == "VERIFIED": verified[t["name"]] = True
                if c in (":endteach", ":endrevise", ":endexample") and demo_start is not None: NG.restore(W, demo_start); demo_start = None
            elif c == ":accept": lib[t["name"]] = L.parse_procedure(t["gold"]) if t["name"] in verified else lib.get(t["name"]); e = {"status": "OK"}
            else: e = {"status": t.get("expect", "OK")}
        elif k in ("RUN", "REQUEST"): st, ret = W.invoke(OR.plan_proc(t["plan"]), {}, lib); e = {"status": st, "return": ret}
        e["state"] = W.state(); exp.append(e)
    return exp


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=sorted(SEEDS)); a = ap.parse_args()
    tfile = os.path.join(HERE, TEMPLATES[a.suite]); TPL = json.load(open(tfile))
    extra = EXTRA_CLAUSES if a.suite == "dev" else TPL.get("_pdx_extra", {"dev": {}, "returns": {}})       # the LOCKED file carries its own (blind) extra clauses
    for kk, v in extra.get("dev", {}).items(): TPL["clauses"].setdefault(kk, v)
    for kk, v in extra.get("returns", {}).items(): TPL["returns"].setdefault(kk, v)
    rng = random.Random(SEEDS[a.suite]); g = PGen(rng, a.suite, TPL); d = os.path.join(HERE, a.suite); os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, "*.json")): os.remove(f)
    for k, cat in enumerate(PLAN[a.suite]):
        B = build(g, cat, k); sid = f"{a.suite}-{k + 1:03d}-{cat}"
        gold_lib = {it["name"]: L.parse_procedure(it["gold"]) for it in B["curriculum"]}
        post = B["post_turns"]
        sc = {"scenario_id": sid, "suite": a.suite, "stratum": cat, "stratum_name": STRATUM[cat], "style": B["style"], "fixture": B["fixture"], "teacher_pool": B["teacher_pool"],
              "eval_pool": B["eval_pool"], "curriculum": B["curriculum"], "post_turns": post}
        pre_exp = expected(B["fixture"]); sc["fixture_expected"] = pre_exp
        sc["post_expected"] = expected(B["fixture"] + post, gold_lib)[len(B["fixture"]):]
        for mode, formal in (("gold_acq_turns", False), ("formal_acq_turns", True)):
            turns = acq_turns(B["curriculum"], formal, g); sc[mode] = turns; sc[mode.replace("turns", "expected")] = expected(B["fixture"] + turns)[len(B["fixture"]):]
        sc["scripted"] = scripted_lessons(g, B["curriculum"], B["style"])
        json.dump(sc, open(os.path.join(d, f"{sid}.json"), "w"), indent=1)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    man = {"suite": a.suite, "seed": SEEDS[a.suite], "n": len(files), "plan": PLAN[a.suite], "templates_file": os.path.basename(tfile), "templates_sha256": hashlib.sha256(open(tfile, "rb").read()).hexdigest(),
           "generator_sha256": hashlib.sha256(open(os.path.realpath(__file__), "rb").read()).hexdigest(), "files_sha256": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files}}
    json.dump(man, open(os.path.join(HERE, f"PDX_{a.suite.upper()}_MANIFEST.json"), "w"), indent=1)
    print({k: v for k, v in man.items() if k not in ("files_sha256", "plan")} if a.suite == "dev" else {"suite": a.suite, "n": man["n"], "manifest": "written (contents not printed)"})


if __name__ == "__main__":
    main()
