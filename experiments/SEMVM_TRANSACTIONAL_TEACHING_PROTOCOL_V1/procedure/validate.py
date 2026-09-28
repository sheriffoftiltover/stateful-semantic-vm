"""Static procedure validation (spec §19, §48-§51): allowed ops only, called procedures ACTIVE, typed parameters, variables defined before use
(FOR variables scoped to their body), no recursion / cycles (call DAG over the library), bounded control flow, constants of the right class,
declared effect class = computed effect class, static result type. Raises ValidationError."""
import os, sys
HERE = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, HERE)
import lang as L, executor as X


class ValidationError(Exception):
    def __init__(self, reason): super().__init__(reason); self.reason = reason


def _const_ok(e, cls):
    if "const" in e and e["const"] not in X.VOCAB[cls]: raise ValidationError(f"constant {e['const']!r} is not a {cls}")


def validate(proc, library, name=None, stack=()):
    """-> {"effect": PURE|STATEFUL, "returns": type, "calls": [...], "depth": n, "primitive_calls": n}"""
    if not isinstance(proc, dict) or set(proc) - {"name", "parameters", "body", "returns", "effect", "description"}: raise ValidationError("malformed procedure object")
    name = name or proc["name"]
    if name in stack: raise ValidationError(f"recursion / cycle via {name}")
    params = {}
    for p in proc["parameters"]:
        if p["type"] not in L.PARAM_TYPES: raise ValidationError(f"untyped / unknown parameter type {p}")
        if p["name"] in params: raise ValidationError(f"duplicate parameter {p['name']}")
        params[p["name"]] = p["type"]
    info = {"effect": "PURE", "calls": [], "depth": 0, "primitive_calls": 0, "returns": "NONE", "used_params": set()}

    def ty(e, env, cls=None):
        if "var" in e:
            if e["var"] not in env: raise ValidationError(f"variable ${e['var']} used before definition")
            return env[e["var"]]
        if "param" in e:
            if e["param"] not in params: raise ValidationError(f"undeclared parameter {e['param']}")
            info["used_params"].add(e["param"])
            if cls and params[e["param"]] != cls: raise ValidationError(f"parameter {e['param']}:{params[e['param']]} used as {cls}")
            return params[e["param"]]
        if cls: _const_ok(e, cls); return cls
        raise ValidationError(f"constant {e['const']!r} in a position that needs a variable")

    def steps(ss, env, depth):
        for st in ss:
            op = st.get("op")
            if op not in X.PRIMITIVES: raise ValidationError(f"op {op} not allowed")
            info["primitive_calls"] += 1; eff = X.PRIMITIVES[op][0]
            if eff == "STATEFUL": info["effect"] = "STATEFUL"
            if op == "FIND":
                ty(st["type"], env, "EVENT_TYPE")
                for sc, rel, x in st["where"]:
                    if sc not in L.SCOPES or rel not in L.RELS: raise ValidationError("bad FIND constraint")
                    ty(x, env, L.REL_CLASS[rel])
                if st.get("status"): ty(st["status"], env, "STATUS")
            elif op == "FIND_LAST": ty(st["type"], env, "EVENT_TYPE")
            elif op in ("GET", "CHILD", "PARENT", "UPDATE", "RETRACT", "SET_STATUS", "DELETE"):
                if ty(st["obj"], env) != "EVENT": raise ValidationError(f"{op} needs an EVENT")
                if op == "UPDATE": ty(st["value"], env, L.REL_CLASS[st["rel"]])
                if op == "SET_STATUS": ty(st["value"], env, "STATUS")
            elif op in ("FIRST", "COUNT", "FILTER", "SELECT", "SORT", "GROUP"):
                t = ty(st["list"], env)
                if t not in ("EVENT_LIST", "VALUE_LIST") or (op not in ("COUNT",) and t != "EVENT_LIST"): raise ValidationError(f"{op} needs an EVENT_LIST")
                if op == "FILTER": ty(st["value"], env, "STATUS" if st["rel"] == "STATUS" else L.REL_CLASS[st["rel"]])
            elif op == "REPORT":
                if ty(st["groups"], env) != "GROUPS": raise ValidationError("REPORT needs GROUPS")
            elif op == "FOR":
                if ty(st["list"], env) != "EVENT_LIST": raise ValidationError("FOR needs an EVENT_LIST")
                inner = dict(env); inner[st["as"]] = "EVENT"; steps(st["body"], inner, depth + 1)
            elif op in ("IF", "PRECONDITION"):
                ty(st["cond"]["nonempty"], env)
                if op == "IF": steps(st["then"], dict(env), depth + 1); steps(st["else"], dict(env), depth + 1)
            elif op == "CALL":
                callee = library.active(st["procedure"]) if library is not None else None
                if callee is None: raise ValidationError(f"CALL to non-ACTIVE procedure {st['procedure']}")
                sub = validate(callee, library, st["procedure"], stack + (name,)); info["calls"].append(st["procedure"]); info["depth"] = max(info["depth"], sub["depth"] + 1)
                if sub["effect"] == "STATEFUL": info["effect"] = "STATEFUL"
                cp = {p["name"]: p["type"] for p in callee["parameters"]}
                if set(st["args"]) != set(cp): raise ValidationError(f"CALL {st['procedure']} argument mismatch")
                for k, x in st["args"].items():
                    t = ty(x, env, None if ("var" in x) else cp[k])
                    if t != cp[k]: raise ValidationError(f"CALL {st['procedure']}: {k} expects {cp[k]}, got {t}")
                env[st["bind"]] = sub["returns"]; continue
            elif op == "RETURN": info["returns"] = ty(st["value"], env)
            res = X.PRIMITIVES[op][1]
            if "bind" in st:
                if res is None: raise ValidationError(f"{op} does not produce a value")
                env[st["bind"]] = L.REL_CLASS[st["rel"]] if res == "VALUE" else res
    steps(proc["body"], {}, 0)
    unused = set(params) - info["used_params"]
    if unused: raise ValidationError(f"unused parameters {sorted(unused)}")
    if not proc["body"] or proc["body"][-1]["op"] != "RETURN": raise ValidationError("procedure must end with RETURN")
    if proc.get("effect") and proc["effect"] != info["effect"]: raise ValidationError(f"declared effect {proc['effect']} != computed {info['effect']}")
    info.pop("used_params"); return info
