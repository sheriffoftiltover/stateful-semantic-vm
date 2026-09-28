"""TTP unit tests (spec §61). Deterministic: a stub grounder (fixed plans per instruction) and a stub teacher drive the REAL transactional
controller + the REAL NLSystem (executor, sandbox, learner, verifier); hosted-grounder / judge tests use a local fake OpenAI-compatible server.
python tests/test_ttp.py [--out results/UNIT_TESTS_TTP.json]"""
import os, sys, json, tempfile, argparse, copy, glob, threading, http.server, socketserver
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("student", "procedure", "core", "core/ir", "core/neural/vendor", "scenarios", "teacher", "evaluator")] + [ROOT]
import frontend as F, nlsystem as NS, protocol as PR, client as CL, transactional as TX, hosted_grounder as HG, behavior as BE
SC = {os.path.basename(p).split("-", 2)[2][:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", "dev", "*.json")))}


def system(d, sc, grounder):
    os.makedirs(d, exist_ok=True)
    S = NS.NLSystem(os.path.join(d, "w.sqlite"), os.path.join(d, "p.sqlite"), os.path.join(d, "learn"), mode="NL_TEACH", grounder=grounder)
    for i, t in enumerate(sc["fixture"]): S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": t["gold_ir"]} if t["kind"] == "ASSERT" else {"text": t["text"]}, f"fx{i}", "t0")
    return S


class StubG:
    """HOSTED-kind grounder with a fixed table: instruction text -> outcome (actions use the student action schema)"""
    kind = "HOSTED"
    def __init__(self, table): self.t = table; self.calls = []
    def ground_instruction(self, utt, ctx):
        self.calls.append((utt, [r.name + ":" + r.kind for r in ctx["results"]]))
        o = self.t.get(utt, {"status": "CLARIFY", "reason": "stub: unknown", "clarify_kind": "PLAN"})
        o = copy.deepcopy(o(ctx) if callable(o) else o); o.setdefault("provenance", {"grounder": "STUB"}); return o


class StubT:
    def __init__(self, replies): self.r = {k: list(v) for k, v in replies.items()}; self.asked = []
    def respond(self, messages, kind, payload):
        self.asked.append((kind, messages[-1]["content"] if messages[-1]["role"] == "user" else None, dict(payload)))
        q = self.r.get(kind) or [""]; return (q.pop(0) if len(q) > 1 else q[0]), {"provider": "stub"}


def OK(*acts): return {"status": "OK", "actions": list(acts)}
FINDC = lambda P, b="r1": {"op": "FIND", "bind": b, "type": "CALL", "where": {"WHO": P}}
CNT = {"op": "COUNT", "bind": "r2", "of": "r1"}; RET2 = {"op": "RETURN", "value": "r2"}
ITEM = lambda sc, **kw: dict({"name": "count_calls_with", "family": "count_calls_with", "sig": {"person": "PERSON"}, "goal": "Given a person, count the calls.",
                              "gold": "PROCEDURE count_calls_with(person:PERSON)\n$v0 = FIND CALL WHERE SELF.WHO={person}\n$v1 = COUNT $v0\nRETURN $v1\nEND",
                              "protocol": {"hint": True, "two_demo": False}, "injection": None}, **kw)


def base(sc):
    P = sc["teacher_pool"]["people"][0]
    return P, {f"Find the calls with {P}.": OK(FINDC(P)), "Count them.": OK(CNT), "Return the count.": OK(RET2)}


def run(sc, table, replies, item=None, d=None):
    S = system(d, sc, StubG(table)); T = StubT(replies); log = []
    O = TX.run_target(S, item or ITEM(sc), T, sc["teacher_pool"], "A", "u", log, []); return S, T, O


# ---------------------------------------------------------------- state machine / ledger ------------------------------------------------------
def t_demo_state_machine():
    D = TX.Demo(0, "x"); D.go("OPEN"); D.go("WAITING_FOR_EXAMPLE"); D.go("WAITING_FOR_GROUNDING"); D.go("WAITING_FOR_CLARIFICATION"); D.go("WAITING_FOR_GROUNDING"); D.go("READY_TO_COMMIT"); D.go("COMMITTED")
    for bad in (("NEW", "COMMITTED"), ("OPEN", "READY_TO_COMMIT"), ("COMMITTED", "OPEN"), ("ABORTED", "OPEN")):
        E = TX.Demo(0, "x"); E.state = bad[0]
        try: E.go(bad[1]); raise AssertionError(f"illegal {bad} accepted")
        except TX.ControllerError: pass


def t_slot_ledger_persistence_and_identity():
    D = TX.Demo(1, "x"); D.slots = [D.slot("a", "TEACHER", lesson_index=0), D.slot("b", "TEACHER", lesson_index=1)]
    s = D.slots[1]; TX._replace(D, s, s, ["b1", "b2"], 1)
    fam = D.family(s["slot_id"]); assert [x["text"] for x in fam] == ["b", "b1", "b2"] and all(x["family"] == s["slot_id"] and x["lesson_index"] == 1 for x in fam)
    assert s["status"] == "REPLACED" and D.family_state(s["slot_id"]) == "UNRESOLVED"
    for x in fam[1:]: x["status"] = "RESOLVED"
    assert D.family_state(s["slot_id"]) == "RESOLVED"
    rec = json.loads(json.dumps(D.record())); assert rec["slots"][1]["slot_id"] == s["slot_id"] and rec["slots"][2]["replacement_for"] == s["slot_id"]


def t_missing_slot_and_pending_block_commit():
    class FakeS: teach = {"steps": [{"op": "RETURN"}], "nl": {"pending": None}}
    D = TX.Demo(0, "x"); D.sig = {"p": "PERSON"}; D.example = {"p": "a"}; D.returned = True
    a = D.slot("a", "TEACHER"); a["status"] = "RESOLVED"; b = D.slot("b", "TEACHER"); b.update(status="REPLACED", displaced=True); D.slots = [a, b]
    assert any("displaced" in p for p in TX.completeness(FakeS, D))
    b.update(status="RESOLVED", displaced=False); c = D.slot("c", "TEACHER"); c["status"] = "CLARIFYING"; D.slots.append(c)
    assert any("pending" in p for p in TX.completeness(FakeS, D))
    c["status"] = "RESOLVED"; FakeS.teach = {"steps": [1], "nl": {"pending": {"kind": "REFERENCE"}}}; assert "pending clarification" in TX.completeness(FakeS, D)
    FakeS.teach = {"steps": [1], "nl": {"pending": None}}; assert TX.completeness(FakeS, D) == []


# ---------------------------------------------------------------- terminal-action gates ------------------------------------------------------
def t_unrequested_return_blocks():
    sc = SC["S5"]; P = sc["teacher_pool"]["people"][0]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc, StubG({f"Find the calls with {P}.": OK(FINDC(P)), "Count them.": OK(CNT, RET2)})); S.process({"text": f":teach count_calls_with(person={P})"}, "h", "t")
        S.process({"kind": "NL", "text": f"Find the calls with {P}."}, "l1", "t"); h = S.world.state_hash(); n = len(S.teach["steps"])
        r = S.process({"kind": "NL", "text": "Count them."}, "l2", "t"); assert r["status"] == "UNREQUESTED_RETURN" and not r["executed_steps"] and len(S.teach["steps"]) == n and S.world.state_hash() == h
        assert F.return_licensed("Return the count.") and F.return_licensed("Please give it back.") and not F.return_licensed("Count them.") and not F.return_licensed("Use person_on_call_at for 5.")
        S.close()


def t_return_with_unresolved_slot_blocks():
    sc = SC["S5"]; P = sc["teacher_pool"]["people"][0]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc, StubG({f"Find the calls with {P} and return them.": OK(FINDC(P), {"op": "RETURN", "value": "r1"})})); S.process({"text": f":teach x(person={P})"}, "h", "t")
        r = S.process({"kind": "NL", "text": f"Find the calls with {P} and return them.", "terminal_allowed": False}, "l", "t"); assert r["status"] == "PREMATURE_TERMINAL_ACTION" and not r["executed_steps"]
        r = S.process({"kind": "NL", "text": f"Find the calls with {P} and return them.", "terminal_allowed": True}, "l2", "t"); assert r["status"] == "OK"
        S.close()


# ---------------------------------------------------------------- saved-skill CALL ----------------------------------------------------------------
def t_saved_skill_call():
    procs = [{"name": "person_on_call_at", "parameters": [{"name": "time", "type": "TIME"}], "returns": "PERSON"}]
    call = [{"op": "CALL", "bind": "r1", "procedure": "person_on_call_at", "args": {"time": "7"}}]
    assert F.unnamed_call(call, "Call person_on_call_at with time 7.", procs) == [] and F.unnamed_call(call, "Find who is on the 7 call.", procs) == ["person_on_call_at"]
    ctx = {"results": [], "procs": procs, "procs_line": "person_on_call_at(time:TIME) -> PERSON"}; u = "Call person_on_call_at with time 7."
    c2 = dict(ctx, values=F.mentioned_values(u), nouns=F.nouns_in(u), status_cue=False, set_status_cues=[], named_procs=F.named_procs(u, procs))
    assert HG.grammar_errors(copy.deepcopy(call), c2, u) == []
    ok, why = F.plan_ok(call, "Find who is on the 7 call.", 1, ctx); assert not ok and "UNNAMED_CALL" in why


class Fake(http.server.BaseHTTPRequestHandler):
    replies = []; seen = []
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); Fake.seen.append(body)
        text = Fake.replies.pop(0) if Fake.replies else '{"status": "CLARIFY", "question": "?"}'
        b = json.dumps({"id": "x", "choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass


def fake(d):
    srv = socketserver.TCPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["TEACHER_URL"] = f"http://127.0.0.1:{srv.server_address[1]}"; os.environ["TEACHER_API_KEY"] = "t"; CL.meter_usd = lambda: 0.0
    old = dict(CL.CACHES)
    for k in CL.CACHES: CL.CACHES[k] = os.path.join(d, k); os.makedirs(CL.CACHES[k], exist_ok=True)
    return srv, old


def t_call_missing_argument_clarifies():
    with tempfile.TemporaryDirectory() as d:
        srv, old = fake(d); procs = [{"name": "person_on_call_at", "parameters": [{"name": "time", "type": "TIME"}], "returns": "PERSON"}]
        Fake.replies = ['{"status": "PLAN", "steps": [{"bind": "r1", "op": "CALL", "procedure": "person_on_call_at", "args": {}}]}']
        r = HG.HostedGrounder().ground_instruction("Call person_on_call_at.", {"results": [], "procs": procs, "procs_line": "person_on_call_at(time:TIME) -> PERSON"})
        assert r["status"] == "CLARIFY" and r["clarify_kind"] == "MISSING_ARGUMENT", r
        CL.CACHES.update(old); srv.shutdown()


def t_parent_when_feedback_and_retry():
    with tempfile.TemporaryDirectory() as d:
        srv, old = fake(d); Fake.seen.clear()
        Fake.replies = ['{"status": "PLAN", "steps": [{"bind": "r1", "op": "FIND", "type": "CALL", "where": {"WHEN": "7"}}]}',
                        '{"status": "PLAN", "steps": [{"bind": "r1", "op": "FIND", "type": "CALL", "where": {"PARENT.WHEN": "7"}}]}']
        r = HG.HostedGrounder().ground_instruction("Find the calls at 7.", {"results": [], "procs": [], "procs_line": "(none)"})
        assert r["status"] == "OK" and r["actions"][0]["where"] == {"PARENT.WHEN": "7"}, r
        fb = r["provenance"]["attempts"][0]["feedback"]; assert fb == [{"error": "ILLEGAL_RELATION_LOCATION", "object_type": "CALL", "relation": "WHEN", "legal_path": "PARENT.WHEN"}]
        last = Fake.seen[-1]["messages"][-1]["content"]; assert "ILLEGAL_RELATION_LOCATION" in last and "count" not in last.lower() and "PROCEDURE" not in last   # legality fact only
        CL.CACHES.update(old); srv.shutdown()


def t_structured_reference_choice():
    res = [F.Result("r1", "a", "EVENT_LIST", "REQUEST", 2), F.Result("r2", "b", "EVENT_LIST", "REQUEST", 2)]
    acts = [{"op": "FIRST", "bind": "r3", "of": "r2"}]; ctx = {"results": res, "procs": []}
    _, notes, why = F.reference_check(copy.deepcopy(acts), ctx, "Take the first one."); assert why and "ambiguous" in why and notes[-1]["candidates"]
    hid = [res[0].__class__("r1", "a", "HIDDEN_BY_REFERENCE_CHOICE", "REQUEST", 2), res[1]]
    a2, notes2, why2 = F.reference_check(copy.deepcopy(acts), {"results": hid, "procs": []}, "Take the first one."); assert why2 is None and a2[0]["of"] == "r2"
    assert PR.parse_reply("REFERENT: r2")["referent"] == "r2" and PR.parse_reply('{"referent_id": "r1"}')["referent"] == "r1"
    # controller: a REFERENCE clarification is asked with ids, the answer is applied as a structured choice
    sc = SC["S15"]; P = sc["teacher_pool"]["people"][0]
    amb = {"status": "CLARIFY", "reason": "reference for FIRST.of is ambiguous", "clarify_kind": "REFERENCE", "clarify_info": {"unresolved_slot": "FIRST.of", "candidates": [{"name": "r1", "kind": "EVENT_LIST", "etype": "REQUEST"}, {"name": "r2", "kind": "EVENT_LIST", "etype": "REQUEST"}]}}
    def first(ctx):
        live = [r.name for r in ctx["results"] if r.kind == "EVENT_LIST"]
        return OK({"op": "FIRST", "bind": "r3", "of": live[0]}) if len(live) == 1 else amb
    tbl = {f"Find the open requests from {P}.": OK({"op": "FIND", "bind": "r1", "type": "REQUEST", "where": {"WHO": P}, "status": "OPEN"}), "Sort them by time.": OK({"op": "SORT", "bind": "r2", "of": "r1", "by": "WHEN"}),
           "Take the first one.": first, "Close it.": OK({"op": "SET_STATUS", "target": "r3", "value": "CLOSED"}), "Return the request.": OK({"op": "RETURN", "value": "r3"})}
    it = dict(sc["curriculum"][0]); it["protocol"] = {"hint": True, "two_demo": False}; it["injection"] = None
    with tempfile.TemporaryDirectory() as d:
        S, T, O = run(sc, tbl, {"LESSON": [f"EXAMPLE: person={P}\nSTEP: Find the open requests from {P}.\nSTEP: Sort them by time.\nSTEP: Take the first one.\nSTEP: Close it.\nSTEP: Return the request."],
                                "CLARIFY_REFERENCE": ["REFERENT: r2"]}, it, d)
        q = [a for a in T.asked if a[0] == "CLARIFY_REFERENCE"]; assert q and "r1:" in q[0][1] and "r2:" in q[0][1]
        assert O["status"] == "ACTIVE" and O["demos"][0]["events"][0]["answer"] == "r2", (O["status"], O.get("fail"))
        S.close()


# ---------------------------------------------------------------- EXAMPLE / injection / budgets / rollback ----------------------------------------
def t_example_required_before_execution():
    sc = SC["S6"]; P, tbl = base(sc)
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc, StubG(tbl)); T = StubT({"LESSON": [f"STEP: Find the calls with {P}.\nSTEP: Count them.\nSTEP: Return the count."], "MISSING_EXAMPLE": [f"EXAMPLE: person={P}"]})
        order = []; orig = S.process
        def spy(turn, uid, ts): order.append(("NL" if turn.get("kind") == "NL" else turn["text"].split()[0])); return orig(turn, uid, ts)
        S.process = spy; O = TX.run_target(S, ITEM(sc), T, sc["teacher_pool"], "A", "u", [], [])
        kinds = [a[0] for a in T.asked]; assert kinds[:2] == ["LESSON", "MISSING_EXAMPLE"], kinds
        assert "NL" in order and order.index(":teach") < order.index("NL") and "WAITING_FOR_EXAMPLE" in O["demos"][0]["states"] and O["status"] == "ACTIVE", (O["status"], O.get("fail"))
        S.close()


def t_injected_step_provenance_and_restoration():
    sc = SC["S6"]; P, tbl = base(sc); vague = "Now do the usual thing with it, like we did for Kevin."
    it = ITEM(sc, injection={"kind": "VAGUE_STEP", "demo": 0, "text": vague})
    with tempfile.TemporaryDirectory() as d:
        S, T, O = run(sc, dict(tbl, **{vague: {"status": "CLARIFY", "reason": "vague", "clarify_kind": "GROUNDER"}}),
                      {"LESSON": [f"EXAMPLE: person={P}\nSTEP: Find the calls with {P}.\nSTEP: Count them.\nSTEP: Return the count."], "RESTATE_OBSCURED": ["STEP: Count them."]}, it, d)
        qs = [a for a in T.asked if a[0] not in ("LESSON",)]
        assert qs and qs[0][0] == "RESTATE_OBSCURED" and "obscured by the evaluator" in qs[0][1] and vague not in qs[0][1] and "Kevin" not in qs[0][1]
        D0 = O["demos"][0]; disp = [s for s in D0["slots"] if s["displaced"]][0]
        assert D0["state"] == "COMMITTED" and any(s["family"] == disp["slot_id"] and s["status"] == "RESOLVED" and s["slot_id"] != disp["slot_id"] for s in D0["slots"])
        assert [s["source"] for s in D0["slots"] if s["text"] == vague] == ["EVALUATOR_INJECTION"] and O["status"] == "ACTIVE"
        S.close()


def t_budget_does_not_reset_on_rephrase_and_abort_yields_zero_evidence():
    sc = SC["S6"]; P, tbl = base(sc); bad = {f"Find the calls with {P}.": {"status": "CLARIFY", "reason": "low margin", "clarify_kind": "MARGIN"}}
    for k in ("Look up the calls with them.", "Get the calls."): bad[k] = {"status": "CLARIFY", "reason": "low margin", "clarify_kind": "MARGIN"}
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc, StubG(dict(tbl, **bad))); h0 = S.world.state_hash()
        T = StubT({"LESSON": [f"EXAMPLE: person={P}\nSTEP: Find the calls with {P}.\nSTEP: Count them.\nSTEP: Return the count."],
                   "RESTATE_SLOT": ["STEP: Look up the calls with them.", "STEP: Get the calls.", "STEP: Get the calls."], "NEW_DEMO": [""]})
        O = TX.run_target(S, ITEM(sc), T, sc["teacher_pool"], "A", "u", [], [])
        D0 = O["demos"][0]; assert D0["end"] == "ABORTED:SLOT_RECOVERY_FAIL", D0["end"]
        assert sum(1 for a in T.asked if a[0] == "RESTATE_SLOT") == TX.B["max_rephrase_exchanges_per_slot"]              # replacements do NOT reset the slot budget
        root = D0["slots"][0]; assert root["rephrase_count"] == TX.B["max_rephrase_exchanges_per_slot"] + 1 and len(D0["slots"]) >= 4 and all(s["family"] == root["slot_id"] for s in D0["slots"] if s["replacement_for"])
        assert not S.examples.get("count_calls_with") and S.lib.active("count_calls_with") is None and S.world.state_hash() == h0 and S.teach is None
        S.close()


def t_transaction_rollback():
    sc = SC["S5"]; P = sc["teacher_pool"]["people"][0]
    close = {"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}
    tbl = {f"Find the calls with {P}.": OK(FINDC(P)), "Close each of them.": OK(close), "Count them.": {"status": "CLARIFY", "reason": "x", "clarify_kind": "MARGIN"}}
    it = ITEM(sc, name="close_calls_with", family="close_calls_with")
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc, StubG(tbl)); h0 = S.world.state_hash()
        T = StubT({"LESSON": [f"EXAMPLE: person={P}\nSTEP: Find the calls with {P}.\nSTEP: Close each of them.\nSTEP: Count them.\nSTEP: Return the count."], "RESTATE_SLOT": ["STEP: Count them."], "NEW_DEMO": [""]})
        O = TX.run_target(S, it, T, sc["teacher_pool"], "A", "u", [], [])
        assert O["demos"][0]["end"].startswith("ABORTED") and S.world.state_hash() == h0 and not S.examples.get("close_calls_with")
        S.close()


def t_judge_connectivity_preflight():
    import ttp_evaluate as TE
    with tempfile.TemporaryDirectory() as d:
        srv, old = fake(d); Fake.replies = ['{"faithful": true, "issues": []}']
        pre = TE.judge_preflight(); assert pre["reached_endpoint"] and pre["parsed_label"] and pre["label"] is True and pre["cache_written"], pre
        CL.CACHES.update(old); srv.shutdown()


def t_parameterless_evaluator_case():
    sc = next(v for v in SC.values() if any(it["family"] == "email_topic_report" for it in v["curriculum"]))
    it = next(it for it in sc["curriculum"] if it["family"] == "email_topic_report")
    ref = BE.reference_steps(sc, it, {}); assert ref and ref[-1]["op"] == "RETURN"
    assert BE.reference_steps(sc, it, None) == ref
    assert TX.example_complete(None, {}, sc["teacher_pool"]) == (True, [])


def t_status_coverage():
    f = [{"op": "FIND", "type": "CALL", "bind": "r1", "where": {"WHO": "Oscar"}}]
    assert F.status_uncovered(f, "Get every open call Oscar is on.") and not F.status_uncovered([dict(f[0], status="OPEN")], "Get every open call Oscar is on.")
    assert not F.status_uncovered(f, "Find all requests by Oscar, open or closed.") and not F.status_uncovered(f, "Find the calls with Oscar.")
    ok, why = F.plan_ok(f, "Get every open call Oscar is on.", 1, {"procs": []}); assert not ok and "STATUS_COVERAGE" in why


def t_malformed_hosted_plan_never_crashes():
    res = [F.Result("r1", 'r1 = {"op": "FIND_LAST", "type": "REMINDER"}', "EVENT", "REMINDER")]; u = "Open the item it is about."
    ctx = {"results": res, "procs": [], "values": F.mentioned_values(u), "nouns": F.nouns_in(u), "status_cue": False, "set_status_cues": [], "named_procs": []}
    assert HG.grammar_errors([{"op": "CHILD", "bind": "r2"}], ctx, u) and not HG.grammar_errors([{"op": "CHILD", "bind": "r2", "of": "r1"}], ctx, u)
    sc = SC["S2"]
    with tempfile.TemporaryDirectory() as d:                                  # defense in depth: even an unchecked malformed plan becomes CLARIFY
        S = system(d, sc, StubG({"Take my latest reminder.": OK({"op": "FIND_LAST", "bind": "r1", "type": "REMINDER"}), u: OK({"op": "CHILD", "bind": "r2"})}))
        S.process({"text": ":teach x"}, "h", "t"); S.process({"kind": "NL", "text": "Take my latest reminder."}, "a", "t")
        r = S.process({"kind": "NL", "text": u}, "b", "t"); assert r["status"] == "CLARIFY" and r["clarify_kind"] == "SCHEMA" and not r["executed_steps"], r
        S.close()


def t_two_demo_protocol_counts_committed_demonstrations():
    sc = SC["S6"]; P, tbl = base(sc); Q = sc["teacher_pool"]["people"][1]
    tbl = dict(tbl, **{f"Find the calls with {Q}.": OK(FINDC(Q)), "Tally the calls with Bob.": {"status": "CLARIFY", "reason": "x", "clarify_kind": "MARGIN"}})
    it = ITEM(sc, protocol={"hint": True, "two_demo": True})
    with tempfile.TemporaryDirectory() as d:                    # demo 1 aborts (zero evidence); demo 2 must NOT be learned alone
        S, T, O = run(sc, tbl, {"LESSON": [f"EXAMPLE: person={P}\nSTEP: Tally the calls with Bob.\nSTEP: Count them.\nSTEP: Return the count."], "RESTATE_SLOT": ["STEP: Tally the calls with Bob."],
                                "NEW_DEMO": [f"EXAMPLE: person={P}\nSTEP: Find the calls with {P}.\nSTEP: Count them.\nSTEP: Return the count.",
                                             f"EXAMPLE: person={Q}\nSTEP: Find the calls with {Q}.\nSTEP: Count them.\nSTEP: Return the count."]}, it, d)
        ds = O["demos"]; assert ds[0]["end"].startswith("ABORTED") and ds[1]["state"] == "COMMITTED" and ds[1]["learn"] is None, [(x["end"], x["learn"]) for x in ds]
        assert ds[2]["learn"] == "VERIFIED" and O["status"] == "ACTIVE" and S.lib.active("count_calls_with") is not None
        S.close()


TESTS = [t_two_demo_protocol_counts_committed_demonstrations, t_malformed_hosted_plan_never_crashes, t_status_coverage, t_demo_state_machine, t_slot_ledger_persistence_and_identity, t_missing_slot_and_pending_block_commit, t_unrequested_return_blocks, t_return_with_unresolved_slot_blocks,
         t_saved_skill_call, t_call_missing_argument_clarifies, t_parent_when_feedback_and_retry, t_structured_reference_choice, t_example_required_before_execution,
         t_injected_step_provenance_and_restoration, t_budget_does_not_reset_on_rephrase_and_abort_yields_zero_evidence, t_transaction_rollback, t_judge_connectivity_preflight,
         t_parameterless_evaluator_case]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "UNIT_TESTS_TTP.json")); a = ap.parse_args(); R = {}
    for t in TESTS:
        try: t(); R[t.__name__[2:]] = "PASS"
        except Exception as e: import traceback; R[t.__name__[2:]] = f"FAIL: {type(e).__name__}: {e} {traceback.format_exc()[-1200:]}"
    out = {"n": len(R), "passed": sum(v == "PASS" for v in R.values()), "tests": R}; json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if out["passed"] == out["n"] else 1)


if __name__ == "__main__":
    main()
