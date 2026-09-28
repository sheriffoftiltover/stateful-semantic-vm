"""ACQUISITION phase of one scenario in a fresh process (teacher ONLINE). Modes:
  GOLD_TRACE     registered gold actions per step (grounding bypassed)          FORMAL_TEACH   parent step language
  SCRIPTED       registered deterministic lessons + lookup answers (spec §30)   TEACHER        the frozen hosted teacher (spec §29 C)
Output: per-target outcomes, the full teacher transcript + provenance (teacher_transcripts/), student neural hashes before / after.
python run_acq.py --scenario S.json --dir WORK --mode MODE --out OUT.json [--backend MODAL|GROQ --model M --reasoning low|medium|high]"""
import os, sys, json, argparse, time, urllib.request
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "student"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "teacher")]
import nlsystem as NS, nllm, llm as PLM


def student_hash():
    try: d = json.loads(urllib.request.urlopen(os.environ.get("SEMVM_LLM_URL", "http://127.0.0.1:8765") + "/frozen", timeout=600).read()); return {"weights_sha256": d.get("weights_sha256"), "frozen": d.get("frozen"), "n_parameters": d.get("n_parameters")}
    except Exception as e: return {"error": type(e).__name__}


def main():
    ap = argparse.ArgumentParser()
    for k in ("--scenario", "--dir", "--mode", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--backend", default="MODAL"); ap.add_argument("--model", default="openai/gpt-oss-120b"); ap.add_argument("--reasoning", default="high")
    ap.add_argument("--grounder", default="LOCAL", choices=["LOCAL", "HOSTED"]); ap.add_argument("--arm", default=None)
    ap.add_argument("--recovery", default=None, choices=[None, "SCRIPTED", "HOSTED", "ORACLE"]); ap.add_argument("--teacher-max-tokens", type=int, default=8192); a = ap.parse_args()
    sc = json.load(open(a.scenario)); d = a.dir; os.makedirs(d, exist_ok=True); t0 = time.time()
    G = None
    if a.grounder == "HOSTED": import hosted_grounder as HG; G = HG.HostedGrounder()
    S = NS.NLSystem(os.path.join(d, "world.sqlite"), os.path.join(d, "procedures.sqlite"), os.path.join(d, "learn"), mode="GOLD_TRACE" if a.mode in ("GOLD_TRACE", "FORMAL_TEACH") else "NL_TEACH", grounder=G)
    H0 = student_hash(); fx = []
    for i, t in enumerate(sc["fixture"]):
        r = S.process({"kind": "ASSERT", "text": "<fixture>", "gold_ir": t["gold_ir"]} if t["kind"] == "ASSERT" else {"text": t["text"]}, f"{sc['scenario_id']}:fx{i}", "t0")
        fx.append({"status": r["status"], "STATE_hash": S.world.state_hash()})
    lib0 = S.lib.library_bytes(); act0 = len(S.lib.list_active()); out = {"scenario_id": sc["scenario_id"], "mode": a.mode, "arm": a.arm, "grounder": a.grounder, "recovery": a.recovery, "teacher_max_tokens": a.teacher_max_tokens,
           "budget": __import__("protocol").BUDGET, "student_hash_before": H0, "fixture": fx}
    if a.mode in ("GOLD_TRACE", "FORMAL_TEACH"):
        turns = sc["gold_acq_turns" if a.mode == "GOLD_TRACE" else "formal_acq_turns"]; res = []
        for i, t in enumerate(turns):
            if t["kind"] == "NL": r = S.process({"kind": "NL", "text": t["text"], "gold_outcome": t["gold"]}, f"{sc['scenario_id']}:a{i}", "t")
            else: r = S.process({"text": t["text"]}, f"{sc['scenario_id']}:a{i}", "t")
            r["STATE"] = S.world.canonical_state(); r["turn"] = i; res.append(r)
        out["acq_turns"] = res
    else:
        import episode as EP, transactional as TX
        sys.path.insert(0, os.path.join(ROOT, "scenarios")); import pdx_generate as PG
        curmap = {c["name"]: c for c in sc["curriculum"]}; out["targets"] = []; tlog = []
        for it in sc["curriculum"]:
            import routing as RT_
            gen_t = {"reasoning_effort": a.reasoning, "max_tokens": a.teacher_max_tokens}
            lesson = TX.ScriptedTeacherTx(sc["scripted"][it["name"]], it, PG.family_steps) if a.mode == "SCRIPTED" else EP.LLMTeacher(a.backend, a.model, gen_t, role="initial_teacher")
            rsrc = a.recovery or ("SCRIPTED" if a.mode == "SCRIPTED" else "HOSTED")
            if rsrc == "SCRIPTED": recov = lesson if a.mode == "SCRIPTED" else None
            elif rsrc == "HOSTED": recov = EP.LLMTeacher(a.backend, a.model, gen_t, role="recovery_teacher")
            else: _pg, _g = RT_.oracle_gen(); recov = RT_.OracleRecovery(it, PG.family_steps, _g)
            if recov is None: raise SystemExit("scripted recovery requires a scripted lesson")
            teacher = RT_.Routed(lesson, recov, "SCRIPTED" if a.mode == "SCRIPTED" else "HOSTED", rsrc)
            active = [dict(p, goal=curmap.get(p["name"], {}).get("goal", "")) for p in S.lib.list_active()]
            log = []; O = TX.run_target(S, it, teacher, sc["teacher_pool"], sc["style"], f"{sc['scenario_id']}:{it['name']}", log, active)
            O["teacher_log"] = log; out["targets"].append(O); tlog += log
            if O["status"] in ("BUDGET_STOP",): break
        tdir = os.path.join(ROOT, "teaching_traces", os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(d)))) or "run", a.arm or a.mode); os.makedirs(tdir, exist_ok=True)
        json.dump({"scenario_id": sc["scenario_id"], "mode": a.mode, "arm": a.arm, "grounder": a.grounder, "backend": a.backend, "model": a.model, "reasoning": a.reasoning,
                   "targets": [{"name": O["name"], "status": O["status"], "transcript": O["transcript"], "teacher_log": O["teacher_log"]} for O in out["targets"]]},
                  open(os.path.join(tdir, f"{sc['scenario_id']}.json"), "w"), indent=1, default=str)
        run = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(d)))) or "run"
        for sub, key in (("slot_ledgers", "slots"), ("teaching_transactions", None)):
            od = os.path.join(ROOT, sub, run, a.arm or a.mode); os.makedirs(od, exist_ok=True)
            json.dump([{"target": O["name"], "status": O["status"], "demos": [({"index": D["index"], "slots": D["slots"]} if key else
                        {"index": D["index"], "states": D["states"], "end": D["end"], "end_detail": D["end_detail"], "learn": D["learn"], "events": D["events"], "example": D["example"]}) for D in O["demos"]]}
                       for O in out["targets"]], open(os.path.join(od, f"{sc['scenario_id']}.json"), "w"), indent=1, default=str)
        for O in out["targets"]: O.pop("transcript", None)
    # ---- VERIFY_FALSE_ACCEPT probes: deliberately bad variants of every ACTIVE learned target, verified against the SAME evidence ----
    import abstraction as AB, lang as L
    probes = []
    for it in sc["curriculum"]:
        p = S.lib.active(it["name"]); trs = S.examples.get(it["name"]) or []
        if p is None or not trs: continue
        variants = {}
        if p["parameters"]:
            fv = json.loads(json.dumps(p)); sl = {c: v for _, c, v in AB.slots(AB.normalize_vars(trs[0]["steps"]), S.lib)}
            def fix(o):
                if isinstance(o, dict):
                    if set(o) == {"param"}: t = next(x["type"] for x in p["parameters"] if x["name"] == o["param"]); return {"const": sl.get(t, "")}
                    return {k: fix(v) for k, v in o.items()}
                if isinstance(o, list): return [fix(x) for x in o]
                return o
            fv["body"] = fix(fv["body"]); fv["parameters"] = []; variants["FROZEN_VALUE"] = fv
        dc = json.loads(json.dumps(p)); ch = False
        for st in dc["body"]:
            if st["op"] == "FIND" and st.get("status"): st["status"] = None; ch = True
        if ch: variants["DROPPED_CONSTANT_FILTER"] = dc
        for k, v in variants.items():
            try: txt = L.fmt_procedure(v).replace("\n", " ; ")
            except Exception: continue
            r = S.process({"text": f":propose {it['name']} <<{txt}>>"}, f"{sc['scenario_id']}:probe:{it['name']}:{k}", "t")
            probes.append({"target": it["name"], "variant": k, "status": r["status"]})
    out["false_accept_probes"] = probes
    out.update(active=S.lib.list_active(), library_bytes_before=lib0, library_bytes_after=S.lib.library_bytes(), active_before=act0, active_after=len(S.lib.list_active()),
               world_state_after=S.world.canonical_state(), student_hash_after=student_hash(), seconds=round(time.time() - t0, 2), nl_llm_calls=len(nllm.CALLS), retrieval_llm_calls=len(PLM.CALLS))
    import client as CLI
    out["hosted_calls"] = [{k: p.get(k) for k in ("role", "kind", "request_hash", "cached", "input_tokens", "output_tokens", "latency_s", "finish_reason", "truncations", "retry_count")} for p in CLI.LOG]
    S.close(); json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
