"""End-to-end pipeline (spec §12, §17, §24-§25, §34, Amendment 001). One Session = one SQLite world model.
Turn kinds: ASSERT (controlled assertion -> [envelope -> frozen binder] | [GOLD_IR] -> IR -> validate -> resolve -> compile -> execute),
COMMAND (SEMVM_CMD_V1 -> deterministic parse -> compile -> execute). Every turn yields a full trace and an audit record; failures never mutate state.
Neural outputs are cached by utterance text (cache replay = same parser output, different runtime version; spec §25)."""
import os, sys, json, hashlib
ROOT = os.path.dirname(os.path.realpath(__file__))
for d in ("neural", "neural/vendor", "ir", "resolver", "vm", "state", "render"): sys.path.insert(0, os.path.join(ROOT, d))
import ir as IR, resolver as RS, vm as VM, store as ST, render as RD, envelope as EV


def graph_to_json(g):
    occs, edges, root = g; return {"occs": sorted([list(o) for o in occs], key=str), "edges": sorted([[r, list(p), list(c)] for r, p, c in edges], key=str), "root": list(root)}


def graph_from_json(j): return ([tuple(o) for o in j["occs"]], [(r, tuple(p), tuple(c)) for r, p, c in j["edges"]])


class Session:
    def __init__(self, db_path, mode="FULL", binder=None, cache=None):
        self.store = ST.Store(db_path); self.mode = mode; self.binder = binder; self.cache = cache if cache is not None else {}

    def close(self): self.store.close()

    def neural(self, text):
        if text in self.cache: return self.cache[text], True
        toks = text.split(); ok, info = EV.check(toks)
        if not ok: out = {"envelope": info, "status": "UNSUPPORTED_INPUT"}
        else:
            if self.binder is None: raise SystemExit("STOP — neural output not cached and no binder loaded")
            p = self.binder.parse(toks, info["n_mod"]); out = {"envelope": info, "status": "PARSED", "graph": graph_to_json(p["graph"]), "log_mass": p["log_mass"], "margin": p["margin_to_runner_up"], "n_outputs": p["n_outputs"]}
        self.cache[text] = out; return out, False

    def process(self, uid, turn, ts):
        st = self.store; T = {"utterance_id": uid, "INPUT": turn["text"], "kind": turn["kind"], "mode": self.mode, "reference_timestamp": ts, "STATE_BEFORE": st.state_hash()}
        def fail(status, stage, reason):
            T.update(status=status, failure_stage=stage, reason=reason, RESPONSE=RD.render(status, reason=reason), STATE_AFTER=st.state_hash(), STATE_DIFF=[])
            assert T["STATE_AFTER"] == T["STATE_BEFORE"], "failure mutated state"
            return self._log(uid, T, ts)
        try:
            if turn["kind"] == "ASSERT":
                if self.mode == "GOLD_IR": T["NEURAL_OUTPUT"] = "BYPASSED (GOLD_IR)"; ir_ = turn["gold_ir"]
                else:
                    nout, cached = self.neural(turn["text"]); T["NEURAL_OUTPUT"] = nout; T["neural_cached"] = cached
                    if nout["status"] == "UNSUPPORTED_INPUT": return fail("UNSUPPORTED_INPUT", "UNSUPPORTED", json.dumps(nout["envelope"]))
                    try: ir_ = IR.from_graph(*graph_from_json(nout["graph"]))
                    except IR.IRError as e: return fail("IR_VALIDATION_ERROR", "IR_INVALID", e.reason)
                T["CANONICAL_IR"] = IR.canonical(ir_)
                try: IR.validate(ir_); T["IR_VALIDATION"] = "OK"
                except IR.IRError as e: T["IR_VALIDATION"] = e.reason; return fail("IR_VALIDATION_ERROR", "IR_INVALID", e.reason)
                resolved, dec = RS.resolve_assertion(IR.canonical(ir_), st); T["RESOLUTION"] = dec
                prog = VM.compile_assertion(resolved)
            else:
                cmd = VM.parse_command(turn["text"]); T["COMMAND_AST"] = cmd; prog = VM.compile_command(cmd, st)
            T["VM_PROGRAM"] = prog; T["VM_PROGRAM_JSON_SHA256"] = hashlib.sha256(VM.program_json(prog).encode()).hexdigest()
            ret, diff = VM.execute(st, prog, ts, uid, fail_after=turn.get("_test_fail_after"))
            T.update(status="OK", failure_stage=None, STATE_DIFF=diff, RETURN=ret, STATE_AFTER=st.state_hash(), RESPONSE=RD.render("OK", st, ret))
            if ret is not None: T["RETURN_RENDERED"] = sorted(RD.render_value(st, v) for v in ret)
            return self._log(uid, T, ts)
        except RS.ResolveError as e: return fail(e.status, {"RESOLUTION_AMBIGUOUS": "RESOLVE_ENTITY", "RESOLVE_REFERENCE": "RESOLVE_REFERENCE", "RESOLVE_TIME": "RESOLVE_TIME"}[e.status], e.reason)
        except VM.VMError as e: return fail(e.status, {"COMMAND_SYNTAX_ERROR": "UNSUPPORTED", "VM_EXEC_ERROR": "VM_EXEC", "COMPILE": "COMPILE"}.get(e.status, "VM_EXEC"), e.reason)

    def _log(self, uid, T, ts):
        T["STATE_CANONICAL_AFTER"] = self.store.canonical_state()
        self.store.log_utterance(uid, T["INPUT"], ts, T["status"], T["kind"]); self.store.log_transaction(uid, T["status"] == "OK", T.get("STATE_DIFF", []))
        rec = {k: T.get(k) for k in ("utterance_id", "INPUT", "reference_timestamp", "NEURAL_OUTPUT", "CANONICAL_IR", "RESOLUTION", "VM_PROGRAM", "STATE_BEFORE", "STATE_DIFF", "STATE_AFTER", "RESPONSE", "status", "failure_stage", "reason")}
        rec["neural_checkpoint_sha256"] = json.load(open(os.path.join(ROOT, "neural", "BINDER_MANIFEST.json")))["checkpoint"]["sha256"]
        self.store.log_audit(uid, rec); return T
