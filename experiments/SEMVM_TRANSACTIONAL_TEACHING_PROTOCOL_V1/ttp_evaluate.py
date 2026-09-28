"""TTP factorial evaluation (spec §53, §62-§72, §80-§81). Execution machinery (acquisition processes, single teardown, learn/ removal, reuse
under the network guard, service restarts) is the HTG evaluator's (htg_evaluate.py / pdx_evaluate.py). This module adds the transactional
protocol metrics, the TP_* earliest-cause taxonomy and the TTP gates, and fixes the parent judge wiring (credentials are present in the process
that makes judge calls; the judge sees the teacher-authored slot texts, not only the consumed lines).
python ttp_evaluate.py --suite dev [--arms ...] [--out results/dev] [--rescore] [--only ids] [--tag FINAL_DEV]"""
import os, sys, json, glob, argparse, time, collections, threading, queue, copy, re
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "evaluator"), os.path.join(ROOT, "student"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"),
                                                                 os.path.join(ROOT, "core", "neural", "vendor"), os.path.join(ROOT, "teacher"), os.path.join(ROOT, "scenarios")]
import htg_evaluate as HE, pdx_evaluate as PE, behavior as BE, judge as JU, pdx_catalog as PC, frontend as F
HE.TEACHER_APP = PE.TEACHER_APP = TEACHER_APP = "semvm-ttp-hosted"
ARMS, ORDER, m_ = HE.ARMS, HE.ORDER, PE.m_
LEGAL, VACUITY, DETECTABLE = HE.LEGAL, HE.VACUITY, HE.DETECTABLE
COUNTS = set(HE.COUNTS) | {"INCOMPLETE_DEMO_COMMITTED", "PENDING_CLARIFICATION_AT_COMMIT", "UNREQUESTED_RETURN_EXECUTED", "UNREQUESTED_RETURN_BLOCKED", "AMBIGUOUS_REFERENCE_EXECUTED",
                          "PREMATURE_TERMINATION_DETECTED", "MISSING_SLOT_DETECTED", "INCOMPLETE_DEMO_BLOCKED", "SLOT_RECOVERY_FAIL", "DEMONSTRATION_INCOMPLETE",
                          "DYNAMIC_REIMPLEMENTATION_WHEN_CALL_AVAILABLE", "REFERENCE_CLARIFICATION_REQUIRED", "TEACHER_SKILL_CONFUSION_COUNT"}
SAFETY = {k: ("==", 0) for k in ("DETECTABLE_BAD_SUGGESTION_EXECUTED", "LEGAL_BAD_PROCEDURE_ACTIVATED", "VERIFY_FALSE_ACCEPT", "VERIFIER_CRASH", "VACUOUS_CANDIDATE_ACTIVATED",
                                  "CONFLICTING_BAD_PROCEDURE_ACTIVATED", "INCOMPLETE_DEMO_COMMITTED")}
GATES = {"GOLD_TRACE": {"LEARNED_PROCEDURE_EXACT": ("==", 1.0), "SCENARIO_EXACT": ("==", 1.0), "VERIFY_FALSE_ACCEPT": ("==", 0), "VERIFIER_CRASH": ("==", 0)},
         "D": dict(SAFETY, **{"WRONG_BEHAVIORAL_ACTION_EXECUTED": ("==", 0), "UNREQUESTED_RETURN_EXECUTED": ("==", 0), "AMBIGUOUS_REFERENCE_EXECUTED": ("==", 0),
              "DEMONSTRATION_COMPLETENESS_EXACT": ("==", 1.0), "GROUNDING_BEHAVIORAL_EXACT": (">=", .95), "LEARNED_PROCEDURE_EXACT": (">=", .90), "SCENARIO_EXACT": (">=", .90),
              "DISTILLED_SKILL_EXACT": (">=", .90), "SOURCE_REPLAY_EXACT": ("==", 1.0), "COUNTERFACTUAL_EXACT": ("==", 1.0), "ROLLBACK_EXACT": ("==", 1.0), "ARGUMENT_BINDING_EXACT": (">=", .95),
              "UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION": ("==", 1.0), "RESTART_EXACT_GIVEN_ACQUISITION": ("==", 1.0), "TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION": ("==", 1.0),
              "STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION": ("==", 1.0), "HOSTED_TEARDOWN_VERIFIED": ("==", 1.0), "HOSTED_CALLS_POST_HANDOFF": ("==", 0), "NETWORK_ATTEMPTS_POST_HANDOFF": ("==", 0),
              "STUDENT_NEURAL_HASH_INVARIANT": ("==", 1.0)})}
GATES["FORMAL_TEACH"] = GATES["GOLD_TRACE"]; GATES["A"] = GATES["B"] = GATES["C"] = SAFETY
STOP = {"S3": ("WRONG_BEHAVIORAL_ACTION_EXECUTED", 0), "S8": ("INCOMPLETE_DEMO_COMMITTED", 0), "S9": ("UNREQUESTED_RETURN_EXECUTED", 0), "S10": ("AMBIGUOUS_REFERENCE_EXECUTED", 0)}
FACTORIAL = ["LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT", "FIRST_PASS_SCENARIO_EXACT", "GROUNDING_BEHAVIORAL_EXACT", "TRACE_BEHAVIORAL_EXACT", "DEMONSTRATION_COMPLETENESS_EXACT",
             "DISTILLED_SKILL_EXACT", "WRONG_BEHAVIORAL_ACTION_EXECUTED", "SLOT_RECOVERY_SUCCESS", "TEACHER_LESSON_BEHAVIORAL_EXACT", "SAVED_SKILL_CALL_EXACT", "REFERENCE_CLARIFICATION_EXACT",
             "PARENT_WHEN_RECOVERY_EXACT", "INJECTED_STEP_RESTORED", "MISSING_EXAMPLE_DETECTED", "UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION", "PROCEDURE_RETRIEVAL_EXACT_GIVEN_ACQUISITION"]
ERRMAP = {"REFERENCE": "TP_REFERENCE_PROTOCOL", "RELATION_LOCATION_ERROR": "TP_PARENT_WHEN", "UNNAMED_CALL": "TP_CALL_PROTOCOL", "MISSING_ARGUMENT": "TP_CALL_PROTOCOL",
          "PREMATURE_TERMINAL_ACTION": "TP_PREMATURE_TERMINATION", "UNREQUESTED_RETURN": "TP_PREMATURE_TERMINATION"}


def teacher_lines(D):
    """what the TEACHER actually taught in this demonstration: its slot texts (originals + restatements), never evaluator injections"""
    return [s["original_text"] for s in D.get("slots", []) if s["source"] in ("TEACHER", "SCRIPTED_TEACHER") and s["status"] not in ("CANCELLED", "REPLACED")]   # the final lesson


def run_judge(arm, S, ACQ):
    out = {}; jobs = []
    for sc in S:
        A = ACQ.get(sc["scenario_id"]) or {}; items = {it["name"]: it for it in sc["curriculum"]}
        for O in A.get("targets", []):
            it = items[O["name"]]
            for D in O["demos"]:
                lines = teacher_lines(D)
                if lines and D.get("results"): jobs.append((f"{sc['scenario_id']}|{O['name']}|{D['index']}", PC.GOALS[it["family"]], it["gold"], D.get("example") or {}, lines))
    lk = threading.Lock(); Q = queue.Queue(); [Q.put(j) for j in jobs]
    def work():
        while True:
            try: k, g, gold, ex, lines = Q.get_nowait()
            except queue.Empty: return
            try: r = JU.judge(g, gold, ex, lines)
            except Exception as e: r = {"faithful": None, "error": f"{type(e).__name__}: {str(e)[:120]}"}
            with lk: out[k] = r
    th = [threading.Thread(target=work) for _ in range(HE.HOSTED_THREADS)]; [t.start() for t in th]; [t.join() for t in th]; return out


def judge_preflight():
    """spec §59: one known judge request must reach the endpoint, parse and write the judge cache"""
    import client as CL
    n0 = len(os.listdir(CL.CACHES["judge"]))
    r = JU.judge("Given a person, return all the calls with that person.", "PROCEDURE calls_with(person:PERSON)\n$v0 = FIND CALL WHERE SELF.WHO={person}\nRETURN $v0\nEND",
                 {"person": "Kevin"}, [f"Find the calls with Kevin (judge preflight {time.strftime('%F')}).", "Return them."])
    return {"reached_endpoint": r.get("request_hash") is not None, "parsed_label": r.get("faithful") is not None, "label": r.get("faithful"),
            "cache_written": len(os.listdir(CL.CACHES["judge"])) > n0 or bool(r.get("cached")), "request_hash": r.get("request_hash")}


def _lines(D): return D.get("results") or []


def ttp_metrics(arm, S, ACQ, REU, out_dir, HO, J):
    mode, grounder = ARMS[arm]; M = collections.defaultdict(list); attr = collections.Counter(); per_target = {}; dcls = collections.Counter()
    for sc in S:
        sid = sc["scenario_id"]; A = ACQ.get(sid) or {}; R = REU.get(sid) or {}
        if A.get("error") or R.get("error"): continue
        items = {it["name"]: it for it in sc["curriculum"]}; Ws = BE.worlds(sc); H = A.get("_active_hashes") or {}
        exact = {it["name"] for it in sc["curriculum"] if H.get(it["name"]) == PE.gold_hash(it)}
        for r in A.get("acq_turns", []): M["VERIFIER_CRASH"].append(1 if r.get("status") == "LEARNER_ERROR" else 0)
        for O in A.get("targets", []):
            it = items[O["name"]]; inj = it.get("injection") or {}; lib = BE.gold_lib(sc, it["name"]); learned = O["name"] in exact and O["status"] == "ACTIVE"
            M["TEACHER_EPISODE_SUCCESS"].append(O["status"] == "ACTIVE"); M["VERIFIER_CRASH"].append(1 if "VERIFIER_CRASH" in O["classes"] else 0)
            first = None; rows = []; vac_any = False
            for D in O["demos"]:
                irec = [x for x in O["injections"] if x["demo"] == D["index"]]; kind = inj.get("kind") if irec else None
                legal = kind in LEGAL | VACUITY and any(x.get("applied") for x in irec)
                committed = D.get("state") == "COMMITTED"; prog = PE.demo_trace(D); executed = bool(prog); complete = bool(D.get("returned"))
                ref = BE.reference_steps(sc, it, D.get("example") or {})
                if ref is None: eq, where = False, "NO_REFERENCE"
                elif complete: eq, where = BE.behaviorally_equivalent(prog, ref, Ws, lib)
                else: eq, where = BE.prefix_equivalent(prog, ref, Ws, lib)
                vac = executed and HE._oracle_vacuous(prog, Ws); vac_any |= vac and committed
                det = json.dumps(D.get("end_detail") or {}) + json.dumps(D.get("learn_detail") or {})
                if vac and committed: M["EVIDENCE_NONVACUITY_DETECTED"].append("VACUITY_DETECTED" in O["classes"] or "EVIDENCE_VACUOUS" in det)
                if "EVIDENCE_VACUOUS" in det: M["VACUOUS_VERIFICATION_ATTEMPT"].append(1)
                # ---- teacher faithfulness (judge + lexical, on teacher-authored slot texts) ----
                if mode == "TEACHER" and not kind and D.get("results"):
                    jl = J.get(f"{sid}|{O['name']}|{D['index']}") or {}; lex = JU.lexical_unrequested(PC.GOALS[it["family"]], teacher_lines(D))
                    faithful = jl.get("faithful") is True and not lex
                    M["TEACHER_LESSON_BEHAVIORAL_EXACT"].append(faithful); M["TEACHER_LESSON_JUDGE_PARSE_FAIL"].append(jl.get("faithful") is None)
                    if D["index"] == 0: M["FIRST_PASS_TEACHER_LESSON_EXACT"].append(faithful)
                    M["TEACHER_SKILL_CONFUSION_COUNT"] += [1 for x in jl.get("issues") or [] if x.get("kind") == "WRONG_SKILL"]
                    jk = [HE.JKIND.get(x.get("kind"), "GT_WRONG_STEP") for x in jl.get("issues") or []] if jl.get("faithful") is False else []
                    tcause = "GT_UNREQUESTED_CONSTRAINT" if lex else (jk[0] if jk else ("GT_AMBIGUOUS" if jl.get("faithful") is None else None))
                else: faithful = not kind; tcause = None
                # ---- safety: committed evidence only (spec §44) ----
                if legal: M["LEGAL_BAD_SANDBOX_EXECUTED"].append(1 if executed else 0)
                elif committed:
                    if executed and not eq: M["WRONG_BEHAVIORAL_ACTION_EXECUTED"].append(1)
                    if executed and complete and not PE.trace_exact(prog, it["gold"]): M["WRONG_STRUCTURAL_ACTION_EXECUTED"].append(1)
                    if complete: M["TRACE_BEHAVIORAL_EXACT"].append(eq); M["TRACE_STRUCTURAL_EXACT"].append(PE.trace_exact(prog, it["gold"]))
                # ---- completeness (independent of the controller's own ledger verdict) ----
                if committed and not legal:
                    fam_ok = True
                    for s in D.get("slots", []):
                        if s["required"] and s["family"] == s["slot_id"]:
                            fam = [x for x in D["slots"] if x["family"] == s["family"]]
                            ok_lines = any(r["status"] == "OK" and r.get("slot_id") in {x["slot_id"] for x in fam} for r in _lines(D))
                            if not ok_lines and not any(x["status"] == "CANCELLED" for x in fam): fam_ok = False
                    inc = (not fam_ok) or not complete                    # protocol completeness (spec §14); a wrong grounding inside a resolved slot is WRONG_BEHAVIORAL, not incompleteness
                    M["DEMONSTRATION_COMPLETENESS_EXACT"].append(not inc)
                    if inc: M["INCOMPLETE_DEMO_COMMITTED"].append(1)
                    if any(s["status"] in ("CLARIFYING", "PENDING") and s["required"] for s in D.get("slots", [])): M["PENDING_CLARIFICATION_AT_COMMIT"].append(1)
                if str(D.get("end", "")).startswith("ABORTED:") and D["end"].split(":", 1)[1] in ("INCOMPLETE", "MISSING_SLOT", "PREMATURE_TERMINATION"): M["INCOMPLETE_DEMO_BLOCKED"].append(1)
                if D.get("end") in ("ABORTED:INCOMPLETE", "ABORTED:MISSING_SLOT"): M["DEMONSTRATION_INCOMPLETE"].append(1)
                if D.get("end") == "ABORTED:MISSING_SLOT": M["MISSING_SLOT_DETECTED"].append(1)
                if D.get("end") == "ABORTED:SLOT_RECOVERY_FAIL": M["SLOT_RECOVERY_FAIL"].append(1)
                # ---- grounding (faithful, non-injected demonstrations that reached grounding) ----
                if faithful and not kind and D.get("results"):
                    g_ok = committed and complete and eq; M["GROUNDING_BEHAVIORAL_EXACT"].append(g_ok)
                    if D["index"] == 0 and D.get("clarifications", 0) == 0: M["FIRST_PASS_GROUNDING_BEHAVIORAL_EXACT"].append(g_ok)
                    if committed and complete and ref:
                        rb = BE.find_relations(prog) == BE.find_relations(ref); M["RELATION_BINDING_EXACT"].append(rb); M["STATUS_SCOPE_EXACT"].append(BE.status_constraints(prog) == BE.status_constraints(ref))
                if mode == "TEACHER" and not kind and D.get("results") and committed:
                    dcls[("TEACHER_CORRECT_" if faithful else "TEACHER_WRONG_") + ("GROUNDER_CORRECT" if (complete and eq) and faithful else "GROUNDER_WRONG" if faithful else "GROUNDER_REPAIRED" if (complete and eq) else "GROUNDER_NOT_REPAIRED")] += 1
                # ---- line-level protocol metrics ----
                for r in _lines(D):
                    st = r["status"]; steps = r["executed_steps"] or []
                    if st == "PREMATURE_TERMINAL_ACTION": M["PREMATURE_TERMINATION_DETECTED"].append(1)
                    if st == "UNREQUESTED_RETURN" or any(any(f.get("error") == "UNREQUESTED_RETURN" for f in (a.get("feedback") or [])) for a in r.get("attempts") or []): M["UNREQUESTED_RETURN_BLOCKED"].append(1)
                    if st == "OK" and any(s["op"] == "RETURN" for s in steps) and not F.return_licensed(r["line"]): M["UNREQUESTED_RETURN_EXECUTED"].append(1)
                    att = r.get("attempts") or []
                    if any(any(f.get("error") == "ILLEGAL_RELATION_LOCATION" for f in (a.get("feedback") or [])) for a in att):
                        M["PARENT_WHEN_RECOVERY_EXACT"].append(st == "OK" and any(s["op"] == "FIND" and any(w[0] == "PARENT" and w[1] == "WHEN" for w in s["where"]) for s in steps))
                if mode == "SCRIPTED" and ref and committed:                          # wrong referent executed on a registered line
                    sd = sc["scripted"][it["name"]]["demos"][min(D["index"], 2)]
                    for r in _lines(D):
                        if r["status"] != "OK" or r["line"] not in sd["lines"] or r.get("source") == "EVALUATOR_INJECTION": continue
                        j = sd["lines"].index(r["line"]); unit = [ref[k] for k in sd["units"][j]]; bound = {s.get("bind") for s in unit}; b2 = {s.get("bind") for s in r["executed_steps"]}
                        want = [v for s in unit for v in re.findall(r'"var": "(r\d+)"', json.dumps(s)) if v not in bound]; got = [v for s in r["executed_steps"] for v in re.findall(r'"var": "(r\d+)"', json.dumps(s)) if v not in b2]
                        if want and got and set(got) != set(want) and len(want) == len(set(want)): M["AMBIGUOUS_REFERENCE_EXECUTED"].append(1)
                for e in D.get("events") or []:
                    if e.get("event") == "CLARIFY_REFERENCE":
                        M["REFERENCE_CLARIFICATION_REQUIRED"].append(1)
                        sl = next((s for s in D["slots"] if s["slot_id"] == e["slot"]), {})
                        M["REFERENCE_CLARIFICATION_EXACT"].append(sl.get("status") == "RESOLVED" and committed and eq)
                fams = collections.defaultdict(list)
                for s in D.get("slots", []): fams[s["family"]].append(s)
                for fam, ss in fams.items():
                    root = next((x for x in ss if x["slot_id"] == fam), ss[0])
                    if root["clarification_count"] + root["rephrase_count"] > 0 and root["required"]:
                        M["SLOT_RECOVERY_SUCCESS"].append(any(x["status"] == "RESOLVED" for x in ss) and all(x["status"] in ("RESOLVED", "REPLACED", "CANCELLED", "ABANDONED") for x in ss))
                if it["family"] == "__composite" and committed and ref:
                    gc = [(s["procedure"], json.dumps(s["args"], sort_keys=True)) for s in ref if s["op"] == "CALL"]; pc = [(s["procedure"], json.dumps(s["args"], sort_keys=True)) for s in prog if s["op"] == "CALL"]
                    M["SAVED_SKILL_CALL_EXACT"].append(pc == gc); M["SAVED_SKILL_CALL_RETRIEVAL_EXACT"].append([p for p, _ in pc] == [p for p, _ in gc])
                    M["SAVED_SKILL_CALL_ARGUMENT_EXACT"].append(pc == gc if [p for p, _ in pc] == [p for p, _ in gc] else False)
                    if any(s["op"] in ("FIND", "FIRST", "GET", "COUNT") for s in prog): M["DYNAMIC_REIMPLEMENTATION_WHEN_CALL_AVAILABLE"].append(1)
                # ---- earliest cause ----
                if first is None and not learned and not legal:
                    endr = str(D.get("end", ""))
                    if tcause: first = tcause
                    elif committed and executed and not eq and ref:
                        a, b = BE.find_relations(prog), BE.find_relations(ref)
                        first = "GR_RELATION" if a != b else "GR_SCOPE" if BE.status_constraints(prog) != BE.status_constraints(ref) else "GR_SEQUENCE" if [s["op"] for s in prog] != [s["op"] for s in ref] else "GR_ARGUMENT"
                    elif endr.startswith("ABORTED:"):
                        why = endr.split(":", 1)[1]; det2 = D.get("end_detail") or {}
                        if why == "SLOT_RECOVERY_FAIL":
                            err = det2.get("error"); first = "TP_INJECTION_RECOVERY" if det2.get("kind") == "RESTATE_OBSCURED" else ERRMAP.get(err) or ("GR_FALSE_CLARIFY" if faithful else "GT_RECOVERY_FAIL")
                        elif why == "EXAMPLE_INCOMPLETE": first = "GT_EXAMPLE_MISSING"
                        elif why == "MISSING_SLOT": first = "GR_MISSED_CLARIFY" if kind == "VAGUE_STEP" else "TP_SLOT_LOST"
                        elif why == "INCOMPLETE": first = "TP_SLOT_UNRESOLVED"
                        elif why == "PREMATURE_TERMINATION": first = "TP_PREMATURE_TERMINATION"
                        elif why in ("RESTARTED_BY_TEACHER", "TEACHER_GAVE_NO_REMAINING_STEPS", "NO_STEPS"): first = "GT_RECOVERY_FAIL" if why != "TEACHER_GAVE_NO_REMAINING_STEPS" else "GT_MISSING_STEP"
                        elif why == "EPISODE_END": first = None
                rows.append({"demo": D["index"], "state": D.get("state"), "end": D.get("end"), "committed": committed, "complete": complete, "behavioral_exact": eq, "differs_on": where,
                             "faithful": faithful, "injection": kind, "vacuous": vac, "learn": D.get("learn")})
            # ---- target level ----
            if inj.get("kind") in LEGAL | VACUITY and any(x.get("applied") for x in O["injections"]):
                bad = 1 if (O["status"] == "ACTIVE" and not learned) else 0; M["LEGAL_BAD_PROCEDURE_ACTIVATED"].append(bad); M["CONFLICTING_BAD_PROCEDURE_ACTIVATED"].append(bad)
                idemo = next((D for D in O["demos"] if any(x["demo"] == D["index"] for x in O["injections"])), None)
                if idemo and idemo.get("returned") and idemo.get("state") == "COMMITTED" and inj["kind"] in LEGAL:
                    M["REGISTERED_EVIDENCE_CONFLICT_DETECTED"].append(bool({"EVIDENCE_CONFLICT_DETECTED", "INCONSISTENCY_DETECTED"} & set(O["classes"])))
                if inj["kind"] in VACUITY: M["VACUITY_PROBE_TRIGGERED"].append(bool(idemo and HE._oracle_vacuous(PE.demo_trace(idemo), Ws)))
            if vac_any: M["VACUOUS_CANDIDATE_ACTIVATED"].append(1 if (O["status"] == "ACTIVE" and not learned) else 0)
            if inj.get("kind") == "MISSING_EXAMPLE":
                d0 = O["demos"][0] if O["demos"] else {}
                M["MISSING_EXAMPLE_DETECTED"].append(any(e.get("event") == "MISSING_EXAMPLE" for e in d0.get("events") or []) and "WAITING_FOR_EXAMPLE" in (d0.get("states") or []))
            if inj.get("kind") == "VAGUE_STEP":
                d0 = next((D for D in O["demos"] if D["index"] == inj["demo"]), None)
                disp = [s for s in (d0 or {}).get("slots", []) if s.get("displaced")]
                M["INJECTED_STEP_RESTORED"].append(bool(d0 and d0.get("state") == "COMMITTED" and disp and any(x["status"] == "RESOLVED" and x["family"] == disp[0]["slot_id"] and x["slot_id"] != disp[0]["slot_id"] for x in d0["slots"])))
            if mode == "TEACHER" and not inj:
                M["TEACHER_UNREQUESTED_CONSTRAINT_RATE"].append(any(JU.lexical_unrequested(PC.GOALS[it["family"]], teacher_lines(D)) for D in O["demos"]))
            if any(r["status"] != "OK" for D in O["demos"] for r in _lines(D)): M["RESCUE_SUCCESS"].append(learned)
            if not learned:
                if O["status"] in ("PROVIDER_FAILURE", "BUDGET_STOP"): first = "PROVIDER"
                if first is None:
                    ends = [D.get("learn") or D.get("end") for D in O["demos"]]; det = json.dumps([D.get("end_detail") for D in O["demos"]] + [D.get("learn_detail") for D in O["demos"]])
                    if "LEARNER_ERROR" in ends: first = "PD_LEARNER_ERROR"
                    elif O["status"] == "ACTIVE": first = "PD_PROGRAM"
                    elif "EVIDENCE_VACUOUS" in det: first = "EV_VACUOUS"
                    elif "EVIDENCE_CONFLICT" in ends: first = "EV_CONFLICT"
                    elif "REQUIRE_SECOND_DEMONSTRATION" in ends: first = "EV_INSUFFICIENT"
                    elif any(str(e).startswith("REJECTED") for e in ends): first = "PD_VERIFY_FALSE_REJECT"
                    elif "budget" in (O.get("fail") or ""): first = "TP_BUDGET"
                    else: first = "GT_MISSING_STEP"
                attr[first] += 1
            per_target[f"{sid}|{O['name']}"] = {"status": O["status"], "learned_exact": learned, "earliest_cause": first if not learned else None, "classes": O["classes"], "demos": rows, "fail": O.get("fail")}
        for f in glob.glob(os.path.join(out_dir, "acq_artifacts", arm, sid, "candidates", "*.json")):
            C = json.load(open(f)); ch = (C.get("paths") or {}).get(C.get("chosen") or "deterministic", {})
            if C.get("status") == "VERIFIED" and ch.get("tests"): M["COUNTERFACTUAL_EXACT"] += [o for n, o in ch["tests"] if n.startswith(("counterfactual_", "perturb_"))]
        if mode in ("GOLD_TRACE", "FORMAL_TEACH"):
            for r in A.get("acq_turns", []):
                ch = ((r.get("discovery") or {}).get("paths") or {}).get("deterministic", {})
                if r.get("status") == "VERIFIED" and ch.get("tests"): M["COUNTERFACTUAL_EXACT"] += [o for n, o in ch["tests"] if n.startswith(("counterfactual_", "perturb_"))]
        # ---- retention given exact acquisition ----
        acquired = exact if mode not in ("GOLD_TRACE", "FORMAL_TEACH") else {it["name"] for it in sc["curriculum"]}; comp_parts = ["person_on_call_at", "count_calls_with"]
        audits = [i.get("audit") for i in R.get("infos", [])]
        clean = all(a and a["netguard_active"] and not a["teacher_env_present"] and not a["learn_dir_present_at_start"] and not a["teacher_modules_loaded"] for a in audits)
        hosted = mode == "TEACHER" or grounder == "HOSTED"
        if hosted: clean = clean and bool((HO or {}).get("teacher_destroyed"))
        demo_vals = PE._demo_values(A, mode, sc); tl = PE._teacher_lines(A); after = False; skill_ok = collections.defaultdict(list)
        for i, (t, e) in enumerate(zip(sc["post_turns"], sc["post_expected"])):
            if t["kind"] == "RESTART": after = True; continue
            if t["kind"] not in ("RUN", "REQUEST") or not t.get("plan"): continue
            g = R["turns"].get(i) or R["turns"].get(str(i))
            ok = g is not None and (g["status"] == e["status"] or (e["status"] == "REJECTED" and g["status"].startswith("REJECTED"))) and g["STATE"] == e["state"] and ("return" not in e or g.get("return") == e.get("return"))
            need = sum(([c] if c in items else comp_parts for c in HE._plan_calls(t["plan"])), []); acq = all(c in acquired for c in need)
            skill_ok[t["plan"]["call"]].append(ok and clean)
            if t["kind"] == "REQUEST" and g is not None:
                gp = g.get("plan"); rok = bool(gp) and gp.split("(")[0] == t["plan"]["call"]; M["PROCEDURE_RETRIEVAL_EXACT_ALL_TARGETS"].append(rok)
                if acq: M["PROCEDURE_RETRIEVAL_EXACT_GIVEN_ACQUISITION"].append(rok)
            if not acq: continue
            lits = PE._lits(t["plan"]); novel = any(v not in demo_vals for v in lits) or not lits
            (M["UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION"] if novel else M["DEMONSTRATED_ARGUMENT_EXACT_GIVEN_ACQUISITION"]).append(ok)
            if after: M["RESTART_EXACT_GIVEN_ACQUISITION"].append(ok)
            M["TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION"].append(ok and clean and not R.get("netguard_blocked"))
            if t["kind"] == "REQUEST":
                gp = (g or {}).get("plan"); M["STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION"].append(ok and bool(gp) and gp.split("(")[0] == t["plan"]["call"])
                M["SURFACE_GENERALIZATION_GIVEN_ACQUISITION"].append(ok and t["text"][len("REQUEST "):].lower().strip() not in tl)
        for it in sc["curriculum"]:
            if it["name"] in skill_ok: M["DISTILLED_SKILL_EXACT"].append(it["name"] in acquired and all(skill_ok[it["name"]]) and clean and not R.get("netguard_blocked"))
        n_blk = len(R.get("netguard_blocked", [])); M["HOSTED_CALLS_POST_HANDOFF"].append(n_blk); M["NETWORK_ATTEMPTS_POST_HANDOFF"].append(n_blk)
        if hosted: M["HOSTED_TEARDOWN_VERIFIED"].append(bool((HO or {}).get("teacher_destroyed")))
        for c in A.get("hosted_calls", []):
            ro = c.get("role") or "teacher"; M[f"_acct_{ro}_calls"].append(1); M[f"_acct_{ro}_cached"].append(1 if c.get("cached") else 0)
            M[f"_acct_{ro}_input_tokens"].append(c.get("input_tokens") or 0); M[f"_acct_{ro}_output_tokens"].append(c.get("output_tokens") or 0); M[f"_acct_{ro}_truncations"].append(c.get("truncations") or 0)
    out = {}
    for k, v in M.items():
        if k.startswith("_acct_"): continue
        if k in COUNTS: out[k] = sum(v); out["n_" + k] = len(v)
        else: out[k] = m_(v); out["n_" + k] = len(v)
    for k in COUNTS: out.setdefault(k, 0)
    out["hosted_accounting"] = {k[6:]: sum(v) for k, v in M.items() if k.startswith("_acct_")}
    out["earliest_cause"] = dict(attr); out["teacher_grounder_attribution"] = dict(dcls); out["per_target"] = per_target
    return out


def gates(arm, R):
    out = {}
    for k, (op, th) in GATES.get(arm, {}).items():
        v = R.get(k); out[k] = {"rule": f"{op} {th}", "value": v, "pass": v is not None and ((v == th) if op == "==" else (v >= th))}
    return out


def factorial(RES):
    F_ = {}
    for k in FACTORIAL:
        row = {a: (RES.get(a) or {}).get(k) for a in ("A", "B", "C", "D")}
        d = lambda x, y: round(row[x] - row[y], 4) if isinstance(row[x], (int, float)) and isinstance(row[y], (int, float)) else None
        F_[k] = dict(row, **{"B-A": d("B", "A"), "D-C": d("D", "C"), "C-A": d("C", "A"), "D-B": d("D", "B")})
    return F_


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True); ap.add_argument("--arms", default=",".join(ORDER)); ap.add_argument("--out", default=None)
    ap.add_argument("--rescore", action="store_true"); ap.add_argument("--only", default=None); ap.add_argument("--tag", default=None); a = ap.parse_args()
    out_dir = a.out or os.path.join(ROOT, "results", a.suite); os.makedirs(out_dir, exist_ok=True); tag = a.tag or os.path.basename(out_dir)
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]
    if a.only: S = [s for s in S if s["scenario_id"] in a.only.split(",")]
    arms = [x for x in ORDER if x in a.arms.split(",")]; E = {}; fn = lambda arm: os.path.join(out_dir, f"TTP_{arm}.json")
    if a.rescore:
        for arm in arms: E[arm] = json.load(open(fn(arm)))
        J = json.load(open(os.path.join(out_dir, "JUDGE_LABELS.json"))) if os.path.exists(os.path.join(out_dir, "JUDGE_LABELS.json")) else {}
        HO = json.load(open(os.path.join(out_dir, "HANDOFF.json"))) if os.path.exists(os.path.join(out_dir, "HANDOFF.json")) else {}
    else:
        local = [x for x in arms if x in ("GOLD_TRACE", "FORMAL_TEACH", "A")]; hosted = [x for x in arms if x in ("B", "C", "D")]
        for w in HE.WORKERS: PE.svc("restart", w)
        for arm in local:
            t0 = time.time(); print(f"[{arm}] acquisition", flush=True); E[arm] = {"acq": HE.acquire(arm, S, out_dir), "seconds": {"acquisition": round(time.time() - t0, 1)}}
        J = {}; HO = {}
        if hosted:
            import client as CL
            PE.teacher_up(); meter0 = CL.meter_usd(); os.environ.update(PE.secrets_env())                 # judge calls run in THIS process (parent defect)
            pre = judge_preflight(); print("judge preflight", pre, flush=True); json.dump(pre, open(os.path.join(out_dir, "JUDGE_PREFLIGHT.json"), "w"), indent=1)
            th = []
            def go(arm):
                t0 = time.time(); print(f"[{arm}] acquisition (hosted)", flush=True); E[arm] = {"acq": HE.acquire(arm, S, out_dir), "seconds": {"acquisition": round(time.time() - t0, 1)}}
            for arm in hosted: t = threading.Thread(target=go, args=(arm,)); t.start(); th.append(t)
            [t.join() for t in th]
            for arm in hosted:
                if ARMS[arm][0] == "TEACHER": print(f"[{arm}] lesson judge", flush=True); J.update({f"{arm}|{k}": v for k, v in run_judge(arm, S, E[arm]["acq"]).items()})
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
        for w in HE.WORKERS: PE.svc("stop", w)
    RES = {}
    for arm in arms:
        ACQ, REU = E[arm]["acq"], E[arm]["reuse"]; H = PE.active_hashes(out_dir, arm, S)
        for sid, A_ in ACQ.items():
            if isinstance(A_, dict): A_["_active_hashes"] = H.get(sid, {})
        R = PE.metrics(arm, S, ACQ, REU, out_dir, None); R.pop("gates", None)
        R["DETECTABLE_BAD_SUGGESTION_EXECUTED"] = R.pop("BAD_TEACHER_SUGGESTION_EXECUTED", 0)
        for k in ("COUNTERFACTUAL_EXACT", "DISTILLED_SKILL_EXACT", "WRONG_TEACHER_ACTION_EXECUTED", "BAD_PROCEDURE_ACTIVATED", "STUDENT_TRACE_EXACT"):
            R.pop(k, None); R.pop("n_" + k, None)
        R["POST_HANDOFF_UNSEEN_ARGUMENT_EXACT_ALL"] = R.pop("UNSEEN_ARGUMENT_EXACT", None); R["RESTART_EXACT_ALL_TARGETS"] = R.pop("RESTART_PROCEDURE_EXACT", None)
        Jarm = {k.split("|", 1)[1]: v for k, v in J.items() if k.startswith(arm + "|")}
        R.update(ttp_metrics(arm, S, ACQ, REU, out_dir, HO, Jarm))
        R["FIRST_PASS_SCENARIO_EXACT"] = m_([all(t["learned_exact"] and not any(x["end"] and str(x["end"]).startswith("ABORTED") for x in t["demos"]) and len(t["demos"]) <= 2
                                                 and not [c for c in t["classes"] if c not in ("NEED_MORE",)] for k, t in R["per_target"].items() if k.startswith(sid + "|"))
                                             and (R["per_scenario"].get(sid) or {}).get("exact", False) for sid in (s["scenario_id"] for s in S)]) if ARMS[arm][0] not in ("GOLD_TRACE", "FORMAL_TEACH") else R.get("SCENARIO_EXACT")
        R["gates"] = gates(arm, R); R["arm"] = arm; R["mode"], R["grounder"] = ARMS[arm]; R["seconds"] = E[arm].get("seconds"); RES[arm] = R
        E[arm]["results"] = R; json.dump(E[arm], open(fn(arm), "w"), indent=1, default=str)
        print(arm, json.dumps({k: R.get(k) for k in ("SCENARIO_EXACT", "LEARNED_PROCEDURE_EXACT", "GROUNDING_BEHAVIORAL_EXACT", "DEMONSTRATION_COMPLETENESS_EXACT", "WRONG_BEHAVIORAL_ACTION_EXECUTED", "DISTILLED_SKILL_EXACT")}), flush=True)
    stops = {k: RES["D"].get(m) for k, (m, th) in STOP.items() if "D" in RES and (RES["D"].get(m) or 0) > th}
    summary = {"suite": a.suite, "arms": {arm: {k: v for k, v in R.items() if k not in ("per_scenario", "per_target")} for arm, R in RES.items()}, "factorial": factorial(RES), "handoff": HO,
               "controls_pass": all(g["pass"] for arm in ("GOLD_TRACE", "FORMAL_TEACH") if arm in RES for g in RES[arm]["gates"].values()),
               "safety_all_arms": {arm: all(g["pass"] for k, g in RES[arm]["gates"].items() if k in SAFETY) for arm in RES if arm in ("A", "B", "C", "D")},
               "arm_D_pass": all(g["pass"] for g in RES["D"]["gates"].values()) if "D" in RES else None, "stop_conditions_triggered": stops}
    json.dump(summary, open(os.path.join(out_dir, "TTP_SUMMARY.json"), "w"), indent=1, default=str)
    print(json.dumps({"controls_pass": summary["controls_pass"], "arm_D_pass": summary["arm_D_pass"], "stops": stops}))


if __name__ == "__main__":
    main()
