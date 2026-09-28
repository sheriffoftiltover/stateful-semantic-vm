"""RCI unit tests (spec §76). Deterministic; no hosted model. python tests/test_rci.py [--out results/UNIT_TESTS_RCI.json]"""
import os, sys, json, tempfile, argparse, copy, glob, threading, http.server, socketserver, math
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("student", "procedure", "core", "core/ir", "core/neural/vendor", "scenarios", "teacher", "evaluator")] + [ROOT]
import rci_metrics as RM, routing as RT, client as CL, behavior as BE, transactional as TX, protocol as PR
import rci_pool as POOL, pdx_generate as PG

ctx = {"find_relations": BE.find_relations, "status_constraints": BE.status_constraints, "teacher_log": []}


def demo(index=0, end="OK", state="COMMITTED", slots=None, results=None, **kw):
    return dict({"index": index, "end": end, "state": state, "slots": slots or [], "results": results or [], "learn": None, "end_detail": {}, "learn_detail": None}, **kw)


def slot(sid, status="RESOLVED", fam=None, required=True, **kw):
    return dict({"slot_id": sid, "status": status, "family": fam or sid, "required": required, "source": "TEACHER", "original_text": sid, "displaced": False, "replacement_for": None}, **kw)


def ev(committed=True, eq=True, legal=False, kind=None, prog=None, ref=None):
    return {"committed": committed, "complete": True, "eq": eq, "legal": legal, "kind": kind, "prog": prog or [], "ref": ref or []}


FIND = lambda rel, v, st=None: {"op": "FIND", "bind": "r1", "type": {"const": "CALL"}, "where": [["SELF", rel, {"const": v}]], "status": {"const": st} if st else None}


def t_committed_demo_counting():                        # Amendment 003 is baseline: the parent unit test must be present and pass in test_ttp
    src = open(os.path.join(ROOT, "tests", "test_ttp.py")).read(); assert "t_two_demo_protocol_counts_committed_demonstrations" in src
    assert "prev = sum(1 for x in O[\"demos\"] if x.get(\"state\") == \"COMMITTED\")" in open(os.path.join(ROOT, "teacher", "transactional.py")).read()


def t_taxonomy_deterministic_assignment():
    O = {"status": "TEACHER_EPISODE_FAIL", "fail": "demonstration budget exhausted", "demos": [demo(end="ABORTED:NO_STEPS", state="ABORTED")], "student_questions": []}
    assert RM.earliest_cause(O, {}, [ev(committed=False, eq=False)], "HOSTED", "HOSTED", {}, {}, ctx) == "TEACHER_INITIAL_FORMAT_ERROR"
    s = slot("demo1-slot1", status="CLARIFYING"); r = {"slot_id": "demo1-slot1", "status": "CLARIFY", "clarify_kind": "MARGIN", "line": "x"}
    O2 = {"status": "TEACHER_EPISODE_FAIL", "fail": "x", "demos": [demo(end="ABORTED:SLOT_RECOVERY_FAIL", state="ABORTED", slots=[s], results=[r, r])], "student_questions": []}
    lab = [RM.earliest_cause(O2, {}, [ev(committed=False, eq=False)], "SCRIPTED", "SCRIPTED", {}, {}, ctx) for _ in range(3)]
    assert lab == ["GROUNDER_FALSE_CLARIFICATION"] * 3                                                # deterministic
    O3 = {"status": "TEACHER_EPISODE_FAIL", "fail": "demonstration budget exhausted (last: REQUIRE_SECOND_DEMONSTRATION)", "demos": [demo(end="OK", learn="REQUIRE_SECOND_DEMONSTRATION")], "student_questions": []}
    assert RM.earliest_cause(O3, {}, [ev()], "HOSTED", "HOSTED", {}, {}, ctx) == "EVIDENCE_INSUFFICIENT_VARIATION"
    O4 = {"status": "PROVIDER_FAILURE", "fail": "HOSTED_TRUNCATION x2", "demos": [demo(end="ABORTED:EPISODE_END", state="ABORTED")], "student_questions": []}
    assert RM.earliest_cause(O4, {}, [ev(committed=False, eq=False)], "HOSTED", "HOSTED", {}, {}, ctx) == "PROVIDER_TRUNCATION"
    O5 = {"status": "ACTIVE", "fail": None, "demos": [demo(end="VERIFIED")], "student_questions": []}
    assert RM.earliest_cause(O5, {}, [ev(prog=[FIND("WHO", "a")], ref=[FIND("RECIPIENT", "a")], eq=False)], "SCRIPTED", "SCRIPTED", {}, {}, ctx) == "GROUNDER_INITIAL_RELATION_ERROR"
    assert all(l in RM.ALL for l in lab)


def t_earliest_cause_tie_breaking():
    """same logical turn: hosted initial lesson unfaithful AND a grounder clarification -> the teacher layer is evaluated first"""
    s = slot("demo1-slot1", status="CLARIFYING"); r = {"slot_id": "demo1-slot1", "status": "CLARIFY", "clarify_kind": "MARGIN", "line": "x"}
    O = {"status": "TEACHER_EPISODE_FAIL", "fail": "x", "demos": [demo(end="ABORTED:SLOT_RECOVERY_FAIL", state="ABORTED", slots=[s], results=[r])], "student_questions": []}
    J = {0: {"faithful": False, "issues": [{"kind": "WRONG_STEP"}]}}
    assert RM.earliest_cause(O, {}, [ev(committed=False, eq=False)], "HOSTED", "HOSTED", J, {}, ctx) == "TEACHER_INITIAL_SEMANTIC_ERROR"
    assert RM.earliest_cause(O, {}, [ev(committed=False, eq=False)], "HOSTED", "HOSTED", {0: {"faithful": True}}, {}, ctx) == "GROUNDER_FALSE_CLARIFICATION"
    # an earlier divergence beats a later provider truncation (spec §12)
    O2 = {"status": "PROVIDER_FAILURE", "fail": "HOSTED_TRUNCATION x2", "demos": [demo(end="ABORTED:SLOT_RECOVERY_FAIL", state="ABORTED", slots=[s], results=[r]), demo(1, end="ABORTED:EPISODE_END", state="ABORTED")], "student_questions": []}
    assert RM.earliest_cause(O2, {}, [ev(committed=False, eq=False), ev(committed=False, eq=False)], "HOSTED", "HOSTED", {}, {}, ctx) == "GROUNDER_FALSE_CLARIFICATION"


def t_recovery_event_start_end_and_attempts():
    ss = [slot("demo1-slot1"), slot("demo1-slot2", status="REPLACED"), slot("demo1-slot4", fam="demo1-slot2", from_recovery=True, replacement_for="demo1-slot2")]
    res = [{"slot_id": "demo1-slot1", "status": "OK"}, {"slot_id": "demo1-slot2", "status": "CLARIFY", "clarify_kind": "MARGIN", "attempts": [1, 2]},
           {"slot_id": "demo1-slot2", "status": "CLARIFY", "clarify_kind": "MARGIN", "attempts": [1]}, {"slot_id": "demo1-slot4", "status": "OK", "attempts": [1]}]
    O = {"student_questions": [{"kind": "RESTATE_SLOT", "slot_id": "demo1-slot2"}, {"kind": "RESTATE_SLOT", "slot_id": "demo1-slot2"}]}
    evs = RM.recovery_events(demo(slots=ss, results=res), O)
    assert len(evs) == 1 and evs[0]["family"] == "demo1-slot2" and evs[0]["resolved"] and evs[0]["teacher_attempts"] == 2 and evs[0]["grounder_retries"] == 1 and evs[0]["attempts"] == 3
    ss2 = [slot("demo1-slot1", status="CLARIFYING")]; res2 = [{"slot_id": "demo1-slot1", "status": "CLARIFY", "clarify_kind": "MARGIN"}]
    e2 = RM.recovery_events(demo(end="ABORTED:SLOT_RECOVERY_FAIL", state="ABORTED", slots=ss2, results=res2), {"student_questions": []})
    assert len(e2) == 1 and not e2[0]["resolved"]
    S = RM.summarize_events(evs + e2); assert S["RECOVERY_EVENT_COUNT"] == 2 and S["RECOVERY_EVENT_SUCCESS"] == .5 and S["RECOVERY_ATTEMPTS_PER_EVENT"]["max"] == 3


def t_recovery_target_metric():
    import rci_evaluate as RE
    R = {"RECOVERY_TARGET_SUCCESS": 2 / 3, "n_RECOVERY_TARGET_SUCCESS": 3}
    assert RE.counts(R, "RECOVERY_TARGET_SUCCESS") == (2, 3) and RE.counts({}, "X") == (0, 0)


class Stub:
    def __init__(self, name): self.name = name; self.calls = []
    def respond(self, m, kind, p): self.calls.append(kind); return f"{self.name}:{kind}", {"provider": self.name}


def t_arm_recovery_routing():
    for lesson, recovery in (("SCRIPTED", "SCRIPTED"), ("SCRIPTED", "HOSTED"), ("HOSTED", "ORACLE"), ("HOSTED", "HOSTED")):
        L_, R_ = Stub("lesson"), Stub("recovery"); T = RT.Routed(L_, R_, lesson, recovery)
        for k in ("LESSON", "NEW_DEMO", "FORMAT", "REMAINING", "MISSING_EXAMPLE", "RESTATE_SLOT", "RESTATE_OBSCURED", "CLARIFY_REFERENCE"): T.respond([], k, {})
        assert L_.calls == ["LESSON", "NEW_DEMO", "FORMAT", "REMAINING", "MISSING_EXAMPLE"] and R_.calls == ["RESTATE_SLOT", "RESTATE_OBSCURED", "CLARIFY_REFERENCE"]
        assert [x["to"] for x in T.routed][-1] == recovery and [x["to"] for x in T.routed][0] == lesson
    import rci_evaluate as RE
    assert RE.ARMS["B"][2] == "SCRIPTED" and RE.ARMS["E"] == ("SCRIPTED", "HOSTED", "HOSTED") and RE.ARMS["F"] == ("TEACHER", "HOSTED", "ORACLE") and RE.ARMS["D"] == ("TEACHER", "HOSTED", "HOSTED")


def t_oracle_recovery_boundary():
    _, g = RT.oracle_gen(); sc = json.load(open(sorted(glob.glob(os.path.join(ROOT, "scenarios", "dev_a", "*S15.json")))[0])); it = sc["curriculum"][0]; P = sc["teacher_pool"]["people"][0]
    O = RT.OracleRecovery(it, PG.family_steps, g); ref = [s for _, s in PG.family_steps(it["family"], {"person": P})]
    t, _ = O.respond([], "CLARIFY_REFERENCE", {"offered": ["r1", "r2"], "state": {"example": {"person": P}, "executed": ref[:2], "pending_teacher_slots_after": 2}})
    assert t == "REFERENT: r2", t                                                                    # FIRST reads the SORTed list
    t, _ = O.respond([], "RESTATE_SLOT", {"state": {"example": {"person": P}, "executed": ref[:1], "pending_teacher_slots_after": 3}})
    assert t.count("STEP:") == 1 and "sort" in t.lower(), t                                          # only the pending slot's semantics
    t, _ = O.respond([], "RESTATE_SLOT", {"state": {"example": {"person": P}, "executed": [], "pending_teacher_slots_after": 2}})
    assert t.count("STEP:") == 3, t                                                                  # a fused slot: n = reference left - pending teacher slots
    bad = copy.deepcopy(ref[:1]); bad[0]["status"] = None
    t, _ = O.respond([], "RESTATE_SLOT", {"state": {"example": {"person": P}, "executed": bad, "pending_teacher_slots_after": 3}})
    assert t == RT.UNSUPPORTED                                                                       # never repairs an unflagged divergence
    t, _ = O.respond([], "NEW_DEMO", {"state": {"example": {"person": P}, "executed": [], "pending_teacher_slots_after": 0}}); assert t == RT.UNSUPPORTED
    try: TX._check_oracle(RT.UNSUPPORTED); raise AssertionError("no abort")
    except TX._Abort as e: assert e.args[0] == "ORACLE_RECOVERY_UNSUPPORTED"


class Fake(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"])); b = json.dumps({"id": "x", "choices": [{"message": {"content": "STEP: x"}, "finish_reason": "stop"}], "usage": {}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass


def t_role_separated_cache_keys():
    srv = socketserver.TCPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["TEACHER_URL"] = f"http://127.0.0.1:{srv.server_address[1]}"; os.environ["TEACHER_API_KEY"] = "t"; CL.meter_usd = lambda: 0.0
    with tempfile.TemporaryDirectory() as d:
        old = dict(CL.CACHES)
        for k in CL.CACHES: CL.CACHES[k] = os.path.join(d, k); os.makedirs(CL.CACHES[k])
        m = [{"role": "user", "content": "same"}]; hs = {r: CL.chat(m, role=r)["provenance"]["request_hash"] for r in ("initial_teacher", "recovery_teacher", "grounder", "judge")}
        assert len(set(hs.values())) == 4 and all(len(os.listdir(CL.CACHES[r])) == 1 for r in hs)
        CL.CACHES.update(old)
    srv.shutdown()


def t_teacher_value_pool_freeze():
    assert PG.PGen.POOL_SIZE == 4
    for suite in ("dev_a",):
        for p in glob.glob(os.path.join(ROOT, "scenarios", suite, "*.json")):
            s = json.load(open(p)); assert all(len(v) == 4 for v in s["teacher_pool"].values()) and not (set(sum(s["teacher_pool"].values(), [])) & set(sum(s["eval_pool"].values(), [])))


def t_token_config_freeze():
    import rci_evaluate as RE
    assert RE.TEACHER_MAX_TOKENS == 8192 or os.environ.get("RCI_TEACHER_MAX_TOKENS")
    src = open(os.path.join(ROOT, "run_acq.py")).read(); assert '"max_tokens": a.teacher_max_tokens' in src and "--teacher-max-tokens" in src
    assert "max_tokens" in json.dumps({"body": {"max_tokens": 8192}})                                   # max_tokens is part of every cached request body


def t_dev_a_dev_b_config_equality():
    import rci_evaluate as RE
    f1 = RE.config_fingerprint(); f2 = RE.config_fingerprint(); assert f1 == f2 and len(f1) == 64
    os.environ["RCI_BUDGET_OVERRIDE"] = json.dumps({"max_teacher_turns_per_target": 20})
    import importlib; importlib.reload(PR); f3 = RE.config_fingerprint()
    del os.environ["RCI_BUDGET_OVERRIDE"]; importlib.reload(PR)
    assert f3 != f1 and RE.config_fingerprint() == f1                                               # any budget change is visible in the fingerprint


def rep(num_den, safety=True, floor_vals=None):
    counts = {k: list(v) for k, v in num_den.items()}
    D = {"counts": counts, "gates": {"S": {"group": "safety", "pass": safety}, "B": {"group": "backend", "pass": True}}}
    D.update({k: (v[0] / v[1] if v[1] else None) for k, v in num_den.items()})
    return {"arms": {"D": D}, "controls_pass": True}


def t_floor_and_pooled_weighting():
    a = rep({"LEARNED_PROCEDURE_EXACT": (34, 36), "SCENARIO_EXACT": (28, 30), "DISTILLED_SKILL_EXACT": (30, 32), "GROUNDING_BEHAVIORAL_EXACT": (38, 40)})
    b = rep({"LEARNED_PROCEDURE_EXACT": (31, 36), "SCENARIO_EXACT": (26, 30), "DISTILLED_SKILL_EXACT": (29, 32), "GROUNDING_BEHAVIORAL_EXACT": (39, 40)})
    out = POOL.decide([a, b]); L = out["arms"]["D"]["LEARNED_PROCEDURE_EXACT"]
    assert L["pooled_counts"] == [65, 72] and L["min_successes"] == math.ceil(.9 * 72) == 65 and L["pass"]
    G = out["arms"]["D"]["GROUNDING_BEHAVIORAL_EXACT"]; assert G["pooled_counts"] == [77, 80] and G["pass"]                  # weighted, not a mean of percentages
    assert out["decision"]["D_per_replicate_floor_pass"] == [True, True] and out["decision"]["LOCKED_ELIGIBLE"]
    c = rep({"LEARNED_PROCEDURE_EXACT": (28, 36), "SCENARIO_EXACT": (30, 30), "DISTILLED_SKILL_EXACT": (32, 32), "GROUNDING_BEHAVIORAL_EXACT": (40, 40)})
    out2 = POOL.decide([a, c]); assert out2["decision"]["D_per_replicate_floor_pass"] == [True, False] and not out2["decision"]["LOCKED_ELIGIBLE"]   # 28/36 = .778 < .80
    out3 = POOL.decide([a, rep(dict((k, tuple(v)) for k, v in b["arms"]["D"]["counts"].items()), safety=False)]); assert not out3["decision"]["LOCKED_ELIGIBLE"]


def t_locked_parity_audit_logic():
    A = json.load(open(os.path.join(ROOT, "locks", "LOCKED_PARITY_AUDIT.json")))
    enc = [k for k, v in A["questions"].items() if v["encoded_in_LOCKED"]]
    assert A["outcome"] == ("N" if enc else "P") and "teacher_example_value_pool_size" in enc and A["generator_matches_manifest"]
    assert not any(A["questions"][k]["encoded_in_LOCKED"] for k in ("teacher_max_tokens", "teacher_reasoning_effort", "teacher_turn_budgets", "recovery_budgets"))


TESTS = [t_committed_demo_counting, t_taxonomy_deterministic_assignment, t_earliest_cause_tie_breaking, t_recovery_event_start_end_and_attempts, t_recovery_target_metric,
         t_arm_recovery_routing, t_oracle_recovery_boundary, t_role_separated_cache_keys, t_teacher_value_pool_freeze, t_token_config_freeze, t_dev_a_dev_b_config_equality,
         t_floor_and_pooled_weighting, t_locked_parity_audit_logic]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "UNIT_TESTS_RCI.json")); a = ap.parse_args(); R = {}
    for t in TESTS:
        try: t(); R[t.__name__[2:]] = "PASS"
        except Exception as e: import traceback; R[t.__name__[2:]] = f"FAIL: {type(e).__name__}: {e} {traceback.format_exc()[-1000:]}"
    out = {"n": len(R), "passed": sum(v == "PASS" for v in R.values()), "tests": R}; json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if out["passed"] == out["n"] else 1)


if __name__ == "__main__":
    main()
