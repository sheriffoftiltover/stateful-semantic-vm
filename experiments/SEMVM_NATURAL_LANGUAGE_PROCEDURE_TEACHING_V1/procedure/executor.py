"""Deterministic procedure executor (spec §7-§8, §18, §23-§24). Interprets the canonical AST only (never generated code).
Primitive semantics (frozen, PROCEDURE_PRIMITIVES_V1): see PRIMITIVES. One invocation = one SQLite transaction (nested CALLs share it); world
postconditions (core vm._check_postconditions) before commit; ANY error -> ROLLBACK (state hash unchanged). Values are typed dicts."""
import os, sys, json
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
for d in ("core", "core/neural/vendor", "core/resolver", "core/vm", "core/state", "core/ir", "procedure"): sys.path.insert(0, os.path.join(ROOT, d))
import mr_config as K, resolver as RS, vm as VM, lang as L
VOCAB = {"PERSON": set(K.PERSONS), "TIME": set(K.TIMES), "PLACE": set(K.PLACES), "TOPIC": set(K.TOPICS), "EVENT_TYPE": set(L.EVENT_TYPES), "STATUS": set(L.STATUSES)}
ITER_LIMIT = 100
PRIMITIVES = {   # op -> (effect, result type, reads)
    "FIND": ("PURE", "EVENT_LIST"), "FIND_LAST": ("PURE", "EVENT"), "GET": ("PURE", "VALUE"), "CHILD": ("PURE", "EVENT"), "PARENT": ("PURE", "EVENT"),
    "FIRST": ("PURE", "EVENT"), "COUNT": ("PURE", "INT"), "FILTER": ("PURE", "EVENT_LIST"), "SELECT": ("PURE", "VALUE_LIST"), "SORT": ("PURE", "EVENT_LIST"),
    "GROUP": ("PURE", "GROUPS"), "REPORT": ("PURE", "REPORT"), "UPDATE": ("STATEFUL", None), "RETRACT": ("STATEFUL", None), "SET_STATUS": ("STATEFUL", None),
    "DELETE": ("STATEFUL", None), "FOR": ("CONTROL", None), "IF": ("CONTROL", None), "PRECONDITION": ("CONTROL", None), "CALL": ("CALL", "CALLEE"), "RETURN": ("CONTROL", None)}
NONE = {"t": "NONE"}


class ProcError(Exception):
    def __init__(self, status, reason): super().__init__(reason); self.status = status; self.reason = reason


class _Return(Exception):
    def __init__(self, v): self.v = v


def resolve_surface(store, cls, surface, create_ok=False):
    """surface literal -> typed value of class cls"""
    if cls not in VOCAB or surface not in VOCAB[cls]: raise ProcError("TYPE_ERROR", f"{surface!r} is not a {cls} value")
    if cls == "PERSON":
        try: kind, oid = RS.resolve_person(store, surface)
        except RS.ResolveError as e: raise ProcError("RESOLUTION_AMBIGUOUS", e.reason)
        return {"t": "PERSON", "id": oid, "surface": surface}
    if cls in ("EVENT_TYPE", "STATUS"): return {"t": cls, "v": surface}
    vid, norm = RS.scalar_id(cls, surface); return {"t": cls, "id": vid, "norm": norm, "surface": surface}


def render(store, v):
    t = v["t"]
    if t == "NONE": return None
    if t == "EVENT": return {"event": v["id"]}
    if t == "EVENT_LIST": return {"events": list(v["ids"])}
    if t == "PERSON": return {"person": (store.alias_of(v["id"]) if v["id"] else v["surface"])}
    if t in ("TIME", "PLACE", "TOPIC"): return {t.lower(): (store.value(v["id"])[2] if store.value(v["id"]) else v["surface"])}
    if t == "VALUE_LIST": return [render(store, x) for x in v["items"]]
    if t == "INT": return v["v"]
    if t in ("EVENT_TYPE", "STATUS"): return v["v"]
    if t == "GROUPS": return {"groups": [[k, list(ids)] for k, ids in v["groups"]]}
    if t == "REPORT": return {"report": v["rows"]}
    raise ProcError("VM_EXEC_ERROR", f"cannot render {t}")


def _typed_rel_value(store, oid, rel):
    for _, _, o in store.rels(oid, rel):
        if o.startswith("person:"): return {"t": "PERSON", "id": o, "surface": store.alias_of(o)}
        r = store.value(o); return {"t": r[0], "id": o, "norm": r[1], "surface": r[2]}
    return NONE


def _key(store, v):
    r = render(store, v); return "￿" if r is None else json.dumps(r, sort_keys=True)


class Executor:
    def __init__(self, store, library, ts="proc", utt="proc"):
        self.s, self.lib, self.ts, self.utt = store, library, ts, utt; self.trace = []; self.diff = []; self.ops = 0

    # ---------- expressions ----------
    def ev(self, e, env, cls=None):
        if "var" in e:
            if e["var"] not in env: raise ProcError("VM_EXEC_ERROR", f"undefined variable ${e['var']}")
            return env[e["var"]]
        if "param" in e:
            if e["param"] not in env: raise ProcError("MISSING_ARGUMENT", f"parameter {e['param']} unbound")
            return env[e["param"]]
        return resolve_surface(self.s, cls, e["const"]) if cls else {"t": "CONST", "v": e["const"]}

    def need(self, v, *types):
        if v["t"] not in types: raise ProcError("TYPE_ERROR", f"expected {types}, got {v['t']}")
        return v

    # ---------- steps ----------
    def run_steps(self, steps, env, depth=0):
        for st in steps: self.step(st, env, depth)

    def step(self, st, env, depth):
        op = st["op"]; s = self.s; self.ops += 1; E = lambda x, c=None: self.ev(x, env, c); res = None; rec = {"depth": depth, "step": L.fmt_step(st)}
        if op == "FIND":
            T = self.need(E(st["type"], "EVENT_TYPE"), "EVENT_TYPE")["v"]; cons = [(sc, rel, E(x, L.REL_CLASS[rel])) for sc, rel, x in st["where"]]
            status = self.need(E(st["status"], "STATUS"), "STATUS")["v"] if st.get("status") else None; out = []
            for x, _ in s.active_objects(T):
                ok = all(self._has(x, sc, rel, val) for sc, rel, val in cons) and (status is None or s.attr(x, "STATUS", "OPEN") == status)
                if ok: out.append(x)
            res = {"t": "EVENT_LIST", "ids": out}
        elif op == "FIND_LAST":
            T = self.need(E(st["type"], "EVENT_TYPE"), "EVENT_TYPE")["v"]; x = s.last_active(T)
            if x is None: raise ProcError("NOT_FOUND", f"no active {T}")
            res = {"t": "EVENT", "id": x}
        elif op in ("CHILD", "PARENT", "GET"):
            o = E(st["obj"])
            if o["t"] == "NONE": res = NONE
            else:
                self.need(o, "EVENT")
                if op == "GET": res = _typed_rel_value(s, o["id"], st["rel"])
                else:
                    r = s.rels(o["id"], "TODO") if op == "CHILD" else s.rels(None, "TODO", o["id"])
                    res = {"t": "EVENT", "id": (r[0][2] if op == "CHILD" else r[0][0])} if r else NONE
        elif op in ("FIRST", "COUNT"):
            l = self.need(E(st["list"]), "EVENT_LIST", "VALUE_LIST")
            items = l.get("ids", l.get("items"))
            res = {"t": "INT", "v": len(items)} if op == "COUNT" else ({"t": "EVENT", "id": items[0]} if items and l["t"] == "EVENT_LIST" else NONE)
        elif op == "FILTER":
            l = self.need(E(st["list"]), "EVENT_LIST")
            if st["rel"] == "STATUS": want = self.need(E(st["value"], "STATUS"), "STATUS")["v"]; ids = [x for x in l["ids"] if s.attr(x, "STATUS", "OPEN") == want]
            else: val = E(st["value"], L.REL_CLASS[st["rel"]]); ids = [x for x in l["ids"] if self._has(x, "SELF", st["rel"], val)]
            res = {"t": "EVENT_LIST", "ids": ids}
        elif op == "SELECT":
            l = self.need(E(st["list"]), "EVENT_LIST"); res = {"t": "VALUE_LIST", "items": [v for v in (_typed_rel_value(s, x, st["rel"]) for x in l["ids"]) if v["t"] != "NONE"]}
        elif op == "SORT":
            l = self.need(E(st["list"]), "EVENT_LIST"); res = {"t": "EVENT_LIST", "ids": sorted(l["ids"], key=lambda x: (_key(s, _typed_rel_value(s, x, st["rel"])), s.seq_of(x)))}
        elif op == "GROUP":
            l = self.need(E(st["list"]), "EVENT_LIST"); g = {}
            for x in l["ids"]:
                v = _typed_rel_value(s, x, st["rel"]); k = json.dumps(render(s, v), sort_keys=True); g.setdefault(k, []).append(x)
            res = {"t": "GROUPS", "groups": sorted(g.items())}
        elif op == "REPORT":
            g = self.need(E(st["groups"]), "GROUPS"); rows = []
            for k, ids in g["groups"]:
                vals = sorted({json.dumps(render(s, _typed_rel_value(s, x, st["rel"])), sort_keys=True) for x in ids} - {"null"})
                rows.append([json.loads(k), len(ids), [json.loads(v) for v in vals]])
            res = {"t": "REPORT", "rows": rows}
        elif op in ("UPDATE", "RETRACT", "SET_STATUS", "DELETE"):
            o = E(st["obj"])
            if o["t"] == "NONE": raise ProcError("NOT_FOUND", f"{op} on NONE")
            oid = self.need(o, "EVENT")["id"]; ob = s.object(oid)
            if not ob or ob["status"] != "active": raise ProcError("NOT_FOUND", f"{op} on inactive {oid}")
            if op in ("UPDATE", "RETRACT"):
                rel = st["rel"]
                if op == "UPDATE" and not K.valid(rel, ob["type"]): raise ProcError("VM_EXEC_ERROR", f"{rel} not allowed on {ob['type']}")
                for a, b, c in s.rels(oid, rel): s.retract_rel(a, b, c); self.diff.append(["-rel", a, b, c])
                if op == "UPDATE":
                    val = E(st["value"], L.REL_CLASS[rel]); self.need(val, L.REL_CLASS[rel]); tgt = val["id"]
                    if val["t"] == "PERSON" and tgt is None:
                        tgt = s.create_object("PERSON", self.ts, self.utt); s.add_alias(tgt, val["surface"], self.ts); self.diff += [["+obj", tgt, "PERSON"], ["+alias", tgt, val["surface"]]]
                    elif val["t"] != "PERSON": s.ensure_value(val["id"], val["t"], val["norm"], val["surface"])
                    s.assert_rel(oid, rel, tgt, self.ts, self.utt); self.diff.append(["+rel", oid, rel, tgt])
            elif op == "SET_STATUS":
                v = self.need(E(st["value"], "STATUS"), "STATUS")["v"]; old = s.attr(oid, "STATUS", "OPEN"); s.set_attr(oid, "STATUS", v); self.diff.append(["status", oid, old, v])
            else:
                removed = s.rels(oid) + s.rels(None, None, oid); s.delete_object(oid); self.diff.append(["-obj", oid]); self.diff += [["-rel", *r] for r in removed]
        elif op == "FOR":
            l = self.need(E(st["list"]), "EVENT_LIST")
            if len(l["ids"]) > ITER_LIMIT: raise ProcError("ITERATION_LIMIT", f"{len(l['ids'])} > {ITER_LIMIT}")
            rec["iterations"] = len(l["ids"]); self.trace.append(rec)
            for x in l["ids"]:
                env[st["as"]] = {"t": "EVENT", "id": x}; self.run_steps(st["body"], env, depth + 1)
            env.pop(st["as"], None); return
        elif op in ("IF", "PRECONDITION"):
            c = self._cond(st["cond"], env); rec["branch"] = c; self.trace.append(rec)
            if op == "PRECONDITION":
                if not c: raise ProcError("PRECONDITION_FALSE", L.fmt_step(st))
                return
            self.run_steps(st["then"] if c else st["else"], env, depth + 1); return
        elif op == "CALL":
            args = {k: self.ev(x, env) for k, x in st["args"].items()}; res = self.call(st["procedure"], args, depth + 1)
        elif op == "RETURN":
            v = E(st["value"]); rec["result"] = render(s, v); self.trace.append(rec); raise _Return(v)
        else: raise ProcError("VM_EXEC_ERROR", f"unknown op {op}")
        if "bind" in st: env[st["bind"]] = res
        rec["result"] = render(s, res) if res is not None else None; self.trace.append(rec)

    def _has(self, x, scope, rel, val):
        if val["t"] == "NONE" or (val["t"] == "PERSON" and val["id"] is None): return False
        nodes = [x] if scope == "SELF" else [a for a, _, _ in self.s.rels(None, "TODO", x)] if scope == "PARENT" else [c for _, _, c in self.s.rels(x, "TODO")]
        return any(o == val["id"] for n in nodes for _, _, o in self.s.rels(n, rel))

    def _cond(self, c, env):
        v = self.ev(c["nonempty"], env)
        return bool(v.get("ids") or v.get("items")) if v["t"] in ("EVENT_LIST", "VALUE_LIST") else (v["v"] > 0 if v["t"] == "INT" else v["t"] != "NONE")

    # ---------- procedures ----------
    def bind_args(self, proc, args):
        env = {}
        for p in proc["parameters"]:
            if p["name"] not in args: raise ProcError("MISSING_ARGUMENT", f"missing argument {p['name']}:{p['type']}")
            a = args[p["name"]]
            if isinstance(a, dict) and a.get("t") not in (None, "CONST"):
                if a["t"] != p["type"] and not (a["t"] == "NONE"): raise ProcError("TYPE_ERROR", f"{p['name']} expects {p['type']}, got {a['t']}")
                env[p["name"]] = a
            else: env[p["name"]] = resolve_surface(self.s, p["type"], a["v"] if isinstance(a, dict) else a)
        extra = set(args) - {p["name"] for p in proc["parameters"]}
        if extra: raise ProcError("TYPE_ERROR", f"unexpected arguments {sorted(extra)}")
        return env

    def call(self, name, args, depth=0):
        proc = self.lib.active(name) if self.lib is not None else None
        if proc is None: raise ProcError("UNKNOWN_PROCEDURE", f"no ACTIVE procedure {name}")
        if depth > 8: raise ProcError("VM_EXEC_ERROR", "call depth limit")
        return self.run_body(proc, args, depth)

    def run_body(self, proc, args, depth=0):
        env = self.bind_args(proc, args)
        try: self.run_steps(proc["body"], env, depth)
        except _Return as r: return r.v
        return NONE


def invoke(store, library, proc, args, ts="proc", utt="proc", fail_after_ops=None):
    """one transaction; -> dict(status, return (rendered), diff, trace, state_before/after, ops). Never leaves a partial mutation."""
    ex = Executor(store, library, ts, utt); h0 = store.state_hash(); store.begin()
    try:
        if fail_after_ops is not None:
            orig = ex.step
            def hooked(st, env, depth):
                orig(st, env, depth)
                if ex.ops >= fail_after_ops: raise ProcError("VM_EXEC_ERROR", "injected failure (test hook)")
            ex.step = hooked
        v = ex.run_body(proc, args); ret = render(store, v)
        try: VM._check_postconditions(store)
        except VM.VMError as e: raise ProcError("VM_EXEC_ERROR", e.reason)
        store.commit(); return {"status": "OK", "return": ret, "diff": ex.diff, "trace": ex.trace, "state_before": h0, "state_after": store.state_hash(), "ops": ex.ops}
    except ProcError as e:
        store.rollback(); return {"status": e.status, "reason": e.reason, "return": None, "diff": [], "trace": ex.trace, "state_before": h0, "state_after": store.state_hash(), "ops": ex.ops}
