"""Procedure-learning session (spec §12-§14, §25-§37, §53-§55, §63-§67). Two persistent stores: WORLD (core SQLite world model) + LIBRARY
(procedures.sqlite). Turn surfaces:
  <controlled assertion> | SEMVM_CMD_V1 command            -> core pipeline (unchanged from END_TO_END_POC_V1)
  <step line>  ($v = FIND ... / UPDATE $x ... / FOR ... )    -> executed immediately (one transaction per step); recorded while teaching
  :teach name(p=v, ...) ... :endteach                         one-shot explicit teaching -> discovery -> verification (NOT activation)
  :example name(p=v) ... :endexample   then   :learn name     multi-example discovery
  :revise name(p=v) ... :endrevise                            new candidate version (parent = active); v1 kept
  :propose name <<PROCEDURE ... END>>                         an externally proposed candidate, verified against the recorded examples
  :save-last-as name(p=v)                                     the last RUN / REQUEST execution becomes a trace (composition level 2)
  :accept name   (explicit 'yes', spec §67)                   VERIFIED -> ACTIVE;  RUN name k=v ...;  REQUEST <text> (controlled NL retrieval)
  :alias name <phrase>  :procedure name  :disable-procedure / :enable-procedure / :delete-procedure name
Discovery runs BOTH proposers (deterministic anti-unification, frozen LLM); every candidate is verified against the evidence derived from the
traces; the chosen candidate = the deterministic one if VERIFIED, else the LLM one if VERIFIED, else rejected. Nothing becomes ACTIVE without
VERIFIED + :accept. No turn after a restart depends on any transcript: only WORLD + LIBRARY + the current request."""
import os, sys, re, json, shutil, time, copy, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "core"))
import pipeline as PL, lang as L, executor as X, validate as VD, abstraction as AB, verify as VF, procstore as PS, retrieval as RT, llm as LM
STEP_START = ("$", "FOR ", "IF ", "REQUIRE ", "RETURN ")


def is_step(t):
    tt = t.split()
    return t.startswith(STEP_START) or (len(tt) >= 2 and tt[0] in ("UPDATE", "RETRACT", "SET_STATUS", "DELETE") and tt[1].startswith("$"))


def parse_header(h):
    m = re.fullmatch(r"([a-z][a-z0-9_]*)\s*(?:\((.*)\))?", h.strip())
    if not m: raise ValueError(f"bad procedure header {h!r}")
    decl = {}
    for kv in [x.strip() for x in (m.group(2) or "").split(",") if x.strip()]:
        k, v = kv.split("=", 1); decl[k.strip()] = v.strip()
    return m.group(1), decl


class System:
    def __init__(self, world_db, proc_db, learn_dir, mode="DISCOVERED", use_llm=True, pipeline_mode="GOLD_IR", binder=None):
        self.sess = PL.Session(world_db, pipeline_mode, binder=binder); self.world = self.sess.store; self.lib = PS.Library(proc_db); self.dir = learn_dir
        os.makedirs(os.path.join(learn_dir, "snapshots"), exist_ok=True); self.mode = mode; self.use_llm = use_llm; self.teach = None; self.examples = self._load_examples()
        self.last_exec = None; self.env = {}; self.n = 0

    def close(self): self.sess.close(); self.lib.close()

    # ---------- persistence of recorded examples (in-progress learning evidence) ----------
    def _ex_path(self): return os.path.join(self.dir, "examples.json")
    def _load_examples(self): return json.load(open(self._ex_path())) if os.path.exists(self._ex_path()) else {}
    def _save_examples(self): json.dump(self.examples, open(self._ex_path(), "w"), indent=1)

    def snapshot(self, tag):
        p = os.path.join(self.dir, "snapshots", f"{tag}.sqlite")
        if os.path.exists(p): os.remove(p)
        self.world.snapshot(p).close(); return p

    # ---------- steps ----------
    def run_step(self, line, env, uid, ts):
        st = L.parse_step(line); ex = X.Executor(self.world, self.lib, ts, uid); s = self.world; s.begin(); ret = None
        try:
            try: ex.step(st, env, 0)
            except X._Return as r: ret = r.v
            try: PL.VM._check_postconditions(s)
            except PL.VM.VMError as e: raise X.ProcError("VM_EXEC_ERROR", e.reason)
            s.commit()
        except X.ProcError as e: s.rollback(); return {"status": e.status, "reason": e.reason, "step": st}
        return {"status": "OK", "step": st, "return": X.render(s, ret) if ret is not None else None, "is_return": st["op"] == "RETURN", "diff": ex.diff,
                "result": ex.trace[-1].get("result") if ex.trace else None}

    # ---------- discovery ----------
    def discover(self, name, traces, parent=None, reason=None, external=None):
        R = {"name": name, "n_traces": len(traces), "paths": {}}; ev = None
        try: det, ev = AB.abstract(name, traces, self.lib); R["paths"]["deterministic"] = {"proposal": L.fmt_procedure(det)}
        except AB.AbstractionError as e: det = None; R["paths"]["deterministic"] = {"status": e.status, "reason": e.reason}
        cands = []
        if external is not None: cands.append(("external", external))
        else:
            if det: cands.append(("deterministic", det))
            if self.use_llm:
                t0 = time.time()
                try:
                    text, _ = LM.propose(name, traces); R["paths"]["llm"] = {"text": text, "seconds": round(time.time() - t0, 2)}
                    cp = L.parse_procedure(text); cp["name"] = name; cands.append(("llm", cp))
                except L.LangError as e: R["paths"]["llm"].update(status="PROPOSAL_UNPARSEABLE", reason=e.reason)
                except Exception as e: R["paths"]["llm"] = {"status": "LLM_ERROR", "reason": str(e)[:200]}
        chosen = None
        for who, c in cands:
            if ev is None: R["paths"].setdefault(who, {}).update(status=R["paths"]["deterministic"].get("status", "REJECTED_AMBIGUOUS"), reason="no evidence interface (abstraction ambiguous)"); continue
            t0 = time.time(); st, tests, vinfo = VF.verify(c, ev, traces, self.lib)
            R["paths"].setdefault(who, {}).update(status=st, verify_seconds=round(time.time() - t0, 2), tests=[[t, ok] for t, ok, _ in tests], failed=[[t, info] for t, ok, info in tests if not ok][:3],
                                                  program=L.fmt_procedure(c), program_hash=L.program_hash(c))
            if st == "VERIFIED" and chosen is None: chosen = (who, c, tests, vinfo)
        pick = chosen or (next(((w, c, None, None) for w, c in cands), None))
        if pick is None: R.update(status=R["paths"]["deterministic"].get("status", "REJECTED_AMBIGUOUS"), stored=None); return R
        who, c, tests, vinfo = pick
        prov = {"proposer": who, "source_interactions": [t["interaction_id"] for t in traces], "source_trace_sha256": [hashlib.sha256(L.canonical_json(t["steps"]).encode()).hexdigest() for t in traces],
                "llm_model": "Qwen/Qwen2.5-Coder-1.5B (frozen, greedy)" if self.use_llm else None, "binder": "A-005 R20 s17 ep40 (frozen)", "runtime": "SEMVM_PROCEDURE_DISCOVERY_POC_V1",
                "verification_suite": "verify.py stages 0-6", "timestamp": time.strftime("%F %T"), "paths": {k: v.get("status") for k, v in R["paths"].items()}}
        pid = self.lib.add_candidate(c, prov, [(t["interaction_id"], "source") for t in traces], "t", prov["source_trace_sha256"][0], parent, reason)
        self.lib.set_status(pid, "TESTING")
        final = R["paths"][who]["status"] if ev is not None else R["paths"]["deterministic"].get("status", "REJECTED_AMBIGUOUS")
        self.lib.set_status(pid, final, effect=vinfo["effect"] if vinfo else None, returns=vinfo["returns"] if vinfo else None)
        if tests: self.lib.record_tests(pid, [(t, ok, info) for t, ok, info in tests])
        R.update(status=final, stored=pid, chosen=who)
        d = os.path.join(self.dir, "candidates"); os.makedirs(d, exist_ok=True)
        json.dump(R, open(os.path.join(d, f"{pid.replace(':', '_')}.json"), "w"), indent=1, default=str); return R

    # ---------- turns ----------
    def process(self, turn, uid, ts):
        self.n += 1; text = turn["text"].strip(); t0 = time.time(); ncalls = len(LM.CALLS)
        out = self._process(turn, text, uid, ts); out["seconds"] = round(time.time() - t0, 3); out["llm_calls"] = len(LM.CALLS) - ncalls; out["input"] = text
        out["world_state_hash"] = self.world.state_hash(); out["library_hash"] = self.lib.hash(); return out

    def _process(self, turn, text, uid, ts):
        if turn.get("kind") == "ASSERT" or (not text.startswith(":") and not is_step(text) and not text.startswith(("RUN ", "REQUEST ")) and not PL.VM.is_command(text)):
            t = self.sess.process(uid, turn if turn.get("kind") == "ASSERT" else {"kind": "ASSERT", "text": text}, ts); return {"status": t["status"], "response": t["RESPONSE"], "kind": "assertion"}
        if PL.VM.is_command(text) and not is_step(text):
            t = self.sess.process(uid, {"kind": "COMMAND", "text": text}, ts); return {"status": t["status"], "response": t["RESPONSE"], "kind": "command", "return": t.get("RETURN_RENDERED")}
        if is_step(text):
            env = self.teach["env"] if self.teach else self.env; r = self.run_step(text, env, uid, ts)
            if self.teach is not None:
                if r["status"] != "OK": self.teach["failed"] = f"{r['status']}: {r['reason']}"
                self.teach["steps"].append(r["step"])
                if r["status"] == "OK" and r.get("is_return"): self.teach["result"] = r["return"]
            return {"status": r["status"], "response": json.dumps(r.get("return") if r.get("is_return") else r.get("result")), "kind": "step", "reason": r.get("reason")}
        cmd, _, rest = text.partition(" ")
        if cmd in (":teach", ":example", ":revise"):
            if self.teach is not None: return {"status": "ERROR", "response": "already teaching"}
            name, decl = parse_header(rest); self.teach = {"mode": cmd, "name": name, "declared": decl or None, "steps": [], "env": {}, "failed": None, "result": None,
                                                           "snapshot": self.snapshot(f"{uid.replace(':', '_')}_start"), "interaction_id": uid}
            return {"status": "OK", "response": f"recording {cmd[1:]} for {name}", "kind": "teach"}
        if cmd in (":endteach", ":endexample", ":endrevise"):
            T = self.teach; self.teach = None
            if T is None: return {"status": "ERROR", "response": "not teaching"}
            if T["failed"] or not T["steps"] or T["steps"][-1]["op"] != "RETURN": return {"status": "TRACE_FAILED", "response": f"not learning from an unsuccessful trace ({T['failed'] or 'must end with RETURN'})", "kind": "teach"}
            tr = {"steps": T["steps"], "declared": T["declared"], "snapshot": T["snapshot"], "result": T["result"], "post_state": self.world.canonical_state(), "interaction_id": T["interaction_id"]}
            if T["mode"] == ":example":
                self.examples.setdefault(T["name"], []).append(tr); self._save_examples(); return {"status": "OK", "response": f"example {len(self.examples[T['name']])} recorded for {T['name']}", "kind": "teach"}
            self.examples[T["name"]] = [tr]; self._save_examples()
            parent = self.lib.active_id(T["name"]) if T["mode"] == ":revise" else None
            R = self.discover(T["name"], [tr], parent=parent, reason="revision" if parent else None); return self._report(R)
        if cmd == ":learn":
            name = rest.strip(); trs = self.examples.get(name, []); R = self.discover(name, trs); return self._report(R)
        if cmd == ":propose":
            m = re.fullmatch(r"([a-z][a-z0-9_]*)\s*<<(.*)>>", rest.strip(), re.S)
            if not m: return {"status": "ERROR", "response": ":propose name <<PROCEDURE ... END>>"}
            try: c = L.parse_procedure(m.group(2).replace(" ; ", "\n")); c["name"] = m.group(1)
            except L.LangError as e: return {"status": "PROPOSAL_UNPARSEABLE", "response": e.reason}
            R = self.discover(m.group(1), self.examples.get(m.group(1), []), external=c); return self._report(R)
        if cmd == ":save-last-as":
            name, decl = parse_header(rest)
            if not self.last_exec or self.last_exec["status"] != "OK": return {"status": "TRACE_FAILED", "response": "no successful last execution"}
            le = self.last_exec; tr = {"steps": le["steps"], "declared": decl or None, "snapshot": le["snapshot"], "result": le["return"], "post_state": le["post_state"], "interaction_id": le["uid"]}
            self.examples[name] = [tr]; self._save_examples(); R = self.discover(name, [tr]); return self._report(R)
        if cmd == ":accept":
            name = rest.strip(); vs = [v for v in self.lib.versions(name) if v["status"] == "VERIFIED"]
            if not vs: return {"status": "NOTHING_TO_ACCEPT", "response": f"no VERIFIED candidate for {name}"}
            self.lib.activate(vs[-1]["id"]); return {"status": "OK", "response": f"{vs[-1]['id']} is now ACTIVE", "kind": "accept", "id": vs[-1]["id"]}
        if cmd == ":alias":
            name, _, phrase = rest.partition(" ")
            try: self.lib.add_alias(name, phrase.strip().strip('"')); return {"status": "OK", "response": "alias added"}
            except KeyError: return {"status": "ERROR", "response": f"no active {name}"}
        if cmd == ":procedure":
            e = self.lib.explain(rest.strip()); return {"status": "OK" if e else "NOT_FOUND", "response": json.dumps(e, indent=1, default=str) if e else "no such procedure", "explain": e}
        if cmd in (":disable-procedure", ":enable-procedure", ":delete-procedure"):
            try:
                if cmd == ":delete-procedure": self.lib.delete(rest.strip())
                else: self.lib.set_enabled(rest.strip(), cmd == ":enable-procedure")
                return {"status": "OK", "response": cmd[1:] + " " + rest.strip()}
            except KeyError: return {"status": "NOT_FOUND", "response": rest.strip()}
        if cmd == "RUN":
            name, _, a = rest.partition(" "); args = dict(x.split("=", 1) for x in a.split()) if a.strip() else {}
            return self._execute({"call": name, "args": args}, uid, ts, "run")
        if cmd == "REQUEST":
            if self.mode == "GOLD_PROC" and turn.get("gold_plan") is not None:
                return self._execute(turn["gold_plan"], uid, ts, "request", retrieval={"status": "GOLD_BYPASS"})
            r = RT.retrieve(rest, self.lib)
            if r["status"] != "OK": return {"status": "CLARIFY", "response": f"Which procedure do you mean? ({r.get('reason')})", "kind": "request", "retrieval": r}
            return self._execute(r["plan"], uid, ts, "request", retrieval=r)
        return {"status": "ERROR", "response": f"unknown input {text!r}"}

    def _execute(self, plan, uid, ts, kind, retrieval=None):
        proc = RT.plan_to_proc(plan); snap = self.snapshot("last_pre"); r = X.invoke(self.world, self.lib, proc, {}, ts, uid)
        self.last_exec = {"status": r["status"], "steps": proc["body"], "snapshot": snap, "return": r["return"], "post_state": self.world.canonical_state(), "uid": uid}
        resp = json.dumps(r["return"]) if r["status"] == "OK" else f"{r['status']}: {r.get('reason')}"
        return {"status": r["status"], "response": resp, "kind": kind, "plan": RT.plan_str(plan), "return": r["return"], "diff": r["diff"], "vm_ops": r["ops"], "retrieval": retrieval,
                "state_unchanged": r["state_before"] == r["state_after"]}

    def _report(self, R):
        st = R["status"]; pid = R.get("stored")
        if st == "VERIFIED":
            n = sum(1 for t in (R["paths"][R["chosen"]].get("tests") or []) if t[1])
            msg = f"I learned `{R['name']}` ({R['chosen']} proposal). It passed {n} verification cases. Save it? (:accept {R['name']})"
        else: msg = f"Not learned: {st}. " + json.dumps({k: v.get("status") for k, v in R["paths"].items()})
        return {"status": st, "response": msg, "kind": "discovery", "discovery": R, "id": pid}

    # ---------- GOLD_PROC bypass (evaluation control only) ----------
    def install_gold(self, name, text):
        c = L.parse_procedure(text); c["name"] = name; info = VD.validate(c, self.lib)
        pid = self.lib.add_candidate(c, {"proposer": "gold (GOLD_PROC bypass)"}, [], "t", "gold"); self.lib.set_status(pid, "VERIFIED", effect=info["effect"], returns=info["returns"]); self.lib.activate(pid); return pid
