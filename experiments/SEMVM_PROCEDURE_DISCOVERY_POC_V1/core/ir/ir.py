"""Canonical semantic IR (spec §5-§6). Typed, explicit, serializable, independent of neural hidden state.
IR = {"objects": [{"local_id", "type", "surface"?}], "relations": [{"predicate", "subject", "object"}]}
Canonical local ids: e0 = the OUTER event, e1 = the INNER event, v0.. = value objects sorted by (type, surface). Canonical order: objects by id,
relations by (predicate, subject, object). Conversion from a semantic graph (occurrences + edges) never reads token positions beyond identity."""
import os, sys, json
HERE = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "neural", "vendor"))
import mr_config as K
EVENT_TYPES = K.OUTER + K.INNER; VALUE_TYPES = {"PERSON": "PERSON", "TIME": "TIME", "PLACE": "PLACE", "TOPIC": "TOPIC_VALUE"}
OBJECT_TYPES = set(EVENT_TYPES) | set(VALUE_TYPES.values()) | {"TEXT_VALUE"}
SIG = {"TODO": ("OUTER_EVENT", "INNER_EVENT"), "WHO": ("EVENT", "PERSON"), "RECIPIENT": ("EVENT", "PERSON"), "WHEN": ("EVENT", "TIME"), "WHERE": ("EVENT", "PLACE"), "TOPIC": ("EVENT", "TOPIC_VALUE")}


class IRError(Exception):
    def __init__(self, reason): super().__init__(reason); self.reason = reason


def canonical(ir):
    return {"objects": sorted(ir["objects"], key=lambda o: o["local_id"]), "relations": sorted(ir["relations"], key=lambda r: (r["predicate"], r["subject"], r["object"]))}


def dumps(ir): return json.dumps(canonical(ir), sort_keys=True, separators=(",", ":"))


def from_graph(occs, edges):
    """occs: iterable of (class, value, anchor); edges: iterable of (relation, parent_occ, child_occ). Raises IRError if the graph is not convertible."""
    occs = list(occs); ev = [o for o in occs if o[0] in EVENT_TYPES]; vals = [o for o in occs if o[0] in VALUE_TYPES]
    if len(ev) + len(vals) != len(occs): raise IRError("UNKNOWN_OBJECT_TYPE")
    outer = [o for o in ev if o[0] in K.OUTER]; inner = [o for o in ev if o[0] in K.INNER]
    if len(outer) != 1 or len(inner) != 1: raise IRError(f"EVENT_STRUCTURE outer={len(outer)} inner={len(inner)}")
    lid = {outer[0]: "e0", inner[0]: "e1"}; objs = [{"local_id": "e0", "type": outer[0][0]}, {"local_id": "e1", "type": inner[0][0]}]
    for k, o in enumerate(sorted(vals, key=lambda o: (VALUE_TYPES[o[0]], o[1], o[2]))):
        lid[o] = f"v{k}"; objs.append({"local_id": f"v{k}", "type": VALUE_TYPES[o[0]], "surface": o[1]})
    rels = []
    for r, p, c in edges:
        if p not in lid or c not in lid: raise IRError("DANGLING_EDGE")
        rels.append({"predicate": r, "subject": lid[p], "object": lid[c]})
    return canonical({"objects": objs, "relations": rels})


def from_gold_item(item):
    """gold IR of a corpus-style item {"gold": {"occs": [[cls, val, anchor]...], "edges": [[rel, p_index, c_index]...]}}"""
    occs = [tuple(o) for o in item["gold"]["occs"]]; return from_graph(occs, [(r, occs[p], occs[c]) for r, p, c in item["gold"]["edges"]])


def validate(ir):
    """deterministic IR validation (§6); raises IRError"""
    ids = [o["local_id"] for o in ir["objects"]]
    if len(ids) != len(set(ids)): raise IRError("DUPLICATE_LOCAL_ID")
    typ = {o["local_id"]: o["type"] for o in ir["objects"]}
    for o in ir["objects"]:
        if o["type"] not in OBJECT_TYPES: raise IRError(f"UNKNOWN_TYPE {o['type']}")
    evs = [i for i, t in typ.items() if t in EVENT_TYPES]
    if sorted(typ[i] in K.OUTER for i in evs) != [False, True]: raise IRError("EVENT_STRUCTURE")
    incoming = {i: 0 for i in typ}; todo = 0
    for r in ir["relations"]:
        p, s, o = r["predicate"], r["subject"], r["object"]
        if p not in SIG: raise IRError(f"UNKNOWN_RELATION {p}")
        if s not in typ or o not in typ: raise IRError("DANGLING_REFERENCE")
        a, b = SIG[p]
        if p == "TODO":
            if not (typ[s] in K.OUTER and typ[o] in K.INNER): raise IRError("SIGNATURE TODO")
            todo += 1
        else:
            if typ[s] not in EVENT_TYPES or typ[o] != b: raise IRError(f"SIGNATURE {p}")
            if not K.valid(p, typ[s]): raise IRError(f"CONSTRUCTOR_NOT_ALLOWED {p}|{typ[s]}")
        incoming[o] += 1
    if todo != 1: raise IRError("TODO_COUNT")
    for i, t in typ.items():
        if t not in EVENT_TYPES and incoming[i] != 1: raise IRError(f"VALUE_NOT_ATTACHED_ONCE {i}")
    seen = set()
    for r in ir["relations"]:
        k = (r["subject"], r["predicate"])
        if r["predicate"] != "TODO" and k in seen: raise IRError(f"DUPLICATE_RELATION_ON_EVENT {k}")
        seen.add(k)
    return True
