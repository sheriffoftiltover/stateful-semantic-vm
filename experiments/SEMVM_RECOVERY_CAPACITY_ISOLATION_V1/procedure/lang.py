"""SEMVM_STEP_V1 (teaching steps) and the procedure text form <-> canonical procedure AST (spec §18). Deterministic parser, never neural.
Step lines (literals = surface values; $v = variables; {p} = parameters, procedure text only):
  $v = FIND <TYPE> [WHERE <SCOPE>.<REL>=<X> ...] [STATUS=<OPEN|CLOSED>]      $v = FIND_LAST <TYPE>
  $v = GET $x <REL>     $v = CHILD $x     $v = PARENT $x     $v = FIRST $l     $v = COUNT $l
  $v = FILTER $l <REL>=<X> | STATUS=<X>    $v = SELECT $l <REL>    $v = SORT $l <REL>    $v = GROUP $l <REL>    $v = REPORT $g <REL>
  UPDATE $x <REL>=<X>    RETRACT $x <REL>    SET_STATUS $x <OPEN|CLOSED>    DELETE $x
  FOR $e IN $l : <step>        IF NONEMPTY $x : <step>        REQUIRE NONEMPTY $x
  $v = CALL <name> <arg>=<X> ...        RETURN $x
Procedure text:  PROCEDURE <name>(<p>:<TYPE>, ...) / <step lines> / END"""
import re, json, hashlib
EVENT_TYPES = ["REMINDER", "PLAN", "REQUEST", "NOTE", "CALL", "EMAIL", "VISIT", "MESSAGE"]
RELS = ["WHO", "WHEN", "WHERE", "RECIPIENT", "TOPIC"]; SCOPES = ["SELF", "PARENT", "CHILD"]; STATUSES = ["OPEN", "CLOSED"]
PARAM_TYPES = ["PERSON", "TIME", "PLACE", "TOPIC", "EVENT_TYPE", "STATUS"]
REL_CLASS = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}


class LangError(Exception):
    def __init__(self, reason): super().__init__(reason); self.reason = reason


def expr(tok):
    if tok.startswith("$"): return {"var": tok[1:]}
    m = re.fullmatch(r"\{(\w+)\}", tok)
    if m: return {"param": m.group(1)}
    return {"const": tok}


def parse_step(line):
    t = line.split()
    if not t: raise LangError("empty step")
    if t[0] in ("FOR", "IF") and ":" in t:
        k = t.index(":"); body = parse_step(" ".join(t[k + 1:]))
        if t[0] == "FOR":
            if len(t[:k]) != 4 or t[2] != "IN" or not t[1].startswith("$"): raise LangError("FOR $e IN $l : <step>")
            return {"op": "FOR", "as": t[1][1:], "list": expr(t[3]), "body": [body]}
        if t[1:k] and t[1] == "NONEMPTY" and len(t[:k]) == 3: return {"op": "IF", "cond": {"nonempty": expr(t[2])}, "then": [body], "else": []}
        raise LangError("IF NONEMPTY $x : <step>")
    if t[0] == "REQUIRE":
        if len(t) != 3 or t[1] != "NONEMPTY": raise LangError("REQUIRE NONEMPTY $x")
        return {"op": "PRECONDITION", "cond": {"nonempty": expr(t[2])}}
    if t[0] == "RETURN":
        if len(t) != 2: raise LangError("RETURN $x")
        return {"op": "RETURN", "value": expr(t[1])}
    if t[0] in ("UPDATE", "RETRACT", "SET_STATUS", "DELETE"):
        if t[0] == "UPDATE":
            if len(t) != 3 or "=" not in t[2]: raise LangError("UPDATE $x REL=X")
            rel, v = t[2].split("=", 1); _rel(rel); return {"op": "UPDATE", "obj": expr(t[1]), "rel": rel, "value": expr(v)}
        if t[0] == "RETRACT":
            if len(t) != 3: raise LangError("RETRACT $x REL")
            _rel(t[2]); return {"op": "RETRACT", "obj": expr(t[1]), "rel": t[2]}
        if t[0] == "SET_STATUS":
            if len(t) != 3: raise LangError("SET_STATUS $x STATUS")
            return {"op": "SET_STATUS", "obj": expr(t[1]), "value": expr(t[2])}
        if len(t) != 2: raise LangError("DELETE $x")
        return {"op": "DELETE", "obj": expr(t[1])}
    if len(t) < 3 or not t[0].startswith("$") or t[1] != "=": raise LangError(f"cannot parse step: {line!r}")
    v, op, a = t[0][1:], t[2], t[3:]
    if op == "FIND":
        if not a: raise LangError("FIND <TYPE>")
        st = {"op": "FIND", "bind": v, "type": expr(a[0]), "where": [], "status": None}; rest = a[1:]
        if rest and rest[0] == "WHERE": rest = rest[1:]
        for c in rest:
            if c.startswith("STATUS="): st["status"] = expr(c.split("=", 1)[1]); continue
            m = re.fullmatch(r"(SELF|PARENT|CHILD)\.(\w+)=(.+)", c)
            if not m: raise LangError(f"bad FIND constraint {c}")
            _rel(m.group(2)); st["where"].append([m.group(1), m.group(2), expr(m.group(3))])
        return st
    if op == "FIND_LAST":
        if len(a) != 1: raise LangError("FIND_LAST <TYPE>")
        return {"op": "FIND_LAST", "bind": v, "type": expr(a[0])}
    if op in ("CHILD", "PARENT", "FIRST", "COUNT"):
        if len(a) != 1: raise LangError(f"{op} $x")
        return {"op": op, "bind": v, ("obj" if op in ("CHILD", "PARENT") else "list"): expr(a[0])}
    if op == "GET":
        if len(a) != 2: raise LangError("GET $x REL")
        _rel(a[1]); return {"op": "GET", "bind": v, "obj": expr(a[0]), "rel": a[1]}
    if op in ("SELECT", "SORT", "GROUP", "REPORT"):
        if len(a) != 2: raise LangError(f"{op} $x REL")
        _rel(a[1]); return {"op": op, "bind": v, ("groups" if op == "REPORT" else "list"): expr(a[0]), "rel": a[1]}
    if op == "FILTER":
        if len(a) != 2 or "=" not in a[1]: raise LangError("FILTER $l REL=X | STATUS=X")
        rel, x = a[1].split("=", 1)
        if rel != "STATUS": _rel(rel)
        return {"op": "FILTER", "bind": v, "list": expr(a[0]), "rel": rel, "value": expr(x)}
    if op == "CALL":
        if not a: raise LangError("CALL <name> ...")
        args = {}
        for x in a[1:]:
            if "=" not in x: raise LangError(f"bad CALL argument {x}")
            k, y = x.split("=", 1); args[k] = expr(y)
        return {"op": "CALL", "bind": v, "procedure": a[0], "args": args}
    raise LangError(f"unknown op {op}")


def _rel(r):
    if r not in RELS: raise LangError(f"unknown relation {r}")


def parse_procedure(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines or not lines[0].startswith("PROCEDURE") or lines[-1] != "END": raise LangError("PROCEDURE name(...) ... END")
    m = re.fullmatch(r"PROCEDURE\s+([a-z][a-z0-9_]*)\s*\((.*)\)", lines[0])
    if not m: raise LangError("bad PROCEDURE header")
    params = []
    for p in [x.strip() for x in m.group(2).split(",") if x.strip()]:
        mm = re.fullmatch(r"([a-z][a-z0-9_]*)\s*:\s*([A-Z_]+)", p)
        if not mm or mm.group(2) not in PARAM_TYPES: raise LangError(f"bad parameter {p}")
        params.append({"name": mm.group(1), "type": mm.group(2)})
    return {"name": m.group(1), "parameters": params, "body": [parse_step(l) for l in lines[1:-1]]}


def fmt_expr(e): return f"${e['var']}" if "var" in e else f"{{{e['param']}}}" if "param" in e else str(e["const"])


def fmt_step(s):
    op = s["op"]; E = fmt_expr
    if op == "FOR": return f"FOR ${s['as']} IN {E(s['list'])} : {fmt_step(s['body'][0])}"
    if op == "IF": return f"IF NONEMPTY {E(s['cond']['nonempty'])} : {fmt_step(s['then'][0])}"
    if op == "PRECONDITION": return f"REQUIRE NONEMPTY {E(s['cond']['nonempty'])}"
    if op == "RETURN": return f"RETURN {E(s['value'])}"
    if op == "UPDATE": return f"UPDATE {E(s['obj'])} {s['rel']}={E(s['value'])}"
    if op == "RETRACT": return f"RETRACT {E(s['obj'])} {s['rel']}"
    if op == "SET_STATUS": return f"SET_STATUS {E(s['obj'])} {E(s['value'])}"
    if op == "DELETE": return f"DELETE {E(s['obj'])}"
    h = f"${s['bind']} = {op}"
    if op == "FIND": return " ".join([h, E(s["type"])] + (["WHERE"] + [f"{a}.{b}={E(c)}" for a, b, c in s["where"]] if s["where"] else []) + ([f"STATUS={E(s['status'])}"] if s.get("status") else []))
    if op == "FIND_LAST": return f"{h} {E(s['type'])}"
    if op in ("CHILD", "PARENT"): return f"{h} {E(s['obj'])}"
    if op in ("FIRST", "COUNT"): return f"{h} {E(s['list'])}"
    if op == "GET": return f"{h} {E(s['obj'])} {s['rel']}"
    if op in ("SELECT", "SORT", "GROUP"): return f"{h} {E(s['list'])} {s['rel']}"
    if op == "REPORT": return f"{h} {E(s['groups'])} {s['rel']}"
    if op == "FILTER": return f"{h} {E(s['list'])} {s['rel']}={E(s['value'])}"
    if op == "CALL": return " ".join([h, s["procedure"]] + [f"{k}={E(v)}" for k, v in sorted(s["args"].items())])
    raise LangError(op)


def fmt_procedure(p): return "\n".join([f"PROCEDURE {p['name']}(" + ", ".join(f"{x['name']}:{x['type']}" for x in p["parameters"]) + ")"] + [fmt_step(s) for s in p["body"]] + ["END"])


def canonical_json(obj): return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def program_hash(p):
    """semantic identity (§57): parameters renamed positionally (p0, p1, ...) -> independent of wording / parameter names"""
    ren = {x["name"]: f"p{i}" for i, x in enumerate(p["parameters"])}
    def walk(o):
        if isinstance(o, dict): return {"param": ren.get(o["param"], o["param"])} if set(o) == {"param"} else {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(x) for x in o]
        return o
    return hashlib.sha256(canonical_json({"params": [x["type"] for x in p["parameters"]], "body": walk(p["body"])}).encode()).hexdigest()
