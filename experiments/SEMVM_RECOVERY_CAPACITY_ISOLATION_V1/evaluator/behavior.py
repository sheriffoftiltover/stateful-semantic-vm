"""HTG behavioural equivalence (spec §24-§28, §66; spec/BEHAVIORAL_EQUIVALENCE_V1.json). Evaluator-side only: never imported by the student.
One deterministic function behavior_signature(program, world) over the INDEPENDENT oracle interpreter (scenarios/oracle.py, not the student
runtime). A demonstration starts from the scenario fixture state (acquisition is sandboxed), so the registered equivalence world set is:
  W0 fixture | W1 all events OPEN | W2 every status flipped | W3 fixture + relation witnesses | W4 = W3 with statuses flipped
W3 adds, for every PERSON / TOPIC / PLACE value of the scenario's pools, events whose ONLY link to the value is a sibling relation (an EMAIL /
CALL / MESSAGE / REQUEST with WHO=p, with RECIPIENT=p, a CALL / EMAIL about t, a CALL / EMAIL / REQUEST at pl), half of them CLOSED, so dropped
or added status filters, wrong relations, wrong constants and wrong scopes change the signature. Signature = (status, rendered return, full
canonical world state after the program)."""
import os, sys, json, copy
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, "scenarios"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "core", "neural", "vendor")]
import oracle as OR, nl_generate as NG, lang as L
VARIANTS = ["W0_FIXTURE", "W1_ALL_OPEN", "W2_STATUS_FLIPPED", "W3_RELATION_WITNESSES", "W4_WITNESSES_FLIPPED"]


def _base(sc):
    W = OR.World(NG.VOCAB); env = {}
    for t in sc["fixture"]:
        if t["kind"] == "ASSERT": W.assertion(t["facts"])
        else: W.run_step_text(t["text"], env, {})
    return W


def _events(W): return [o for o, v in W.obj.items() if v[0] in L.EVENT_TYPES and v[1] == "active"]


def _set_all(W, st):
    for o in _events(W): W.attr[(o, "STATUS")] = st


def _flip(W):
    for o in _events(W): W.attr[(o, "STATUS")] = "CLOSED" if W.status_of(o) == "OPEN" else "OPEN"


def _witnesses(W, sc):
    pools = {k: list(dict.fromkeys((sc["teacher_pool"].get(k) or []) + (sc["eval_pool"].get(k) or []))) for k in ("people", "topics", "places")}
    facts = []
    for p in pools["people"]:
        facts += [{"outer": "REMINDER", "inner": "EMAIL", "mods": [("WHO", p, "inner")]}, {"outer": "REMINDER", "inner": "CALL", "mods": [("RECIPIENT", p, "inner")]},
                  {"outer": "REQUEST", "inner": "MESSAGE", "mods": [("RECIPIENT", p, "outer")]}, {"outer": "REQUEST", "inner": "MESSAGE", "mods": [("WHO", p, "inner")]}]
    for t in pools["topics"]: facts += [{"outer": "REMINDER", "inner": "CALL", "mods": [("TOPIC", t, "inner")]}]
    for pl in pools["places"]: facts += [{"outer": "REQUEST", "inner": "EMAIL", "mods": [("WHERE", pl, "inner")]}, {"outer": "REMINDER", "inner": "CALL", "mods": [("WHERE", pl, "inner")]}]
    for k, f in enumerate(facts):
        n0 = set(W.obj); W.assertion(f); new = sorted(set(W.obj) - n0)
        if k % 2:
            for o in new:
                if W.obj[o][0] in L.EVENT_TYPES: W.attr[(o, "STATUS")] = "CLOSED"
    return W


def worlds(sc):
    """-> {name: oracle World} (fresh deep copies; the caller may mutate them)"""
    b = _base(sc); out = {}
    for name in VARIANTS:
        W = copy.deepcopy(b)
        if name in ("W3_RELATION_WITNESSES", "W4_WITNESSES_FLIPPED"): _witnesses(W, sc)
        if name == "W1_ALL_OPEN": _set_all(W, "OPEN")
        if name in ("W2_STATUS_FLIPPED", "W4_WITNESSES_FLIPPED"): _flip(W)
        out[name] = W
    return out


def behavior_signature(program, W, lib=None):
    """program = list of parent step ASTs (a demonstration's executed steps, or a reference) -> canonical signature on a COPY of W"""
    W = copy.deepcopy(W); env = {}
    try: st, ret = NG.run_steps(W, copy.deepcopy(program), env, lib or {})
    except Exception as e: st, ret = "EVAL_ERROR:" + type(e).__name__, None
    return json.dumps({"status": st, "return": ret, "state": W.state()}, sort_keys=True)


def state_only(program, W, lib=None):
    return json.loads(behavior_signature(program, W, lib))["state"]


def behaviorally_equivalent(P, G, Ws, lib=None):
    """P, G step lists; Ws = worlds(sc). -> (bool, first differing variant or None)"""
    for name, W in Ws.items():
        if behavior_signature(P, W, lib) != behavior_signature(G, W, lib): return False, name
    return True, None


def prefix_equivalent(P, G, Ws, lib=None):
    """an INCOMPLETE demonstration (no RETURN): its world effect must equal the effect of some prefix of the reference on every variant"""
    for name, W in Ws.items():
        s = state_only(P, W, lib)
        if not any(s == state_only(G[:k], W, lib) for k in range(len(G) + 1)): return False, name
    return True, None


def gold_lib(sc, upto_name):
    """gold procedures of the curriculum items BEFORE upto_name (what a demonstration's CALLs mean)"""
    lib = {}
    for it in sc["curriculum"]:
        if it["name"] == upto_name: break
        lib[it["name"]] = L.parse_procedure(it["gold"])
    return lib


def reference_steps(sc, it, example):
    """the registered intended demonstration for the given example values (gold family steps)"""
    import pdx_generate as PG
    ps = it["sig"]
    example = example or {}
    if not all(p in example for p in ps): return None                  # (parameterless families have an empty example; ENGINEERING_LOG #6)
    return [s for _, s in PG.family_steps(it["family"], {p: example[p] for p in ps})]


def find_relations(steps):
    """(type, scope.relation) of every FIND / FILTER constraint (relation-binding diagnostic, spec §32)"""
    out = []
    for s in steps:
        if s["op"] == "FIND": out += [(s["type"]["const"], f"{sc}.{r}") for sc, r, _ in s["where"]]
        if s["op"] == "FILTER": out.append(("FILTER", s["rel"]))
    return sorted(out)


def status_constraints(steps): return sorted((s["type"]["const"], (s.get("status") or {}).get("const")) for s in steps if s["op"] == "FIND")
