"""Independent reference semantics for procedure scenarios (spec §40). Re-implements the world model and every PROCEDURE_PRIMITIVES_V1 op over
plain dicts from the frozen semantics text; imports NO runtime module except procedure/lang.py for parsing gold procedure TEXT into steps
(parsing is not under test; the executor semantics are). The discovery system never imports this module."""
import copy, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "procedure"))
import lang as L
OUTER = ["REMINDER", "PLAN", "REQUEST", "NOTE"]; INNER = ["CALL", "EMAIL", "VISIT", "MESSAGE"]
VALID = {"WHEN": set(OUTER + INNER), "WHO": {"REMINDER", "PLAN", "REQUEST", "CALL", "EMAIL", "VISIT", "MESSAGE"}, "RECIPIENT": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "MESSAGE"},
         "TOPIC": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "MESSAGE"}, "WHERE": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "VISIT", "MESSAGE"}}
CLS = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}
VOCAB = None


class OErr(Exception):
    def __init__(self, status): self.status = status


class _Ret(Exception):
    def __init__(self, v): self.v = v


def tnorm(s):
    if s in ("noon", "midnight", "dawn", "dusk"): return s.upper()
    h, _, m = s.partition(":"); return f"{int(h):02d}:{m or '00'}"


class World:
    def __init__(self, vocab):
        global VOCAB
        VOCAB = vocab; self.obj = {}; self.rels = []; self.alias = {}; self.cnt = {}; self.seq = 0; self.attr = {}; self.surf = {}

    def new(self, t):
        n = self.cnt.get(t, 0) + 1; self.cnt[t] = n; self.seq += 1; oid = f"{t.lower()}:{n:06d}"; self.obj[oid] = [t, "active", self.seq]; return oid

    def sid(self, cls, v): vid = f"{cls.lower()}:{tnorm(v) if cls == 'TIME' else v.lower()}"; self.surf.setdefault(vid, v); return vid

    def persons(self, a): return sorted(o for o, al in self.alias.items() if self.obj[o][1] == "active" and a.lower() in [x.lower() for x in al])

    def state(self):
        act = lambda o: self.obj[o][1] == "active"
        return {"objects": sorted([[o, v[0]] for o, v in self.obj.items() if v[1] == "active"]), "relations": sorted([list(r) for r in self.rels]),
                "aliases": sorted([[o, a] for o, al in self.alias.items() if act(o) for a in al]), "attributes": sorted([[o, k, v] for (o, k), v in self.attr.items() if act(o)])}

    def assertion(self, f):
        e0 = self.new(f["outer"]); e1 = self.new(f["inner"]); ev = {"outer": e0, "inner": e1}; pers = {}
        order = {"PERSON": "PERSON", "TIME": "TIME", "PLACE": "PLACE", "TOPIC": "TOPIC_VALUE"}
        for r, v, _ in sorted(f["mods"], key=lambda m: (order[CLS[m[0]]], m[1])):
            if CLS[r] == "PERSON" and v not in pers:
                h = self.persons(v)
                if len(h) >= 2: raise OErr("RESOLUTION_AMBIGUOUS")
                if h: pers[v] = h[0]
                else: pers[v] = self.new("PERSON"); self.alias[pers[v]] = [v]
        self.rels.append((e0, "TODO", e1))
        for r, v, a in f["mods"]: self.rels.append((ev[a], r, pers[v] if CLS[r] == "PERSON" else self.sid(CLS[r], v)))

    # ---------- values ----------
    def lit(self, cls, s):
        if s not in VOCAB[cls]: raise OErr("TYPE_ERROR")
        if cls == "PERSON":
            h = self.persons(s)
            if len(h) >= 2: raise OErr("RESOLUTION_AMBIGUOUS")
            return ("PERSON", h[0] if h else None, s)
        if cls in ("EVENT_TYPE", "STATUS"): return (cls, s)
        return (cls, self.sid(cls, s), s)

    def val_of(self, x, rel):
        for s, p, o in self.rels:
            if s == x and p == rel: return ("PERSON", o, self.alias[o][0]) if o.startswith("person:") else (CLS[rel], o, self.surf[o])
        return ("NONE",)

    def render(self, v):
        k = v[0]
        if k == "NONE": return None
        if k == "EVENT": return {"event": v[1]}
        if k == "LIST": return {"events": list(v[1])}
        if k == "PERSON": return {"person": self.alias[v[1]][0] if v[1] else v[2]}
        if k in ("TIME", "PLACE", "TOPIC"): return {k.lower(): self.surf.get(v[1], v[2])}
        if k == "VALUES": return [self.render(x) for x in v[1]]
        if k == "INT": return v[1]
        if k == "GROUPS": return {"groups": [[a, list(b)] for a, b in v[1]]}
        if k == "REPORT": return {"report": v[1]}
        if k in ("EVENT_TYPE", "STATUS"): return v[1]

    def status_of(self, x): return self.attr.get((x, "STATUS"), "OPEN")

    def has(self, x, sc, rel, val):
        if val[0] == "NONE" or (val[0] == "PERSON" and val[1] is None): return False
        nodes = [x] if sc == "SELF" else [s for s, p, o in self.rels if p == "TODO" and o == x] if sc == "PARENT" else [o for s, p, o in self.rels if p == "TODO" and s == x]
        return any((n, rel, val[1]) in self.rels for n in nodes)

    def active_of(self, t): return [o for o, v in sorted(self.obj.items(), key=lambda kv: kv[1][2]) if v[0] == t and v[1] == "active"]

    # ---------- interpreter ----------
    def E(self, e, env, cls=None):
        if "var" in e: return env[e["var"]]
        if "param" in e:
            if e["param"] not in env: raise OErr("MISSING_ARGUMENT")
            return env[e["param"]]
        return self.lit(cls, e["const"]) if cls else ("CONST", e["const"])

    def steps(self, ss, env, lib):
        for s in ss: self.step(s, env, lib)

    def step(self, s, env, lib):
        op = s["op"]; E = lambda e, c=None: self.E(e, env, c); r = None
        if op == "FIND":
            T = E(s["type"], "EVENT_TYPE")[1]; cons = [(sc, rel, E(x, CLS[rel])) for sc, rel, x in s["where"]]; st = E(s["status"], "STATUS")[1] if s.get("status") else None
            r = ("LIST", [x for x in self.active_of(T) if all(self.has(x, a, b, c) for a, b, c in cons) and (st is None or self.status_of(x) == st)])
        elif op == "FIND_LAST":
            l = self.active_of(E(s["type"], "EVENT_TYPE")[1])
            if not l: raise OErr("NOT_FOUND")
            r = ("EVENT", l[-1])
        elif op in ("GET", "CHILD", "PARENT"):
            o = E(s["obj"])
            if o[0] == "NONE": r = ("NONE",)
            elif op == "GET": r = self.val_of(o[1], s["rel"])
            else:
                c = [(a, b) for a, p, b in self.rels if p == "TODO" and (a == o[1] if op == "CHILD" else b == o[1])]
                r = ("EVENT", c[0][1] if op == "CHILD" else c[0][0]) if c else ("NONE",)
        elif op == "FIRST": l = E(s["list"]); r = ("EVENT", l[1][0]) if l[0] == "LIST" and l[1] else ("NONE",)
        elif op == "COUNT": r = ("INT", len(E(s["list"])[1]))
        elif op == "FILTER":
            l = E(s["list"])[1]
            if s["rel"] == "STATUS": w = E(s["value"], "STATUS")[1]; r = ("LIST", [x for x in l if self.status_of(x) == w])
            else: v = E(s["value"], CLS[s["rel"]]); r = ("LIST", [x for x in l if self.has(x, "SELF", s["rel"], v)])
        elif op == "SELECT": r = ("VALUES", [v for v in (self.val_of(x, s["rel"]) for x in E(s["list"])[1]) if v[0] != "NONE"])
        elif op == "SORT":
            key = lambda x: ("￿" if self.render(self.val_of(x, s["rel"])) is None else json.dumps(self.render(self.val_of(x, s["rel"])), sort_keys=True), self.obj[x][2])
            r = ("LIST", sorted(E(s["list"])[1], key=key))
        elif op == "GROUP":
            g = {}
            for x in E(s["list"])[1]: g.setdefault(json.dumps(self.render(self.val_of(x, s["rel"])), sort_keys=True), []).append(x)
            r = ("GROUPS", sorted(g.items()))
        elif op == "REPORT":
            rows = []
            for k, ids in E(s["groups"])[1]:
                vals = sorted({json.dumps(self.render(self.val_of(x, s["rel"])), sort_keys=True) for x in ids} - {"null"}); rows.append([json.loads(k), len(ids), [json.loads(v) for v in vals]])
            r = ("REPORT", rows)
        elif op in ("UPDATE", "RETRACT", "SET_STATUS", "DELETE"):
            o = E(s["obj"])
            if o[0] == "NONE" or self.obj.get(o[1], [None, "gone"])[1] != "active": raise OErr("NOT_FOUND")
            x = o[1]; t = self.obj[x][0]
            if op in ("UPDATE", "RETRACT"):
                if op == "UPDATE" and t not in VALID[s["rel"]]: raise OErr("VM_EXEC_ERROR")
                self.rels = [q for q in self.rels if not (q[0] == x and q[1] == s["rel"])]
                if op == "UPDATE":
                    v = E(s["value"], CLS[s["rel"]]); tgt = v[1]
                    if v[0] == "PERSON" and tgt is None: tgt = self.new("PERSON"); self.alias[tgt] = [v[2]]
                    self.rels.append((x, s["rel"], tgt))
            elif op == "SET_STATUS": self.attr[(x, "STATUS")] = E(s["value"], "STATUS")[1]
            else: self.obj[x][1] = "deleted"; self.rels = [q for q in self.rels if x not in (q[0], q[2])]
        elif op == "FOR":
            for x in E(s["list"])[1]: env[s["as"]] = ("EVENT", x); self.steps(s["body"], env, lib)
            env.pop(s["as"], None); return
        elif op in ("IF", "PRECONDITION"):
            v = E(s["cond"]["nonempty"]); c = bool(v[1]) if v[0] in ("LIST", "VALUES") else (v[1] > 0 if v[0] == "INT" else v[0] != "NONE")
            if op == "PRECONDITION":
                if not c: raise OErr("PRECONDITION_FALSE")
                return
            self.steps(s["then"] if c else s["else"], env, lib); return
        elif op == "CALL": r = self.call(lib[s["procedure"]], {k: self.E(x, env) for k, x in s["args"].items()}, lib)
        elif op == "RETURN": raise _Ret(E(s["value"]))
        if "bind" in s: env[s["bind"]] = r

    def call(self, proc, args, lib):
        env = {}
        for p in proc["parameters"]:
            if p["name"] not in args: raise OErr("MISSING_ARGUMENT")
            a = args[p["name"]]
            if isinstance(a, tuple) and a[0] not in ("CONST", "NONE") and a[0] != p["type"]: raise OErr("TYPE_ERROR")
            env[p["name"]] = a if a[0] not in ("CONST",) and not isinstance(a, str) else self.lit(p["type"], a[1] if isinstance(a, tuple) else a)
        if set(args) - {p["name"] for p in proc["parameters"]}: raise OErr("TYPE_ERROR")
        try: self.steps(proc["body"], env, lib)
        except _Ret as r: return r.v
        return ("NONE",)

    def invoke(self, proc, args, lib):
        """one transaction -> (status, rendered return)"""
        snap = copy.deepcopy((self.obj, self.rels, self.alias, self.cnt, self.seq, self.attr, self.surf))
        try:
            for k in args: args[k] = ("CONST", args[k]) if isinstance(args[k], str) else args[k]
            v = self.call(proc, args, lib); return "OK", self.render(v)
        except OErr as e:
            self.obj, self.rels, self.alias, self.cnt, self.seq, self.attr, self.surf = snap; return e.status, None

    def run_step_text(self, line, env, lib):
        """a live teaching / setup step (own transaction); env persists across steps"""
        snap = copy.deepcopy((self.obj, self.rels, self.alias, self.cnt, self.seq, self.attr, self.surf))
        try:
            try: self.step(L.parse_step(line), env, lib)
            except _Ret as r: return "OK", self.render(r.v)
            return "OK", None
        except OErr as e:
            self.obj, self.rels, self.alias, self.cnt, self.seq, self.attr, self.surf = snap; return e.status, None


def plan_proc(plan):
    body = []; n = [0]
    def emit(pl):
        args = {k: ({"var": emit(v)} if isinstance(v, dict) else {"const": v}) for k, v in pl["args"].items()}
        var = f"c{n[0]}"; n[0] += 1; body.append({"op": "CALL", "bind": var, "procedure": pl["call"], "args": args}); return var
    body.append({"op": "RETURN", "value": {"var": emit(plan)}}); return {"name": "__plan", "parameters": [], "body": body}
