"""Skill-acquisition episode controller (spec §18-§22, §42-§46). Runs the teacher <-> student dialogue for one registered target skill:
teacher lesson -> each STEP grounded by the frozen student (NLSystem) -> on a student problem, a templated student QUESTION goes to the
teacher -> teacher reply (replacement STEP lines / ANSWER / new demonstration) -> ... -> :endteach / :endexample / :learn by the frozen
learner -> the EVALUATOR issues :accept only if VERIFIED. The teacher never touches the student's stores: its text reaches the VM only
through the student's grounding + deterministic checks. Budgets (spec §19): 8 teacher turns per demonstration, 2 clarification exchanges
per instruction, 3 demonstrations per target. Injections (registered, spec §42, §44, §45) modify the TEACHER'S text before the student
reads it; the teacher's own messages are recorded unmodified."""
import re, json, copy, time
import protocol as PR, client as CL

INJ_TEXT = {"UNSUPPORTED_PRIMITIVE": "Also send the result to Kevin by Slack.", "PREMATURE_RETURN": "Return it.", "WRONG_ARGUMENT_TYPE": "Set their status to Paris.",
            "INVALID_VALUE": "Mark each of them as archived."}
DETECTABLE = set(INJ_TEXT); LEGAL = {"DROPPED_FILTER", "CONSTANT_SWAP"}


class LLMTeacher:
    def __init__(self, backend="MODAL", model="openai/gpt-oss-120b", gen=None): self.backend, self.model, self.gen = backend, model, gen or {}
    def respond(self, messages, kind, payload):
        r = CL.chat(messages, backend=self.backend, model=self.model, gen=self.gen, meta={"kind": kind}); return r["text"], r["provenance"]


class ScriptedTeacher:
    """deterministic registered lessons + lookup responses (spec §30): no adaptation beyond the registered lookup"""
    def __init__(self, script): self.s = script
    def respond(self, messages, kind, payload):
        d = self.s["demos"][min(payload.get("demo", 0), len(self.s["demos"]) - 1)]
        ex = "EXAMPLE: " + ", ".join(f"{k}={v}" for k, v in d["example"].items()) + "\n" if d["example"] else ""
        if kind in ("LESSON", "NEW_DEMO", "REMAINING"): return ex + "\n".join("STEP: " + l for l in d["lines"][payload.get("from", 0):]), {"provider": "scripted"}
        if kind == "REPHRASE":
            line = payload.get("line"); i = d["lines"].index(line) if line in d["lines"] else None      # only lines this teacher wrote
            if i is None: return "STEP: SKIP", {"provider": "scripted"}
            return "STEP: " + d["rephrase"][i][0].upper() + d["rephrase"][i][1:], {"provider": "scripted"}
        if kind == "ANSWER": return "ANSWER: " + self.s["answer"], {"provider": "scripted"}
        return ex + "\n".join("STEP: " + l for l in d["lines"]), {"provider": "scripted"}


def _inject_legal(lines, kind):
    """text-level legal-but-wrong perturbations of the teacher's own lines (applied to ONE demonstration)"""
    out = []; hit = False
    for l in lines:
        n = l
        if kind == "DROPPED_FILTER":
            n = re.sub(r"(?i)\s*(that|which) (are|is) (still )?open", "", n); n = re.sub(r"(?i)\s*(that|which) (are not|aren't|haven't been|have not been) closed( yet)?", "", n)
            n = re.sub(r"(?i)\b(still[- ])?open\s+", "", n); n = re.sub(r"(?i)\s+(that are )?still open\b", "", n)
        if kind == "CONSTANT_SWAP": n = re.sub(r"(?i)\b(still[- ])?open\b", "closed", n)
        hit |= n != l; out.append(n)
    return out, hit


def reason_text(r):
    k = r.get("status"); why = str(r.get("reason") or "")
    if k == "UNSUPPORTED": return "it needs an action I do not have"
    if "ambiguous" in why: return "I do not know which earlier result it refers to"
    if "not named" in why or "event search" in why: return "it does not say which kind of event to look for"
    if "RETURN asks" in why: return "it asks for a result that does not exist yet"
    if "multi-clause" in why or "segmentation" in why: return "I could not split it into separate actions"
    if "values not used" in why or "coverage" in why or "mentions" in why: return "I could not use all of the values it mentions"
    if k == "NOT_FOUND": return "there was nothing to act on (an earlier step found nothing for these example values); nothing was changed. You may give a new demonstration with other example values (EXAMPLE line + STEP lines)"
    if k not in ("OK", "CLARIFY"): return f"it failed when executed ({k}); nothing was changed"
    return "I am not sure what it means"


def run_target(S, it, teacher, pool, style, uid, log, active_desc):
    """-> outcome dict. S = NLSystem; it = curriculum item; teacher = LLMTeacher | ScriptedTeacher"""
    name = it["name"]; sig = it["sig"]; inj = it.get("injection") or {}; B = PR.BUDGET; O = {"name": name, "demos": [], "teacher_turns": 0, "student_questions": [], "injections": [],
         "status": None, "classes": set(), "first_lesson_lines_ok": True}
    msgs = [{"role": "system", "content": PR.system_prompt()}, {"role": "user", "content": PR.lesson_request(it, pool, active_desc, style)}]
    S.process({"text": f":target {name}(" + ", ".join(f"{p}:{t}" for p, t in sig.items()) + ")"}, f"{uid}:target", "t")
    n = [0]
    def ask(kind, text, payload, demo_state):
        if demo_state["turns"] >= B["max_teacher_turns_per_demonstration"]: raise _Budget("teacher turns per demonstration")
        if text: msgs.append({"role": "user", "content": text}); O["student_questions"].append({"kind": kind, "text": text})
        try: reply, prov = teacher.respond(msgs, kind, payload)
        except CL.BudgetStop as e: raise _Stop("BUDGET_STOP", str(e))
        except CL.ProviderFailure as e: raise _Stop("PROVIDER_FAILURE", str(e))
        msgs.append({"role": "assistant", "content": reply}); O["teacher_turns"] += 1; demo_state["turns"] += 1; log.append({"kind": kind, "reply": reply, "provenance": prov}); return reply
    ex_used = 0
    try:
        demo_state = {"turns": 0}; reply = ask("LESSON", None, {"demo": 0}, demo_state)
        while len(O["demos"]) < B["max_demonstrations_per_target"]:
            d = len(O["demos"]); D = {"index": d, "lines": [], "results": [], "example": None, "hinted": False, "returned": False, "clarifications": 0}
            ex, steps, _ = PR.parse_lesson(reply)
            if not steps:
                reply = ask("FORMAT", "Please reply only with an EXAMPLE line and STEP lines, as described.", {"demo": d}, demo_state); ex, steps, _ = PR.parse_lesson(reply)
            # ---- registered injections (spec §42, §44, §45) ----
            if inj and inj.get("demo") == d:
                k = inj["kind"]
                if k == "VAGUE_STEP" and steps: j = min(1, len(steps) - 1); O["injections"].append({"kind": k, "demo": d, "replaced": steps[j]}); steps[j] = inj["text"]
                elif k in DETECTABLE: j = 0 if k == "PREMATURE_RETURN" else min(1, len(steps)); steps.insert(j, INJ_TEXT[k]); O["injections"].append({"kind": k, "demo": d, "line": INJ_TEXT[k], "at": j})
                elif k in LEGAL:
                    steps2, hit = _inject_legal(steps, k); O["injections"].append({"kind": k, "demo": d, "applied": hit, "before": steps, "after": steps2}); steps = steps2
            D["example"] = ex
            hint_ok = bool(it["protocol"]["hint"]) and ex is not None and set(sig) <= set(ex) and all(ex[p] in sum(pool.values(), []) for p in sig)
            two = it["protocol"]["two_demo"]; D["hinted"] = hint_ok
            hdr = (":example" if (two or d > 0) else ":teach") + f" {name}" + ("(" + ", ".join(f"{p}={ex[p]}" for p in sig) + ")" if hint_ok and sig else "")
            S.process({"text": hdr}, f"{uid}:d{d}:hdr", "t"); queue = [(k, x) for k, x in enumerate(steps)]; li = 0; clar_per = {}; restart = None; nid = [len(steps)]
            while queue:
                iid, line = queue.pop(0); line = line.strip().strip("`*")
                if re.fullmatch(r"(?i)skip\.?", line): continue
                D["lines"].append(line); r = S.process({"kind": "NL", "text": line}, f"{uid}:d{d}:l{li}", "t"); D["results"].append(_brief(r, line)); li += 1
                if r["status"] == "OK":
                    if any(s["op"] == "RETURN" for s in r.get("executed_steps") or []): D["returned"] = True; queue = []
                    elif not queue and not D["returned"]:
                        reply = ask("REMAINING", "Done. Send the next STEP line(s)." if style == "C" else "Done, but the demonstration has not returned a result yet. Send the remaining STEP line(s).", {"demo": d, "from": li}, demo_state)
                        _, more, _ = PR.parse_lesson(reply); queue = [(nid[0] + k, x) for k, x in enumerate(more)]; nid[0] += len(more)
                    continue
                if d == 0: O["first_lesson_lines_ok"] = False
                key = iid; clar_per[key] = clar_per.get(key, 0) + 1            # replacements inherit the id of the instruction they replace
                if clar_per[key] > B["max_clarification_exchanges_per_instruction"]: raise _Budget("clarification exchanges for one instruction")
                D["clarifications"] += 1
                if r["status"] == "CLARIFY" and (r.get("reason") or "").startswith("reference for"):
                    reply = ask("ANSWER", f"In the step \"{line}\" I do not know which earlier result you mean. Reply with one line: ANSWER: <which result>.", {"demo": d, "line_index": li - 1}, demo_state)
                    _, more, ans = PR.parse_lesson(reply)
                    if ans:
                        r2 = S.process({"kind": "NL", "text": ans[0]}, f"{uid}:d{d}:a{li}", "t"); D["lines"].append("ANSWER: " + ans[0]); D["results"].append(_brief(r2, ans[0]))
                        if r2["status"] == "OK":
                            if any(s["op"] == "RETURN" for s in r2.get("executed_steps") or []): D["returned"] = True; queue = []
                            O["classes"].add("CLARIFICATION_SUCCESS"); continue
                        queue = [(iid, line)] + queue; continue
                    queue = [(iid, x) for x in more] + queue; continue
                q = f"I could not carry out the step \"{line}\" because {reason_text(r)}. Please rephrase it: reply only with replacement STEP line(s), or STEP: SKIP if it is not needed."
                reply = ask("REPHRASE", q, {"demo": d, "line_index": li - 1, "line": line}, demo_state); ex2, more, _ = PR.parse_lesson(reply)
                if ex2 is not None and len(more) >= 2: restart = reply; break      # the teacher answered with a NEW demonstration -> restart it
                queue = [(iid, x) for x in (more or [])] + queue
                if more and not re.fullmatch(r"(?i)skip\.?", more[0].strip()): O["classes"].add("REPHRASE_SUCCESS_CANDIDATE")
            if restart is not None:                                  # abandoned demonstration: closed WITHOUT learning, sandbox restored
                S.restore_world(S.teach["snapshot"]); S.teach = None; D["end"] = "RESTARTED_BY_TEACHER"; O["demos"].append(D)
                if len(O["demos"]) >= B["max_demonstrations_per_target"]: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = "demonstration budget exhausted (restart)"; break
                reply = restart; demo_state = {"turns": 0}; continue
            end = S.process({"text": ":endexample" if (two or d > 0) else ":endteach"}, f"{uid}:d{d}:end", "t"); D["end"] = end["status"]; O["demos"].append(D)
            st = end["status"]
            if (two or d > 0) and st == "OK":
                if two and d == 0: st = "NEED_MORE"                      # registered two-demonstration protocol
                else: lr = S.process({"text": f":learn {name}"}, f"{uid}:d{d}:learn", "t"); st = lr["status"]; D["learn"] = st; D["learn_detail"] = {k: lr.get(k) for k in ("examples_used", "examples_discarded_inconsistent", "insufficient")}
            if st == "VERIFIED":
                acc = S.process({"text": f":accept {name}"}, f"{uid}:accept", "t"); O["status"] = "ACTIVE" if acc["status"] == "OK" else "ACCEPT_FAILED"; break
            if len(O["demos"]) >= B["max_demonstrations_per_target"]: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = f"demonstration budget exhausted (last: {st})"; break
            demo_state = {"turns": 0}
            if st in ("REQUIRE_SECOND_DEMONSTRATION", "NEED_MORE"):
                q = ("I have one demonstration. " if st == "NEED_MORE" else f"I have {len(O['demos'])} demonstration(s) but cannot yet tell which values are inputs of {name}. ") + \
                    "Please give another complete demonstration with DIFFERENT example values (EXAMPLE line and STEP lines)."
                if st == "REQUIRE_SECOND_DEMONSTRATION": O["classes"].add("SECOND_DEMO_REQUESTED")
            elif st == "DEMONSTRATIONS_INCONSISTENT": q = "Your demonstrations do not follow the same steps, so I cannot tell which is right. Please give one more complete demonstration (EXAMPLE line and STEP lines)."; O["classes"].add("INCONSISTENCY_DETECTED")
            elif st == "TRACE_FAILED" or not D["returned"]: q = "That demonstration did not finish by returning the result. Please give a complete demonstration again (EXAMPLE line and STEP lines)."
            else: q = f"I could not learn a consistent skill from that demonstration ({st}). Please give another complete demonstration (EXAMPLE line and STEP lines)."
            reply = ask("NEW_DEMO", q, {"demo": len(O["demos"])}, demo_state)
    except _Budget as b: O["status"] = "TEACHER_EPISODE_FAIL"; O["fail"] = f"budget: {b}"
    except _Stop as s: O["status"] = s.args[0]; O["fail"] = s.args[1]
    if S.teach is not None:                                   # aborted demonstration: close it WITHOUT learning; restore the sandbox
        S.restore_world(S.teach["snapshot"]); S.teach = None; O["aborted_open_demonstration"] = True
    if O["status"] is None: O["status"] = "TEACHER_EPISODE_FAIL"
    O["classes"] = sorted(O["classes"]); O["transcript"] = msgs; return O


class _Budget(Exception): pass
class _Stop(Exception): pass


def _brief(r, line):
    return {"line": line, "status": r["status"], "reason": r.get("reason"), "executed_steps": r.get("executed_steps") or [], "grounding_raw": ((r.get("grounding") or {}).get("raw_text") or "")[:400],
            "llm_calls": (r.get("grounding") or {}).get("llm_calls"), "seconds": r.get("seconds")}
