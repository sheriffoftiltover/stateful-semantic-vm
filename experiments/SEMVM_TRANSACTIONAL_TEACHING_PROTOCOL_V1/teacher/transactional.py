"""TTP transactional teaching controller (spec §11-§39; spec/TEACHING_STATE_MACHINE_V1.json, spec/DEMONSTRATION_SLOT_SCHEMA_V1.json,
spec/STRUCTURED_CLARIFICATION_V1.json, spec/DEMONSTRATION_COMPLETENESS_V1.json). Replaces the parent's informal utterance stream
(teacher/episode.py run_target) for the SCRIPTED and TEACHER modes.

A demonstration is a transaction: DEMO_OPEN -> EXAMPLE bound -> every lesson line is a SLOT in a ledger -> each slot is grounded and executed
inside the teaching sandbox (so later slots can refer to its runtime result) -> failures are recovered PER SLOT through structured questions
(RESTATE_SLOT / CLARIFY_REFERENCE / MISSING_EXAMPLE / evaluator-obscured restatement) -> completeness check -> COMMIT (:endteach/:endexample,
only now does the trace become learning evidence). A slot that exhausts its budget aborts the WHOLE demonstration: sandbox rolled back, zero
evidence. The teacher never touches the student's stores; the controller never invents content: it only routes, counts and checks."""
import re, json, copy
import protocol as PR, client as CL, episode as EP

STATES = ["NEW", "OPEN", "WAITING_FOR_EXAMPLE", "WAITING_FOR_GROUNDING", "WAITING_FOR_CLARIFICATION", "WAITING_FOR_REPHRASE", "READY_TO_COMMIT", "COMMITTED", "ABORTED"]
TRANSITIONS = {"NEW": {"OPEN"}, "OPEN": {"WAITING_FOR_EXAMPLE", "WAITING_FOR_GROUNDING", "ABORTED"},
               "WAITING_FOR_EXAMPLE": {"WAITING_FOR_GROUNDING", "ABORTED"},
               "WAITING_FOR_GROUNDING": {"WAITING_FOR_GROUNDING", "WAITING_FOR_CLARIFICATION", "WAITING_FOR_REPHRASE", "READY_TO_COMMIT", "ABORTED"},
               "WAITING_FOR_CLARIFICATION": {"WAITING_FOR_GROUNDING", "WAITING_FOR_REPHRASE", "ABORTED"},
               "WAITING_FOR_REPHRASE": {"WAITING_FOR_GROUNDING", "ABORTED"},
               "READY_TO_COMMIT": {"COMMITTED", "ABORTED"}, "COMMITTED": set(), "ABORTED": set()}
SLOT_STATES = ["PENDING", "GROUNDED", "CLARIFYING", "REPLACED", "RESOLVED", "UNSUPPORTED", "ABANDONED", "CANCELLED"]
B = PR.BUDGET
EXEC_FAIL = ("NOT_FOUND", "VM_EXEC_ERROR", "TYPE_ERROR", "RESOLUTION_AMBIGUOUS", "MISSING_ARGUMENT", "EXEC_FAILED")


class ControllerError(Exception): pass
class _Budget(Exception): pass
class _Stop(Exception): pass
class _Abort(Exception): pass


class Demo:
    def __init__(self, index, name):
        self.index = index; self.name = name; self.state = "NEW"; self.states = ["NEW"]; self.slots = []; self.results = []; self.example = None; self.lesson_lines = []
        self.returned = False; self.end = None; self.end_detail = {}; self.learn = None; self.learn_detail = None; self.clarifications = 0; self.events = []; self.header_sent = False
        self.n = 0

    def go(self, st):
        if st not in TRANSITIONS[self.state]: raise ControllerError(f"illegal demonstration transition {self.state} -> {st}")
        self.state = st; self.states.append(st)

    def slot(self, text, source, required=True, replacement_for=None, lesson_index=None, family=None):
        self.n += 1; sid = f"demo{self.index + 1}-slot{self.n}"
        return {"slot_id": sid, "source": source, "status": "PENDING", "original_text": text, "text": text, "replacement_for": replacement_for, "grounded_plan": None,
                "clarification_count": 0, "rephrase_count": 0, "required": required, "lesson_index": lesson_index, "family": family or sid, "displaced": False,
                "history": [], "reference_choice": None}

    def family(self, fam): return [s for s in self.slots if s["family"] == fam]

    def family_state(self, fam):
        m = [s for s in self.family(fam) if s["status"] not in ("REPLACED", "ABANDONED")]
        if any(s["status"] == "CANCELLED" for s in self.family(fam)): return "CANCELLED"
        if m and all(s["status"] == "RESOLVED" for s in m): return "RESOLVED"
        return "UNRESOLVED"

    def record(self):
        return {"index": self.index, "state": self.state, "states": self.states, "slots": self.slots, "results": self.results, "example": self.example, "lesson_lines": self.lesson_lines,
                "returned": self.returned, "end": self.end, "end_detail": self.end_detail, "learn": self.learn, "learn_detail": self.learn_detail, "clarifications": self.clarifications,
                "events": self.events, "lines": [r["line"] for r in self.results]}


class ScriptedTeacherTx(EP.ScriptedTeacher):
    """registered lessons + FROZEN lookup responses for the registered structured questions (spec §44 of the parent)"""
    def __init__(self, script, item, family_steps):
        super().__init__(script); self.item = item; self.fs = family_steps

    def respond(self, messages, kind, payload):
        d = self.s["demos"][min(payload.get("demo", 0), len(self.s["demos"]) - 1)]
        j = payload.get("lesson_index"); P = {"provider": "scripted"}
        ex = "EXAMPLE: " + ", ".join(f"{k}={v}" for k, v in d["example"].items())
        if kind == "MISSING_EXAMPLE": return ex, P
        if kind in ("RESTATE_SLOT", "RESTATE_OBSCURED"):
            if j is None or j >= len(d["rephrase"]): return "CANCEL_SLOT", P
            return "STEP: " + d["rephrase"][j][0].upper() + d["rephrase"][j][1:], P
        if kind == "CLARIFY_REFERENCE":                                   # lookup: the earlier result the registered gold unit of this line reads
            try:
                st = self.fs(self.item["family"], d["example"]); unit = [st[k][1] for k in d["units"][j]]; bound = {s.get("bind") for s in unit}
                refs = [v for s in unit for v in re.findall(r'"var": "(r\d+)"', json.dumps(s)) if v not in bound]
                ch = next((r for r in refs if r in payload.get("offered", [])), None)
                return f"REFERENT: {ch or 'NONE'}", P
            except Exception: return "REFERENT: NONE", P
        return super().respond(messages, kind, payload)


def example_complete(ex, sig, pool):
    if not sig: return True, []                                         # parameterless skill: the empty binding is complete
    if not ex: return False, sorted(sig)
    allv = sum(pool.values(), []); miss = [p for p in sig if not ex.get(p) or ex.get(p) not in allv]
    return not miss, miss


def _desc(r, D):
    """natural description of a live result for a structured reference question: WHAT it is (its operation), and the step that produced it"""
    try: a = json.loads(r.text.split("=", 1)[1]) if "=" in r.text.split("{")[0] else json.loads(r.text[r.text.index("{"):])
    except Exception: a = {}
    op = a.get("op"); t = (a.get("type") or r.etype or "event").lower()
    cond = ", ".join(f"{k.lower()}={v}" for k, v in (a.get("where") or {}).items()) + (f", status {a['status'].lower()}" if a.get("status") else "")
    what = {"FIND": f"the {t}s found" + (f" ({cond})" if cond else ""), "SORT": f"{a.get('of')} sorted by {(a.get('by') or a.get('rel') or '').lower()}", "FILTER": f"{a.get('of')} filtered",
            "FIRST": f"the first element of {a.get('of')}", "FIND_LAST": f"the most recent {t}", "COUNT": f"the number of elements of {a.get('of')}", "GET": f"the {str(a.get('rel', '')).lower()} of {a.get('of')}",
            "SELECT": f"the {str(a.get('rel', '')).lower()} of every element of {a.get('of')}", "CHILD": f"the item {a.get('of')} is about", "PARENT": f"the event {a.get('of')} belongs to",
            "GROUP": f"{a.get('of')} grouped by {str(a.get('by', '')).lower()}", "REPORT": f"a report of {a.get('of')}", "CALL": f"the result of {a.get('procedure')}"}.get(op, r.kind.lower())
    n = f" ({r.n} element{'s' if r.n != 1 else ''})" if r.kind == "EVENT_LIST" and isinstance(r.n, int) else ""
    src = next((x for x in D.results if r.name in [s.get("bind") for s in x["executed_steps"]]), None)
    return what + n + (f", from the step \"{src['line']}\"" if src else "")


def run_target(S, it, teacher, pool, style, uid, log, active_desc):
    it = dict(it, _style=style); name = it["name"]; sig = it["sig"]; inj = it.get("injection") or {}; two = it["protocol"]["two_demo"]
    O = {"name": name, "demos": [], "teacher_turns": 0, "student_questions": [], "injections": [], "status": None, "classes": set(), "first_lesson_lines_ok": True, "protocol": "TTP"}
    msgs = [{"role": "system", "content": PR.system_prompt()}, {"role": "user", "content": PR.lesson_request(it, pool, active_desc, style)}]
    S.process({"text": f":target {name}(" + ", ".join(f"{p}:{t}" for p, t in sig.items()) + ")"}, f"{uid}:target", "t")

    def ask(kind, text, payload):
        if O["teacher_turns"] >= B["max_teacher_turns_per_target"]: raise _Budget("teacher turns per target")
        if text: msgs.append({"role": "user", "content": text}); O["student_questions"].append({"kind": kind, "text": text, "slot_id": payload.get("slot_id")})
        try: reply, prov = teacher.respond(msgs, kind, payload)
        except CL.BudgetStop as e: raise _Stop("BUDGET_STOP", str(e))
        except CL.ProviderFailure as e: raise _Stop("PROVIDER_FAILURE", str(e))
        msgs.append({"role": "assistant", "content": reply}); O["teacher_turns"] += 1; log.append({"kind": kind, "reply": reply, "provenance": prov, "slot_id": payload.get("slot_id")}); return reply

    def abort(D, why, detail=None):
        if S.teach is not None: S.restore_world(S.teach["snapshot"]); S.teach = None           # rollback: no partial mutation, zero evidence
        D.go("ABORTED"); D.end = "ABORTED:" + why; D.end_detail = dict(detail or {}, reason=why); O["demos"].append(D.record()); O["classes"].add("DEMO_ABORTED_" + why)

    try:
        reply = ask("LESSON", None, {"demo": 0}); restart_reply = None
        while len(O["demos"]) < B["max_demonstrations_per_target"]:
            d = len(O["demos"]); D = Demo(d, name); D.sig = sig; D.go("OPEN")
            R = PR.parse_reply(reply)
            if not R["steps"]:
                reply = ask("FORMAT", "Please reply only with an EXAMPLE line and STEP lines, as described (any values from VALUES may be used, including values already used).", {"demo": d}); R = PR.parse_reply(reply)
            if not R["steps"]:
                abort(D, "NO_STEPS"); reply = ask("NEW_DEMO", "Please give a complete demonstration (EXAMPLE line and STEP lines).", {"demo": d + 1}); continue
            ex = R["example"]; D.lesson_lines = list(R["steps"]); src = "SCRIPTED_TEACHER" if isinstance(teacher, EP.ScriptedTeacher) else "TEACHER"
            D.slots = [D.slot(t, src, lesson_index=k) for k, t in enumerate(R["steps"])]
            # ---- registered evaluator injections, with provenance (spec §29-§31) ----
            if inj and inj.get("demo") == d:
                k = inj["kind"]
                if k == "VAGUE_STEP":
                    j = min(1, len(D.slots) - 1); tgt = D.slots[j]; tgt.update(status="REPLACED", displaced=True)
                    v = D.slot(inj["text"], "EVALUATOR_INJECTION", required=False, replacement_for=tgt["slot_id"]); v["family"] = v["slot_id"]
                    D.slots.insert(j, v); O["injections"].append({"kind": k, "demo": d, "replaced": tgt["text"], "displaced_slot": tgt["slot_id"], "line": inj["text"]})
                elif k in EP.DETECTABLE:
                    j = 0 if k == "PREMATURE_RETURN" else min(1, len(D.slots)); s = D.slot(EP.INJ_TEXT[k], "EVALUATOR_INJECTION", required=False)
                    D.slots.insert(j, s); O["injections"].append({"kind": k, "demo": d, "line": EP.INJ_TEXT[k], "at": j})
                elif k in EP.LEGAL or k == "RELATION_SWAP":
                    before = [s["text"] for s in D.slots]
                    after, hit = (EP._inject_legal(before, k) if k in EP.LEGAL else EP._inject_relation_swap(before, pool.get("people", [])))
                    for s, t in zip(D.slots, after):
                        if t != s["text"]: s.update(text=t, source="EVALUATOR_INJECTION")
                    O["injections"].append({"kind": k, "demo": d, "applied": hit, "before": before, "after": after})
                elif k == "MISSING_EXAMPLE":
                    O["injections"].append({"kind": k, "demo": d, "applied": ex is not None, "removed_example": ex}); ex = None
            # ---- EXAMPLE-before-execution (spec §27-§28) ----
            ok, miss = example_complete(ex, sig, pool)
            if not ok:
                D.go("WAITING_FOR_EXAMPLE"); O["classes"].add("MISSING_EXAMPLE_DETECTED"); D.events.append({"event": "MISSING_EXAMPLE", "missing": miss})
                for _ in range(B["max_example_requests_per_demonstration"]):
                    q = (f"Demonstration {d + 1} has no complete EXAMPLE line (values needed for: {', '.join(sig) if sig else 'none'}; only values from VALUES). No step has been run. "
                         "Reply with one line: EXAMPLE: " + ", ".join(f"{p}=<value>" for p in sig))
                    R2 = PR.parse_reply(ask("MISSING_EXAMPLE", q, {"demo": d}))
                    if R2["example"]: ex = dict(ex or {}, **R2["example"])
                    ok, miss = example_complete(ex, sig, pool)
                    if ok: break
                if not ok:
                    abort(D, "EXAMPLE_INCOMPLETE", {"missing": miss})
                    if len(O["demos"]) >= B["max_demonstrations_per_target"]: break
                    reply = ask("NEW_DEMO", "Please give a complete demonstration: an EXAMPLE line with a value for every input, then STEP lines.", {"demo": d + 1}); continue
            D.example = ex; hint = bool(it["protocol"]["hint"])
            prev = sum(1 for x in O["demos"] if x.get("state") == "COMMITTED")      # amendment 003: COMMITTED evidence, not the demonstration index
            multi = two or prev > 0
            hdr = (":example" if multi else ":teach") + f" {name}" + ("(" + ", ".join(f"{p}={ex[p]}" for p in sig) + ")" if hint and sig else "")
            S.process({"text": hdr}, f"{uid}:d{d}:hdr", "t"); D.header_sent = True; D.go("WAITING_FOR_GROUNDING")
            new_demo = None
            try:
                new_demo = _run_slots(S, D, O, ask, uid, it, pool)
            except _Abort as a:
                abort(D, a.args[0], a.args[1] if len(a.args) > 1 else None)
                if len(O["demos"]) >= B["max_demonstrations_per_target"]: break
                reply = ask("NEW_DEMO", f"I could not complete demonstration {d + 1} ({a.args[0].lower().replace('_', ' ')}); it was discarded and nothing was learned from it. "
                                        "Please give a complete new demonstration (EXAMPLE line and STEP lines).", {"demo": d + 1}); continue
            if new_demo is not None:                                  # the teacher answered a question with a whole new demonstration
                abort(D, "RESTARTED_BY_TEACHER")
                if len(O["demos"]) >= B["max_demonstrations_per_target"]: break
                reply = new_demo; continue
            # ---- completeness (spec §14) ----
            probs = completeness(S, D)
            if probs:
                O["classes"].add("DEMONSTRATION_INCOMPLETE"); abort(D, "INCOMPLETE", {"problems": probs})
                if len(O["demos"]) >= B["max_demonstrations_per_target"]: break
                reply = ask("NEW_DEMO", "That demonstration was incomplete (" + "; ".join(probs[:2]) + "); it was discarded. Please give a complete new demonstration (EXAMPLE line and STEP lines).",
                            {"demo": d + 1}); continue
            D.go("READY_TO_COMMIT")
            end = S.process({"text": ":endexample" if multi else ":endteach"}, f"{uid}:d{d}:end", "t"); D.end = end["status"]; D.go("COMMITTED")
            D.end_detail = {k: end.get(k) for k in ("insufficient",) if end.get(k)}; st = end["status"]
            if multi and st == "OK":
                if two and prev == 0: st = "NEED_MORE"                      # the registered two-demonstration protocol needs 2 COMMITTED demonstrations
                else:
                    lr = S.process({"text": f":learn {name}"}, f"{uid}:d{d}:learn", "t"); st = lr["status"]; D.learn = st
                    D.learn_detail = {k: lr.get(k) for k in ("examples_used", "examples_discarded_inconsistent", "insufficient", "conflict", "response")}
                    if st == "EVIDENCE_CONFLICT": O["classes"].add("EVIDENCE_CONFLICT_DETECTED")
                    if st == "LEARNER_ERROR": O["classes"].add("VERIFIER_CRASH")
            O["demos"].append(D.record())
            if st == "VERIFIED":
                acc = S.process({"text": f":accept {name}"}, f"{uid}:accept", "t"); O["status"] = "ACTIVE" if acc["status"] == "OK" else "ACCEPT_FAILED"; break
            if len(O["demos"]) >= B["max_demonstrations_per_target"]: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = f"demonstration budget exhausted (last: {st})"; break
            if st in ("REQUIRE_SECOND_DEMONSTRATION", "NEED_MORE"):
                q = ("I have one demonstration. " if st == "NEED_MORE" else f"I have {len(O['demos'])} demonstration(s) but cannot yet tell which values are inputs of {name}. ") + \
                    "Please give another complete demonstration with DIFFERENT example values (EXAMPLE line and STEP lines)."
                if st == "REQUIRE_SECOND_DEMONSTRATION": O["classes"].add("SECOND_DEMO_REQUESTED")
                if "EVIDENCE_VACUOUS" in json.dumps(D.end_detail or {}) + json.dumps(D.learn_detail or {}):
                    O["classes"].add("VACUITY_DETECTED")
                    q = (f"In your demonstration(s) of {name} a search found nothing (or could not tell the intended condition apart), so the demonstration does not show what {name} does. "
                         "Please give another complete demonstration with DIFFERENT example values (EXAMPLE line and STEP lines).")
            elif st in ("EVIDENCE_CONFLICT", "DEMONSTRATIONS_INCONSISTENT"):
                q = ("Your demonstrations do not follow the same steps, so I cannot tell which is right. Please give one more complete demonstration (EXAMPLE line and STEP lines); "
                     "example values may repeat values you already used."); O["classes"].add("INCONSISTENCY_DETECTED")
            else: q = f"I could not learn a consistent skill from that demonstration ({st}). Please give another complete demonstration (EXAMPLE line and STEP lines)."
            reply = ask("NEW_DEMO", q, {"demo": len(O["demos"])})
    except _Budget as b: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = f"budget: {b}"
    except _Stop as s: O["status"] = s.args[0]; O["fail"] = s.args[1]
    except CL.BudgetStop as e: O["status"] = "BUDGET_STOP"; O["fail"] = "grounder: " + str(e)
    except CL.ProviderFailure as e: O["status"] = "PROVIDER_FAILURE"; O["fail"] = "grounder: " + str(e)
    if S.teach is not None:                                           # an open demonstration at an episode end: rolled back, zero evidence
        S.restore_world(S.teach["snapshot"]); S.teach = None; O["aborted_open_demonstration"] = True
        if "D" in dir() and D.state not in ("COMMITTED", "ABORTED"):
            try: D.go("ABORTED")
            except ControllerError: pass
            D.end = "ABORTED:EPISODE_END"; O["demos"].append(D.record())
    if O["status"] is None: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = O.get("fail") or "demonstration budget exhausted"
    O["classes"] = sorted(O["classes"]); O["transcript"] = msgs; return O


def completeness(S, D):
    """spec §14: the demonstration may commit only if every condition holds"""
    p = []
    if D.sig and not D.example: p.append("no EXAMPLE binding")
    for fam in dict.fromkeys(s["family"] for s in D.slots):
        root = next(s for s in D.slots if s["slot_id"] == fam)
        if not root["required"]: continue
        if D.family_state(fam) not in ("RESOLVED", "CANCELLED"): p.append(f"required step {root['slot_id']} unresolved")
        if root["displaced"] and D.family_state(fam) != "RESOLVED": p.append(f"displaced step {root['slot_id']} not restored")
    if any(s["status"] in ("PENDING", "CLARIFYING") for s in D.slots): p.append("a step is still pending")
    N = (S.teach or {}).get("nl") or {}
    if N.get("pending"): p.append("pending clarification")
    if not D.returned: p.append("no RETURN")
    if not (S.teach or {}).get("steps"): p.append("empty trace")
    return p


def _later_required(D, i):
    for s in D.slots[i + 1:]:
        if s["required"] and s["status"] in ("PENDING", "REPLACED") and D.family_state(s["family"]) not in ("RESOLVED", "CANCELLED"): return True
    return False


def _question(kind, D, s, r, extra=""):
    k = (s["lesson_index"] or 0) + 1; line = s["text"]
    if kind == "RESTATE_OBSCURED":
        return (f"Step {k} of demonstration {D.index + 1} was intentionally obscured by the evaluator (the wording I received was not yours). "
                f"RESTATE step {k}: reply only with the STEP line(s) for the action that belongs at step {k} of your demonstration.")
    why = {"PREMATURE_TERMINAL_ACTION": f"it would return the result, but the steps after step {k} are still to come",
           "UNREQUESTED_RETURN": "it would return the result although the step does not ask for it",
           "UNNAMED_CALL": "it would call a saved skill that the step does not name (name the skill and give its inputs: \"Call <skill> with <input> <value>\")",
           "RELATION_LOCATION_ERROR": "of where a relation is stored: " + extra, "MISSING_ARGUMENT": "a saved skill it calls is missing an input: " + extra}.get(r.get("clarify_kind")) or EP.reason_text(r)
    return f"I could not carry out step {k} (\"{line}\") because {why}. RESTATE step {k}: reply only with replacement STEP line(s) for step {k}, or CANCEL_SLOT."


def _run_slots(S, D, O, ask, uid, it, pool):
    """ground + execute pending slots in order; per-slot recovery. -> None (all processed) or a reply text holding a NEW demonstration.
    Raises _Abort(reason, detail) on SLOT_RECOVERY_FAIL."""
    remaining_asks = 0
    while True:
        i = next((k for k, s in enumerate(D.slots) if s["status"] == "PENDING"), None)
        if i is None:
            lost = [x["slot_id"] for x in D.slots if x["required"] and x["family"] == x["slot_id"] and D.family_state(x["family"]) not in ("RESOLVED", "CANCELLED")]
            if lost: O["classes"].add("MISSING_SLOT_DETECTED"); raise _Abort("MISSING_SLOT", {"slots": lost})      # spec §31: a skipped slot blocks the commit
            if D.returned: return None
            remaining_asks += 1
            reply = ask("REMAINING", "Done. Send the next STEP line(s)." if it.get("_style") == "C" else "Done, but the demonstration has not returned a result yet. Send the remaining STEP line(s).",
                        {"demo": D.index, "from": len(D.lesson_lines)})
            R = PR.parse_reply(reply)
            if R["example"] and len(R["steps"]) >= 2: return reply
            if not R["steps"]: raise _Abort("TEACHER_GAVE_NO_REMAINING_STEPS")
            base = len(D.lesson_lines); D.lesson_lines += R["steps"]
            D.slots += [D.slot(t, D.slots[0]["source"] if D.slots else "TEACHER", lesson_index=base + k) for k, t in enumerate(R["steps"])]
            continue
        s = D.slots[i]; fam_root = next(x for x in D.slots if x["slot_id"] == s["family"])
        turn = {"kind": "NL", "text": s["text"], "terminal_allowed": not _later_required(D, i), "slot_id": s["slot_id"], "source": s["source"]}
        if s["reference_choice"]: turn["reference_choice"] = s["reference_choice"]
        r = S.process(turn, f"{uid}:d{D.index}:{s['slot_id']}:{len(D.results)}", "t"); rec = EP._brief(r, s["text"]); rec.update(slot_id=s["slot_id"], source=s["source"],
            terminal_allowed=turn["terminal_allowed"], reference_choice=s["reference_choice"], blocked_plan=r.get("blocked_plan"), structured=r.get("structured"),
            attempts=((r.get("grounding") or {}).get("attempts"))); D.results.append(rec)
        s["history"].append({"status": r["status"], "clarify_kind": r.get("clarify_kind"), "reason": (r.get("reason") or "")[:200]})
        if r["status"] == "OK":
            s.update(status="RESOLVED", grounded_plan=r.get("executed_steps")); D.go("WAITING_FOR_GROUNDING")
            if any(x["op"] == "RETURN" for x in r.get("executed_steps") or []):
                D.returned = True
                for x in D.slots:
                    if x["status"] == "PENDING" and not x["required"]: x["status"] = "ABANDONED"
                if _later_required(D, i): raise _Abort("PREMATURE_TERMINATION", {"slot": s["slot_id"]})   # guard: never execute past a terminal action
            continue
        if D.index == 0: O["first_lesson_lines_ok"] = False
        # ---- evaluator-injected slots: never attributed to the teacher (spec §29-§30) ----
        if s["source"] == "EVALUATOR_INJECTION" and not s["required"]:
            s["status"] = "UNSUPPORTED" if r["status"] == "UNSUPPORTED" else "ABANDONED"
            if s["replacement_for"]:                                        # the obscured slot must be restored by the teacher
                disp = next(x for x in D.slots if x["slot_id"] == s["replacement_for"])
                _restate(S, D, O, ask, disp, i + 1, "RESTATE_OBSCURED", r)
            continue
        # ---- structured reference clarification (spec §22-§23) ----
        info = r.get("clarify_info") or {}
        if r["status"] == "CLARIFY" and r.get("clarify_kind") == "REFERENCE" and info.get("candidates"):
            fam_root["clarification_count"] += 1; D.clarifications += 1; s["status"] = "CLARIFYING"; D.go("WAITING_FOR_CLARIFICATION")
            if fam_root["clarification_count"] > B["max_clarification_exchanges_per_slot"]: raise _Abort("SLOT_RECOVERY_FAIL", {"slot": s["slot_id"], "error": "REFERENCE"})
            N = (S.teach or {}).get("nl") or {}; live = {x.name: x for x in N.get("results", [])}
            offered = [c["name"] for c in info["candidates"]]
            k = (s["lesson_index"] or 0) + 1
            q = (f"For step {k} (\"{s['text']}\") more than one earlier result fits:\n" + "\n".join(f"  {n}: {_desc(live[n], D) if n in live else n}" for n in offered) +
                 "\nReply with one line: REFERENT: <id>")
            rep = ask("CLARIFY_REFERENCE", q, {"demo": D.index, "slot_id": s["slot_id"], "lesson_index": s["lesson_index"], "offered": offered})
            R = PR.parse_reply(rep); O["classes"].add("REFERENCE_CLARIFICATION_REQUIRED")
            D.events.append({"event": "CLARIFY_REFERENCE", "slot": s["slot_id"], "offered": offered, "answer": R["referent"]})
            if R["referent"] in offered: s.update(status="PENDING", reference_choice={"chosen": R["referent"], "offered": offered}); D.go("WAITING_FOR_GROUNDING"); continue
            if R["example"] and len(R["steps"]) >= 2: return rep
            if R["steps"]: _replace(D, s, fam_root, R["steps"], i); D.go("WAITING_FOR_REPHRASE"); D.go("WAITING_FOR_GROUNDING"); continue
            s["status"] = "PENDING"; D.go("WAITING_FOR_GROUNDING"); continue          # unusable answer: same slot, budget already charged
        # ---- every other failure: restate this slot (spec §30, §36-§37) ----
        extra = ""
        for f in r.get("structured") or []:
            if f.get("error") == "ILLEGAL_RELATION_LOCATION": extra = f"for {f['object_type'].lower()}s the {f['relation']} relation is stored on the parent event ({f['legal_path']})"
            if f.get("error") == "CALL_ARGUMENT": extra = f"{f['procedure']} needs {f['parameter']} ({f['type'].lower()})"
        rep = _restate(S, D, O, ask, s, i, "RESTATE_SLOT", r, extra)
        if rep is not None: return rep


def _replace(D, s, root, steps, i):
    """teacher replacement lines for a slot: same semantic family (identity preserved), inserted in place; earlier failed members REPLACED"""
    for x in D.family(root["slot_id"]):
        if x["status"] != "RESOLVED": x["status"] = "REPLACED"
    new = [D.slot(t, "TEACHER" if s["source"] != "SCRIPTED_TEACHER" else "SCRIPTED_TEACHER", replacement_for=root["slot_id"], lesson_index=root["lesson_index"], family=root["slot_id"]) for t in steps]
    for k, n in enumerate(new): D.slots.insert(i + 1 + k, n)
    if not root["displaced"] and root["status"] == "RESOLVED": pass


def _restate(S, D, O, ask, s, i, kind, r, extra=""):
    root = next(x for x in D.slots if x["slot_id"] == s["family"])
    root["rephrase_count"] += 1; D.clarifications += 1
    if s["status"] not in ("REPLACED",): s["status"] = "CLARIFYING"
    D.go("WAITING_FOR_REPHRASE")
    if root["rephrase_count"] > B["max_rephrase_exchanges_per_slot"]: raise _Abort("SLOT_RECOVERY_FAIL", {"slot": s["slot_id"], "error": r.get("clarify_kind") or r["status"], "kind": kind})
    q = _question(kind, D, s, r, extra)
    rep = ask(kind, q, {"demo": D.index, "slot_id": s["slot_id"], "lesson_index": s["lesson_index"], "line": s["text"]})
    R = PR.parse_reply(rep); D.events.append({"event": kind, "slot": s["slot_id"], "error": r.get("clarify_kind") or r["status"], "reply_steps": len(R["steps"]), "cancel": R["cancel"]})
    if R["example"] and len(R["steps"]) >= 2: return rep
    if R["cancel"] and not root["displaced"] and root["source"] != "EVALUATOR_INJECTION":
        for x in D.family(root["slot_id"]):
            if x["status"] != "RESOLVED": x["status"] = "CANCELLED"
        D.go("WAITING_FOR_GROUNDING"); return None
    if R["steps"]:
        if root["displaced"]: O["classes"].add("INJECTED_STEP_RESTATED")
        _replace(D, s, root, R["steps"], i if s is not root or not root["displaced"] else D.slots.index(s))
        D.go("WAITING_FOR_GROUNDING"); return None
    if s["status"] == "CLARIFYING": s["status"] = "PENDING"                        # nothing usable: the same slot is retried (budget already charged)
    D.go("WAITING_FOR_GROUNDING"); return None
