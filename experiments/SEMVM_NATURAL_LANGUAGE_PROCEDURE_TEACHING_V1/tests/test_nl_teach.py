"""Deterministic NL_TEACH unit tests (spec §52). No LLM: grounding post-checks are driven by a scripted grounder; teaching-session behaviour
by GOLD_TRACE actions. python tests/test_nl_teach.py [--out results/NL_TEACH_UNIT_TESTS.json]"""
import os, sys, json, copy, tempfile, subprocess, argparse, hashlib, shutil, glob
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("nlteach", "procedure", "core", "core/ir", "scenarios")]
import frontend as F, nlsystem as NS, lang as L
R = F.Result


def ctx(results=(), procs=()):
    c = {"results": list(results), "procs": list(procs), "procs_line": "(none)"}; return c


class Scripted(F.Grounder):
    """a grounder whose 'LLM' returns scripted complete hypotheses (text, score)"""
    def __init__(self, hyps, margin=F.MARGIN): self.margin = margin; self.beam = 3; self.prefix = ""; self.hyps = hyps
    def decode(self, utt, c):
        out = []
        for text, sc in self.hyps:
            h = F.Hyp(); h.text = text; h.score = sc; h.actions = F.parse_actions(text); h.done = True; out.append(h)
        return sorted(out, key=lambda h: -h.score), 0, ""


CALLS = R("r1", '{"op": "FIND", "type": "CALL", "where": {"WHO": "Alice"}}', "EVENT_LIST", "CALL", 2)
PEOPLE = R("r2", '{"op": "SELECT", "of": "r1", "rel": "WHO"}', "VALUE_LIST", None, 2)
CNT = R("r2", '{"op": "COUNT", "of": "r1"}', "INT")


def t_schema_parsing():
    a = F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Alice"}, "status": "OPEN"}\n{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}\n')
    assert a[0]["bind"] == "r1" and a[0]["where"] == {"WHO": "Alice"} and a[1]["each"] == "r1"
    for bad in ('r1 = {"op": "SHELL", "cmd": "rm"}', "FIND CALL", 'r1 = {"op": "FIND", "type": '):
        try: F.parse_actions(bad); raise AssertionError(bad)
        except F.SchemaError: pass


def t_primitive_selection():
    g = F.Grounder.__new__(F.Grounder); c = dict(ctx([CALLS]), values=F.mentioned_values("x"), nouns=set())
    ops = {o[1][1] for o in g.options(F.Hyp(), c) if o[1][0] == "OP"}
    assert ops <= set(F.OPS) and "CALL" not in ops and "UPDATE" not in ops          # no procedures active; no value to update with
    assert {"COUNT", "FIRST", "SET_STATUS", "RETURN"} <= ops and "FIND" not in ops                   # V1.2: no named event type -> no event search
    c3 = dict(ctx([CALLS]), values=F.mentioned_values("find the calls"), nouns=F.nouns_in("find the calls")); assert "FIND" in {o[1][1] for o in g.options(F.Hyp(), c3) if o[1][0] == "OP"}
    c2 = dict(ctx(), values=F.mentioned_values("find my visits"), nouns=F.nouns_in("find my visits")); h = F.Hyp(); h.cur = {"op": "FIND"}; h.stage = "type"
    assert {o[1][1]["type"] for o in g.options(h, c2)} == {"VISIT"}                  # EVENT_TYPE values restricted to named type nouns


def t_argument_normalization():
    assert F.canon_value("3:00", "TIME") == "3" and F.canon_value("alice", "PERSON") == "Alice" and F.canon_value("PARIS.", "PLACE") == "Paris"
    v = F.mentioned_values("Find Alice's calls at 3:00 in rome")
    assert v["PERSON"] == ["Alice"] and v["TIME"] == ["3"] and v["PLACE"] == ["Rome"]


def t_typed_validation():
    c = ctx(); assert F.validate_actions(F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Bob"}}'), c, "find the calls with Alice")      # value not in instruction
    assert F.validate_actions(F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "noon"}}'), c, "calls at noon")                             # wrong class
    assert F.validate_actions(F.parse_actions('{"op": "COUNT", "of": "r7"}'), c, "count them")                                                                  # unknown result
    assert not F.validate_actions(F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Alice"}}'), c, "find the calls with Alice")


def t_multi_action_segmentation():
    acts = F.parse_actions('r1 = {"op": "FIND", "type": "EMAIL", "where": {"RECIPIENT": "Bob"}, "status": "OPEN"}\n{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}\n{"op": "RETURN", "value": "r1"}')
    st = F.to_steps(acts, [0]); assert [s["op"] for s in st] == ["FIND", "FOR", "RETURN"] and st[1]["as"] == "e0" and st[1]["body"][0]["op"] == "SET_STATUS"
    assert L.fmt_step(st[0]) == "$r1 = FIND EMAIL WHERE SELF.RECIPIENT=Bob STATUS=OPEN"
    st2 = F.to_steps(F.parse_actions('r1 = {"op": "FIND", "type": "REQUEST", "where": {"WHEN": "3", "WHO": "Bob"}}'), [0])
    assert [w[1] for w in st2[0]["where"]] == ["WHO", "WHEN"]                             # canonical constraint order


def t_local_anaphora():
    a, notes, why = F.reference_check(F.parse_actions('{"op": "RETURN", "value": "r1"}'), ctx([CALLS, CNT]), "Return the count."); assert why is None and a[0]["value"] == "r2"   # R2 repair
    a, notes, why = F.reference_check(F.parse_actions('{"op": "RETURN", "value": "r2"}'), ctx([CALLS, CNT]), "Return it."); assert why is None and a[0]["value"] == "r2"          # R3
    a, notes, why = F.reference_check(F.parse_actions('r2 = {"op": "COUNT", "of": "r1"}'), ctx([CALLS]), "Count them."); assert why is None                                      # R0
    a, notes, why = F.reference_check(F.parse_actions('r2 = {"op": "FIND", "type": "EMAIL"}\nr3 = {"op": "COUNT", "of": "r2"}'), ctx([CALLS]), "Find my emails and count them."); assert why is None   # R1


def t_clarify_ambiguous_variable():
    a, notes, why = F.reference_check(F.parse_actions('{"op": "RETURN", "value": "r2"}'), ctx([CALLS, PEOPLE]), "Return them."); assert why and "ambiguous" in why
    G = Scripted([('{"op": "RETURN", "value": "r2"}\n', -0.1)]); out = F.ground("Return them.", ctx([CALLS, PEOPLE]), G); assert out["status"] == "CLARIFY"
    out = F.ground("Return them. (I mean the people)", ctx([CALLS, PEOPLE]), Scripted([('{"op": "RETURN", "value": "r1"}\n', -0.1)])); assert out["status"] == "OK" and out["actions"][0]["value"] == "r2"
    out = F.ground("Find the calls with Alice.", ctx(), Scripted([('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Alice"}}\n', -0.5), ('r1 = {"op": "FIND", "type": "CALL", "where": {"RECIPIENT": "Alice"}}\n', -0.9)]))
    assert out["status"] == "CLARIFY" and out.get("clarify_kind") == "MARGIN"           # distinct canonical outcomes within MARGIN
    out = F.ground("Find Bob's requests at 3.", ctx(), Scripted([('r1 = {"op": "FIND", "type": "REQUEST", "where": {"WHO": "Bob", "WHEN": "3"}}\n', -0.5), ('r1 = {"op": "FIND", "type": "REQUEST", "where": {"WHEN": "3", "WHO": "Bob"}}\n', -0.6)]))
    assert out["status"] == "OK"                                                          # equivalent after canonicalization -> collapsed, not a tie


def t_unsupported_rejection():
    out = F.ground("Send Alice a Slack message.", ctx(), Scripted([('{"op": "UNSUPPORTED"}\n', -0.2), ('r1 = {"op": "FIND", "type": "MESSAGE", "where": {"WHO": "Alice"}}\n', -3.0)]))
    assert out["status"] == "UNSUPPORTED"
    with tempfile.TemporaryDirectory() as d:
        S = world(d); S.process({"text": ":teach calls_with(person=Alice)"}, "u:1", "t1"); h0 = S.world.state_hash()
        r = S.process({"kind": "NL", "text": "Post it on Slack.", "gold_outcome": {"status": "UNSUPPORTED", "steps": []}}, "u:2", "t2")
        assert r["status"] == "UNSUPPORTED" and S.world.state_hash() == h0 and S.teach["steps"] == []; S.close()


def world(d, mode="GOLD_TRACE"):
    import nl_generate as G, random
    g = G.Gen(random.Random(5), "dev", json.load(open(os.path.join(ROOT, "scenarios", "templates_dev.json")))); V, facts, setup = g.world()
    S = NS.NLSystem(os.path.join(d, "w.sqlite"), os.path.join(d, "p.sqlite"), os.path.join(d, "learn"), mode=mode)
    for f in facts: S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": G.fact_ir(f)}, "fx", "t0")
    S.V = V; return S


def FINDC(p): return {"op": "FIND", "bind": "r1", "type": {"const": "CALL"}, "where": [["SELF", "WHO", {"const": p}]], "status": None}


def t_teaching_transaction_rollback():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); S.process({"text": ":teach calls_with(person=Alice)"}, "u:1", "t1"); h0 = S.world.state_hash()
        steps = [{"op": "FIND_LAST", "bind": "r1", "type": {"const": "EMAIL"}}, {"op": "UPDATE", "obj": {"var": "r1"}, "rel": "RECIPIENT", "value": {"const": "Bob"}},
                 {"op": "FIND_LAST", "bind": "r2", "type": {"const": "PLAN"}}]                     # third step fails: NOT_FOUND after a mutation
        r = S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "EXEC_FAILED", "steps": steps}}, "u:2", "t2")
        assert r["status"] == "NOT_FOUND" and S.world.state_hash() == h0 and r["state_unchanged"] and S.teach["steps"] == []; S.close()


def t_teaching_sandbox_reset():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); h0 = S.world.state_hash(); P = S.V["P"][0]
        S.process({"text": f":teach close_calls_with(person={P})"}, "u:1", "t1")
        for k, st in enumerate([[FINDC(P)], [{"op": "FOR", "as": "e0", "list": {"var": "r1"}, "body": [{"op": "SET_STATUS", "obj": {"var": "e0"}, "value": {"const": "CLOSED"}}]}],
                                [{"op": "COUNT", "bind": "r2", "list": {"var": "r1"}}], [{"op": "RETURN", "value": {"var": "r2"}}]]):
            r = S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": st}}, f"u:{k + 2}", f"t{k + 2}"); assert r["status"] == "OK"
        assert S.world.state_hash() != h0
        r = S.process({"text": ":endteach"}, "u:9", "t9"); assert r["status"] == "VERIFIED" and r.get("sandbox_restored") and S.world.state_hash() == h0; S.close()


def t_trace_provenance_and_failed_not_evidence():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P = S.V["P"][0]; Q = S.V["P"][1]
        S.process({"text": f":teach calls_with(person={P})"}, "u:1", "t1")
        S.process({"kind": "NL", "text": "take my latest plan and close it", "gold_outcome": {"status": "EXEC_FAILED", "steps": [{"op": "FIND_LAST", "bind": "r1", "type": {"const": "PLAN"}}]}}, "u:2", "t2")
        S.process({"kind": "NL", "text": "Return them.", "gold_outcome": {"status": "CLARIFY", "steps": []}}, "u:3", "t3")
        S.process({"kind": "NL", "text": "find the calls with Q", "gold_outcome": {"status": "OK", "steps": [FINDC(Q)]}}, "u:4", "t4")
        S.process({"kind": "NL", "text": "No, find the calls with P", "gold_outcome": {"status": "OK", "steps": [FINDC(P)], "undo": True}}, "u:5", "t5")
        S.process({"kind": "NL", "text": "return them", "gold_outcome": {"status": "OK", "steps": [{"op": "RETURN", "value": {"var": "r1"}}]}}, "u:6", "t6")
        assert S.teach["steps"] == [FINDC(P), {"op": "RETURN", "value": {"var": "r1"}}]      # failed, clarified and undone proposals are NOT evidence
        r = S.process({"text": ":endteach"}, "u:7", "t7"); assert r["status"] == "VERIFIED"
        tt = json.load(open(glob.glob(os.path.join(d, "learn", "teaching_traces", "*.json"))[0]))
        assert len(tt["utterances"]) >= 5 and tt["trace_sha256"] and tt["start_snapshot_sha256"] and any(u.get("undo") for u in tt["utterances"])
        ex = json.load(open(os.path.join(d, "learn", "examples.json")))["calls_with"][0]["steps"]; assert ex == [FINDC(P), {"op": "RETURN", "value": {"var": "r1"}}]; S.close()


def t_require_second_demonstration():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P, Q = S.V["P"][0], S.V["P"][1]
        S.process({"text": ":teach proc_11"}, "u:1", "t1")
        for k, st in enumerate([[FINDC(P)], [{"op": "RETURN", "value": {"var": "r1"}}]]): S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": st}}, f"u:{k + 2}", "t")
        r = S.process({"text": ":endteach"}, "u:4", "t4"); assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION" and S.lib.versions("proc_11") == []
        S.process({"text": ":example proc_11"}, "u:5", "t5")
        for k, st in enumerate([[FINDC(Q)], [{"op": "RETURN", "value": {"var": "r1"}}]]): S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": st}}, f"u:{k + 6}", "t")
        S.process({"text": ":endexample"}, "u:8", "t8"); r = S.process({"text": ":learn proc_11"}, "u:9", "t9"); assert r["status"] == "VERIFIED"
        assert L.parse_procedure(r["discovery"]["paths"]["deterministic"]["proposal"])["parameters"][0]["type"] == "PERSON"; S.close()


def t_prompt_model_hash_recording():
    h1 = hashlib.sha256(F.prompt_prefix().encode()).hexdigest(); h2 = hashlib.sha256(F.prompt_prefix().encode()).hexdigest(); assert h1 == h2
    lock = os.path.join(ROOT, "locks", "NL_TEACH_POC_LOCK.json")
    if os.path.exists(lock):
        L0 = json.load(open(lock)); fz = L0.get("integration_freeze")
        if fz: assert fz["prompt_prefix_sha256"] == h1, "prompt changed after the integration freeze"


def t_restart_without_teaching_transcript():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P, Q = S.V["P"][0], S.V["P"][3]
        S.process({"text": f":teach calls_with(person={P})"}, "u:1", "t1")
        for k, st in enumerate([[FINDC(P)], [{"op": "RETURN", "value": {"var": "r1"}}]]): S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": st}}, f"u:{k + 2}", "t")
        assert S.process({"text": ":endteach"}, "u:4", "t4")["status"] == "VERIFIED"; S.process({"text": ":accept calls_with"}, "u:5", "t5"); S.close()
        shutil.rmtree(os.path.join(d, "learn"))                                                   # NO teaching transcript / examples / snapshots survive
        code = (f"import sys; sys.path[:0]=[{os.path.join(ROOT,'nlteach')!r},{os.path.join(ROOT,'procedure')!r},{os.path.join(ROOT,'core')!r}]; import nlsystem as NS; "
                f"S=NS.NLSystem({d+'/w.sqlite'!r},{d+'/p.sqlite'!r},{d+'/learn2'!r},mode='GOLD_TRACE'); import json; r=S.process({{'text':'RUN calls_with person={Q}'}},'x','t'); print(json.dumps([r['status'], r['return']]))")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True); st, ret = json.loads(out.stdout.strip().splitlines()[-1])
        assert st == "OK" and isinstance(ret, dict) and "events" in ret


def t_v11_candidate_segmentation():
    st, fu = F.segments("Find Alice's open calls and close them, then return how many there are.")
    assert st == ["Find Alice's open calls and close them.", "Return how many there are."] and fu == ["Find Alice's open calls.", "Close them.", "Return how many there are."]
    st, fu = F.segments("Find open and closed calls."); assert st == ["Find open and closed calls."] and len(fu) == 2          # weak 'and' is only a candidate boundary


def t_v11_whole_plan_validation():
    c = ctx([]); c["procs"] = []
    ok = lambda t, u, n: F.plan_ok(F.parse_actions(t), u, n, c)
    assert ok('r1 = {"op": "FIND", "type": "EMAIL"}\nr2 = {"op": "COUNT", "of": "r1"}\n{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}', "x", 1)[1] == "DEAD_PURE_RESULT"
    assert ok('r1 = {"op": "FIND", "type": "EMAIL"}\n{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}\nr2 = {"op": "COUNT", "of": "r1"}\n{"op": "RETURN", "value": "r2"}', "x", 3)[0]
    assert ok('r1 = {"op": "FIND", "type": "EMAIL"}\n{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}', "x", 3)[1].startswith("CLAUSE_COVERAGE")                    # truncated plan
    assert ok('r1 = {"op": "FIND", "type": "EMAIL"}', "find the emails to Bob", 1)[1].startswith("coverage")


def t_v11_structured_pending_clarification():
    pend = {"kind": "REFERENCE", "source_utterance_id": "u:3", "instruction": "Return them.", "unresolved_slot": "RETURN.value",
            "legal_answers": [{"name": "r1", "kind": "EVENT_LIST", "etype": "CALL"}, {"name": "r2", "kind": "VALUE_LIST", "etype": None}]}
    assert F.answers_clarification("I mean the people", pend) and F.answers_clarification("the calls", pend)
    assert not F.answers_clarification("Please look up Dad's emails.", pend) and not F.answers_clarification("Give it back.", pend)
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P = S.V["P"][0]; S.process({"text": f":teach calls_with(person={P})"}, "u:1", "t1")
        S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": [FINDC(P)]}}, "u:2", "t2")
        S.process({"kind": "NL", "text": "Return them.", "gold_outcome": {"status": "CLARIFY", "steps": []}}, "u:3", "t3")
        assert S.teach["nl"]["pending"]["kind"] == "REFERENCE" and S.teach["nl"]["pending"]["source_utterance_id"] == "u:3"; S.close()


def t_v12_antecedent_and_output_obligation():
    assert F.output_missing(F.parse_actions('r2 = {"op": "COUNT", "of": "r1"}'), "Tell me how many there are.")
    assert not F.output_missing(F.parse_actions('r2 = {"op": "COUNT", "of": "r1"}\n{"op": "RETURN", "value": "r2"}'), "Tell me how many there are.")
    assert not F.output_missing(F.parse_actions('r3 = {"op": "GET", "of": "r2", "rel": "WHO"}'), "See who it is with.")
    assert F.antecedent_missing(F.parse_actions('r1 = {"op": "FIND", "type": "EMAIL"}'), ctx(), "Close them.")
    assert not F.antecedent_missing(F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Bob"}, "status": "OPEN"}'), ctx(), "Look up the calls with Bob that are still open.")
    out = F.ground("Count them.", ctx(), Scripted([('r1 = {"op": "FIND", "type": "REMINDER"}\nr2 = {"op": "COUNT", "of": "r1"}\n', -0.3)]))
    assert out["status"] == "CLARIFY"                                                   # no antecedent + unnamed search -> never executed
    out = F.ground("Tell me how many there are.", ctx([CALLS]), Scripted([('r2 = {"op": "COUNT", "of": "r1"}\n', -0.2), ('r2 = {"op": "COUNT", "of": "r1"}\n{"op": "RETURN", "value": "r2"}\n', -1.5)]))
    assert out["status"] == "OK" and out["actions"][-1]["op"] == "RETURN"                # COUNT-only plan is not a candidate


TESTS = [t_schema_parsing, t_primitive_selection, t_argument_normalization, t_typed_validation, t_multi_action_segmentation, t_local_anaphora, t_clarify_ambiguous_variable,
         t_unsupported_rejection, t_teaching_transaction_rollback, t_teaching_sandbox_reset, t_trace_provenance_and_failed_not_evidence, t_require_second_demonstration,
         t_prompt_model_hash_recording, t_restart_without_teaching_transcript, t_v11_candidate_segmentation, t_v11_whole_plan_validation,
         t_v11_structured_pending_clarification, t_v12_antecedent_and_output_obligation]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "NL_TEACH_UNIT_TESTS_NEW.json")); a = ap.parse_args(); R0 = {}
    for t in TESTS:
        try: t(); R0[t.__name__[2:]] = "PASS"
        except Exception as e: import traceback; R0[t.__name__[2:]] = f"FAIL: {type(e).__name__}: {e} {traceback.format_exc()[-600:]}"
    out = {"n": len(R0), "passed": sum(v == "PASS" for v in R0.values()), "tests": R0}; json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1))
    sys.exit(0 if out["passed"] == out["n"] else 1)


if __name__ == "__main__":
    main()
