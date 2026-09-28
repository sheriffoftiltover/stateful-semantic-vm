"""HTG unit tests (spec §99). Deterministic; no hosted model and no student LLM service needed (hosted calls go to a local fake
OpenAI-compatible server). python tests/test_htg.py [--out results/UNIT_TESTS_HTG.json]"""
import os, sys, json, tempfile, subprocess, argparse, copy, glob, threading, shutil, http.server, socketserver
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("student", "procedure", "core", "core/ir", "core/neural/vendor", "scenarios", "teacher", "evaluator")] + [ROOT]
import frontend as F, nlsystem as NS, lang as L, protocol as PR, client as CL, episode as EP, hosted_grounder as HG
import behavior as BE, judge as JU, nl_generate as NG

SC = {os.path.basename(p).split("-", 2)[2][:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", "dev", "*.json")))}


def scen(stratum): return next(v for k, v in SC.items() if k == stratum)


def system(d, sc, mode="GOLD_TRACE", grounder=None):
    os.makedirs(d, exist_ok=True)
    S = NS.NLSystem(os.path.join(d, "w.sqlite"), os.path.join(d, "p.sqlite"), os.path.join(d, "learn"), mode=mode, grounder=grounder)
    for i, t in enumerate(sc["fixture"]):
        S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": t["gold_ir"]} if t["kind"] == "ASSERT" else {"text": t["text"]}, f"fx{i}", "t0")
    return S


def demo(S, hdr, steps, uid):
    S.process({"text": hdr}, uid + "h", "t")
    for k, st in enumerate(steps): S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": [st]}}, f"{uid}{k}", "t")


def FIND(t, rel, v, status=None): return {"op": "FIND", "bind": "r1", "type": {"const": t}, "where": [["SELF", rel, {"const": v}]], "status": {"const": status} if status else None}
CNT = [{"op": "COUNT", "bind": "r2", "list": {"var": "r1"}}, {"op": "RETURN", "value": {"var": "r2"}}]


# ---------------------------------------------------------------- behavioural equivalence ----------------------------------------------------
def t_behavior_signature_canonicalization():
    sc = scen("S6"); Ws = BE.worlds(sc); P = sc["teacher_pool"]["people"][0]
    a = [FIND("CALL", "WHO", P, "OPEN")] + CNT
    b = json.loads(json.dumps(a).replace('"r1"', '"q7"').replace('"r2"', '"q9"'))                  # variable names are not behaviour
    for W in Ws.values(): assert BE.behavior_signature(a, W) == BE.behavior_signature(a, W) == BE.behavior_signature(b, W)
    assert set(Ws) == set(BE.VARIANTS) and len(Ws) == 5


def t_behavioral_equivalence_positive_negative():
    sc = scen("S5"); Ws = BE.worlds(sc); P = sc["teacher_pool"]["people"][0]
    f = FIND("CALL", "WHO", P); close = {"op": "FOR", "as": "e0", "list": {"var": "r1"}, "body": [{"op": "SET_STATUS", "obj": {"var": "e0"}, "value": {"const": "CLOSED"}}]}
    ref = [f, close] + CNT; alt = [f] + [CNT[0], close, CNT[1]]                                        # spec §26: allowed order difference
    assert BE.behaviorally_equivalent(alt, ref, Ws)[0]
    f_open = FIND("CALL", "WHO", P, "OPEN"); ref2 = [f_open, CNT[0], close, CNT[1]]                      # spec §27: post-mutation FIND
    bad = [f_open, close, dict(f_open, bind="r3"), {"op": "COUNT", "bind": "r2", "list": {"var": "r3"}}, CNT[1]]
    assert not BE.behaviorally_equivalent(bad, ref2, Ws)[0]
    assert not BE.behaviorally_equivalent([dict(f_open, status=None), CNT[0], close, CNT[1]], ref2, Ws)[0]  # dropped filter


def t_recipient_vs_who_binding():
    sc = scen("S16"); Ws = BE.worlds(sc); P = sc["teacher_pool"]["people"][0]
    ref = [FIND("EMAIL", "RECIPIENT", P)] + CNT; wrong = [FIND("EMAIL", "WHO", P)] + CNT
    ok, where = BE.behaviorally_equivalent(wrong, ref, Ws); assert not ok
    assert BE.find_relations(ref) != BE.find_relations(wrong)
    ctx = dict(F_ctx(), values=F.mentioned_values(f"find the visits with {P}"), nouns=F.nouns_in(f"find the visits with {P}"), status_cue=False, set_status_cues=[], named_procs=[])
    assert HG.grammar_errors([{"op": "FIND", "bind": "r1", "type": "VISIT", "where": {"RECIPIENT": P}}], ctx, f"find the visits with {P}")   # ontology: VISIT has no RECIPIENT


def F_ctx(): return {"results": [], "procs": [], "procs_line": "(none)"}


# ---------------------------------------------------------------- evidence prechecks -----------------------------------------------------------
def t_evidence_nonvacuity():
    sc = scen("S18"); P, Q = sc["teacher_pool"]["people"]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc); S.process({"text": ":target count_emails_to(person:PERSON)"}, "t", "t")
        demo(S, f":teach count_emails_to(person={P})", [FIND("EMAIL", "WHO", P)] + CNT, "a")           # the vacuity probe: WHO finds nothing
        r = S.process({"text": ":endteach"}, "e", "t"); assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION" and "EVIDENCE_VACUOUS" in r["insufficient"], r
        S.close()
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc); S.process({"text": ":target count_emails_to(person:PERSON)"}, "t", "t")
        demo(S, f":teach count_emails_to(person={P})", [FIND("EMAIL", "RECIPIENT", P)] + CNT, "a")
        r = S.process({"text": ":endteach"}, "e", "t"); assert r["status"] == "VERIFIED", r; S.close()
    with tempfile.TemporaryDirectory() as d:                                                           # status contrast needs a witness
        sc6 = scen("S6"); S = system(d, sc6); S.process({"text": ":target count_open_calls_with(person:PERSON)"}, "t", "t")
        P1 = sc6["teacher_pool"]["people"][1]; ok, why = S.evidence_nonvacuous([{"steps": [FIND("CALL", "WHO", P1, "OPEN")] + CNT, "snapshot": S.snapshot("x")}])
        P0 = sc6["teacher_pool"]["people"][0]; ok0, _ = S.evidence_nonvacuous([{"steps": [FIND("CALL", "WHO", P0, "OPEN")] + CNT, "snapshot": S.snapshot("y")}])
        assert ok0 and (not ok and "STATUS_DROPPED" in why), (ok0, ok, why); S.close()


def t_evidence_conflict_and_legal_bad_block():
    sc = scen("S6"); P, Q = sc["teacher_pool"]["people"]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc); S.process({"text": ":target count_open_calls_with(person:PERSON)"}, "t", "t")
        demo(S, f":example count_open_calls_with(person={P})", [FIND("CALL", "WHO", P, "OPEN")] + CNT, "a"); S.process({"text": ":endexample"}, "a", "t")
        demo(S, f":example count_open_calls_with(person={Q})", [FIND("CALL", "WHO", Q, "CLOSED")] + CNT, "b"); S.process({"text": ":endexample"}, "b", "t")   # CONSTANT_SWAP
        r = S.process({"text": ":learn count_open_calls_with"}, "l1", "t"); assert r["status"] == "EVIDENCE_CONFLICT", r            # no verifier call, no crash
        assert S.lib.active("count_open_calls_with") is None
        demo(S, f":example count_open_calls_with(person={Q})", [FIND("CALL", "WHO", Q)] + CNT, "c"); S.process({"text": ":endexample"}, "c", "t")          # DROPPED_FILTER
        r = S.process({"text": ":learn count_open_calls_with"}, "l2", "t"); assert r["status"] == "EVIDENCE_CONFLICT", r
        demo(S, f":example count_open_calls_with(person={Q})", [FIND("CALL", "WHO", Q, "OPEN")] + CNT, "e"); S.process({"text": ":endexample"}, "e", "t")
        r = S.process({"text": ":learn count_open_calls_with"}, "l3", "t"); assert r["status"] == "VERIFIED" and r["examples_discarded_inconsistent"] == 2, r
        S.close()
    with tempfile.TemporaryDirectory() as d:                                                           # guard: a non-signature class varying in one group
        S = system(d, sc); S.process({"text": ":target count_open_calls_with(person:PERSON)"}, "t", "t")
        trs = [{"steps": [FIND("CALL", "WHO", P, "OPEN")] + CNT}, {"steps": [FIND("CALL", "WHO", Q, "CLOSED")] + CNT}]
        assert S.evidence_conflict("count_open_calls_with", trs); assert not S.evidence_conflict("count_open_calls_with", trs[:1] * 2); S.close()


def t_single_example_insufficiency():
    sc = scen("S1"); P = sc["teacher_pool"]["people"][0]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc); S.process({"text": ":target calls_with(person:PERSON)"}, "t", "t")
        demo(S, ":teach calls_with", [FIND("CALL", "WHO", P), {"op": "RETURN", "value": {"var": "r1"}}], "a")
        r = S.process({"text": ":endteach"}, "e", "t"); assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION", r; S.close()


# ---------------------------------------------------------------- hosted grounder ------------------------------------------------------------------
class Fake(http.server.BaseHTTPRequestHandler):
    replies = []; seen = []
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); Fake.seen.append(body)
        text, fin = Fake.replies.pop(0) if Fake.replies else ('{"status": "CLARIFY", "question": "?"}', "stop")
        out = {"id": "x", "choices": [{"message": {"content": text}, "finish_reason": fin}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
        b = json.dumps(out).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass


def fake_server():
    srv = socketserver.TCPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["TEACHER_URL"] = f"http://127.0.0.1:{srv.server_address[1]}"; os.environ["TEACHER_API_KEY"] = "test"; CL.meter_usd = lambda: 0.0; return srv


def isolated_caches(d):
    old = dict(CL.CACHES)
    for k in CL.CACHES: CL.CACHES[k] = os.path.join(d, k); os.makedirs(CL.CACHES[k], exist_ok=True)
    return old


def t_detectable_bad_block_hosted():
    sc = scen("S14D"); P = sc["teacher_pool"]["people"][0]; srv = fake_server()
    with tempfile.TemporaryDirectory() as d:
        old = isolated_caches(os.path.join(d, "c")); S = system(os.path.join(d, "s"), sc, mode="NL_TEACH", grounder=HG.HostedGrounder()); S.process({"text": ":target calls_with(person:PERSON)"}, "t", "t")
        S.process({"text": f":teach calls_with(person={P})"}, "h", "t"); h0 = S.world.state_hash()
        bad = [('{"status": "PLAN", "steps": [{"bind": "r1", "op": "SEND", "to": "x"}]}', "stop"),                                             # unsupported primitive
               ('{"status": "PLAN", "steps": [{"bind": "r1", "op": "FIND", "type": "CALL", "where": {"WHO": "%s"}, "status": "OPEN"}]}' % P, "stop"),  # uncued status
               ('{"status": "PLAN", "steps": [{"op": "SET_STATUS", "target": "r9", "value": "CLOSED"}]}', "stop"),                          # undefined result
               ('{"status": "PLAN", "steps": [{"bind": "r1", "op": "FIND", "type": "CALL", "where": {"WHERE": "%s"}}]}' % P, "stop"),         # wrong type
               ("not json at all", "stop")]
        texts = [f"Find the calls with {P}.", f"Look up the calls with {P}.", "Close it.", f"Get the calls with {P}.", f"Show the calls with {P}."]
        for (rep, fin), tx in zip(bad, texts):
            Fake.replies = [(rep, fin)]; r = S.process({"kind": "NL", "text": tx}, f"l{len(Fake.seen)}", "t")
            assert r["status"] in ("CLARIFY", "UNSUPPORTED") and not r["executed_steps"], (rep, r["status"], r.get("reason"))
        assert S.world.state_hash() == h0 and S.teach["steps"] == []
        Fake.replies = [('{"status": "PLAN", "steps": [{"bind": "r7", "op": "FIND", "type": "CALL", "where": {"WHO": "%s"}}, {"op": "RETURN", "value": "r7"}]}' % P, "stop")]
        r = S.process({"kind": "NL", "text": f"Find the calls with {P} and return them."}, "ok", "t"); assert r["status"] == "OK" and r["executed_steps"][0]["bind"] == "r1", r
        S.close(); CL.CACHES.update(old)
    srv.shutdown()


def t_context_isolation():
    ctx = {"results": [], "procs": [], "procs_line": "(none)"}; m = HG.messages("Find the calls with Kevin.", ctx); blob = json.dumps(m)
    card = PR.system_prompt()
    assert "TEACH EXACTLY THE REQUESTED SKILL" in card and "GROUNDER" not in card
    assert card[:200] not in blob and "goal" not in blob.lower() and "EXAMPLE:" not in blob and "STEP:" not in blob
    assert m[0]["content"] == HG.CARD and m[-1]["content"].endswith("Instruction: Find the calls with Kevin.\n")
    import pdx_catalog as PC
    for fam in PC.FAMILIES: assert fam not in blob                                                    # no catalogue procedure names / gold


def t_cache_separation_and_truncation():
    srv = fake_server()
    with tempfile.TemporaryDirectory() as d:
        old = isolated_caches(d); msgs = [{"role": "user", "content": "hi"}]
        Fake.replies = [("A", "stop"), ("B", "stop")]
        a = CL.chat(msgs, role="teacher"); b = CL.chat(msgs, role="grounder")
        assert a["text"] == "A" and b["text"] == "B" and a["provenance"]["request_hash"] != b["provenance"]["request_hash"]
        assert len(os.listdir(CL.CACHES["teacher"])) == 1 and len(os.listdir(CL.CACHES["grounder"])) == 1
        assert CL.chat(msgs, role="teacher")["cached"] and CL.chat(msgs, role="grounder")["text"] == "B"
        Fake.replies = [("partial", "length"), ("partial", "length")]; n0 = len(os.listdir(CL.CACHES["teacher"]))
        try: CL.chat([{"role": "user", "content": "long"}], role="teacher"); raise AssertionError("truncation parsed")
        except CL.ProviderFailure as e: assert "HOSTED_TRUNCATION" in str(e)
        assert len(os.listdir(CL.CACHES["teacher"])) == n0                                                 # truncated output never cached
        Fake.replies = [("partial", "length"), ("full", "stop")]; assert CL.chat([{"role": "user", "content": "retry"}], role="teacher")["text"] == "full"
        CL.CACHES.update(old)
    srv.shutdown()


# ---------------------------------------------------------------- handoff -----------------------------------------------------------------------------
def t_teardown_verification():
    import htg_evaluate as HE
    calls = []
    class R:
        def __init__(s, rc, out=""): s.returncode = rc; s.stdout = out; s.stderr = ""
    orig_run, orig_open = HE.subprocess.run, HE.urllib.request.urlopen
    with tempfile.TemporaryDirectory() as d:
        uf = os.path.join(d, "u"); open(uf, "w").write("http://127.0.0.1:9"); os.environ["PDX_TEACHER_URL_FILE"] = uf
        try:
            HE.subprocess.run = lambda cmd, **k: (calls.append(cmd), R(0, "[]"))[1]
            def gone(*a, **k): raise HE.urllib.error.HTTPError("u", 404, "gone", {}, None)
            HE.urllib.request.urlopen = gone; A = HE.teardown("unit_ok"); assert A["teacher_destroyed"] and ["modal", "app", "stop", "--yes", HE.TEACHER_APP] in calls
            HE.urllib.request.urlopen = lambda *a, **k: object(); A = HE.teardown("unit_reachable"); assert not A["teacher_destroyed"]
            HE.urllib.request.urlopen = gone; HE.subprocess.run = lambda cmd, **k: R(1); A = HE.teardown("unit_rc"); assert not A["teacher_destroyed"]
        finally:
            HE.subprocess.run, HE.urllib.request.urlopen = orig_run, orig_open
            for f in glob.glob(os.path.join(ROOT, "handoff_audit", "teardown_unit_*.json")): os.remove(f)


def t_network_guard():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "n.jsonl"); code = "import socket\ntry:\n socket.create_connection(('8.8.8.8',53),timeout=2); print('OPEN')\nexcept Exception as e: print('BLOCKED')"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "netguard"), NETGUARD_LOG=log))
        assert r.stdout.strip() == "BLOCKED" and len(open(log).read().splitlines()) == 1


def t_transcript_removal():
    import htg_evaluate as HE
    with tempfile.TemporaryDirectory() as d:
        sc = {"scenario_id": "x"}; os.makedirs(os.path.join(d, "work", "D", "x", "learn", "teaching_traces")); open(os.path.join(d, "work", "D", "x", "learn", "teaching_traces", "t.json"), "w").write("{}")
        assert HE.move_learn("D", [sc], d) == ["x"] and not os.path.exists(os.path.join(d, "work", "D", "x", "learn")) and os.path.exists(os.path.join(d, "acq_artifacts", "D", "x", "teaching_traces", "t.json"))


def t_neural_hash_recording():
    sc = scen("S1")
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, "o.json"); p = os.path.join(d, "s.json"); json.dump(sc, open(p, "w"))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "run_acq.py"), "--scenario", p, "--dir", os.path.join(d, "w"), "--mode", "GOLD_TRACE", "--out", o], capture_output=True, text=True,
                           env=dict(os.environ, SEMVM_LLM_URL="http://127.0.0.1:9"))
        A = json.load(open(o)); assert "student_hash_before" in A and "student_hash_after" in A and "hosted_calls" in A and A["hosted_calls"] == []


def t_stored_procedure_post_restart_reuse():
    sc = scen("S1"); P, Q = sc["teacher_pool"]["people"][0], sc["eval_pool"]["people"][0]
    with tempfile.TemporaryDirectory() as d:
        S = system(d, sc); S.process({"text": ":target calls_with(person:PERSON)"}, "t", "t")
        demo(S, f":teach calls_with(person={P})", [FIND("CALL", "WHO", P), {"op": "RETURN", "value": {"var": "r1"}}], "a")
        assert S.process({"text": ":endteach"}, "e", "t")["status"] == "VERIFIED"; assert S.process({"text": ":accept calls_with"}, "acc", "t")["status"] == "OK"; S.close()
        shutil.rmtree(os.path.join(d, "learn"))                                                        # teaching artefacts gone
        S2 = NS.NLSystem(os.path.join(d, "w.sqlite"), os.path.join(d, "p.sqlite"), os.path.join(d, "learn2"), mode="GOLD_TRACE")
        r = S2.process({"text": f"RUN calls_with person={Q}"}, "run", "t"); assert r["status"] == "OK", r; S2.close()


def t_scripted_units_and_relation_swap_injection():
    sc = scen("S18"); it = sc["curriculum"][0]; dm = sc["scripted"][it["name"]]["demos"][0]
    assert len(dm["units"]) == len(dm["lines"]) and sorted(sum(dm["units"], [])) == list(range(3))
    out, hit = EP._inject_relation_swap(dm["lines"], sc["teacher_pool"]["people"]); assert hit and any(" with " in l for l in out)
    assert JU.lexical_unrequested("Given a person, return all the calls with that person.", ["Find the open calls with Bob.", "Return them."]) == [1]
    assert JU.lexical_unrequested("Given a person, return how many of the calls with that person are still open.", ["Find the open calls with Bob."]) == []


TESTS = [t_behavior_signature_canonicalization, t_behavioral_equivalence_positive_negative, t_recipient_vs_who_binding, t_evidence_nonvacuity, t_evidence_conflict_and_legal_bad_block,
         t_single_example_insufficiency, t_detectable_bad_block_hosted, t_context_isolation, t_cache_separation_and_truncation, t_teardown_verification, t_network_guard,
         t_transcript_removal, t_neural_hash_recording, t_stored_procedure_post_restart_reuse, t_scripted_units_and_relation_swap_injection]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "UNIT_TESTS_HTG.json")); a = ap.parse_args(); R = {}
    for t in TESTS:
        try: t(); R[t.__name__[2:]] = "PASS"
        except Exception as e: import traceback; R[t.__name__[2:]] = f"FAIL: {type(e).__name__}: {e} {traceback.format_exc()[-900:]}"
    out = {"n": len(R), "passed": sum(v == "PASS" for v in R.values()), "tests": R}; json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if out["passed"] == out["n"] else 1)


if __name__ == "__main__":
    main()
