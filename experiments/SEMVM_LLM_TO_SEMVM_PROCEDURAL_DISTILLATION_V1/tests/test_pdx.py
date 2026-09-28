"""PDX unit tests (deterministic; no hosted teacher, no LLM service needed except where noted: none). python tests/test_pdx.py [--out ...]"""
import os, sys, json, tempfile, subprocess, argparse, copy, random
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, d) for d in ("student", "procedure", "core", "core/ir", "scenarios", "teacher")]
import frontend as F, nlsystem as NS, lang as L, protocol as PR, client as CL, episode as EP
import nl_generate as NG, pdx_catalog as PC


def world(d):
    g = NG.Gen(random.Random(5), "dev", json.load(open(os.path.join(ROOT, "scenarios", "templates_dev.json")))); V, facts, setup = g.world()
    S = NS.NLSystem(os.path.join(d, "w.sqlite"), os.path.join(d, "p.sqlite"), os.path.join(d, "learn"), mode="GOLD_TRACE")
    for f in facts: S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": NG.fact_ir(f)}, "fx", "t0")
    S.V = V; return S


def FINDC(p, status=None): return {"op": "FIND", "bind": "r1", "type": {"const": "CALL"}, "where": [["SELF", "WHO", {"const": p}]], "status": {"const": status} if status else None}
CNT = [{"op": "COUNT", "bind": "r2", "list": {"var": "r1"}}, {"op": "RETURN", "value": {"var": "r2"}}]


def demo(S, hdr, steps, uid):
    S.process({"text": hdr}, uid + "h", "t")
    for k, st in enumerate(steps): S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": [st]}}, f"{uid}{k}", "t")


def t_protocol_parsing():
    ex, st, an = PR.parse_lesson("EXAMPLE=person=Peggy\nSTEP 1: Find the calls with Peggy.\n2. STEP: Count them.\nANSWER: the people")
    assert ex == {"person": "Peggy"} and st == ["Find the calls with Peggy.", "Count them."] and an == ["the people"]
    ex, st, _ = PR.parse_lesson("EXAMPLE: person=Bob, time=3\nSTEP: x"); assert ex == {"person": "Bob", "time": "3"}


def t_card_contains_no_gold():
    card = PR.system_prompt() + json.dumps(PR.STYLE)
    for fam, f in PC.FAMILIES.items():
        assert fam not in card
        for line in f["gold"].splitlines()[1:-1]: assert line.split("=")[-1].strip() not in card or len(line) < 12
    req = PR.lesson_request({"name": "count_open_calls_with", "sig": {"person": "PERSON"}, "goal": PC.GOALS["count_open_calls_with"]}, {"people": ["A"]}, [], "A")
    assert "FIND" not in req and "STATUS=" not in req and "$v" not in req


def t_evidence_sufficiency():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P, Q = S.V["P"][0], S.V["P"][1]; S.process({"text": ":target count_calls_with(person:PERSON)"}, "t", "t")
        tr = lambda p, hint: {"steps": [FINDC(p)] + CNT, "declared": {"person": p} if hint else None}
        assert S.evidence_sufficient("count_calls_with", [tr(P, True)])[0]
        assert not S.evidence_sufficient("count_calls_with", [tr(P, False)])[0]
        assert not S.evidence_sufficient("count_calls_with", [tr(P, False), tr(P, False)])[0]          # two demonstrations, same value
        assert S.evidence_sufficient("count_calls_with", [tr(P, False), tr(Q, False)])[0]
        demo(S, ":teach count_calls_with", [FINDC(P)] + CNT, "u1"); r = S.process({"text": ":endteach"}, "e", "t"); assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION"
        r = S.process({"text": ":learn count_calls_with"}, "l", "t"); assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION"       # 9.2 at :learn too
        r = S.process({"text": ":propose count_calls_with <<PROCEDURE count_calls_with() ; $v0 = FIND CALL WHERE SELF.WHO=%s ; $v1 = COUNT $v0 ; RETURN $v1 ; END>>" % P}, "p", "t")
        assert r["status"] == "REQUIRE_SECOND_DEMONSTRATION"                                                                      # ... and at :propose
        S.close()


def t_cross_demonstration_consistency():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); P, Q = S.V["P"][0], S.V["P"][1]; S.process({"text": ":target count_open_calls_with(person:PERSON)"}, "t", "t")
        demo(S, f":example count_open_calls_with(person={P})", [FINDC(P, "OPEN")] + CNT, "a"); S.process({"text": ":endexample"}, "a", "t")
        demo(S, f":example count_open_calls_with(person={Q})", [FINDC(Q)] + CNT, "b"); S.process({"text": ":endexample"}, "b", "t")     # dropped filter
        r = S.process({"text": ":learn count_open_calls_with"}, "l1", "t"); assert r["status"] == "DEMONSTRATIONS_INCONSISTENT"
        demo(S, f":example count_open_calls_with(person={Q})", [FINDC(Q, "OPEN")] + CNT, "c"); S.process({"text": ":endexample"}, "c", "t")
        r = S.process({"text": ":learn count_open_calls_with"}, "l2", "t"); assert r["status"] == "VERIFIED" and r["examples_used"] == 2 and r["examples_discarded_inconsistent"] == 1
        assert "STATUS=OPEN" in r["discovery"]["paths"]["deterministic"]["program"]; S.close()


class Scripted(F.Grounder):
    def __init__(self, hyps): self.margin = F.MARGIN; self.beam = 3; self.prefix = ""; self.hyps = hyps
    def decode(self, utt, c):
        out = []
        for text, sc in self.hyps:
            h = F.Hyp(); h.text = text; h.score = sc; h.actions = F.parse_actions(text); h.done = True; out.append(h)
        return out, 0, ""


def t_fix_9_1_failed_split_clarifies():
    ctx = {"results": [], "procs": [], "procs_line": "(none)"}
    out = F.ground_instruction("Find the calls with Alice and do the usual thing.", ctx, Scripted([('{"op": "CLARIFY"}\n', -0.1)]))
    assert out["status"] == "CLARIFY"
    out = F.ground_instruction("Find the calls with Alice and do the usual thing.", ctx, Scripted([('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Alice"}}\n', -0.1)]))
    assert out["status"] == "CLARIFY" and out.get("clarify_kind") in ("SEGMENTATION_FAILED", "SEGMENTATION", "PLAN")      # no whole-sentence fallback execution


def t_set_status_cues():
    assert F.set_status_cues("Mark each of them as archived.") == [] and F.set_status_cues("close them all") == ["CLOSED"] and F.set_status_cues("reopen it") == ["OPEN"]


def t_network_guard_blocks():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "n.jsonl"); code = "import urllib.request\ntry: urllib.request.urlopen('http://example.com', timeout=5); print('LEAK')\nexcept Exception as e: print('BLOCKED', type(e).__name__)"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "netguard"), NETGUARD_LOG=log))
        assert "BLOCKED" in r.stdout and os.path.exists(log) and len(open(log).read().splitlines()) >= 1


def t_client_cache_and_budget_stop():
    msgs = [{"role": "user", "content": "unit-test %f" % random.random()}]
    body = {"model": "gpt-oss-120b", "messages": msgs, "temperature": 0.0, "top_p": 1.0, "max_tokens": CL.GEN["max_tokens"], "seed": 0, "reasoning_effort": "low"}
    key = CL.sha(json.dumps({"backend": "MODAL", "model": "openai/gpt-oss-120b", "body": body}, sort_keys=True)); p = os.path.join(CL.CACHE, key + ".json")
    json.dump({"text": "STEP: cached", "provenance": {"provider": "modal-vllm"}}, open(p, "w"))
    os.environ.setdefault("TEACHER_URL", "http://127.0.0.1:9"); os.environ.setdefault("TEACHER_API_KEY", "x")
    r = CL.chat(msgs, gen={"reasoning_effort": "low"}); assert r["cached"] and r["text"] == "STEP: cached"; os.remove(p)
    old = CL.meter_usd; CL.meter_usd = lambda: 99.0
    try: CL.chat([{"role": "user", "content": "uncached %f" % random.random()}]); raise AssertionError("no budget stop")
    except CL.BudgetStop: pass
    finally: CL.meter_usd = old


def t_scripted_episode_with_injections():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); S.nl_mode = "GOLD_TRACE"
        # detectable injection: an UNSUPPORTED line inserted into the lesson must not execute (GOLD_TRACE student -> no grounding; use a stub grounder)
        class G(F.Grounder):
            def __init__(self): self.margin = 1.0; self.beam = 1; self.prefix = ""
        S.nl_mode = "NL_TEACH"; S.grounder = None
        calls = {"n": 0}
        def fake_ground(instr, ctx, gr):
            calls["n"] += 1
            if "slack" in instr.lower(): return {"status": "UNSUPPORTED", "provenance": {}}
            if instr.lower().startswith("return"): return {"status": "OK", "actions": F.parse_actions('{"op": "RETURN", "value": "r2"}'), "provenance": {}}
            if "find" in instr.lower(): return {"status": "OK", "actions": F.parse_actions('r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "%s"}}' % S.V["P"][0]), "provenance": {}}
            if "count" in instr.lower(): return {"status": "OK", "actions": F.parse_actions('r2 = {"op": "COUNT", "of": "r1"}'), "provenance": {}}
            return {"status": "OK", "actions": F.parse_actions('{"op": "RETURN", "value": "r2"}'), "provenance": {}}
        orig = F.ground_instruction; F.ground_instruction = fake_ground
        try:
            it = {"name": "count_calls_with", "family": "count_calls_with", "sig": {"person": "PERSON"}, "goal": "g", "protocol": {"hint": True, "two_demo": False},
                  "injection": {"kind": "UNSUPPORTED_PRIMITIVE", "demo": 0}}
            script = {"demos": [{"example": {"person": S.V["P"][0]}, "lines": ["Find the calls.", "Count them.", "Return the count."], "rephrase": ["find.", "count.", "return."]}], "answer": "the people"}
            O = EP.run_target(S, it, EP.ScriptedTeacher(script), {"people": [S.V["P"][0]]}, "A", "u", [], [])
        finally: F.ground_instruction = orig
        assert O["status"] == "ACTIVE", O
        inj = [r for D in O["demos"] for r in D["results"] if "Slack" in r["line"]]; assert inj and all(r["status"] != "OK" for r in inj)
        assert S.teach is None; S.close()


def t_none_result_keeps_static_kind():
    with tempfile.TemporaryDirectory() as d:
        S = world(d); S.process({"text": ":teach person_on_call_at(time=12)"}, "h", "t")
        for k, st in enumerate([{"op": "FIND", "bind": "r1", "type": {"const": "CALL"}, "where": [["PARENT", "WHEN", {"const": "12"}]], "status": None},
                                {"op": "FIRST", "bind": "r2", "list": {"var": "r1"}}, {"op": "GET", "bind": "r3", "obj": {"var": "r2"}, "rel": "WHO"}]):
            S.process({"kind": "NL", "text": "x", "gold_outcome": {"status": "OK", "steps": [st]}}, f"s{k}", "t")
        kinds = [r.kind for r in S.teach["nl"]["results"]]; assert kinds[-1] == "PERSON", kinds; S.close()


TESTS = [t_protocol_parsing, t_card_contains_no_gold, t_evidence_sufficiency, t_cross_demonstration_consistency, t_fix_9_1_failed_split_clarifies, t_set_status_cues,
         t_network_guard_blocks, t_client_cache_and_budget_stop, t_scripted_episode_with_injections, t_none_result_keeps_static_kind]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "results", "PDX_UNIT_TESTS_PDX.json")); a = ap.parse_args(); R = {}
    for t in TESTS:
        try: t(); R[t.__name__[2:]] = "PASS"
        except Exception as e: import traceback; R[t.__name__[2:]] = f"FAIL: {type(e).__name__}: {e} {traceback.format_exc()[-700:]}"
    out = {"n": len(R), "passed": sum(v == "PASS" for v in R.values()), "tests": R}; json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); sys.exit(0 if out["passed"] == out["n"] else 1)


if __name__ == "__main__":
    main()
