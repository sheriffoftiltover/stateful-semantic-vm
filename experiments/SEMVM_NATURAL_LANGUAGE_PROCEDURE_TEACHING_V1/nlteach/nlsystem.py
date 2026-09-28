"""NL_TEACH session = the FROZEN parent procedure-learning System (procedure/system.py, unchanged) + a natural-language teaching ingress.
Only the teaching ingress is new (spec §6). Added behaviour, identical in all three evaluation modes (GOLD_TRACE / FORMAL_TEACH / NL_TEACH):
  * NL teaching utterances (inside :teach / :example / :revise) -> frontend.ground -> validated actions -> executed as ONE transaction per
    utterance (parent executor + core world postconditions); only successfully executed steps enter the teaching trace (spec §16-§17, §42)
  * CLARIFY keeps the instruction pending; the next utterance is its answer (appended) or a restatement ("I mean: ...") (spec §18)
  * correction markers ("No, ...") undo the previous grounded instruction of the demonstration and ground the rest instead; ":undo" undoes
    it only (spec §50). Undone proposals remain provenance only.
  * teaching sandbox: at :endteach / :endexample / :endrevise the world is restored to the demonstration's start snapshot (spec §43)
  * UNHINTED one-shot teaching whose trace contains a PERSON / TIME / PLACE / TOPIC literal -> REQUIRE_SECOND_DEMONSTRATION; the trace is kept
    as example 1 (continue with :example name ... :endexample, then :learn name) (spec §21)
  * procedure abstraction is the frozen DETERMINISTIC anti-unifier only (use_llm=False: the LLM is not a procedure proposer in this V1, §1)
GOLD_TRACE mode executes the scenario's gold actions for each utterance instead of grounding it (evaluation control only)."""
import os, sys, re, json, copy, time, sqlite3, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import system as SY, executor as X, lang as L, pipeline as PL
import frontend as F, nllm
CORR = [m.lower() for m in F.LANG["correction_markers"]]; RESTATE = F.LANG["restatement_marker"].lower()
ENTITY = ("PERSON", "TIME", "PLACE", "TOPIC")


def steps_to_actions(steps):
    """inverse of frontend.to_steps (for context rendering when steps did not come from the frontend)"""
    out = []
    for s in steps:
        op = s["op"]; cv = lambda e: e.get("const") if "const" in e else e.get("var")
        if op == "FIND":
            a = {"op": "FIND", "type": cv(s["type"])}; w = {(r if sc == "SELF" else f"{sc}.{r}"): cv(x) for sc, r, x in s["where"]}
            if w: a["where"] = w
            if s.get("status"): a["status"] = cv(s["status"])
        elif op == "FIND_LAST": a = {"op": op, "type": cv(s["type"])}
        elif op in ("FIRST", "COUNT"): a = {"op": op, "of": cv(s["list"])}
        elif op in ("CHILD", "PARENT"): a = {"op": op, "of": cv(s["obj"])}
        elif op == "GET": a = {"op": op, "of": cv(s["obj"]), "rel": s["rel"]}
        elif op == "SELECT": a = {"op": op, "of": cv(s["list"]), "rel": s["rel"]}
        elif op in ("GROUP", "SORT"): a = {"op": op, "of": cv(s["list"]), "by": s["rel"]}
        elif op == "REPORT": a = {"op": op, "of": cv(s["groups"]), "rel": s["rel"]}
        elif op == "FILTER": a = {"op": op, "of": cv(s["list"])}; a.update({"status": cv(s["value"])} if s["rel"] == "STATUS" else {"where": {s["rel"]: cv(s["value"])}})
        elif op == "FOR":
            b = steps_to_actions(s["body"])[0]; b.pop("target", None); b["each"] = cv(s["list"]); a = b
        elif op in ("UPDATE", "SET_STATUS", "DELETE", "RETRACT"):
            a = {"op": op, "target": cv(s["obj"])}
            if op == "UPDATE": a.update(rel=s["rel"], value=cv(s["value"]))
            if op == "SET_STATUS": a["value"] = cv(s["value"])
            if op == "RETRACT": a["rel"] = s["rel"]
        elif op == "CALL": a = {"op": op, "procedure": s["procedure"], "args": {k: cv(v) for k, v in s["args"].items()}}
        elif op == "RETURN": a = {"op": op, "value": cv(s["value"])}
        else: a = {"op": op}
        if s.get("bind"): a["bind"] = s["bind"]
        out.append(a)
    return out


def canon_steps(steps):
    """harmless canonical ordering (spec §25): FIND constraints SELF < PARENT < CHILD then lang.RELS order"""
    sco = {"SELF": 0, "PARENT": 1, "CHILD": 2}; out = copy.deepcopy(steps)
    for s in out:
        if s["op"] == "FIND": s["where"] = sorted(s["where"], key=lambda x: (sco[x[0]], L.RELS.index(x[1])))
        if "status" in s and s["op"] == "FIND" and not s.get("status"): s["status"] = None
    return out


class NLSystem(SY.System):
    def __init__(self, world_db, proc_db, learn_dir, mode="NL_TEACH", grounder=None, pipeline_mode="GOLD_IR", binder=None, probe=False):
        super().__init__(world_db, proc_db, learn_dir, mode="DISCOVERED", use_llm=False, pipeline_mode=pipeline_mode, binder=binder)
        self.nl_mode = mode; self.probe = probe; self.grounder = grounder or (F.Grounder() if (mode == "NL_TEACH" or probe) else None)
        os.makedirs(os.path.join(learn_dir, "teaching_traces"), exist_ok=True)

    # ---------------------------------------------------------------- world snapshot / restore ----------------------------------------------
    def restore_world(self, path):
        src = sqlite3.connect(path); src.backup(self.world.db); src.close()

    # ---------------------------------------------------------------- turns ----------------------------------------------------------------
    def _process(self, turn, text, uid, ts):
        cmd = text.split(" ", 1)[0] if text else ""
        if self.teach is not None and (turn.get("kind") == "NL" or turn.get("gold_outcome") is not None) and not text.startswith(":") and not SY.is_step(text):
            return self.nl_turn(turn, text, uid, ts)
        if self.teach is not None and text == ":undo": return self.undo()
        if cmd in (":endteach", ":endexample", ":endrevise") and self.teach is not None:
            T = self.teach; snap = T["snapshot"]; self._flush_teaching_trace(T, uid)
            if cmd == ":endteach" and not T["declared"] and not T["failed"] and T["steps"] and T["steps"][-1]["op"] == "RETURN" and self._has_entity_literal(T["steps"]):
                self.teach = None
                tr = {"steps": T["steps"], "declared": None, "snapshot": snap, "result": T["result"], "post_state": self.world.canonical_state(), "interaction_id": T["interaction_id"]}
                self.examples[T["name"]] = [tr]; self._save_examples(); self.restore_world(snap)
                return {"status": "REQUIRE_SECOND_DEMONSTRATION", "response": f"One unhinted example cannot separate parameters from constants. It is kept as example 1 of {T['name']}; "
                        f"show another (:example {T['name']} ... :endexample) and then :learn {T['name']}.", "kind": "teach"}
            out = super()._process(turn, text, uid, ts); self.restore_world(snap); out["sandbox_restored"] = True; return out
        return super()._process(turn, text, uid, ts)

    def _has_entity_literal(self, steps):
        return any(c in ENTITY for _, c, _ in __import__("abstraction").slots(steps, self.lib))

    def _nl(self):
        T = self.teach
        if "nl" not in T: T["nl"] = {"results": [], "loop": 0, "history": [], "pending": None, "last_pre": None}
        return T["nl"]

    def ctx(self, results):
        procs = self.lib.list_active()
        return {"results": results, "procs": procs, "procs_line": " ; ".join(f"{p['name']}(" + ", ".join(f"{x['name']}:{x['type']}" for x in p["parameters"]) + f") -> {p['returns']}" for p in procs) or "(none)"}

    def capture(self, N, uid):
        p = self.snapshot(f"{uid.replace(':', '_')}_pre"); T = self.teach
        return {"snapshot": p, "n_steps": len(T["steps"]), "env": copy.copy(T["env"]), "results": list(N["results"]), "loop": N["loop"], "result": T["result"]}

    def undo(self):
        T = self.teach; N = self._nl(); pre = N["last_pre"]
        if pre is None: return {"status": "NOTHING_TO_UNDO", "response": "no grounded instruction to undo", "kind": "nl"}
        self.restore_world(pre["snapshot"]); del T["steps"][pre["n_steps"]:]; T["env"] = pre["env"]; N["results"] = pre["results"]; N["loop"] = pre["loop"]; T["result"] = pre["result"]
        N["last_pre"] = None; N["history"].append({"undo": True}); return {"status": "OK", "response": "undone", "kind": "nl", "undone": True}

    def nl_turn(self, turn, text, uid, ts):
        T = self.teach; N = self._nl(); t0 = time.time(); low = text.lower().strip(); rec = {"utterance": text, "uid": uid}
        correction = next((m for m in CORR if low.startswith(m)), None); instr = text.strip()
        if correction: instr = text.strip()[len(correction):].strip(); N["pending"] = None
        elif low.startswith(RESTATE): instr = text.strip()[len(RESTATE):].strip(); N["pending"] = None
        elif N["pending"]:
            pend = N["pending"]; N["pending"] = None
            if F.answers_clarification(text, pend): instr = f"{pend['instruction']} ({text.strip()})"; rec["consumed_clarification"] = pend["source_utterance_id"]
            else: rec["pending_cleared"] = pend["source_utterance_id"]
        rec["instruction"] = instr; rec["correction"] = bool(correction)
        pre_ctx = N["last_pre"]["results"] if (correction and N["last_pre"]) else N["results"]
        # ---- grounding (NL_TEACH) or gold actions (GOLD_TRACE) ----
        probe = None
        if self.nl_mode == "GOLD_TRACE" and self.probe:              # DEV diagnostic: teacher-forced grounding of this utterance (never executed)
            P = F.ground_instruction(instr, self.ctx(pre_ctx), self.grounder); probe = {"status": P["status"], "reason": P.get("reason"), "provenance": P.get("provenance")}
            if P["status"] == "OK": probe["steps"] = canon_steps(F.to_steps(P["actions"], [N["last_pre"]["loop"] if (correction and N["last_pre"]) else N["loop"]]))
        if self.nl_mode == "GOLD_TRACE":
            g = turn["gold_outcome"]; G = {"status": "OK" if g["status"] in ("OK", "EXEC_FAILED") else g["status"], "steps": copy.deepcopy(g.get("steps", [])), "provenance": {"source": "gold"},
                                           "clarify_kind": "REFERENCE" if g["status"] == "CLARIFY" else None,
                                           "clarify_info": {"unresolved_slot": "RETURN.value", "candidates": [{"name": r.name, "kind": r.kind, "etype": r.etype} for r in pre_ctx]} if g["status"] == "CLARIFY" else None}
            if g.get("undo"): correction = correction or "gold-undo"
        else:
            G = F.ground_instruction(instr, self.ctx(pre_ctx), self.grounder)
        rec["grounding"] = G.get("provenance"); rec["status"] = G["status"]
        if G["status"] != "OK":
            if G["status"] == "CLARIFY" and G.get("clarify_kind") == "REFERENCE":                        # "which one?" -> a structured pending record
                info = G.get("clarify_info") or {}
                N["pending"] = {"kind": "REFERENCE", "source_utterance_id": uid, "instruction": instr, "unresolved_slot": info.get("unresolved_slot"), "legal_answers": info.get("candidates") or []}
            N["history"].append(rec); rec["seconds"] = round(time.time() - t0, 3)
            msg = f"Which do you mean? ({G.get('reason')})" if G["status"] == "CLARIFY" else "I can't do that with the available operations (UNSUPPORTED_TEACHING_INPUT)."
            return {"status": G["status"], "response": msg, "kind": "nl", "grounding": G.get("provenance"), "reason": G.get("reason"), "executed_steps": [], "probe": probe}
        if correction and N["last_pre"] is not None: self.undo(); N["history"][-1]["undo_for"] = uid
        if "actions" in G: lc = [N["loop"]]; G["steps"] = F.to_steps(G["actions"], lc); N["loop"] = lc[0]
        steps = canon_steps(G["steps"])
        pre = self.capture(N, uid); env = copy.copy(T["env"]); ex = X.Executor(self.world, self.lib, ts, uid); s = self.world; ret = None; h0 = s.state_hash(); s.begin()
        try:
            try:
                for st in steps: ex.step(st, env, 0)
            except X._Return as r: ret = r.v
            try: PL.VM._check_postconditions(s)
            except PL.VM.VMError as e: raise X.ProcError("VM_EXEC_ERROR", e.reason)
            s.commit()
        except X.ProcError as e:
            s.rollback(); rec.update(status=e.status, reason=e.reason, steps=steps); N["history"].append(rec); rec["seconds"] = round(time.time() - t0, 3)
            return {"probe": probe, "status": e.status, "response": f"That failed ({e.status}: {e.reason}); nothing was changed and it is not part of the demonstration.", "kind": "nl",
                    "grounding": G.get("provenance"), "attempted_steps": steps, "executed_steps": [], "state_unchanged": s.state_hash() == h0}
        T["steps"].extend(steps); T["env"] = env; N["last_pre"] = pre
        acts = G.get("actions") or steps_to_actions(steps)
        for a, st in zip(acts, steps):
            if st.get("bind"): N["results"].append(self._result(st, a, env))
        if ret is not None: T["result"] = X.render(s, ret)
        rec.update(steps=steps, diff=ex.diff, state_before=h0, state_after=s.state_hash(), seconds=round(time.time() - t0, 3)); N["history"].append(rec)
        return {"status": "OK", "response": "Did: " + " ; ".join(L.fmt_step(x) for x in steps), "kind": "nl", "grounding": G.get("provenance"), "executed_steps": steps, "probe": probe,
                "return": X.render(s, ret) if ret is not None else None, "diff": ex.diff}

    def _result(self, st, a, env):
        v = env[st["bind"]]; t = v["t"]; txt = F.action_text(dict(a, bind=st["bind"]))
        if t == "EVENT_LIST":
            et = st["type"]["const"] if st["op"] == "FIND" else None
            if et is None and v["ids"]: et = (self.world.object(v["ids"][0]) or {}).get("type")
            return F.Result(st["bind"], txt, "EVENT_LIST", et, len(v["ids"]))
        if t == "EVENT": return F.Result(st["bind"], txt, "EVENT", (self.world.object(v["id"]) or {}).get("type"))
        if t == "VALUE_LIST": return F.Result(st["bind"], txt, "VALUE_LIST", None, len(v["items"]))
        return F.Result(st["bind"], txt, t)

    def _flush_teaching_trace(self, T, uid):
        N = T.get("nl") or {"history": []}
        rec = {"name": T["name"], "mode": T["mode"], "declared": T["declared"], "interaction_id": T["interaction_id"], "start_snapshot": T["snapshot"],
               "start_snapshot_sha256": hashlib.sha256(open(T["snapshot"], "rb").read()).hexdigest(), "utterances": N["history"], "final_steps": T["steps"],
               "trace_sha256": hashlib.sha256(L.canonical_json(T["steps"]).encode()).hexdigest(), "nl_mode": self.nl_mode}
        json.dump(rec, open(os.path.join(self.dir, "teaching_traces", f"{T['interaction_id'].replace(':', '_')}.json"), "w"), indent=1, default=str)
