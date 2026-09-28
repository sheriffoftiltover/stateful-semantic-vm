"""RCI failure taxonomy, earliest-cause rule and recovery metrics (spec §10-§14, §36-§40, §55-§57; spec/FAILURE_TAXONOMY_V1.json,
spec/RECOVERY_METRICS_V1.json). Evaluator-only, deterministic given the saved acquisition records and the (saved) judge labels.

EARLIEST-CAUSE RULE (frozen): walk the target's demonstrations chronologically, skipping registered legal-bad / relation-swap probe
demonstrations; the FIRST demonstration that did not end COMMITTED-and-behaviourally-exact is the divergence point, and within it the layers are
evaluated in the frozen precedence  teacher -> grounder -> controller -> evidence -> procedure  (spec §13). If no demonstration diverged, the
learn-level / budget / provider outcome decides. A provider failure is the cause only if nothing diverged earlier (spec §12 example)."""
import json, re, collections, statistics
TAXONOMY = {
 "provider": ["PROVIDER_TRUNCATION", "PROVIDER_TRANSPORT", "PROVIDER_RUNTIME"],
 "teacher_initial": ["TEACHER_INITIAL_SEMANTIC_ERROR", "TEACHER_INITIAL_MISSING_CONTENT", "TEACHER_INITIAL_FORMAT_ERROR"],
 "grounder_initial": ["GROUNDER_INITIAL_OP_ERROR", "GROUNDER_INITIAL_ARGUMENT_ERROR", "GROUNDER_INITIAL_RELATION_ERROR", "GROUNDER_INITIAL_REFERENCE_ERROR",
                      "GROUNDER_INITIAL_SEQUENCE_ERROR", "GROUNDER_INITIAL_SCOPE_ERROR"],
 "recovery": ["GROUNDER_FALSE_CLARIFICATION", "GROUNDER_RECOVERY_SEMANTIC_ERROR", "TEACHER_RECOVERY_SEMANTIC_ERROR", "TEACHER_RECOVERY_MISSING_CONTENT",
              "TEACHER_RECOVERY_FORMAT_ERROR", "RECOVERY_CLARIFICATION_BUDGET", "RECOVERY_REPHRASE_BUDGET", "RECOVERY_TEACHER_TURN_BUDGET", "RECOVERY_DEMONSTRATION_BUDGET"],
 "controller": ["CONTROLLER_STATE_ERROR", "CONTROLLER_REFERENCE_ERROR", "CONTROLLER_EVIDENCE_COUNT_ERROR", "CONTROLLER_PROTOCOL_VIOLATION"],
 "evidence": ["EVIDENCE_INSUFFICIENT_VARIATION", "EVIDENCE_CONFLICT_UNRESOLVED", "EVIDENCE_NONVACUITY_FAILURE"],
 "procedure": ["PROCEDURE_ABSTRACTION_ERROR", "PROCEDURE_RETRIEVAL_ERROR", "VERIFIER_FALSE_ACCEPT", "VERIFIER_FALSE_REJECT", "VERIFIER_CRASH"],
 "fallback": ["OTHER_PREDECLARED"]}
ALL = [x for v in TAXONOMY.values() for x in v]
PRECEDENCE = ["teacher", "grounder", "controller", "evidence", "procedure"]
LEGIT = {"REFERENCE"}                                                   # a clarification that is NEEDED (>=2 compatible live results)
GR_ILLEGAL = {"RELATION_LOCATION_ERROR": "GROUNDER_INITIAL_RELATION_ERROR", "UNREQUESTED_RETURN": "GROUNDER_INITIAL_SEQUENCE_ERROR",
              "PREMATURE_TERMINAL_ACTION": "GROUNDER_INITIAL_SEQUENCE_ERROR", "UNNAMED_CALL": "GROUNDER_INITIAL_OP_ERROR", "SCHEMA": "GROUNDER_INITIAL_OP_ERROR",
              "MISSING_ARGUMENT": "GROUNDER_INITIAL_ARGUMENT_ERROR"}
EXEC_FAIL = ("NOT_FOUND", "VM_EXEC_ERROR", "TYPE_ERROR", "RESOLUTION_AMBIGUOUS", "MISSING_ARGUMENT", "EXEC_FAILED")
RECOVERY_Q = ("RESTATE_SLOT", "RESTATE_OBSCURED", "CLARIFY_REFERENCE")


def diff_label(prog, ref, find_relations, status_constraints, prefix="GROUNDER_INITIAL_"):
    """classify a behavioural divergence of an executed program from its reference (frozen order)"""
    if find_relations(prog) != find_relations(ref): return prefix + "RELATION_ERROR"
    if status_constraints(prog) != status_constraints(ref): return prefix + "SCOPE_ERROR"
    if [s["op"] for s in prog] != [s["op"] for s in ref][:len(prog)]: return prefix + ("OP_ERROR" if len(prog) == len(ref) else "SEQUENCE_ERROR")
    c = lambda st: re.findall(r'"const": "([^"]+)"', json.dumps(st))
    if c(prog) != c(ref)[:len(c(prog))]: return prefix + "ARGUMENT_ERROR"
    return prefix + "REFERENCE_ERROR"


def recovery_events(D, O):
    """spec §36-§37: one event per required slot FAMILY that ever left the happy path; attempts = recovery questions to the teacher + grounder retries"""
    fams = collections.OrderedDict()
    for s in D.get("slots", []): fams.setdefault(s["family"], []).append(s)
    lines = D.get("results") or []; qs = [q for q in O.get("student_questions", []) if q["kind"] in RECOVERY_Q]
    ev = []
    for fam, ss in fams.items():
        root = next((x for x in ss if x["slot_id"] == fam), ss[0])
        ids = {x["slot_id"] for x in ss}; recs = [r for r in lines if r.get("slot_id") in ids]
        bad = [r for r in recs if r["status"] != "OK"]
        if not root["required"] or (not bad and not root.get("displaced")): continue
        first = bad[0] if bad else None
        fam_q = [q for q in qs if q.get("slot_id") in ids]
        retries = sum(max(0, len(r.get("attempts") or []) - 1) for r in recs)
        resolved = any(x["status"] == "RESOLVED" for x in ss if x["slot_id"] != fam or not root.get("displaced")) and \
                   all(x["status"] in ("RESOLVED", "REPLACED", "CANCELLED", "ABANDONED") for x in ss)
        ev.append({"demo": D["index"], "family": fam, "start_error": (first or {}).get("clarify_kind") or (first or {}).get("status") or ("OBSCURED" if root.get("displaced") else None),
                   "start_status": (first or {}).get("status"), "teacher_attempts": len(fam_q), "grounder_retries": retries, "attempts": len(fam_q) + retries,
                   "resolved": bool(resolved), "demo_end": D.get("end"), "displaced": bool(root.get("displaced"))})
    return ev


def initial_lesson_lines(D):
    return [s["original_text"] for s in D.get("slots", []) if s["source"] in ("TEACHER", "SCRIPTED_TEACHER") and not s.get("from_recovery") and not s.get("replacement_for")]


def final_lesson_lines(D):
    return [s["original_text"] for s in D.get("slots", []) if s["source"] in ("TEACHER", "SCRIPTED_TEACHER") and s["status"] not in ("CANCELLED", "REPLACED")]


def earliest_cause(O, it, demo_evals, lesson_src, recovery_src, J_init, J_final, ctx):
    """-> one label from ALL. demo_evals[i] = dict(committed, complete, eq, prog, ref, legal, kind)"""
    fail = O.get("fail") or ""
    for D, ev in zip(O["demos"], demo_evals):
        if ev["legal"]: continue                                      # registered probe demonstration: its detection is scored separately
        if ev["committed"] and ev["eq"]: continue
        end = str(D.get("end") or ""); why = end.split(":", 1)[1] if end.startswith("ABORTED:") else None
        # ---- teacher (lesson stream) ----
        if why in ("NO_STEPS", "RESTARTED_BY_TEACHER", "TEACHER_GAVE_NO_REMAINING_STEPS"): return "TEACHER_INITIAL_FORMAT_ERROR"
        if why == "EXAMPLE_INCOMPLETE": return "TEACHER_INITIAL_MISSING_CONTENT"
        if lesson_src == "HOSTED" and not ev["kind"]:
            ji = J_init.get(D["index"]) or {}
            if ji.get("faithful") is False:
                kinds = [x.get("kind") for x in ji.get("issues") or []]
                return "TEACHER_INITIAL_MISSING_CONTENT" if "MISSING_STEP" in kinds else "TEACHER_INITIAL_SEMANTIC_ERROR"
        evs = [e for e in recovery_events(D, O) if not e["displaced"] or True]
        rec_used = bool(evs)
        if recovery_src == "HOSTED" and rec_used:
            ji, jf = J_init.get(D["index"]) or {}, J_final.get(D["index"]) or {}
            init_ok = lesson_src == "SCRIPTED" or ji.get("faithful") is True
            if init_ok and jf.get("faithful") is False: return "TEACHER_RECOVERY_SEMANTIC_ERROR"
        # ---- committed but wrong ----
        if ev["committed"]:
            if rec_used: return "TEACHER_RECOVERY_SEMANTIC_ERROR" if recovery_src == "HOSTED" else "GROUNDER_RECOVERY_SEMANTIC_ERROR"
            return diff_label(ev["prog"], ev["ref"], ctx["find_relations"], ctx["status_constraints"]) if ev["ref"] else "TEACHER_INITIAL_MISSING_CONTENT"
        # ---- aborted ----
        if why == "EPISODE_END":
            if O["status"] in ("PROVIDER_FAILURE", "BUDGET_STOP") and not rec_used: return "PROVIDER_TRUNCATION" if "TRUNCATION" in fail else "PROVIDER_TRANSPORT"
            if not rec_used: return "RECOVERY_TEACHER_TURN_BUDGET" if "turns" in fail else ("PROVIDER_TRUNCATION" if "TRUNCATION" in fail else "PROVIDER_RUNTIME")
        if why == "MISSING_SLOT": return "GROUNDER_INITIAL_OP_ERROR"             # an obscured line was executed instead of clarified
        if why in ("INCOMPLETE", "PREMATURE_TERMINATION"): return "CONTROLLER_PROTOCOL_VIOLATION"
        if why == "ORACLE_RECOVERY_UNSUPPORTED":
            return diff_label(ev["prog"], ev["ref"], ctx["find_relations"], ctx["status_constraints"]) if (ev["prog"] and ev["ref"]) else "OTHER_PREDECLARED"
        if evs:
            e = evs[0]; se = e["start_error"]; st = e["start_status"]
            if se in GR_ILLEGAL: return GR_ILLEGAL[se]
            if st in EXEC_FAIL: return "GROUNDER_INITIAL_ARGUMENT_ERROR"
            if se in LEGIT:
                fmt = [l for l in ctx["teacher_log"] if l.get("kind") == "CLARIFY_REFERENCE" and l.get("slot_id", "").startswith(f"demo{D['index'] + 1}-") and not re.search(r"(?i)REFERENT\s*[:=]", l.get("reply") or "")]
                return "TEACHER_RECOVERY_FORMAT_ERROR" if fmt else "RECOVERY_CLARIFICATION_BUDGET"
            if se == "OBSCURED" or e["displaced"]:
                return "TEACHER_RECOVERY_MISSING_CONTENT" if recovery_src == "HOSTED" else "GROUNDER_RECOVERY_SEMANTIC_ERROR"
            if why == "SLOT_RECOVERY_FAIL" or why is None or why == "EPISODE_END":
                fmt = [l for l in ctx["teacher_log"] if l.get("kind") in ("RESTATE_SLOT", "RESTATE_OBSCURED") and l.get("slot_id", "").startswith(f"demo{D['index'] + 1}-")
                       and not re.search(r"(?im)^\s*(STEP\s*\d*\s*:|CANCEL_SLOT)", l.get("reply") or "")]
                if fmt and recovery_src == "HOSTED": return "TEACHER_RECOVERY_FORMAT_ERROR"
                return "GROUNDER_FALSE_CLARIFICATION"
        if why == "EPISODE_END": return "RECOVERY_TEACHER_TURN_BUDGET" if "turns" in fail else ("PROVIDER_TRUNCATION" if "TRUNCATION" in fail else "PROVIDER_RUNTIME")
        return "OTHER_PREDECLARED"
    # ---- nothing diverged: evidence / procedure / budgets ----
    ends = [D.get("learn") or D.get("end") for D in O["demos"]]; det = json.dumps([D.get("end_detail") for D in O["demos"]] + [D.get("learn_detail") for D in O["demos"]])
    if O["status"] in ("PROVIDER_FAILURE", "BUDGET_STOP"): return "PROVIDER_TRUNCATION" if "TRUNCATION" in fail else "PROVIDER_TRANSPORT"
    if "LEARNER_ERROR" in ends: return "VERIFIER_CRASH"
    if "EVIDENCE_VACUOUS" in det: return "EVIDENCE_NONVACUITY_FAILURE"
    if O["status"] == "ACTIVE": return "PROCEDURE_ABSTRACTION_ERROR"
    if any(str(e).startswith("REJECTED") for e in ends): return "VERIFIER_FALSE_REJECT"
    last = next((e for e in reversed(ends) if e), None)
    if last == "EVIDENCE_CONFLICT": return "EVIDENCE_CONFLICT_UNRESOLVED"
    if last == "REQUIRE_SECOND_DEMONSTRATION" or "not identifiable" in det or "does not vary" in det: return "EVIDENCE_INSUFFICIENT_VARIATION"
    if "turns per target" in fail: return "RECOVERY_TEACHER_TURN_BUDGET"
    if "demonstration budget" in fail: return "RECOVERY_DEMONSTRATION_BUDGET"
    return "OTHER_PREDECLARED"


def wrong_action_cause(D, O, ev, lesson_src, recovery_src, J_init, J_final, ctx):
    if lesson_src == "HOSTED" and (J_init.get(D["index"]) or {}).get("faithful") is False: return "TEACHER_INITIAL_SEMANTIC_ERROR"
    if recovery_events(D, O):
        if recovery_src == "HOSTED" and (J_final.get(D["index"]) or {}).get("faithful") is False: return "TEACHER_RECOVERY_SEMANTIC_ERROR"
        return "GROUNDER_RECOVERY_SEMANTIC_ERROR"
    return diff_label(ev["prog"], ev["ref"], ctx["find_relations"], ctx["status_constraints"]) if ev["ref"] else "OTHER_PREDECLARED"


def summarize_events(events):
    at = [e["attempts"] for e in events]
    return {"RECOVERY_EVENT_COUNT": len(events), "RECOVERY_EVENT_SUCCESS": round(sum(e["resolved"] for e in events) / len(events), 4) if events else None,
            "n_RECOVERY_EVENT_SUCCESS": len(events), "RECOVERY_EVENT_SUCCESS_COUNT": sum(e["resolved"] for e in events),
            "RECOVERY_ATTEMPTS_PER_EVENT": {"mean": round(statistics.mean(at), 3) if at else None, "median": statistics.median(at) if at else None, "max": max(at) if at else None,
                                            "distribution": dict(sorted(collections.Counter(at).items()))},
            "RECOVERY_EVENTS_BY_START_ERROR": dict(collections.Counter(str(e["start_error"]) for e in events))}
