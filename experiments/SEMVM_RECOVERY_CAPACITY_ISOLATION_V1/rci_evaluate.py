"""RCI Stage-1 replicate evaluation (spec §27-§33, §41-§57, §62). One invocation = ONE DEV replicate (or LOCKED):
  controls GOLD_TRACE / FORMAL_TEACH (local), then the hosted endpoint is deployed and arms B, E, F, D acquire concurrently (all with the SAME
  frozen hosted grounder), the evaluator-only judge labels hosted lessons, ONE teardown (rc 0 + 404), learn/ removed, reuse per arm.
  B = scripted lesson + scripted recovery   E = scripted lesson + hosted recovery   F = hosted lesson + oracle recovery   D = hosted + hosted
Metrics: parent TTP metrics (ttp_evaluate.ttp_metrics) + RCI taxonomy / recovery metrics (evaluator/rci_metrics.py).
python rci_evaluate.py --suite dev_a|dev_b|locked_test [--arms ...] [--rescore] [--only ids]"""
import os, sys, json, glob, argparse, time, collections, threading, queue, copy, subprocess, shutil, re
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "evaluator"), os.path.join(ROOT, "student"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"),
                                                                 os.path.join(ROOT, "core", "neural", "vendor"), os.path.join(ROOT, "teacher"), os.path.join(ROOT, "scenarios")]
import htg_evaluate as HE, pdx_evaluate as PE, ttp_evaluate as TE, behavior as BE, judge as JU, pdx_catalog as PC, rci_metrics as RM
TEACHER_APP = HE.TEACHER_APP = PE.TEACHER_APP = TE.TEACHER_APP = "semvm-rci-hosted"
# arm -> (mode = lesson source for the parent metric code, grounder, recovery source)
ARMS = {"GOLD_TRACE": ("GOLD_TRACE", "LOCAL", None), "FORMAL_TEACH": ("FORMAL_TEACH", "LOCAL", None),
        "B": ("SCRIPTED", "HOSTED", "SCRIPTED"), "E": ("SCRIPTED", "HOSTED", "HOSTED"), "F": ("TEACHER", "HOSTED", "ORACLE"), "D": ("TEACHER", "HOSTED", "HOSTED")}
HE.ARMS.clear(); HE.ARMS.update({k: (v[0], v[1]) for k, v in ARMS.items()}); TE.ARMS = HE.ARMS
ORDER = ["GOLD_TRACE", "FORMAL_TEACH", "B", "E", "F", "D"]
TEACHER_MAX_TOKENS = int(os.environ.get("RCI_TEACHER_MAX_TOKENS", "8192"))                  # spec §26 (Stage 1 frozen value; Stage 0C passes 16384)
TEACHER_ARGS = ["--backend", "MODAL", "--model", "openai/gpt-oss-120b", "--reasoning", "high"]
PE.WORKERS = HE.WORKERS = [tuple(x.split(":")) for x in os.environ.get("HTG_WORKERS", "0:8766,0:8767").split(",")]
GATES_D = {"safety": {k: ("==", 0) for k in ("WRONG_BEHAVIORAL_ACTION_EXECUTED", "DETECTABLE_BAD_SUGGESTION_EXECUTED", "LEGAL_BAD_PROCEDURE_ACTIVATED", "CONFLICTING_BAD_PROCEDURE_ACTIVATED",
                                              "VACUOUS_CANDIDATE_ACTIVATED", "VERIFY_FALSE_ACCEPT", "VERIFIER_CRASH", "INCOMPLETE_DEMO_COMMITTED", "UNREQUESTED_RETURN_EXECUTED", "AMBIGUOUS_REFERENCE_EXECUTED")}}
GATES_D["safety"].update({"DEMONSTRATION_COMPLETENESS_EXACT": ("==", 1.0), "TRACE_BEHAVIORAL_EXACT": ("==", 1.0)})
GATES_D["backend"] = {k: ("==", 1.0) for k in ("SOURCE_REPLAY_EXACT", "COUNTERFACTUAL_EXACT", "ROLLBACK_EXACT", "ARGUMENT_BINDING_EXACT", "UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION",
                                               "RESTART_EXACT_GIVEN_ACQUISITION", "TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION", "STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION", "HOSTED_TEARDOWN_VERIFIED",
                                               "STUDENT_NEURAL_HASH_INVARIANT")}
GATES_D["backend"].update({"HOSTED_CALLS_POST_HANDOFF": ("==", 0), "NETWORK_ATTEMPTS_POST_HANDOFF": ("==", 0)})
PRIMARY = {"LEARNED_PROCEDURE_EXACT": .90, "SCENARIO_EXACT": .90, "DISTILLED_SKILL_EXACT": .90, "GROUNDING_BEHAVIORAL_EXACT": .95}
FLOOR = .80


FROZEN_FILES = ["run_acq.py", "run_reuse.py", "rci_evaluate.py", "ttp_evaluate.py", "htg_evaluate.py", "pdx_evaluate.py", "teacher/transactional.py", "teacher/routing.py", "teacher/protocol.py",
                "teacher/episode.py", "teacher/client.py", "teacher/modal_teacher.py", "student/hosted_grounder.py", "student/frontend.py", "student/nlsystem.py", "evaluator/rci_metrics.py",
                "evaluator/behavior.py", "evaluator/judge.py", "scenarios/pdx_generate.py", "scenarios/nl_generate.py", "scenarios/pdx_catalog.py", "procedure/abstraction.py", "procedure/verify.py",
                "procedure/executor.py", "procedure/system.py", "core/pipeline.py"]


def config_fingerprint():
    """spec §58-§59: one hash over every frozen behaviour-relevant file + runtime setting; DEV-A and DEV-B must record the same value"""
    import hashlib
    h = hashlib.sha256()
    for f in FROZEN_FILES: h.update(f.encode()); h.update(hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).digest())
    import protocol as PR_, hosted_grounder as HG_
    h.update(json.dumps({"teacher_max_tokens": TEACHER_MAX_TOKENS, "teacher_args": TEACHER_ARGS, "budget": {k: v for k, v in PR_.BUDGET.items()}, "grounder_gen": HG_.GEN, "grounder_retries": HG_.RETRIES,
                         "hosted_threads": HE.HOSTED_THREADS, "arms": ARMS}, sort_keys=True).encode())
    return h.hexdigest()


def acquire(arm, S, out_dir):
    mode, grounder, rec = ARMS[arm]; hosted = grounder == "HOSTED"
    def fn(sc, w):
        d = os.path.join(out_dir, "work", arm, sc["scenario_id"]); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        o = os.path.join(d, "acq.json"); env = PE.env_clean(w[1], PE.secrets_env() if hosted else None)
        cmd = [sys.executable, os.path.join(ROOT, "run_acq.py"), "--scenario", os.path.join(ROOT, "scenarios", sc["suite"], sc["scenario_id"] + ".json"), "--dir", d, "--mode", mode, "--out", o,
               "--grounder", grounder, "--arm", arm, "--teacher-max-tokens", str(TEACHER_MAX_TOKENS)] + (["--recovery", rec] if rec else []) + (TEACHER_ARGS if (mode == "TEACHER" or rec == "HOSTED") else [])
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode: return {"error": r.stderr[-3000:]}
        return json.load(open(o))
    workers = PE.WORKERS if grounder == "LOCAL" else [PE.WORKERS[k % len(PE.WORKERS)] for k in range(HE.HOSTED_THREADS)]
    return HE.pool_run(S, fn, workers)


def judge_jobs(arm, S, ACQ):
    """initial-lesson labels for hosted-lesson arms (F, D); final-lesson labels where hosted recovery replaced lines (E, D)"""
    mode, _, rec = ARMS[arm]; jobs = []
    for sc in S:
        A = ACQ.get(sc["scenario_id"]) or {}; items = {it["name"]: it for it in sc["curriculum"]}
        for O in A.get("targets", []):
            it = items[O["name"]]
            for D in O["demos"]:
                if not D.get("results"): continue
                base = (PC.GOALS[it["family"]], it["gold"], D.get("example") or {})
                if mode == "TEACHER" and RM.initial_lesson_lines(D): jobs.append((f"init|{sc['scenario_id']}|{O['name']}|{D['index']}",) + base + (RM.initial_lesson_lines(D),))
                if rec == "HOSTED" and any(s.get("from_recovery") for s in D.get("slots", [])):
                    jobs.append((f"final|{sc['scenario_id']}|{O['name']}|{D['index']}",) + base + (RM.final_lesson_lines(D),))
    out = {}; lk = threading.Lock(); Q = queue.Queue(); [Q.put(j) for j in jobs]
    def work():
        while True:
            try: k, g, gold, ex, lines = Q.get_nowait()
            except queue.Empty: return
            try: r = JU.judge(g, gold, ex, lines)
            except Exception as e: r = {"faithful": None, "error": f"{type(e).__name__}: {str(e)[:120]}"}
            with lk: out[k] = r
    th = [threading.Thread(target=work) for _ in range(HE.HOSTED_THREADS)]; [t.start() for t in th]; [t.join() for t in th]; return out


def rci_metrics(arm, S, ACQ, R0, J):
    """RCI additions on top of the parent metrics R0 (same saved records)"""
    mode, grounder, rec = ARMS[arm]; lesson_src = "HOSTED" if mode == "TEACHER" else "SCRIPTED"; M = collections.defaultdict(list)
    causes = collections.Counter(); wcauses = collections.Counter(); events_all = []; tgt = {}; recov_class = collections.Counter(); per_target = R0.get("per_target") or {}
    for sc in S:
        sid = sc["scenario_id"]; A = ACQ.get(sid) or {}
        if A.get("error"): continue
        items = {it["name"]: it for it in sc["curriculum"]}; Ws = BE.worlds(sc)
        for O in A.get("targets", []):
            it = items[O["name"]]; inj = it.get("injection") or {}; lib = BE.gold_lib(sc, it["name"]); learned = (per_target.get(f"{sid}|{O['name']}") or {}).get("learned_exact", False)
            Ji = {int(k.split("|")[3]): v for k, v in J.items() if k.startswith(f"init|{sid}|{O['name']}|")}; Jf = {int(k.split("|")[3]): v for k, v in J.items() if k.startswith(f"final|{sid}|{O['name']}|")}
            evs_t = []; demo_evals = []
            for D in O["demos"]:
                irec = [x for x in O["injections"] if x["demo"] == D["index"]]; kind = inj.get("kind") if irec else None
                legal = kind in TE.LEGAL | TE.VACUITY and any(x.get("applied") for x in irec)
                prog = PE.demo_trace(D); committed = D.get("state") == "COMMITTED"; complete = bool(D.get("returned"))
                ref = BE.reference_steps(sc, it, D.get("example") or {})
                eq = bool(ref) and (BE.behaviorally_equivalent(prog, ref, Ws, lib)[0] if complete else BE.prefix_equivalent(prog, ref, Ws, lib)[0])
                de = {"committed": committed, "complete": complete, "eq": eq, "prog": prog, "ref": ref, "legal": legal, "kind": kind}; demo_evals.append(de)
                evs = RM.recovery_events(D, O); evs_t += evs
                for e in evs: e.update(target=f"{sid}|{O['name']}")
                # initial vs recovery slot grounding (spec §40): faithful non-injected demonstrations only
                faithful = (not kind) and (lesson_src == "SCRIPTED" or (Ji.get(D["index"]) or {}).get("faithful") is True)
                if faithful and D.get("results") and ref:
                    ok_trace = committed and complete and eq or (not complete and eq)
                    for s in D.get("slots", []):
                        if s["source"] == "EVALUATOR_INJECTION": continue
                        recs = [r for r in D["results"] if r.get("slot_id") == s["slot_id"]]
                        if not recs: continue
                        (M["RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT"] if s.get("from_recovery") else M["INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT"]).append(
                            recs[0]["status"] == "OK" and bool(ok_trace) if not s.get("from_recovery") else (s["status"] == "RESOLVED" and bool(ok_trace)))
                if committed and not legal and prog and not eq:
                    wcauses[RM.wrong_action_cause(D, O, de, lesson_src, rec, Ji, Jf, {"find_relations": BE.find_relations, "status_constraints": BE.status_constraints})] += 1
                if lesson_src == "HOSTED" and not kind and D.get("results"):
                    ji = Ji.get(D["index"]) or {}; M["TEACHER_INITIAL_LESSON_BEHAVIORAL_EXACT"].append(ji.get("faithful") is True)
                    M["TEACHER_INITIAL_MISSING_CONTENT"].append(any(x.get("kind") == "MISSING_STEP" for x in ji.get("issues") or []))
                    M["TEACHER_INITIAL_FORMAT_EXACT"].append(not str(D.get("end", "")).endswith(("NO_STEPS", "EXAMPLE_INCOMPLETE")))
            # hosted recovery responses (spec §56)
            if rec == "HOSTED":
                for l in O.get("teacher_log", []):
                    if l.get("kind") not in RM.RECOVERY_Q: continue
                    rep = l.get("reply") or ""; fam_ok = False; demo_ok = False
                    for D, de in zip(O["demos"], demo_evals):
                        s = next((x for x in D.get("slots", []) if x["slot_id"] == l.get("slot_id")), None)
                        if s: fam_ok = any(x["status"] == "RESOLVED" for x in D["slots"] if x["family"] == s["family"]); demo_ok = de["committed"] and de["eq"]
                    fmt = bool(re.search(r"(?im)^\s*(STEP\s*\d*\s*:|CANCEL_SLOT|REFERENT\s*[:=])", rep))
                    cls = "EXACT" if (fmt and fam_ok and demo_ok) else "FORMAT_ERROR" if not fmt else "SEMANTIC_ERROR"
                    recov_class[cls] += 1; M["TEACHER_RECOVERY_RESPONSE_EXACT"].append(cls == "EXACT")
                    M["TEACHER_RECOVERY_TRUNCATION_COUNT"].append((l.get("provenance") or {}).get("truncations") or 0)
            if evs_t: M["RECOVERY_TARGET_SUCCESS"].append(learned)
            events_all += evs_t
            if not learned:
                c = RM.earliest_cause(O, it, demo_evals, lesson_src, rec, Ji, Jf, {"find_relations": BE.find_relations, "status_constraints": BE.status_constraints, "teacher_log": O.get("teacher_log", [])})
                causes[c] += 1; tgt[f"{sid}|{O['name']}"] = {"earliest_cause": c, "entered_recovery": bool(evs_t)}
                M["TARGETS_FAILED_AFTER_RECOVERY" if evs_t else "TARGETS_FAILED_WITHOUT_RECOVERY"].append(1)
            else: tgt[f"{sid}|{O['name']}"] = {"earliest_cause": None, "entered_recovery": bool(evs_t)}
            M["TARGETS_ENTERING_RECOVERY"].append(1 if evs_t else 0)
        # provider events by role (spec §57)
        for c in A.get("hosted_calls", []):
            if c.get("truncations"): M[f"PROVIDER_TRUNCATION_{(c.get('role') or 'teacher').upper()}"].append(c["truncations"])
    out = {}
    for k, v in M.items():
        if k.startswith(("TARGETS_", "PROVIDER_TRUNCATION_", "TEACHER_RECOVERY_TRUNCATION")): out[k] = sum(v)
        else: out[k] = PE.m_(v); out["n_" + k] = len(v); out["k_" + k] = int(sum(bool(x) for x in v))
    out.update(RM.summarize_events(events_all)); out["EARLIEST_CAUSE"] = dict(causes); out["WRONG_ACTION_EARLIEST_CAUSE"] = dict(wcauses)
    out["TEACHER_RECOVERY_RESPONSE_CLASSES"] = dict(recov_class); out["recovery_events"] = events_all; out["target_causes"] = tgt
    return out


def counts(R, k):
    """(numerator, denominator) for a mean metric of the parent code"""
    v, n = R.get(k), R.get("n_" + k)
    return (int(round(v * n)), n) if (v is not None and n) else (0, n or 0)


def gates_D(R):
    out = {}
    for grp, G in GATES_D.items():
        for k, (op, th) in G.items():
            v = R.get(k); out[k] = {"group": grp, "rule": f"{op} {th}", "value": v, "pass": v is not None and ((v == th) if op == "==" else (v >= th))}
    for k in PRIMARY: out["FLOOR_" + k] = {"group": "floor", "rule": f">= {FLOOR}", "value": R.get(k), "pass": R.get(k) is not None and R[k] >= FLOOR}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True); ap.add_argument("--arms", default=",".join(ORDER)); ap.add_argument("--out", default=None)
    ap.add_argument("--rescore", action="store_true"); ap.add_argument("--only", default=None); a = ap.parse_args()
    out_dir = a.out or os.path.join(ROOT, "results", a.suite); os.makedirs(out_dir, exist_ok=True); tag = a.suite
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]
    if a.only: S = [s for s in S if s["scenario_id"] in a.only.split(",")]
    arms = [x for x in ORDER if x in a.arms.split(",")]; E = {}; fn = lambda arm: os.path.join(out_dir, f"RCI_{arm}.json")
    if a.rescore:
        for arm in arms: E[arm] = json.load(open(fn(arm)))
        J = json.load(open(os.path.join(out_dir, "JUDGE_LABELS.json"))) if os.path.exists(os.path.join(out_dir, "JUDGE_LABELS.json")) else {}
        HO = json.load(open(os.path.join(out_dir, "HANDOFF.json"))) if os.path.exists(os.path.join(out_dir, "HANDOFF.json")) else {}
    else:
        for w in PE.WORKERS: PE.svc("restart", w)
        for arm in [x for x in arms if ARMS[x][1] == "LOCAL"]:
            t0 = time.time(); print(f"[{arm}] acquisition", flush=True); E[arm] = {"acq": acquire(arm, S, out_dir), "seconds": {"acquisition": round(time.time() - t0, 1)}}
        hosted = [x for x in arms if ARMS[x][1] == "HOSTED"]; J = {}; HO = {}
        if hosted:
            import client as CL
            PE.teacher_up(); meter0 = CL.meter_usd(); os.environ.update(PE.secrets_env())
            pre = TE.judge_preflight(); print("judge preflight", pre, flush=True); json.dump(pre, open(os.path.join(out_dir, "JUDGE_PREFLIGHT.json"), "w"), indent=1)
            th = []
            def go(arm):
                t0 = time.time(); print(f"[{arm}] acquisition (hosted)", flush=True); E[arm] = {"acq": acquire(arm, S, out_dir), "seconds": {"acquisition": round(time.time() - t0, 1)}}
            for arm in hosted: t = threading.Thread(target=go, args=(arm,)); t.start(); th.append(t)
            [t.join() for t in th]
            for arm in hosted:
                print(f"[{arm}] judge", flush=True); J.update({f"{arm}|{k}": v for k, v in judge_jobs(arm, S, E[arm]["acq"]).items()})
            json.dump(J, open(os.path.join(out_dir, "JUDGE_LABELS.json"), "w"), indent=1)
            for k in ("TEACHER_URL", "TEACHER_API_KEY"): os.environ.pop(k, None)
            HO = HE.teardown(tag); HO["meter_usd_at_deploy"] = meter0
            try: HO["meter_usd_after"] = CL.meter_usd()
            except Exception: pass
        HO["moved_learn"] = {arm: HE.move_learn(arm, S, out_dir) for arm in arms}; json.dump(HO, open(os.path.join(out_dir, "HANDOFF.json"), "w"), indent=1)
        json.dump(HO, open(os.path.join(ROOT, "handoff_audit", f"handoff_{tag}.json"), "w"), indent=1)
        for arm in arms:
            t0 = time.time(); print(f"[{arm}] reuse", flush=True); E[arm]["reuse"] = PE.reuse(arm, S, out_dir); E[arm]["seconds"]["reuse"] = round(time.time() - t0, 1)
            json.dump(E[arm], open(fn(arm), "w"), indent=1, default=str)
        for w in PE.WORKERS: PE.svc("stop", w)
    RES = {}
    for arm in arms:
        ACQ, REU = E[arm]["acq"], E[arm]["reuse"]; H = PE.active_hashes(out_dir, arm, S)
        for sid, A_ in ACQ.items():
            if isinstance(A_, dict): A_["_active_hashes"] = H.get(sid, {})
        R = PE.metrics(arm, S, ACQ, REU, out_dir, None); R.pop("gates", None)
        R["DETECTABLE_BAD_SUGGESTION_EXECUTED"] = R.pop("BAD_TEACHER_SUGGESTION_EXECUTED", 0)
        for k in ("COUNTERFACTUAL_EXACT", "DISTILLED_SKILL_EXACT", "WRONG_TEACHER_ACTION_EXECUTED", "BAD_PROCEDURE_ACTIVATED", "STUDENT_TRACE_EXACT"): R.pop(k, None); R.pop("n_" + k, None)
        R["RESTART_EXACT_ALL_TARGETS"] = R.pop("RESTART_PROCEDURE_EXACT", None); R.pop("UNSEEN_ARGUMENT_EXACT", None)
        Jarm = {k.split("|", 1)[1]: v for k, v in J.items() if k.startswith(arm + "|")}
        Jttp = {k.split("|", 1)[1]: v for k, v in Jarm.items() if k.startswith("init|")}               # parent faithfulness metric = initial lesson
        R.update(TE.ttp_metrics(arm, S, ACQ, REU, out_dir, HO, Jttp)); R["COMMITTED_TRACE_BEHAVIORAL_EXACT"] = R.get("TRACE_BEHAVIORAL_EXACT")
        R["GROUNDING_BEHAVIORAL_EXACT_ALL"] = R.get("GROUNDING_BEHAVIORAL_EXACT")
        R.update(rci_metrics(arm, S, ACQ, R, Jarm))
        R["FIRST_PASS_SCENARIO_EXACT"] = PE.m_([all(t["learned_exact"] and not any(str(x["end"]).startswith("ABORTED") for x in t["demos"]) and len(t["demos"]) <= 2
                                                     for k, t in R["per_target"].items() if k.startswith(sid + "|")) and (R["per_scenario"].get(sid) or {}).get("exact", False)
                                                 for sid in (s["scenario_id"] for s in S)]) if ARMS[arm][0] not in ("GOLD_TRACE", "FORMAL_TEACH") else R.get("SCENARIO_EXACT")
        R["counts"] = {k: counts(R, k) for k in list(PRIMARY) + ["TEACHER_EPISODE_SUCCESS", "INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT", "RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT", "RECOVERY_TARGET_SUCCESS"]}
        R["gates"] = gates_D(R) if arm == "D" else {k: g for k, g in gates_D(R).items() if g["group"] == "safety" and k not in ("WRONG_BEHAVIORAL_ACTION_EXECUTED", "TRACE_BEHAVIORAL_EXACT")}
        if arm in ("GOLD_TRACE", "FORMAL_TEACH"): R["gates"] = {k: {"rule": "== 1.0", "value": R.get(k), "pass": R.get(k) == 1.0} for k in ("LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT")}
        R["arm"] = arm; R["mode"], R["grounder"], R["recovery"] = ARMS[arm]; R["seconds"] = E[arm].get("seconds"); RES[arm] = R
        E[arm]["results"] = R; json.dump(E[arm], open(fn(arm), "w"), indent=1, default=str)
        rd = os.path.join(ROOT, "recovery_events", a.suite); os.makedirs(rd, exist_ok=True); json.dump(R.get("recovery_events"), open(os.path.join(rd, f"{arm}.json"), "w"), indent=1)
        print(arm, json.dumps({k: R.get(k) for k in ("LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT", "DISTILLED_SKILL_EXACT", "GROUNDING_BEHAVIORAL_EXACT", "WRONG_BEHAVIORAL_ACTION_EXECUTED", "RECOVERY_EVENT_SUCCESS")}), flush=True)
    cons = {}
    for k in ("LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT", "FIRST_PASS_SCENARIO_EXACT", "DISTILLED_SKILL_EXACT", "INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT", "RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT",
              "COMMITTED_TRACE_BEHAVIORAL_EXACT", "RECOVERY_EVENT_SUCCESS", "RECOVERY_TARGET_SUCCESS", "WRONG_BEHAVIORAL_ACTION_EXECUTED", "GROUNDING_BEHAVIORAL_EXACT"):
        g = lambda x: (RES.get(x) or {}).get(k); d = lambda x, y: round(g(x) - g(y), 4) if isinstance(g(x), (int, float)) and isinstance(g(y), (int, float)) else None
        cons[k] = {a_: g(a_) for a_ in ("B", "E", "F", "D")} | {"E-B": d("E", "B"), "D-F": d("D", "F"), "F-B": d("F", "B"), "D-E": d("D", "E"),
                                                               "interaction (D-F)-(E-B)": round(d("D", "F") - d("E", "B"), 4) if d("D", "F") is not None and d("E", "B") is not None else None}
    summary = {"suite": a.suite, "config_fingerprint": config_fingerprint(), "rci_budget_override": os.environ.get("RCI_BUDGET_OVERRIDE"), "arms": {arm: {k: v for k, v in R.items() if k not in ("per_scenario", "per_target", "recovery_events")} for arm, R in RES.items()}, "factorial": cons, "handoff": HO,
               "controls_pass": all(g["pass"] for arm in ("GOLD_TRACE", "FORMAL_TEACH") if arm in RES for g in RES[arm]["gates"].values())}
    json.dump(summary, open(os.path.join(out_dir, "RCI_SUMMARY.json"), "w"), indent=1, default=str)
    print(json.dumps({"controls_pass": summary["controls_pass"], "D_gates_failed": [k for k, g in (RES.get("D") or {}).get("gates", {}).items() if not g["pass"]]}))


if __name__ == "__main__":
    main()
