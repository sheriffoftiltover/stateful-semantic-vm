"""Deterministic procedure-runtime unit suite (spec §75; gate = 100%). No neural model: the LLM is stubbed where retrieval needs an argument call.
python tests/test_procedures.py [--out results/PROCEDURE_UNIT_TESTS.json]"""
import os, sys, json, tempfile, subprocess, traceback, argparse, copy
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("procedure", "core", "core/ir")]
import system as SY, lang as L, validate as VD, executor as X, abstraction as AB, verify as VF, retrieval as RT, llm as LM, ir as IR
TESTS = []
def test(f): TESTS.append(f); return f
VC = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}
def fact(O, I, mods):
    occs = [(O, None, 0), (I, None, 1)] + [(VC[r], v, 2 + k) for k, (r, v, _) in enumerate(mods)]
    return IR.from_graph(occs, [("TODO", occs[0], occs[1])] + [(r, occs[0] if a == "outer" else occs[1], occs[2 + k]) for k, (r, v, a) in enumerate(mods)])
WORLD = [("REMINDER", "CALL", [("WHEN", "3", "outer"), ("WHO", "Alice", "inner")]), ("REQUEST", "CALL", [("WHEN", "noon", "outer"), ("WHO", "Bob", "inner")]),
         ("REMINDER", "CALL", [("WHEN", "5", "outer"), ("WHO", "Carol", "inner")]), ("REMINDER", "EMAIL", [("RECIPIENT", "Carol", "inner"), ("TOPIC", "budget", "inner")]),
         ("REQUEST", "VISIT", [("WHERE", "Oslo", "inner")])]
def sysd(d=None, world=True):
    d = d or tempfile.mkdtemp(); S = SY.System(f"{d}/w.sqlite", f"{d}/p.sqlite", f"{d}/learn", use_llm=False)
    if world and not S.world.canonical_state()["objects"]:
        for i, (O, I, m) in enumerate(WORLD): S.process({"kind": "ASSERT", "text": "<g>", "gold_ir": fact(O, I, m)}, f"w{i}", "ts")
    return S, d
def P(S, t, k=[0]): k[0] += 1; return S.process({"text": t}, f"t{k[0]}", "ts")
def teach(S, header, steps, mode=":teach"):
    P(S, f"{mode} {header}")
    for s in steps: assert P(S, s)["status"] == "OK", s
    return P(S, {":teach": ":endteach", ":example": ":endexample", ":revise": ":endrevise"}[mode])
CALLS_WITH = ["$c = FIND CALL WHERE SELF.WHO=Alice", "RETURN $c"]

@test
def ast_validation():
    lib = sysd(world=False)[0].lib
    for bad, why in [("PROCEDURE x(p:PERSON)\n$a = FIND CALL WHERE SELF.WHO={q}\nRETURN $a\nEND", "undeclared"), ("PROCEDURE x()\nRETURN $a\nEND", "before definition"),
                     ("PROCEDURE x()\n$a = CALL nope\nRETURN $a\nEND", "non-ACTIVE"), ("PROCEDURE x()\n$a = FIND CALL WHERE SELF.WHO=noon\nRETURN $a\nEND", "not a PERSON"),
                     ("PROCEDURE x(p:PERSON)\n$a = FIND CALL\nRETURN $a\nEND", "unused"), ("PROCEDURE x()\n$a = FIND CALL\nEND", "RETURN")]:
        try: VD.validate(L.parse_procedure(bad), lib); raise AssertionError("accepted: " + why)
        except VD.ValidationError as e: assert why in e.reason, (why, e.reason)
    for bad in ["PROCEDURE x()\n$a = SHELL rm\nRETURN $a\nEND", "PROCEDURE x(p:STRING)\nRETURN $p\nEND"]:
        try: L.parse_procedure(bad); raise AssertionError("parsed unsafe")
        except L.LangError: pass
@test
def parameter_binding_and_types():
    S, _ = sysd(); S.install_gold("cw", "PROCEDURE cw(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\nRETURN $c\nEND")
    assert json.loads(P(S, "RUN cw person=Bob")["response"]) == {"events": ["call:000002"]}
    assert P(S, "RUN cw")["status"] == "MISSING_ARGUMENT" and P(S, "RUN cw person=noon")["status"] == "TYPE_ERROR" and P(S, "RUN cw person=Bob extra=1")["status"] == "TYPE_ERROR"
@test
def constant_preservation_multi_example():
    S, _ = sysd()
    for p in ("Alice", "Bob"): teach(S, "ocw", [f"$c = FIND CALL WHERE SELF.WHO={p} STATUS=OPEN", "$n = COUNT $c", "RETURN $n"], ":example")
    R = P(S, ":learn ocw")["discovery"]; prog = R["paths"]["deterministic"]["proposal"]
    assert "STATUS=OPEN" in prog and "{person}" in prog and "CALL" in prog and R["status"] == "VERIFIED", R
@test
def one_shot_ambiguity_rejected():
    S, _ = sysd(); r = teach(S, "amb(person=Alice)", ["$c = FIND CALL WHERE SELF.WHO=Alice", "$d = FILTER $c WHO=Alice", "RETURN $d"])
    assert r["status"] == "REJECTED_AMBIGUOUS", r
@test
def variable_scope_for():
    lib = sysd(world=False)[0].lib
    try: VD.validate(L.parse_procedure("PROCEDURE x()\n$l = FIND CALL\nFOR $e IN $l : SET_STATUS $e CLOSED\nRETURN $e\nEND"), lib); raise AssertionError("FOR var leaked")
    except VD.ValidationError as e: assert "before definition" in e.reason
@test
def call_procedure_and_dependencies():
    S, _ = sysd(); S.install_gold("pc", "PROCEDURE pc(time:TIME)\n$c = FIND CALL WHERE PARENT.WHEN={time}\n$f = FIRST $c\n$p = GET $f WHO\nRETURN $p\nEND")
    S.install_gold("cc", "PROCEDURE cc(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\n$n = COUNT $c\nRETURN $n\nEND")
    S.install_gold("comp", "PROCEDURE comp(time:TIME)\n$a = CALL pc time={time}\n$b = CALL cc person=$a\nRETURN $b\nEND")
    assert P(S, "RUN comp time=5")["response"] == "1"; e = S.lib.explain("comp"); assert e["dependencies"] == ["cc", "pc"]
    try: VD.validate(L.parse_procedure("PROCEDURE bad(time:TIME)\n$a = CALL pc time={time}\n$b = CALL cc person=$zz\nRETURN $b\nEND"), S.lib); raise AssertionError
    except VD.ValidationError: pass
    try: VD.validate(L.parse_procedure("PROCEDURE bad2(person:PERSON)\n$b = CALL cc person={person} extra=3\nRETURN $b\nEND"), S.lib); raise AssertionError
    except VD.ValidationError as e: assert "mismatch" in e.reason
@test
def cycle_rejection():
    S, _ = sysd(); S.install_gold("a1", "PROCEDURE a1()\n$l = FIND CALL\nRETURN $l\nEND")
    p = L.parse_procedure("PROCEDURE a1()\n$x = CALL a1\nRETURN $x\nEND")
    try: VD.validate(p, S.lib); raise AssertionError("recursion accepted")
    except VD.ValidationError as e: assert "recursion" in e.reason
@test
def source_and_counterfactual_replay():
    S, _ = sysd(); r = teach(S, "cw(person=Alice)", CALLS_WITH); d = r["discovery"]["paths"]["deterministic"]
    assert r["status"] == "VERIFIED" and all(ok for t, ok in d["tests"]) and any(t.startswith("counterfactual") for t, _ in d["tests"]) and any(t.startswith("replay") for t, _ in d["tests"])
@test
def verifier_rejects_bad_candidates():
    S, _ = sysd()
    for p in ("Alice", "Bob"): teach(S, "ocw", [f"$c = FIND CALL WHERE SELF.WHO={p} STATUS=OPEN", "$n = COUNT $c", "RETURN $n"], ":example")
    bad = {"frozen_value": "PROCEDURE ocw()\n$c = FIND CALL WHERE SELF.WHO=Alice STATUS=OPEN\n$n = COUNT $c\nRETURN $n\nEND",
           "param_constant": "PROCEDURE ocw(person:PERSON, status:STATUS)\n$c = FIND CALL WHERE SELF.WHO={person} STATUS={status}\n$n = COUNT $c\nRETURN $n\nEND",
           "dropped_filter": "PROCEDURE ocw(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\n$n = COUNT $c\nRETURN $n\nEND",
           "wrong_type": "PROCEDURE ocw(person:PERSON)\n$c = FIND EMAIL WHERE SELF.RECIPIENT={person} STATUS=OPEN\n$n = COUNT $c\nRETURN $n\nEND"}
    P(S, "$z = FIND CALL WHERE SELF.WHO=Bob"); P(S, "FOR $e IN $z : SET_STATUS $e CLOSED")     # make STATUS=OPEN matter for the counterfactual state
    for k, t in bad.items():
        r = P(S, ":propose ocw <<" + t + ">>"); assert r["status"].startswith("REJECTED"), (k, r["status"])
@test
def transaction_rollback():
    S, _ = sysd(); S.install_gold("mv", "PROCEDURE mv(place:PLACE)\n$v = FIND_LAST VISIT\nUPDATE $v WHERE={place}\n$p = PARENT $v\nUPDATE $p WHERE={place}\nRETURN $v\nEND")
    S.process({"kind": "ASSERT", "text": "<g>", "gold_ir": fact("PLAN", "VISIT", [("WHEN", "dusk", "outer")])}, "wp", "ts"); h = S.world.state_hash()
    r = P(S, "RUN mv place=Rome"); assert r["status"] == "VM_EXEC_ERROR" and S.world.state_hash() == h and r["state_unchanged"], r
    r = X.invoke(S.world, S.lib, S.lib.active("mv"), {"place": "Rome"}, fail_after_ops=2); assert r["status"] == "VM_EXEC_ERROR" and r["state_before"] == r["state_after"]
@test
def restart_persistence():
    S, d = sysd(); r = teach(S, "cw(person=Alice)", CALLS_WITH); P(S, ":accept cw"); h = S.lib.hash(); S.close()
    code = (f"import sys; sys.path[:0]=[{os.path.join(ROOT,'procedure')!r},{os.path.join(ROOT,'core')!r}]; import system as SY; S=SY.System({d+'/w.sqlite'!r},{d+'/p.sqlite'!r},{d+'/learn'!r},use_llm=False);"
            f"r=S.process({{'text':'RUN cw person=Carol'}},'x','ts'); print(r['response']); print(S.lib.hash())")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.split("\n")
    assert json.loads(out[0]) == {"events": ["call:000003"]} and out[1] == h, out
@test
def versioning_and_revision():
    S, _ = sysd(); teach(S, "cnt(person=Alice)", ["$c = FIND CALL WHERE SELF.WHO=Alice", "$n = COUNT $c", "RETURN $n"]); P(S, ":accept cnt"); v1 = S.lib.active_id("cnt")
    r = teach(S, "cnt(person=Alice)", ["$c = FIND CALL WHERE SELF.WHO=Alice STATUS=OPEN", "$n = COUNT $c", "RETURN $n"], ":revise"); assert r["status"] == "VERIFIED"
    P(S, ":accept cnt"); vs = S.lib.versions("cnt"); assert [v["status"] for v in vs] == ["RETIRED", "ACTIVE"] and vs[1]["parent"] == v1 and S.lib.active_id("cnt").endswith(":v2")
@test
def disable_enable_delete():
    S, _ = sysd(); S.install_gold("cw", "PROCEDURE cw(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\nRETURN $c\nEND")
    P(S, ":disable-procedure cw"); assert P(S, "RUN cw person=Bob")["status"] == "UNKNOWN_PROCEDURE"
    P(S, ":enable-procedure cw"); assert P(S, "RUN cw person=Bob")["status"] == "OK"
    P(S, ":delete-procedure cw"); assert P(S, "RUN cw person=Bob")["status"] == "UNKNOWN_PROCEDURE" and S.lib.versions("cw")[0]["status"] == "DELETED"
@test
def activation_requires_verified():
    S, _ = sysd(); r = teach(S, "amb(person=Alice)", ["$c = FIND CALL WHERE SELF.WHO=Alice", "$d = FILTER $c WHO=Alice", "RETURN $d"])
    assert P(S, ":accept amb")["status"] == "NOTHING_TO_ACCEPT"
    try: S.lib.activate(r["id"]); raise AssertionError("activated a rejected candidate")
    except PermissionError: pass
@test
def alias_and_ambiguous_retrieval():
    S, _ = sysd(); S.install_gold("cw", "PROCEDURE cw(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\nRETURN $c\nEND"); S.install_gold("cc", "PROCEDURE cc(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\n$n = COUNT $c\nRETURN $n\nEND")
    orig = LM.generate_call; LM.generate_call = lambda req, procs, name: (f"{name}(person=Bob)", "")
    try:
        P(S, ":alias cw call list"); r = P(S, "REQUEST give me the call list for Bob"); assert r["status"] == "OK" and r["plan"] == "cw(person=Bob)", r
        P(S, ":alias cc call list"); r = P(S, "REQUEST give me the call list for Bob"); assert r["status"] == "CLARIFY" and "2 procedures" in r["response"], r
        LM.generate_call = lambda req, procs, name: (f"{name}(person=Zoe)", "")
        P(S, ":alias cw only mine")
        # ENGINEERING_LOG #3: a hallucinated value is still rejected; the typed fallback then binds the value that actually occurs in the request
        r = P(S, "REQUEST only mine for Bob"); rr = r["retrieval"]
        assert r["status"] == "OK" and "does not occur" in rr["llm_argument_error"] and rr["argument_source"] == "typed_fallback" and r["plan"] == "cw(person=Bob)", r
        r = P(S, "REQUEST only mine for nobody"); assert r["status"] == "CLARIFY" and "no typed candidate" in r["response"], r     # no valid value anywhere -> CLARIFY
    finally: LM.generate_call = orig
@test
def unsuccessful_trace_not_learned():
    S, _ = sysd(); P(S, ":teach bad(person=Alice)"); P(S, "$v = FIND_LAST MESSAGE"); r = P(S, ":endteach"); assert r["status"] == "TRACE_FAILED", r
@test
def canonical_hashing():
    a = L.parse_procedure("PROCEDURE a(person:PERSON)\n$x = FIND CALL WHERE SELF.WHO={person}\nRETURN $x\nEND")
    b = L.parse_procedure("PROCEDURE other_name(p:PERSON)\n$x = FIND CALL WHERE SELF.WHO={p}\nRETURN $x\nEND")
    c = L.parse_procedure("PROCEDURE a(person:PERSON)\n$x = FIND EMAIL WHERE SELF.RECIPIENT={person}\nRETURN $x\nEND")
    assert L.program_hash(a) == L.program_hash(b) != L.program_hash(c); assert L.parse_procedure(L.fmt_procedure(a)) == a
@test
def composition_level2_save_last():
    S, _ = sysd(); S.install_gold("pc", "PROCEDURE pc(time:TIME)\n$c = FIND CALL WHERE PARENT.WHEN={time}\n$f = FIRST $c\n$p = GET $f WHO\nRETURN $p\nEND")
    S.install_gold("cc", "PROCEDURE cc(person:PERSON)\n$c = FIND CALL WHERE SELF.WHO={person}\n$n = COUNT $c\nRETURN $n\nEND")
    orig = LM.score_names, LM.generate_call
    LM.score_names = lambda req, procs: ([0.0 if p["name"] == "cc" else -9.0 for p in procs], ""); LM.generate_call = lambda req, procs, name: ("cc(person=pc(time=3))", "")
    try:
        r = P(S, "REQUEST count calls with the person on my 3 call"); assert r["status"] == "OK" and r["return"] == 1, r
        r = P(S, ":save-last-as cct(time=3)"); assert r["status"] == "VERIFIED", r["discovery"]["paths"]
        P(S, ":accept cct"); assert P(S, "RUN cct time=noon")["response"] == "1"
    finally: LM.score_names, LM.generate_call = orig


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "PROCEDURE_UNIT_TESTS.json")); a = ap.parse_args(); R = {}
    for f in TESTS:
        try: f(); R[f.__name__] = "PASS"
        except Exception: R[f.__name__] = "FAIL: " + " | ".join(traceback.format_exc().splitlines()[-3:])
    n = sum(v == "PASS" for v in R.values()); out = {"passed": n, "total": len(R), "pass_rate": n / len(R), "tests": R}
    os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
