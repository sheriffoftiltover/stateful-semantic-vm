"""Deterministic semantic VM (spec §12-§15; Amendment 001 command language SEMVM_CMD_V1).
Instruction set (tuples; registers '$<local_id>' bind objects created in the same program):
  CREATE(type, reg)  ADD_ALIAS(ref, alias)  ENSURE_VALUE(value_id, type, normalized, surface)
  ASSERT(s, p, o)    RETRACT(s, p, o)       DELETE(object_id)
  MATCH(pattern)     RETURN(kind)
Compilation is deterministic and never neural. Execution: one transaction per utterance; postconditions checked before commit; any failure ->
ROLLBACK (no partial mutation). No instruction can execute code, shell, or anything outside the semantic state API."""
import os, sys, json
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
for d in ("neural/vendor", "resolver", "ir"): sys.path.insert(0, os.path.join(ROOT, d))
import mr_config as K, resolver as RS, ir as IR
EVENTS = K.OUTER + K.INNER; RELS = ["WHO", "WHEN", "WHERE", "RECIPIENT", "TOPIC"]; VCLASS = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}
VALUES = {cls: set(v) for cls, v in (("PERSON", K.PERSONS), ("TIME", K.TIMES), ("PLACE", K.PLACES), ("TOPIC", K.TOPICS))}


class VMError(Exception):
    def __init__(self, status, reason): super().__init__(reason); self.status = status; self.reason = reason


# ---------------- SEMVM_CMD_V1 parser ----------------
def is_command(text): return text.split()[:1] and text.split()[0] in ("QUERY", "UPDATE", "RETRACT", "DELETE", "NEW")


def _target(t):
    if t in EVENTS or (t.startswith("LAST_") and t[5:] in EVENTS): return t
    raise VMError("COMMAND_SYNTAX_ERROR", f"bad target {t}")


def _assign(tok, scope_ok=False):
    if "=" not in tok: raise VMError("COMMAND_SYNTAX_ERROR", f"expected REL=VALUE, got {tok}")
    lhs, val = tok.split("=", 1); scope = "SELF"
    if "." in lhs:
        if not scope_ok: raise VMError("COMMAND_SYNTAX_ERROR", f"scope not allowed in {tok}")
        scope, lhs = lhs.split(".", 1)
        if scope not in ("SELF", "PARENT", "CHILD"): raise VMError("COMMAND_SYNTAX_ERROR", f"bad scope {scope}")
    if lhs not in RELS: raise VMError("COMMAND_SYNTAX_ERROR", f"bad relation {lhs}")
    if val not in VALUES[VCLASS[lhs]]: raise VMError("COMMAND_SYNTAX_ERROR", f"value {val!r} is not a {VCLASS[lhs]} value")
    return scope, lhs, val


def parse_command(text):
    t = text.split()
    if t[0] == "QUERY":
        if len(t) < 4 or t[1] not in RELS or t[2] != "OF": raise VMError("COMMAND_SYNTAX_ERROR", "QUERY <REL> OF <TARGET> [WHERE ...]")
        cons = []
        if len(t) > 4:
            if t[4] != "WHERE" or len(t) < 6: raise VMError("COMMAND_SYNTAX_ERROR", "expected WHERE <SCOPE>.<REL>=<VALUE>")
            cons = [_assign(x, True) for x in t[5:]]
        return {"op": "QUERY", "rel": t[1], "target": _target(t[3]), "where": cons}
    if t[0] == "UPDATE":
        if len(t) < 3 or not t[1].startswith("LAST_"): raise VMError("COMMAND_SYNTAX_ERROR", "UPDATE <REF> <REL>=<VALUE>+")
        return {"op": "UPDATE", "ref": _target(t[1]), "set": [_assign(x)[1:] for x in t[2:]]}
    if t[0] == "RETRACT":
        if len(t) != 3 or not t[1].startswith("LAST_") or t[2] not in RELS: raise VMError("COMMAND_SYNTAX_ERROR", "RETRACT <REF> <REL>")
        return {"op": "RETRACT", "ref": _target(t[1]), "rel": t[2]}
    if t[0] == "DELETE":
        if len(t) != 2 or not t[1].startswith("LAST_"): raise VMError("COMMAND_SYNTAX_ERROR", "DELETE <REF>")
        return {"op": "DELETE", "ref": _target(t[1])}
    if t[0] == "NEW":
        if len(t) != 3 or t[1] != "PERSON" or t[2] not in VALUES["PERSON"]: raise VMError("COMMAND_SYNTAX_ERROR", "NEW PERSON <NAME>")
        return {"op": "NEW_PERSON", "alias": t[2]}
    raise VMError("COMMAND_SYNTAX_ERROR", "unknown command")


# ---------------- compiler ----------------
def value_operand(store, rel, surface, created=None):
    """-> (operand, extra instructions) for a command value; persons resolved (ambiguity is an error), scalars ensured; a new person named twice in one
    program is created once (`created` = registers already emitted)"""
    cls = VCLASS[rel]; created = created if created is not None else set()
    if cls == "PERSON":
        kind, oid = RS.resolve_person(store, surface)
        if kind == "EXISTING": return oid, []
        r = f"$new_{surface}"
        if r in created: return r, []
        created.add(r); return r, [("CREATE", "PERSON", r), ("ADD_ALIAS", r, surface)]
    vid, norm = RS.scalar_id(cls, surface); return vid, [("ENSURE_VALUE", vid, cls, norm, surface)]


def compile_assertion(resolved):
    ir, B = resolved["ir"], resolved["binds"]; prog = []; op = {}
    for o in ir["objects"]:
        b = B[o["local_id"]]; lid = o["local_id"]
        if b["kind"] == "NEW_EVENT": prog.append(("CREATE", b["type"], f"${lid}")); op[lid] = f"${lid}"
    for o in ir["objects"]:
        b = B[o["local_id"]]; lid = o["local_id"]
        if b["kind"] == "NEW_PERSON": prog += [("CREATE", "PERSON", f"${lid}"), ("ADD_ALIAS", f"${lid}", b["alias"])]; op[lid] = f"${lid}"
        elif b["kind"] == "EXISTING": op[lid] = b["id"]
        elif b["kind"] == "SCALAR": prog.append(("ENSURE_VALUE", b["id"], b["type"], b["norm"], b["surface"])); op[lid] = b["id"]
    for r in ir["relations"]: prog.append(("ASSERT", op[r["subject"]], r["predicate"], op[r["object"]]))
    return prog


def compile_command(cmd, store):
    if cmd["op"] == "QUERY":
        where = []
        for scope, rel, val in cmd["where"]:
            if VCLASS[rel] == "PERSON":
                hits = store.persons_with_alias(val)
                if len(hits) >= 2: raise RS.ResolveError("RESOLUTION_AMBIGUOUS", f"'{val}' matches {len(hits)} people")
                where.append([scope, rel, hits[0] if hits else f"person:?{val}"])
            else: where.append([scope, rel, RS.scalar_id(VCLASS[rel], val)[0]])
        tgt = cmd["target"]; tgt = RS.resolve_ref(store, tgt) if tgt.startswith("LAST_") else tgt
        return [("MATCH", {"target": tgt, "rel": cmd["rel"], "where": where}), ("RETURN", "VALUES")]
    if cmd["op"] == "NEW_PERSON": return [("CREATE", "PERSON", "$p"), ("ADD_ALIAS", "$p", cmd["alias"])]
    oid = RS.resolve_ref(store, cmd["ref"]); prog = []
    if cmd["op"] == "UPDATE":
        created = set()
        for rel, val in cmd["set"]:
            for s, p, o in store.rels(oid, rel): prog.append(("RETRACT", s, p, o))
            opnd, extra = value_operand(store, rel, val, created); prog += extra + [("ASSERT", oid, rel, opnd)]
        return prog
    if cmd["op"] == "RETRACT": return [("RETRACT", s, p, o) for s, p, o in store.rels(oid, cmd["rel"])]
    if cmd["op"] == "DELETE": return [("DELETE", oid)]
    raise VMError("COMPILE", f"cannot compile {cmd}")


# ---------------- executor ----------------
def _check_postconditions(store):
    """every active relation: live endpoints, legal typed signature (frozen matrix), no duplicate, at most one value per (event, relation)"""
    seen = set(); fun = set()
    for s, p, o in store.rels():
        so = store.object(s)
        if not so or so["status"] != "active": raise VMError("VM_EXEC_ERROR", f"relation on inactive subject {s}")
        if (s, p, o) in seen: raise VMError("VM_EXEC_ERROR", f"duplicate relation {(s, p, o)}")
        seen.add((s, p, o))
        if p == "TODO":
            oo = store.object(o)
            if not (so["type"] in K.OUTER and oo and oo["status"] == "active" and oo["type"] in K.INNER): raise VMError("VM_EXEC_ERROR", f"illegal TODO {(s, o)}")
            continue
        if so["type"] not in EVENTS or not K.valid(p, so["type"]): raise VMError("VM_EXEC_ERROR", f"relation {p} not allowed on {so['type']}")
        if VCLASS[p] == "PERSON":
            oo = store.object(o)
            if not oo or oo["status"] != "active" or oo["type"] != "PERSON": raise VMError("VM_EXEC_ERROR", f"{p} object not an active PERSON")
        elif not store.value(o) or store.value(o)[0] != VCLASS[p]: raise VMError("VM_EXEC_ERROR", f"{p} object not a {VCLASS[p]} value")
        if (s, p) in fun: raise VMError("VM_EXEC_ERROR", f"two active {p} values on {s}")
        fun.add((s, p))


def run_query(store, pat):
    tgt = pat["target"]; cands = [tgt] if ":" in tgt else [oid for oid, _ in store.active_objects(tgt)]
    def has(x, rel, val): return any(o == val for _, _, o in store.rels(x, rel))
    out = []
    for x in cands:
        ok = True
        for scope, rel, val in pat["where"]:
            nodes = [x] if scope == "SELF" else [s for s, _, _ in store.rels(None, "TODO", x)] if scope == "PARENT" else [o for _, _, o in store.rels(x, "TODO")]
            if not any(has(n, rel, val) for n in nodes): ok = False; break
        if ok: out += [o for _, _, o in store.rels(x, pat["rel"])]
    return sorted(set(out))


def execute(store, prog, ts, utt, fail_after=None):
    """one transaction; returns (return_value, state_diff). fail_after: TEST HOOK ONLY (rollback unit test)."""
    reg = {}; diff = []; ret = None; res = lambda x: reg.get(x, x)
    store.begin()
    try:
        for k, ins in enumerate(prog):
            op = ins[0]
            if op == "CREATE": reg[ins[2]] = store.create_object(ins[1], ts, utt); diff.append(["+obj", reg[ins[2]], ins[1]])
            elif op == "ADD_ALIAS": store.add_alias(res(ins[1]), ins[2], ts); diff.append(["+alias", res(ins[1]), ins[2]])
            elif op == "ENSURE_VALUE": store.ensure_value(*ins[1:])
            elif op == "ASSERT": store.assert_rel(res(ins[1]), ins[2], res(ins[3]), ts, utt); diff.append(["+rel", res(ins[1]), ins[2], res(ins[3])])
            elif op == "RETRACT":
                if store.retract_rel(res(ins[1]), ins[2], res(ins[3])) != 1: raise VMError("VM_EXEC_ERROR", f"retract of absent relation {ins[1:]}")
                diff.append(["-rel", res(ins[1]), ins[2], res(ins[3])])
            elif op == "DELETE":
                o = store.object(ins[1])
                if not o or o["status"] != "active": raise VMError("VM_EXEC_ERROR", f"delete of inactive object {ins[1]}")
                removed = store.rels(ins[1]) + store.rels(None, None, ins[1]); store.delete_object(ins[1]); diff.append(["-obj", ins[1]]); diff += [["-rel", *r] for r in removed]
            elif op == "MATCH": ret = run_query(store, ins[1])
            elif op == "RETURN": pass
            else: raise VMError("VM_EXEC_ERROR", f"unknown instruction {op}")
            if fail_after is not None and k == fail_after: raise VMError("VM_EXEC_ERROR", "injected failure (test hook)")
        _check_postconditions(store); store.commit(); return ret, diff
    except Exception:
        store.rollback(); raise


def program_json(prog): return json.dumps(prog, separators=(",", ":"))
