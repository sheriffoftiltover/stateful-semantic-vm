"""Deterministic-runtime unit suite (spec §39, M2 gate = 100%). Gold IR only; no neural model. Plain-python runner:
python tests/test_runtime.py [--out results/UNIT_TESTS.json]"""
import os, sys, json, tempfile, subprocess, traceback, argparse
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import pipeline as PL
import ir as IR, resolver as RS, vm as VM, store as ST
TESTS = []
def test(f): TESTS.append(f); return f
def gold(O, I, mods):
    """mods: [(rel, value, 'outer'|'inner')] -> gold IR via the canonical converter"""
    occs = [(O, None, 0), (I, None, 2)] + [({"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}[r], v, 10 + k) for k, (r, v, _) in enumerate(mods)]
    edges = [("TODO", occs[0], occs[1])] + [(r, occs[0] if a == "outer" else occs[1], occs[2 + k]) for k, (r, v, a) in enumerate(mods)]
    return IR.from_graph(occs, edges)
def sess(path=None): return PL.Session(path or tempfile.mktemp(suffix=".db"), mode="GOLD_IR")
def A(s, uid, ir_, ts="2026-09-26T16:00:00-07:00"): return s.process(uid, {"kind": "ASSERT", "text": "<gold>", "gold_ir": ir_}, ts)
def Q(s, uid, text, ts="2026-09-26T16:00:00-07:00"): return s.process(uid, {"kind": "COMMAND", "text": text}, ts)
def raises(fn, cls, reason=None):
    try: fn()
    except cls as e:
        assert reason is None or reason in e.reason, e.reason; return
    raise AssertionError("expected exception")

# ---------------- IR ----------------
@test
def ir_canonical_order_and_roundtrip():
    a = gold("REMINDER", "CALL", [("WHO", "Alice", "inner"), ("WHEN", "5", "outer")]); b = gold("REMINDER", "CALL", [("WHEN", "5", "outer"), ("WHO", "Alice", "inner")])
    assert IR.dumps(a) == IR.dumps(b); assert IR.canonical(json.loads(IR.dumps(a))) == IR.canonical(a); IR.validate(a)
@test
def ir_type_and_signature_errors():
    g = gold("REMINDER", "CALL", [("WHEN", "5", "outer")])
    bad = json.loads(json.dumps(g)); bad["objects"][0]["type"] = "FOO"; raises(lambda: IR.validate(bad), IR.IRError, "UNKNOWN_TYPE")
    bad = json.loads(json.dumps(g)); bad["relations"][1]["predicate"] = "WHO"; raises(lambda: IR.validate(bad), IR.IRError, "SIGNATURE WHO")
    bad = json.loads(json.dumps(g)); bad["relations"].append({"predicate": "WHEN", "subject": "e1", "object": "v9"}); raises(lambda: IR.validate(bad), IR.IRError, "DANGLING")
    bad = json.loads(json.dumps(g)); bad["objects"].append(dict(bad["objects"][0])); raises(lambda: IR.validate(bad), IR.IRError, "DUPLICATE_LOCAL_ID")
    bad = json.loads(json.dumps(g)); bad["relations"] = [r for r in bad["relations"] if r["predicate"] != "TODO"]; raises(lambda: IR.validate(bad), IR.IRError, "TODO_COUNT")
@test
def ir_constructor_matrix():
    g = gold("NOTE", "CALL", [("WHO", "Alice", "outer")]); raises(lambda: IR.validate(g), IR.IRError, "CONSTRUCTOR_NOT_ALLOWED WHO|NOTE")
@test
def ir_unattached_value():
    g = gold("REMINDER", "CALL", [("WHEN", "5", "outer")]); g["relations"] = [r for r in g["relations"] if r["predicate"] != "WHEN"]; raises(lambda: IR.validate(g), IR.IRError, "VALUE_NOT_ATTACHED")

# ---------------- resolver ----------------
@test
def resolver_new_existing_alias_reuse():
    s = sess(); t1 = A(s, "u1", gold("REMINDER", "CALL", [("WHO", "Alice", "inner")])); t2 = A(s, "u2", gold("PLAN", "VISIT", [("WHO", "Alice", "inner")]))
    assert t1["RESOLUTION"][2][3] == "NEW" and t2["RESOLUTION"][2][3] == "EXISTING"
    assert len([o for o in s.store.canonical_state()["objects"] if o[1] == "PERSON"]) == 1
@test
def resolver_ambiguity_no_mutation():
    s = sess(); Q(s, "u1", "NEW PERSON Alice"); Q(s, "u2", "NEW PERSON Alice"); h = s.store.state_hash()
    t = A(s, "u3", gold("REMINDER", "CALL", [("WHO", "Alice", "inner")])); assert t["status"] == "RESOLUTION_AMBIGUOUS" and s.store.state_hash() == h
@test
def resolver_time_normalization():
    assert RS.norm_time("5") == "05:00" and RS.norm_time("1:30") == "01:30" and RS.norm_time("noon") == "NOON" and RS.norm_time("12") == "12:00"
    raises(lambda: RS.norm_time("tomorrow"), RS.ResolveError)
@test
def resolver_reference():
    s = sess(); t = Q(s, "u0", "DELETE LAST_CALL"); assert t["status"] == "RESOLVE_REFERENCE"
    A(s, "u1", gold("REMINDER", "CALL", [("WHO", "Alice", "inner")])); A(s, "u2", gold("REMINDER", "CALL", [("WHO", "Bob", "inner")]))
    assert RS.resolve_ref(s.store, "LAST_CALL") == "call:000002"

# ---------------- compiler / VM ----------------
@test
def compiler_expected_program():
    s = sess(); r, _ = RS.resolve_assertion(gold("REMINDER", "CALL", [("WHO", "Alice", "inner"), ("WHEN", "5", "outer")]), s.store)
    exp = [("CREATE", "REMINDER", "$e0"), ("CREATE", "CALL", "$e1"), ("CREATE", "PERSON", "$v0"), ("ADD_ALIAS", "$v0", "Alice"), ("ENSURE_VALUE", "time:05:00", "TIME", "05:00", "5"),
           ("ASSERT", "$e0", "TODO", "$e1"), ("ASSERT", "$e0", "WHEN", "time:05:00"), ("ASSERT", "$e1", "WHO", "$v0")]
    assert VM.compile_assertion(r) == exp, VM.compile_assertion(r)
@test
def vm_create_assert_query():
    s = sess(); A(s, "u1", gold("REMINDER", "CALL", [("WHO", "Alice", "inner"), ("WHEN", "5", "outer")]))
    assert Q(s, "q1", "QUERY WHO OF CALL")["RETURN_RENDERED"] == ["Alice"]
    assert Q(s, "q2", "QUERY WHEN OF REMINDER")["RETURN_RENDERED"] == ["5"]
    assert Q(s, "q3", "QUERY WHEN OF CALL")["RETURN"] == []
    assert Q(s, "q4", "QUERY WHO OF CALL WHERE PARENT.WHEN=5")["RETURN_RENDERED"] == ["Alice"]
    assert Q(s, "q5", "QUERY WHO OF CALL WHERE PARENT.WHEN=noon")["RETURN"] == []
    assert Q(s, "q6", "QUERY WHEN OF REMINDER WHERE CHILD.WHO=Alice")["RETURN_RENDERED"] == ["5"]
@test
def vm_update_retract_delete():
    s = sess(); A(s, "u1", gold("REMINDER", "CALL", [("WHEN", "5", "outer")]))
    t = Q(s, "u2", "UPDATE LAST_REMINDER WHEN=noon"); assert t["status"] == "OK" and ["-rel", "reminder:000001", "WHEN", "time:05:00"] in t["STATE_DIFF"]
    assert Q(s, "q", "QUERY WHEN OF REMINDER")["RETURN_RENDERED"] == ["noon"]
    Q(s, "u3", "RETRACT LAST_REMINDER WHEN"); assert Q(s, "q2", "QUERY WHEN OF REMINDER")["RETURN"] == []
    Q(s, "u4", "DELETE LAST_CALL"); st = s.store.canonical_state(); assert all(o[0] != "call:000001" for o in st["objects"]) and not any("call:000001" in r for r in st["relations"])
@test
def vm_rollback_on_postcondition():
    s = sess(); A(s, "u1", gold("REMINDER", "VISIT", [("WHO", "Alice", "inner")])); h = s.store.state_hash()
    t = Q(s, "u2", "UPDATE LAST_VISIT WHO=Bob RECIPIENT=Bob")      # WHO retract+assert executes, then RECIPIENT|VISIT violates the matrix
    assert t["status"] == "VM_EXEC_ERROR" and s.store.state_hash() == h
    assert Q(s, "q", "QUERY WHO OF VISIT")["RETURN_RENDERED"] == ["Alice"]
@test
def vm_rollback_injected():
    s = sess(); h = s.store.state_hash(); t = s.process("u1", {"kind": "ASSERT", "text": "<gold>", "gold_ir": gold("REMINDER", "CALL", [("WHEN", "5", "outer")]), "_test_fail_after": 3}, "ts")
    assert t["status"] == "VM_EXEC_ERROR" and s.store.state_hash() == h
@test
def update_same_new_person_once():
    s = sess(); A(s, "u1", gold("REMINDER", "EMAIL", [("TOPIC", "budget", "inner")]))
    prog = VM.compile_command(VM.parse_command("UPDATE LAST_EMAIL WHO=Bob RECIPIENT=Bob"), s.store)
    assert [i for i in prog if i[0] == "CREATE"] == [("CREATE", "PERSON", "$new_Bob")], prog
    t = Q(s, "u2", "UPDATE LAST_EMAIL WHO=Bob RECIPIENT=Bob"); assert t["status"] == "OK" and len([o for o in s.store.canonical_state()["objects"] if o[1] == "PERSON"]) == 1
@test
def command_syntax():
    for bad in ("QUERY WHO CALL", "UPDATE CALL WHO=Alice", "RETRACT LAST_CALL FOO", "QUERY WHO OF CALL WHERE GRAND.WHO=Alice", "UPDATE LAST_CALL WHEN=Alice", "NEW PERSON Zorro"):
        raises(lambda: VM.parse_command(bad), VM.VMError)
    assert VM.parse_command("QUERY WHO OF LAST_CALL WHERE SELF.WHEN=5 PARENT.WHERE=Oslo")["where"] == [("SELF", "WHEN", "5"), ("PARENT", "WHERE", "Oslo")]

# ---------------- persistence / determinism ----------------
@test
def persistence_restart():
    db = tempfile.mktemp(suffix=".db"); s = sess(db); A(s, "u1", gold("REMINDER", "CALL", [("WHO", "Alice", "inner")])); h = s.store.state_hash(); s.close()
    code = f"import sys; sys.path.insert(0,{ROOT!r}); import pipeline as PL; s=PL.Session({db!r},'GOLD_IR'); t=s.process('q',{{'kind':'COMMAND','text':'QUERY WHO OF CALL'}},'ts'); print(t['RETURN_RENDERED'], s.store.state_hash())"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.split()
    assert out[0] == "['Alice']" and out[1] == h, out
@test
def determinism_bit_identical():
    def run():
        s = sess(); A(s, "u1", gold("REQUEST", "EMAIL", [("TOPIC", "budget", "inner"), ("WHEN", "noon", "outer")])); Q(s, "u2", "UPDATE LAST_EMAIL TOPIC=trip")
        t = Q(s, "q", "QUERY TOPIC OF EMAIL WHERE PARENT.WHEN=noon"); return json.dumps([t["VM_PROGRAM"], t["RETURN"], s.store.canonical_state(), t["RESPONSE"]])
    assert run() == run()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "UNIT_TESTS.json")); a = ap.parse_args(); R = {}
    for f in TESTS:
        try: f(); R[f.__name__] = "PASS"
        except Exception: R[f.__name__] = "FAIL: " + traceback.format_exc().splitlines()[-1]
    n = sum(v == "PASS" for v in R.values()); out = {"passed": n, "total": len(R), "pass_rate": n / len(R), "tests": R}
    os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
