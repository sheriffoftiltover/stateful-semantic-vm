"""NL_TEACH scenario suites (spec §23-§33, §61-§66). Strata T1-T13 x difficulty bands A-E x NAMED/OPAQUE x HINTED/UNHINTED.
Every NL teaching utterance carries its GOLD outcome (status + gold primitive steps, independent of the frontend), a registered band-A
rephrase (used only by the simulated user in the ASSISTED protocol), and the scenario carries a paired FORMAL_TEACH turn list (parent step
language, the same gold trace). Expected per-turn status / return / world state for both turn lists come from the independent oracle.
DEV and LOCKED_TEST use separate seeds AND disjoint template files (templates_dev.json / templates_locked.json).
python scenarios/nl_generate.py --suite dev|locked_test"""
import os, sys, json, random, argparse, hashlib, glob, copy, re
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "core", "ir"), os.path.join(ROOT, "core", "neural", "vendor")]
import mr_config as K, ir as IR, lang as L, catalog as CAT, oracle as OR
VOCAB = {"PERSON": set(K.PERSONS), "TIME": set(K.TIMES), "PLACE": set(K.PLACES), "TOPIC": set(K.TOPICS), "EVENT_TYPE": set(L.EVENT_TYPES), "STATUS": set(L.STATUSES)}
SEEDS = {"dev": "SEMVM-NLT-V1-DEV-20260926", "locked_test": "SEMVM-NLT-V1-LOCKED-20260926-independent"}
PLAN = {"dev": {"T1": 2, "T2": 4, "T3": 2, "T4": 2, "T5": 2, "T6": 2, "T7": 2, "T8": 2, "T9": 3, "T10": 2, "T11": 2, "T12": 2, "T13": 3},
        "locked_test": {"T1": 1, "T2": 2, "T3": 2, "T4": 1, "T5": 1, "T6": 1, "T7": 2, "T8": 1, "T9": 2, "T10": 2, "T11": 1, "T12": 2, "T13": 2}}
VC = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}
PH = {"person": "P", "time": "T", "place": "PL"}


# ---------------------------------------------------------------- gold steps per family (independent of the frontend) ------------------------
def C(v): return {"const": v}
def VAR(v): return {"var": v}
def FIND(b, t, where=(), status=None): return {"op": "FIND", "bind": b, "type": C(t), "where": [[s, r, C(x)] for s, r, x in where], "status": C(status) if status else None}


def family_steps(fam, a):
    """-> list of (pattern, return_key or None, gold step) for a demonstration with argument values a"""
    P, T, PL = a.get("person"), a.get("time"), a.get("place")
    close = lambda l: {"op": "FOR", "as": "e0", "list": VAR(l), "body": [{"op": "SET_STATUS", "obj": VAR("e0"), "value": C("CLOSED")}]}
    ret = lambda x: {"op": "RETURN", "value": VAR(x)}
    S = {
     "calls_with": [("find_calls_with", FIND("r1", "CALL", [("SELF", "WHO", P)])), ("return_calls", ret("r1"))],
     "count_open_calls_with": [("find_open_calls_with", FIND("r1", "CALL", [("SELF", "WHO", P)], "OPEN")), ("count", {"op": "COUNT", "bind": "r2", "list": VAR("r1")}), ("return_count", ret("r2"))],
     "close_calls_with": [("find_calls_with", FIND("r1", "CALL", [("SELF", "WHO", P)])), ("close_each", close("r1")), ("count", {"op": "COUNT", "bind": "r2", "list": VAR("r1")}), ("return_count", ret("r2"))],
     "move_last_reminder_and_return_call_person": [("find_last_reminder", {"op": "FIND_LAST", "bind": "r1", "type": C("REMINDER")}), ("update_when", {"op": "UPDATE", "obj": VAR("r1"), "rel": "WHEN", "value": C(T)}),
                                                   ("child", {"op": "CHILD", "bind": "r2", "obj": VAR("r1")}), ("get_who", {"op": "GET", "bind": "r3", "obj": VAR("r2"), "rel": "WHO"}), ("return_person", ret("r3"))],
     "retarget_last_email": [("find_last_email", {"op": "FIND_LAST", "bind": "r1", "type": C("EMAIL")}), ("update_recipient", {"op": "UPDATE", "obj": VAR("r1"), "rel": "RECIPIENT", "value": C(P)}), ("return_email", ret("r1"))],
     "replace_visit_location": [("find_last_visit", {"op": "FIND_LAST", "bind": "r1", "type": C("VISIT")}), ("update_where", {"op": "UPDATE", "obj": VAR("r1"), "rel": "WHERE", "value": C(PL)}), ("return_visit", ret("r1"))],
     "call_people_at": [("find_calls_at", FIND("r1", "CALL", [("PARENT", "WHEN", T)])), ("select_who", {"op": "SELECT", "bind": "r2", "list": VAR("r1"), "rel": "WHO"}), ("return_people", ret("r2"))],
     "email_topic_report": [("find_all_emails", FIND("r1", "EMAIL")), ("group_by_recipient", {"op": "GROUP", "bind": "r2", "list": VAR("r1"), "rel": "RECIPIENT"}),
                            ("report_topics", {"op": "REPORT", "bind": "r3", "groups": VAR("r2"), "rel": "TOPIC"}), ("return_report", ret("r3"))],
     "count_requests_by_at": [("find_requests_by_at", FIND("r1", "REQUEST", [("SELF", "WHO", P), ("SELF", "WHEN", T)])), ("count", {"op": "COUNT", "bind": "r2", "list": VAR("r1")}), ("return_count", ret("r2"))],
     "close_open_emails_to": [("find_open_emails_to", FIND("r1", "EMAIL", [("SELF", "RECIPIENT", P)], "OPEN")), ("close_each", close("r1")), ("return_emails", ret("r1"))],
     "person_on_call_at": [("find_calls_at", FIND("r1", "CALL", [("PARENT", "WHEN", T)])), ("first", {"op": "FIRST", "bind": "r2", "list": VAR("r1")}), ("get_who", {"op": "GET", "bind": "r3", "obj": VAR("r2"), "rel": "WHO"}), ("return_person", ret("r3"))],
     "count_calls_with": [("find_calls_with", FIND("r1", "CALL", [("SELF", "WHO", P)])), ("count", {"op": "COUNT", "bind": "r2", "list": VAR("r1")}), ("return_count", ret("r2"))],
     "move_visit_and_parent": [("find_last_visit", {"op": "FIND_LAST", "bind": "r1", "type": C("VISIT")}), ("update_where", {"op": "UPDATE", "obj": VAR("r1"), "rel": "WHERE", "value": C(PL)}),
                               ("parent", {"op": "PARENT", "bind": "r2", "obj": VAR("r1")}), ("update_where_again", {"op": "UPDATE", "obj": VAR("r2"), "rel": "WHERE", "value": C(PL)}), ("return_visit", ret("r1"))],
     "__composite": [("call_person_on_call_at", {"op": "CALL", "bind": "r1", "procedure": "person_on_call_at", "args": {"time": C(T)}}),
                     ("call_count_calls_with", {"op": "CALL", "bind": "r2", "procedure": "count_calls_with", "args": {"person": VAR("r1")}}), ("return_count", ret("r2"))]}
    return S[fam]


# RETURN forms that are licensed by the registered reference grammar for each family (never an ambiguous one; spec §63)
RETURN_FORMS = {"call_people_at": ["noun"], "move_visit_and_parent": ["noun"]}
STATUS_FAMS = ["count_open_calls_with", "close_open_emails_to"]


def fam_spec(fam): return CAT.FAMILIES[fam] if fam in CAT.FAMILIES else CAT.COMPOSITE


def gold_text(fam, name):
    return fam_spec(fam)["gold"].replace(f"PROCEDURE {fam_spec(fam).get('name', fam)}(", f"PROCEDURE {name}(", 1) if fam == "__composite" else CAT.FAMILIES[fam]["gold"].replace(f"PROCEDURE {fam}(", f"PROCEDURE {name}(", 1)


def fact_ir(f):
    occs = [(f["outer"], None, 0), (f["inner"], None, 1)] + [(VC[r], v, 2 + k) for k, (r, v, _) in enumerate(f["mods"])]
    return IR.from_graph(occs, [("TODO", occs[0], occs[1])] + [(r, occs[0] if a == "outer" else occs[1], occs[2 + k]) for k, (r, v, a) in enumerate(f["mods"])])


class Gen:
    def __init__(self, rng, suite, TPL): self.r = rng; self.suite = suite; self.tpl = TPL; self.opaque_ids = rng.sample(range(10, 100), 60)

    def world(self):
        r = self.r; P = r.sample(K.PERSONS, 7); T = r.sample(K.TIMES, 5); PLc = r.sample(K.PLACES, 4); TO = r.sample(K.TOPICS, 4)
        F = [{"outer": "REMINDER", "inner": "EMAIL", "mods": [("RECIPIENT", P[1], "inner"), ("TOPIC", TO[0], "inner")]},
             {"outer": "REQUEST", "inner": "EMAIL", "mods": [("RECIPIENT", P[4], "inner"), ("TOPIC", TO[1], "inner")]},
             {"outer": "REMINDER", "inner": "EMAIL", "mods": [("RECIPIENT", P[1], "inner"), ("TOPIC", TO[2], "inner")]},
             {"outer": "REQUEST", "inner": "EMAIL", "mods": [("RECIPIENT", P[5], "inner"), ("TOPIC", TO[3], "inner")]},
             {"outer": "REMINDER", "inner": "VISIT", "mods": [("WHERE", PLc[0], "inner")]},
             {"outer": "REQUEST", "inner": "VISIT", "mods": [("WHERE", PLc[1], "inner")]},
             {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[2], "outer"), ("WHEN", T[0], "outer")]},
             {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[5], "outer"), ("WHEN", T[1], "outer")]},
             {"outer": "REQUEST", "inner": "CALL", "mods": [("WHO", P[2], "outer"), ("WHEN", T[1], "outer")]}]
        for k in range(6): F.append({"outer": "REMINDER", "inner": "CALL", "mods": [("WHEN", T[k % 5], "outer"), ("WHO", P[[0, 1, 3, 0, 6, 3][k]], "inner")]})
        setup = ["$s0 = FIND CALL WHERE SELF.WHO=" + P[3], "FOR $s1 IN $s0 : SET_STATUS $s1 CLOSED", "$s2 = FIND EMAIL WHERE SELF.TOPIC=" + TO[2], "FOR $s3 IN $s2 : SET_STATUS $s3 CLOSED"]
        return {"P": P, "T": T, "PL": PLc, "TO": TO}, F, setup

    def pools(self, fam, V):
        P, T, PLc = V["P"], V["T"], V["PL"]
        per = {"calls_with": [P[0], P[1], P[3], P[6]], "count_open_calls_with": [P[0], P[3], P[1], P[6]], "close_calls_with": [P[0], P[1], P[6], P[3]], "retarget_last_email": [P[5], P[6], P[2], P[0]],
               "count_calls_with": [P[0], P[3], P[1], P[6]], "close_open_emails_to": [P[1], P[4], P[5], P[1]], "count_requests_by_at": [P[2], P[5], P[2]]}
        return {"PERSON": per.get(fam, P[:4]), "TIME": [T[1], T[0], T[1]] if fam == "count_requests_by_at" else [T[0], T[1], T[2], T[3], T[4]], "PLACE": [PLc[2], PLc[3], PLc[0], PLc[1]]}

    def values(self, fam, V, k):
        ps = fam_spec(fam)["params"]; pools = self.pools(fam, V); out = []
        orders = {c: (list(p) if fam == "count_requests_by_at" else self.r.sample(p, len(p))) for c, p in pools.items()}
        for i in range(k): out.append({p: orders[c][i % len(orders[c])] for p, c in ps.items()})
        return out

    # ---------------- surface realization ----------------
    def clause(self, pat, band, a, ret_forms=None):
        T = self.tpl; fill = lambda s: s.format(P=a.get("person"), T=a.get("time"), PL=a.get("place"))
        if pat in T["returns"]:
            R = T["returns"][pat]; forms = ret_forms or [f for f in ("noun", "pronoun", "plural_pronoun") if f in R]
            if band == "C": forms = [f for f in forms if f != "noun"] or forms          # band C: anaphora wherever licensed
            f = self.r.choice(forms); lst = R[f][band if band in ("A", "B") else self.r.choice("AB")] if f == "noun" else R[f]
            return fill(self.r.choice(lst)), f
        c = T["clauses"][pat]; b = band if band in c else ("A" if band == "A" else self.r.choice([x for x in ("A", "B") if x in c]))
        return fill(self.r.choice(c[b])), None

    def sentence(self, clause):
        s = self.r.choice(self.tpl["sentence"]["prefixes"]) + clause
        return s[0].upper() + s[1:] + self.tpl["sentence"]["end"]

    def rephrase(self, pats, a, fam):
        cl = [self.clause(p, "A", a, RETURN_FORMS.get(fam, ["noun"]) if p.startswith("return_") else None)[0] for p in pats]
        s = cl[0] if len(cl) == 1 else self.r.choice(self.tpl["connectors"]).format(a=cl[0], b=cl[1])
        return self.tpl["rephrase_prefix"] + s + self.tpl["sentence"]["end"]

    def demo_units(self, fam, a, band):
        """-> list of units: (patterns, step indices, utterance text, form info)"""
        st = family_steps(fam, a); pats = [p for p, _ in st]; units = []; i = 0; rf = RETURN_FORMS.get(fam)
        while i < len(st):
            if band == "D" and i + 1 < len(st) and self.r.random() < 0.75:
                key = f"{pats[i]}+{pats[i + 1]}"
                if key in self.tpl["combos"] and self.r.random() < 0.6:
                    s = self.r.choice(self.tpl["combos"][key]).format(P=a.get("person"), T=a.get("time"), PL=a.get("place")); units.append(([pats[i], pats[i + 1]], [i, i + 1], self.sentence(s))); i += 2; continue
                c1, _ = self.clause(pats[i], "B", a, rf if pats[i].startswith("return_") else None); c2, _ = self.clause(pats[i + 1], "A", a, rf if pats[i + 1].startswith("return_") else None)
                units.append(([pats[i], pats[i + 1]], [i, i + 1], self.sentence(self.r.choice(self.tpl["connectors"]).format(a=c1, b=c2)))); i += 2; continue
            b = band if band in ("A", "B", "C") else ("E" if band == "E" and pats[i] in ("find_open_calls_with", "find_open_emails_to") else self.r.choice("AB"))
            if band == "E" and pats[i] in ("find_open_calls_with", "find_open_emails_to") and i + 1 < len(st):
                c1 = self.r.choice(self.tpl["clauses"][pats[i]]["E"]).format(P=a.get("person")); c2, _ = self.clause(pats[i + 1], "A", a, rf if pats[i + 1].startswith("return_") else None)
                units.append(([pats[i], pats[i + 1]], [i, i + 1], self.sentence(self.r.choice(self.tpl["connectors"]).format(a=c1, b=c2)))); i += 2; continue
            c, _ = self.clause(pats[i], b, a, rf if pats[i].startswith("return_") else None)
            units.append(([pats[i]], [i], self.sentence(c))); i += 1
        return units, st


def T(kind, text=None, **kw): return dict({"kind": kind, "text": text}, **kw)


def nl_demo(g, fam, a, band, demo, designed=None):
    """NL turns for one demonstration (+ the matching formal step lines)"""
    units, st = g.demo_units(fam, a, band); turns = []; formal = []
    for k, (pats, idx, text) in enumerate(units):
        steps = [st[i][1] for i in idx]
        if designed == "clarify" and pats[-1] == "return_people":           # T13: plural pronoun with two compatible lists -> CLARIFY, then an answer
            q = g.sentence(g.r.choice(g.tpl["returns"]["return_people"]["plural_pronoun"]))
            if len(pats) == 2: turns.append(T("NL", g.sentence(g.clause(pats[0], "A", a)[0]), gold={"status": "OK", "steps": steps[:1]}, band=band, pats=pats[:1], demo=demo, rephrase=g.rephrase(pats[:1], a, fam))); steps = steps[1:]
            turns.append(T("NL", q, gold={"status": "CLARIFY", "steps": []}, band=band, pats=["return_people"], demo=demo, designed="clarify"))
            turns.append(T("NL", g.r.choice(g.tpl["clarify_answers"]["people"]), gold={"status": "OK", "steps": steps}, band=band, pats=["return_people"], demo=demo, designed="answer", rephrase=g.rephrase(["return_people"], a, fam)))
            continue
        if designed == "correction" and k == 0:                             # T13: the user first asks for the unfiltered calls, then corrects
            wrong = [FIND("r1", "CALL", [("SELF", "WHO", a["person"])])]
            turns.append(T("NL", g.sentence(g.clause("find_calls_with", "A", a)[0]), gold={"status": "OK", "steps": wrong}, band=band, pats=["find_calls_with"], demo=demo, designed="pre_correction", rephrase=g.rephrase(["find_calls_with"], a, fam)))
            cm = g.r.choice(g.tpl["correction_marker"]); cl = g.clause(pats[0], "A" if band != "B" else "B", a)[0]; sn = g.sentence(cl)
            turns.append(T("NL", cm[0].upper() + cm[1:] + sn[0].lower() + sn[1:], gold={"status": "OK", "steps": [st[0][1]], "undo": True}, band=band, pats=[pats[0]], demo=demo, designed="correction", rephrase=g.rephrase([pats[0]], a, fam)))
            if len(idx) > 1:
                p2 = pats[1:]; turns.append(T("NL", g.sentence(g.clause(p2[0], "A", a, RETURN_FORMS.get(fam) if p2[0].startswith("return_") else None)[0]), gold={"status": "OK", "steps": steps[1:]}, band=band, pats=p2, demo=demo, rephrase=g.rephrase(p2, a, fam)))
            continue
        turns.append(T("NL", text, gold={"status": "OK", "steps": steps}, band=band, pats=pats, demo=demo, rephrase=g.rephrase(pats, a, fam)))
    # formal: the final gold trace of the demonstration (clarify / correction artefacts removed)
    formal = [s for _, s in st]
    return turns, [T("STEP", L.fmt_step(s), teaching=True) for s in formal]


def build(g, cat, V):
    r = g.r; turns = []; formal = []; meta = {"category": cat, "procedures": []}
    def both(ts, fs=None): turns.extend(ts); formal.extend(ts if fs is None else fs)
    def name_for(fam, opaque): return f"proc_{g.opaque_ids.pop()}" if opaque else ("count_calls_for_time_person" if fam == "__composite" else fam)
    bands = ["A", "B", "C", "D", "E"]
    def teach(fam, vals, band, name, mode="one_shot_hinted", designed=None, extra=None):
        """mode: one_shot_hinted | two_hinted | unhinted_two (one-shot -> REQUIRE_SECOND_DEMONSTRATION -> :example -> :learn) | two_examples_unhinted"""
        meta["procedures"].append({"name": name, "family": fam, "mode": mode, "band": band, "opaque": name.startswith("proc_")})
        hdr = lambda a: "(" + ", ".join(f"{k}={v}" for k, v in a.items()) + ")" if a else ""
        if mode == "one_shot_hinted":
            t, f = nl_demo(g, fam, vals[0], band, 0, designed); ext = extra or []
            both([T("CMD", f":teach {name}{hdr(vals[0])}")], [T("CMD", f":teach {name}{hdr(vals[0])}")]); both(ext + t, f)
            both([T("CMD", ":endteach", expect="VERIFIED", family=fam, name=name)])
        elif mode == "unhinted_two":
            t, f = nl_demo(g, fam, vals[0], band, 0, designed); both([T("CMD", f":teach {name}")]); both((extra or []) + t, f)
            both([T("CMD", ":endteach", expect="REQUIRE_SECOND_DEMONSTRATION", family=fam, name=name)])
            t2, f2 = nl_demo(g, fam, vals[1], bands[(bands.index(band) + 1) % 5] if band != "E" else "D", 1); both([T("CMD", f":example {name}")]); both(t2, f2); both([T("CMD", ":endexample", expect="OK")])
            both([T("CMD", f":learn {name}", expect="VERIFIED", family=fam, name=name)])
        else:
            hint = mode == "two_hinted"
            for d in range(2):
                t, f = nl_demo(g, fam, vals[d], band if d == 0 else (bands[(bands.index(band) + 1) % 5] if band != "E" else "D"), d, designed if d == 0 else None)
                both([T("CMD", f":example {name}{hdr(vals[d]) if hint else ''}")]); both(((extra or []) if d == 0 else []) + t, f); both([T("CMD", ":endexample", expect="OK")])
            both([T("CMD", f":learn {name}", expect="VERIFIED", family=fam, name=name)])
    def accept(fam, name): both([T("CMD", f":accept {name}", expect="OK", gold=gold_text(fam, name), name=name)])
    def run(fam, vals, name): both([T("RUN", f"RUN {name} " + " ".join(f"{k}={v}" for k, v in vals.items()), plan={"call": name, "args": dict(vals)}, family=fam)])
    def req(fam, vals, name, plan=None): both([T("REQUEST", "REQUEST " + r.choice(fam_spec(fam)["dev" if g.suite == "dev" else "locked"]).format(**vals), plan=plan or {"call": name, "args": dict(vals)}, family=fam)])
    band = r.choice(bands)
    if cat in ("T1", "T2", "T3", "T8"):
        fam = {"T1": ["calls_with"], "T2": ["count_calls_with", "retarget_last_email", "replace_visit_location", "person_on_call_at", "move_last_reminder_and_return_call_person"],
               "T3": ["close_calls_with", "close_open_emails_to"], "T8": ["count_calls_with", "call_people_at", "retarget_last_email", "replace_visit_location", "person_on_call_at"]}[cat]
        fam = r.choice(fam); opaque = cat in ("T2", "T8") and r.random() < 0.5 or (cat == "T3" and r.random() < 0.3)
        if band == "E" and fam not in STATUS_FAMS: band = "D"
        v = g.values(fam, V, 3); nm = name_for(fam, opaque); teach(fam, v, band, nm); accept(fam, nm); run(fam, v[1], nm); both([T("RESTART")]); req(fam, v[2], nm)
    elif cat == "T4":
        fam = r.choice(["retarget_last_email", "replace_visit_location", "move_visit_and_parent"]); v = g.values(fam, V, 3); nm = name_for(fam, False)
        if band == "E": band = "D"
        teach(fam, v, band, nm, "two_hinted" if fam == "move_visit_and_parent" else "one_shot_hinted"); accept(fam, nm)
        if fam == "move_visit_and_parent":
            f = {"outer": "PLAN", "inner": "VISIT", "mods": [("WHEN", V["T"][2], "outer")]}; both([T("ASSERT", "<fixture>", facts=f, gold_ir=fact_ir(f))])
        both([T("RESTART")]); req(fam, v[2], nm); run(fam, v[1], nm)
    elif cat == "T5":
        fam = r.choice(["email_topic_report", "call_people_at"]); v = g.values(fam, V, 3) if fam != "email_topic_report" else [{}, {}, {}]; nm = name_for(fam, False)
        if band == "E": band = "D"
        teach(fam, v, band, nm, "one_shot_hinted"); accept(fam, nm); both([T("RESTART")]); req(fam, v[2], nm); run(fam, v[1], nm)
    elif cat == "T6":
        fam = "count_requests_by_at"; P2 = [V["P"][2], V["P"][5]]; T2 = [V["T"][0], V["T"][1]]; nm = name_for(fam, False)
        if band == "E": band = "D"
        teach(fam, [{"person": P2[0], "time": T2[0]}, {"person": P2[1], "time": T2[1]}], band, nm, "two_hinted"); accept(fam, nm)
        run(fam, {"person": V["P"][2], "time": V["T"][1]}, nm); both([T("RESTART")]); req(fam, {"person": V["P"][5], "time": V["T"][0]}, nm)
    elif cat == "T7":
        fam = r.choice(STATUS_FAMS); v = g.values(fam, V, 3); nm = name_for(fam, False)
        band = "E"; teach(fam, v, band, nm, "two_examples_unhinted")
        lrn = turns.pop(); formal.pop()
        if fam == "count_open_calls_with":
            bads = {"frozen_value": f"PROCEDURE {nm}() ; $v0 = FIND CALL WHERE SELF.WHO={v[0]['person']} STATUS=OPEN ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                    "param_constant": f"PROCEDURE {nm}(person:PERSON, status:STATUS) ; $v0 = FIND CALL WHERE SELF.WHO={{person}} STATUS={{status}} ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                    "dropped_constant_filter": f"PROCEDURE {nm}(person:PERSON) ; $v0 = FIND CALL WHERE SELF.WHO={{person}} ; $v1 = COUNT $v0 ; RETURN $v1 ; END",
                    "wrong_relation": f"PROCEDURE {nm}(person:PERSON) ; $v0 = FIND CALL WHERE SELF.RECIPIENT={{person}} STATUS=OPEN ; $v1 = COUNT $v0 ; RETURN $v1 ; END"}
        else:
            bads = {"frozen_value": f"PROCEDURE {nm}() ; $v0 = FIND EMAIL WHERE SELF.RECIPIENT={v[0]['person']} STATUS=OPEN ; FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED ; RETURN $v0 ; END",
                    "param_constant": f"PROCEDURE {nm}(person:PERSON, status:STATUS) ; $v0 = FIND EMAIL WHERE SELF.RECIPIENT={{person}} STATUS={{status}} ; FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED ; RETURN $v0 ; END",
                    "dropped_constant_filter": f"PROCEDURE {nm}(person:PERSON) ; $v0 = FIND EMAIL WHERE SELF.RECIPIENT={{person}} ; FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED ; RETURN $v0 ; END",
                    "wrong_relation": f"PROCEDURE {nm}(person:PERSON) ; $v0 = FIND EMAIL WHERE SELF.WHO={{person}} STATUS=OPEN ; FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED ; RETURN $v0 ; END"}
        for k in r.sample(sorted(bads), 3): both([T("CMD", f":propose {nm} <<{bads[k]}>>", expect="REJECTED", family=fam, name=nm, bad=k)])
        both([lrn]); accept(fam, nm); run(fam, v[2], nm); both([T("RESTART")]); req(fam, v[1], nm)
    elif cat == "T9":
        fam = r.choice(["count_calls_with", "retarget_last_email", "close_calls_with", "person_on_call_at", "move_visit_and_parent"]); v = g.values(fam, V, 3); nm = name_for(fam, r.random() < 0.3)
        if band == "E": band = "D"
        teach(fam, v, band, nm, "two_hinted" if fam == "move_visit_and_parent" else "unhinted_two"); accept(fam, nm); both([T("RESTART")]); req(fam, v[2], nm); run(fam, v[0], nm)
    elif cat in ("T10", "T11"):
        t = g.values("person_on_call_at", V, 3); p = g.values("count_calls_with", V, 2)
        if band == "E": band = "D"
        teach("person_on_call_at", t, band, "person_on_call_at"); accept("person_on_call_at", "person_on_call_at")
        teach("count_calls_with", p, r.choice("ABCD"), "count_calls_with"); accept("count_calls_with", "count_calls_with"); cn = CAT.COMPOSITE["name"]
        if cat == "T10":
            teach("__composite", [{"time": t[0]["time"]}], r.choice("ABD"), cn); accept("__composite", cn); both([T("RESTART")])
            run("__composite", {"time": t[1]["time"]}, cn); req("__composite", {"time": t[2]["time"]}, cn)
        else:
            both([T("RESTART")]); comp = {"call": "count_calls_with", "args": {"person": {"call": "person_on_call_at", "args": {"time": t[1]["time"]}}}}
            both([T("REQUEST", "REQUEST " + r.choice(CAT.COMPOSITE["dev" if g.suite == "dev" else "locked"]).format(time=t[1]["time"]), plan=comp, family="__composite", composition="L1")])
            both([T("CMD", f":save-last-as {cn}(time={t[1]['time']})", expect="VERIFIED", family="__composite", name=cn, composition="L2")]); accept("__composite", cn)
            both([T("RESTART")]); run("__composite", {"time": t[2]["time"]}, cn); req("__composite", {"time": t[0]["time"]}, cn)
    elif cat == "T12":
        fam = r.choice(["count_calls_with", "retarget_last_email", "replace_visit_location", "close_calls_with"]); v = g.values(fam, V, 3); nm = name_for(fam, False)
        if band == "E": band = "D"
        ftxt, ftype = r.choice(g.tpl["failing"]); fail = T("NL", g.sentence(ftxt), gold={"status": "EXEC_FAILED", "steps": [{"op": "FIND_LAST", "bind": "r1", "type": C(ftype)}, {"op": "SET_STATUS", "obj": VAR("r1"), "value": C("CLOSED")}]}, band=band, pats=["failing"], demo=0, designed="failing")
        uns = T("NL", g.sentence(r.choice(g.tpl["unsupported"]).format(P=v[0].get("person") or V["P"][0])), gold={"status": "UNSUPPORTED", "steps": []}, band=band, pats=["unsupported"], demo=0, designed="unsupported")
        teach(fam, v, band, nm, "one_shot_hinted", extra=[fail, uns]); accept(fam, nm); run(fam, v[1], nm); both([T("RESTART")]); req(fam, v[2], nm)
    elif cat == "T13":
        kind = CLAR_CYCLE[g.suite].pop(0)
        fam = "call_people_at" if kind == "clarify" else "count_open_calls_with"; v = g.values(fam, V, 3); nm = name_for(fam, False)
        if band in ("C", "E") and kind == "clarify": band = "A"
        teach(fam, v, band if kind == "clarify" else r.choice("AB"), nm, "one_shot_hinted", designed=kind); accept(fam, nm); both([T("RESTART")]); req(fam, v[2], nm); run(fam, v[1], nm)
    meta["band"] = band
    return turns, formal, meta


CLAR_CYCLE = {"dev": ["clarify", "correction", "clarify"], "locked_test": ["clarify", "correction"]}


def demo_values(turns):
    """literal example values used in each procedure's demonstrations (for UNHINTED teaching the values come from the gold steps)"""
    cur = None; out = {}
    for t in turns:
        if t["kind"] == "CMD" and t["text"].split()[0] in (":teach", ":example", ":revise"): cur = t["text"].split()[1].split("(")[0]
        if t["kind"] == "CMD" and t["text"].split()[0] == ":save-last-as": cur = t["text"].split()[1].split("(")[0]; out.setdefault(cur, set()).add(t["text"].split("=")[1].rstrip(")"))
        if t["kind"] == "NL" and cur and t["gold"].get("status") == "OK":
            for s in t["gold"]["steps"]:
                for c in re.findall(r'"const": "([^"]+)"', json.dumps(s)): out.setdefault(cur, set()).add(c)
        if t["kind"] == "STEP" and t.get("teaching") and cur:
            for c in re.findall(r"=([A-Za-z0-9:]+)", t["text"]): out.setdefault(cur, set()).add(c)
    return out


def novelty(turns):
    dv = demo_values(turns)
    for t in turns:
        if t["kind"] in ("RUN", "REQUEST") and t.get("plan"):
            def lits(pl): return [v for v in pl["args"].values() if isinstance(v, str)] + [x for v in pl["args"].values() if isinstance(v, dict) for x in lits(v)]
            t["novel_args"] = any(v not in dv.get(t["plan"]["call"], set()) for v in lits(t["plan"]))
    return turns


# ---------------------------------------------------------------- oracle expectations ----------------------------------------------------------------
def snap(W): return copy.deepcopy((W.obj, W.rels, W.alias, W.cnt, W.seq, W.attr, W.surf))
def restore(W, s): W.obj, W.rels, W.alias, W.cnt, W.seq, W.attr, W.surf = copy.deepcopy(s)


def run_steps(W, steps, env, lib):
    s0 = snap(W); e0 = dict(env)
    try:
        try:
            for s in steps: W.step(copy.deepcopy(s), env, lib)
        except OR._Ret as r: return "OK", W.render(r.v)
        return "OK", None
    except OR.OErr as e: restore(W, s0); env.clear(); env.update(e0); return e.status, None


def expected(turns):
    W = OR.World(VOCAB); lib = {}; env = {}; exp = []; verified = {}; demo_start = None; last_ok = None
    for t in turns:
        k = t["kind"]
        if k == "RESTART": exp.append(None); env = {}; continue
        if k == "ASSERT": W.assertion(t["facts"]); e = {"status": "OK"}
        elif k == "STEP":
            st, ret = W.run_step_text(t["text"], env, lib); e = {"status": st}
        elif k == "NL":
            g = t["gold"]
            if g["status"] in ("CLARIFY", "UNSUPPORTED"): e = {"status": g["status"]}
            else:
                if g.get("undo") and last_ok is not None: restore(W, last_ok[0]); env.clear(); env.update(last_ok[1])
                pre = (snap(W), dict(env)); st, ret = run_steps(W, g["steps"], env, lib); e = {"status": st}
                if st == "OK": last_ok = pre
        elif k == "CMD":
            c = t["text"].split()[0]
            if c in (":teach", ":example", ":revise"): env = {}; e = {"status": "OK"}; demo_start = snap(W); last_ok = None
            elif c in (":endteach", ":endrevise", ":learn", ":save-last-as", ":endexample") or c.startswith(":propose"):
                e = {"status": t.get("expect", "OK")}
                if t.get("expect") == "VERIFIED": verified[t["name"]] = True
                if c in (":endteach", ":endrevise", ":endexample") and demo_start is not None: restore(W, demo_start); demo_start = None   # teaching sandbox
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
    tfile = os.path.join(HERE, "templates_dev.json" if a.suite == "dev" else "templates_locked.json"); TPL = json.load(open(tfile))
    rng = random.Random(SEEDS[a.suite]); g = Gen(rng, a.suite, TPL); d = os.path.join(HERE, a.suite); os.makedirs(d, exist_ok=True); k = 0; out = []
    for f in glob.glob(os.path.join(d, "*.json")): os.remove(f)
    for cat, n in PLAN[a.suite].items():
        for _ in range(n):
            k += 1; V, facts, setup = g.world(); pre = [T("ASSERT", "<fixture>", facts=f, gold_ir=fact_ir(f)) for f in facts] + [T("STEP", s) for s in setup]
            turns, formal, meta = build(g, cat, V); turns = novelty(pre + turns); formal = novelty(copy.deepcopy(pre) + formal)
            sc = {"scenario_id": f"{a.suite}-{k:03d}-{cat}", "suite": a.suite, "category": cat, "meta": meta, "turns": turns, "expected": expected(turns),
                  "formal_turns": formal, "formal_expected": expected(formal)}
            json.dump(sc, open(os.path.join(d, f"{sc['scenario_id']}.json"), "w"), indent=1); out.append(sc)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    man = {"suite": a.suite, "seed": SEEDS[a.suite], "n": len(out), "categories": PLAN[a.suite], "templates_file": os.path.basename(tfile), "templates_sha256": hashlib.sha256(open(tfile, "rb").read()).hexdigest(),
           "generator_sha256": hashlib.sha256(open(os.path.realpath(__file__), "rb").read()).hexdigest(),
           "files_sha256": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files}}
    json.dump(man, open(os.path.join(HERE, f"{a.suite.upper()}_MANIFEST.json"), "w"), indent=1)
    if a.suite == "dev": print({k: v for k, v in man.items() if k != "files_sha256"})
    else: print({"suite": man["suite"], "n": man["n"], "manifest": "written (contents not printed)"})


if __name__ == "__main__":
    main()
