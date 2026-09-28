"""Deterministic trace abstraction = anti-unification (spec §14-§16, §38). Input: one or more SUCCESSFUL teaching traces (concrete steps).
1. variables renamed canonically (v0, v1, ... in definition order); 2. literal SLOTS enumerated with their class (EVENT_TYPE / STATUS / PERSON /
TIME / PLACE / TOPIC; CALL-argument class from the callee signature); 3. all traces must share one skeleton (else REJECTED_AMBIGUOUS: PD_GROUP);
4. PARAMETER vs CONSTANT:
   - several traces: a slot whose values vary is a PARAMETER; slots with identical value vectors share one parameter; invariant slots are CONSTANTS
   - one trace + declared example values (:teach name(p=value)): a slot is the parameter iff its value equals the declared value; a declared
     value that matches no slot, or matches slots of different classes, or (one-shot) more than one slot -> REJECTED_AMBIGUOUS (need more examples)
   - variables are DERIVED / LOCAL_TEMPORARY (never parameters)
Returns (candidate procedure AST, evidence interface). The evidence interface (parameter -> slot paths + source values) is what the verifier uses."""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import lang as L


class AbstractionError(Exception):
    def __init__(self, status, reason): super().__init__(reason); self.status = status; self.reason = reason


def normalize_vars(steps):
    ren = {}
    def nv(n):
        if n not in ren: ren[n] = f"v{len(ren)}"
        return ren[n]
    def walk(ss):
        out = []
        for s in ss:
            s = copy.deepcopy(s)
            for k in ("bind", "as"):
                if k in s: s[k] = nv(s[k])
            def fix(o):
                if isinstance(o, dict):
                    if set(o) == {"var"}: return {"var": ren.get(o["var"], o["var"])}
                    return {k: (walk(v) if k in ("body", "then", "else") else fix(v)) for k, v in o.items()}
                if isinstance(o, list): return [fix(x) for x in o]
                return o
            s = fix(s); out.append(s)
        return out
    return walk(steps)


def slots(steps, library=None, path=()):
    """-> list of (path, class, value) for every literal in the steps"""
    out = []
    for i, s in enumerate(steps):
        p = path + (i,); op = s["op"]
        def lit(key_path, e, cls):
            if "const" in e: out.append((p + key_path, cls, e["const"]))
        if op in ("FIND", "FIND_LAST"): lit(("type",), s["type"], "EVENT_TYPE")
        if op == "FIND":
            for j, (sc, rel, x) in enumerate(s["where"]): lit(("where", j, 2), x, L.REL_CLASS[rel])
            if s.get("status"): lit(("status",), s["status"], "STATUS")
        if op == "FILTER": lit(("value",), s["value"], "STATUS" if s["rel"] == "STATUS" else L.REL_CLASS[s["rel"]])
        if op == "UPDATE": lit(("value",), s["value"], L.REL_CLASS[s["rel"]])
        if op == "SET_STATUS": lit(("value",), s["value"], "STATUS")
        if op == "CALL":
            callee = library.active(s["procedure"]) if library is not None else None
            types = {x["name"]: x["type"] for x in callee["parameters"]} if callee else {}
            for k in sorted(s["args"]): lit(("args", k), s["args"][k], types.get(k, "UNKNOWN"))
        for k in ("body", "then", "else"):
            if k in s: out += slots(s[k], library, p + (k,))
    return out


def get_path(steps, path):
    o = steps
    for k in path: o = o[k]
    return o


def set_path(steps, path, value):
    o = steps
    for k in path[:-1]: o = o[k]
    o[path[-1]] = value


def skeleton(steps, library=None):
    sk = copy.deepcopy(steps)
    for p, cls, v in slots(steps, library): set_path(sk, p, {"slot": cls})
    return json.dumps(sk, sort_keys=True)


def pkey(path): return tuple((0, x) if isinstance(x, int) else (1, str(x)) for x in path)


PNAME = {"PERSON": "person", "TIME": "time", "PLACE": "place", "TOPIC": "topic", "EVENT_TYPE": "event_type", "STATUS": "status"}


def abstract(name, traces, library=None):
    """traces: [{"steps": [...], "declared": {name: value} | None}] (successful only) -> (procedure, evidence)"""
    if not traces: raise AbstractionError("REJECTED_AMBIGUOUS", "no successful trace")
    norm = [normalize_vars(t["steps"]) for t in traces]; sks = {skeleton(s, library) for s in norm}
    if len(sks) != 1: raise AbstractionError("REJECTED_AMBIGUOUS", "PD_GROUP: traces do not share one operation / data-flow skeleton")
    S = [slots(s, library) for s in norm]; base = S[0]; params = []
    if any(c == "UNKNOWN" for _, c, _ in base): raise AbstractionError("REJECTED_AMBIGUOUS", "CALL to a non-ACTIVE procedure inside the trace")
    decl = traces[0].get("declared") or {}
    if len(traces) == 1:
        for pn, pv in decl.items():
            hit = [(p, c) for p, c, v in base if v == pv]
            if not hit: raise AbstractionError("REJECTED_AMBIGUOUS", f"declared parameter {pn}={pv} does not occur in the trace")
            if len(hit) > 1: raise AbstractionError("REJECTED_AMBIGUOUS", f"one-shot: {pn}={pv} occurs in {len(hit)} slots; variable/constant split ambiguous -> need another example")
            params.append({"name": pn, "type": hit[0][1], "slots": [hit[0][0]], "values": [pv]})
    else:
        vec = {}
        for k, (p, c, v) in enumerate(base):
            vals = tuple(s[k][2] for s in S)
            if len(set(vals)) > 1: vec.setdefault(vals, []).append((p, c))
        taken = set()
        for vals, sl in sorted(vec.items(), key=lambda kv: pkey(kv[1][0][0])):
            cls = {c for _, c in sl}
            if len(cls) != 1: raise AbstractionError("REJECTED_AMBIGUOUS", f"co-varying slots of different classes {sorted(cls)}")
            c = cls.pop(); dn = [n for n, v in decl.items() if v == vals[0]]
            nm = dn[0] if dn else PNAME[c]; k = 2
            while nm in taken: nm = f"{PNAME[c]}_{k}"; k += 1
            taken.add(nm); params.append({"name": nm, "type": c, "slots": [p for p, _ in sl], "values": list(vals)})
        for pn, pv in decl.items():
            if not any(p["name"] == pn for p in params): raise AbstractionError("REJECTED_AMBIGUOUS", f"declared parameter {pn} does not vary / match across the examples")
    body = copy.deepcopy(norm[0])
    for p in params:
        for sp in p["slots"]: set_path(body, sp, {"param": p["name"]})
    params.sort(key=lambda p: pkey(p["slots"][0]))
    proc = {"name": name, "parameters": [{"name": p["name"], "type": p["type"]} for p in params], "body": body}
    evidence = {"params": [{"name": p["name"], "type": p["type"], "slots": [list(s) for s in p["slots"]], "values": p["values"]} for p in params],
                "constants": [[list(p), c, v] for p, c, v in base if not any(tuple(p) in [tuple(s) for s in q["slots"]] for q in params)], "n_traces": len(traces)}
    return proc, evidence
