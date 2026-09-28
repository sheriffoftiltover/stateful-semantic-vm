"""Deterministic resolver (spec §8-§11, Amendment 001).
Entities (PERSON): exact normalized alias -> 0 matches: new entity (allowed); 1: reuse; >= 2: RESOLUTION_AMBIGUOUS (never an arbitrary choice).
Scalars: TIME normalized (digits -> HH:MM clock; noon / midnight / dawn / dusk -> NAMED); PLACE / TOPIC lowercase; natural-key ids.
Events in assertions: always new objects. References: LAST_<EVENT_TYPE> = most recently created active event of that type; none -> RESOLVE_REFERENCE."""
import re


class ResolveError(Exception):
    def __init__(self, status, reason): super().__init__(reason); self.status = status; self.reason = reason


def norm_time(s):
    if s in ("noon", "midnight", "dawn", "dusk"): return s.upper()
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", s)
    if not m: raise ResolveError("RESOLVE_TIME", f"unsupported time {s!r}")
    return f"{int(m.group(1)):02d}:{m.group(2) or '00'}"


def scalar_id(vtype, surface):
    norm = norm_time(surface) if vtype == "TIME" else surface.lower(); return f"{vtype.lower()}:{norm}", norm


def resolve_person(store, surface):
    """-> (decision, object_id or None)"""
    hits = store.persons_with_alias(surface)
    if len(hits) >= 2: raise ResolveError("RESOLUTION_AMBIGUOUS", f"'{surface}' matches {len(hits)} people: {hits}")
    return ("EXISTING", hits[0]) if hits else ("NEW", None)


def resolve_assertion(ir, store):
    """validated IR -> resolved IR {local_id: binding} + decisions"""
    binds, dec = {}, []
    for o in ir["objects"]:
        t, lid = o["type"], o["local_id"]
        if lid.startswith("e"): binds[lid] = {"kind": "NEW_EVENT", "type": t}; dec.append(["EVENT", lid, "NEW"])
        elif t == "PERSON":
            kind, oid = resolve_person(store, o["surface"])
            binds[lid] = {"kind": "EXISTING", "id": oid} if kind == "EXISTING" else {"kind": "NEW_PERSON", "alias": o["surface"]}
            dec.append(["ENTITY", lid, o["surface"], kind, oid])
        else:
            vt = {"TIME": "TIME", "PLACE": "PLACE", "TOPIC_VALUE": "TOPIC"}[t]; vid, norm = scalar_id(vt, o["surface"])
            binds[lid] = {"kind": "SCALAR", "id": vid, "type": vt, "norm": norm, "surface": o["surface"]}; dec.append(["TIME" if vt == "TIME" else "SCALAR", lid, o["surface"], vid])
    return {"ir": ir, "binds": binds}, dec


def resolve_ref(store, ref):
    if not ref.startswith("LAST_"): raise ResolveError("RESOLVE_REFERENCE", f"unsupported reference {ref}")
    oid = store.last_active(ref[5:])
    if oid is None: raise ResolveError("RESOLVE_REFERENCE", f"no active {ref[5:]} to refer to")
    return oid
