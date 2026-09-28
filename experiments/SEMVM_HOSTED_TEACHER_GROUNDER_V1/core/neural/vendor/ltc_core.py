"""SEMVM_LATENT_TYPED_COMPOSITION_SYMBOLIC_V1 — core: ontology, executor (APPLY / EXEC), canonical serialization, audit scores, toy corpus,
surface primitive candidates, fragment templates + instances, and the TRAIN-only fragment enumerator. Pure Python, no learning.
Occurrence identity = (constructor, payload, trigger token index); edges = (role, parent_occ, child_occ)."""
import hashlib, itertools, json
from typing import NamedTuple
TYPES = {"REMINDER": "V", "CALL": "V", "PLAN": "V", "PERSON": "E", "TIME": "T"}
SIG = {"TODO": ("V", "V"), "WHO": ("V", "E"), "WHEN": ("V", "T")}
ROLES = sorted(SIG)
LEX = {"remind": ("REMINDER", None), "call": ("CALL", None), "plan": ("PLAN", None), "Mom": ("PERSON", "Mom"), "Dad": ("PERSON", "Dad"), "8": ("TIME", "8"), "noon": ("TIME", "noon")}
PAYLOAD_CLASSES = {"PERSON", "TIME"}
K = 3
def typ(o): return TYPES[o[0]]
def ser_occ(o): return f"{o[0]}({o[1]})@{o[2]}" if o[1] is not None else f"{o[0]}@{o[2]}"
def ser_edge(e): return f"{e[0]}|{ser_occ(e[1])}|{ser_occ(e[2])}"
def edge_key(e): return (e[0], ser_occ(e[1]), ser_occ(e[2]))
class Obj(NamedTuple):
    occs: frozenset
    edges: frozenset
    root: tuple
def ser_graph(g): return "ROOT=" + ser_occ(g.root) + ";OCC=" + ",".join(sorted(map(ser_occ, g.occs))) + ";E=" + ",".join(sorted(map(ser_edge, g.edges)))
def out_key(g): return (g.occs, g.edges, g.root)
class IllegalApply(Exception): pass
def apply(r, P, C):
    """APPLY(r, P, C): legal iff sig(r) = (type(root P), type(root C)), disjoint occurrences, new edge absent. Deterministic."""
    if r not in SIG: raise IllegalApply("unknown role")
    if SIG[r] != (typ(P.root), typ(C.root)): raise IllegalApply("type")
    if P.occs & C.occs: raise IllegalApply("duplicate occurrence")
    e = (r, P.root, C.root)
    if e in P.edges or e in C.edges: raise IllegalApply("duplicate edge")
    return Obj(P.occs | C.occs, P.edges | C.edges | {e}, P.root)
def audit_score(s):
    """SHA256(canonical serialization) -> first 13 hex digits as an integer u in [0, 16^13) -> 0.2 * u / 16^13 - 0.1 in [-0.1, 0.1)"""
    return 0.2 * int(hashlib.sha256(s.encode()).hexdigest()[:13], 16) / 16 ** 13 - 0.1
# ---------------- toy corpus ----------------
def _g(occs, edges, root): return {"occs": occs, "edges": edges, "root": root}
CORPUS = [
    {"id": "T1", "split": "TRAIN", "surface": "call Mom", "gold": _g([["CALL", None, 0], ["PERSON", "Mom", 1]], [["WHO", 0, 1]], 0)},
    {"id": "T2", "split": "TRAIN", "surface": "call at 8", "gold": _g([["CALL", None, 0], ["TIME", "8", 2]], [["WHEN", 0, 1]], 0)},
    {"id": "T3", "split": "TRAIN", "surface": "remind to call", "gold": _g([["REMINDER", None, 0], ["CALL", None, 2]], [["TODO", 0, 1]], 0)},
    {"id": "T4", "split": "TRAIN", "surface": "remind Mom to call", "gold": _g([["REMINDER", None, 0], ["PERSON", "Mom", 1], ["CALL", None, 3]], [["TODO", 0, 2], ["WHO", 2, 1]], 0)},
    {"id": "T5", "split": "TRAIN", "surface": "call Mom at 8", "gold": _g([["CALL", None, 0], ["PERSON", "Mom", 1], ["TIME", "8", 3]], [["WHO", 0, 1], ["WHEN", 0, 2]], 0)},
    {"id": "T6", "split": "TRAIN", "surface": "at 8 plan for Mom to call", "gold": _g([["TIME", "8", 1], ["PLAN", None, 2], ["PERSON", "Mom", 4], ["CALL", None, 6]], [["WHEN", 1, 0], ["TODO", 1, 3], ["WHO", 3, 2]], 1)},
    {"id": "T7", "split": "TRAIN", "surface": "call at noon", "gold": _g([["CALL", None, 0], ["TIME", "noon", 2]], [["WHEN", 0, 1]], 0)},
    {"id": "G", "split": "TEST", "surface": "remind Mom to call at 8", "gold": _g([["REMINDER", None, 0], ["PERSON", "Mom", 1], ["CALL", None, 3], ["TIME", "8", 5]], [["TODO", 0, 2], ["WHO", 2, 1], ["WHEN", 2, 3]], 0)},
    {"id": "L", "split": "TEST", "surface": "at 8 remind Mom to call", "gold": _g([["TIME", "8", 1], ["REMINDER", None, 2], ["PERSON", "Mom", 3], ["CALL", None, 5]], [["WHEN", 1, 0], ["TODO", 1, 3], ["WHO", 3, 2]], 1)},
    {"id": "LG", "split": "TEST", "surface": "at 8 remind Mom to call at noon", "gold": _g([["TIME", "8", 1], ["REMINDER", None, 2], ["PERSON", "Mom", 3], ["CALL", None, 5], ["TIME", "noon", 7]], [["WHEN", 1, 0], ["TODO", 1, 3], ["WHO", 3, 2], ["WHEN", 3, 4]], 1)}]
def gold_obj(item):
    g = item["gold"]; occs = [tuple(o) for o in g["occs"]]
    return Obj(frozenset(occs), frozenset((r, occs[p], occs[c]) for r, p, c in g["edges"]), occs[g["root"]])
def tokens(item): return item["surface"].split()
def prim_candidates(toks):
    """surface cue -> semantic primitive only (no roles / parents / valency); one occurrence per trigger token"""
    return [(LEX[t][0], LEX[t][1], i) for i, t in enumerate(toks) if t in LEX]
def align_spans(i, n):
    return [(a, a + L) for L in range(1, K + 1) for a in range(i - L + 1, i + 1) if a >= 0 and a + L <= n]
# ---------------- fragment templates ----------------
def node_class(o): return (o[0], "*" if o[0] in PAYLOAD_CLASSES else None)
def canon_template(classes, edges, root):
    """classes: list of (constructor, '*'|None); edges: list of (role, i, j); root: index -> canonical (min over node permutations) template tuple"""
    best = None; m = len(classes)
    for perm in itertools.permutations(range(m)):
        inv = {old: new for new, old in enumerate(perm)}
        t = (tuple(classes[old] for old in perm), tuple(sorted((r, inv[i], inv[j]) for r, i, j in edges)), inv[root])
        s = json.dumps(t)
        if best is None or s < best[0]: best = (s, t)
    return best[1]
def tid(t): return json.dumps(t, separators=(",", ":"))
def enumerate_fragments(graph):
    """TRAIN fragment enumerator: reads ONLY its argument (one gold graph). Every connected sub-graph with 1..3 occurrences, every contained node as the
    designated interface root, payload leaves canonicalized to CLASS(*). Returns a set of canonical templates."""
    occs = sorted(graph.occs, key=ser_occ); out = set()
    for m in (1, 2, 3):
        for sub in itertools.combinations(occs, m):
            S = set(sub); es = [e for e in graph.edges if e[1] in S and e[2] in S]
            adj = {o: set() for o in sub}
            for e in es: adj[e[1]].add(e[2]); adj[e[2]].add(e[1])
            seen = {sub[0]}; st = [sub[0]]
            while st:
                x = st.pop()
                for y in adj[x]:
                    if y not in seen: seen.add(y); st.append(y)
            if len(seen) != m: continue
            ix = {o: k for k, o in enumerate(sub)}
            for root in sub: out.add(canon_template([node_class(o) for o in sub], [(e[0], ix[e[1]], ix[e[2]]) for e in es], ix[root]))
    return out
def primitive_templates(): return {canon_template([(c, "*" if c in PAYLOAD_CLASSES else None)], [], 0) for c in sorted(TYPES)}
def instances(toks, templates):
    """ground every template to distinct surface primitives (matching constructor class), each member aligned to a K-envelope span containing its trigger,
    member spans pairwise non-overlapping; instance hull = [min start, max end); hull tokens outside member spans are SKIPPED. Never reads gold."""
    cands = prim_candidates(toks); n = len(toks); out = {}
    for t in sorted(templates, key=tid):
        classes, edges, root = t
        pools = [[o for o in cands if node_class(o) == cl] for cl in classes]
        for g in itertools.product(*pools):
            if len(set(g)) != len(g): continue
            for spans in itertools.product(*[align_spans(o[2], n) for o in g]):
                ss = sorted(spans)
                if any(ss[k][1] > ss[k + 1][0] for k in range(len(ss) - 1)): continue
                ie = frozenset((r, g[i], g[j]) for r, i, j in edges); obj = Obj(frozenset(g), ie, g[root])
                key = (tid(t), frozenset(zip(map(ser_occ, g), spans)), ie, g[root])
                if key in out: continue
                gs = ",".join(f"{ser_occ(o)}:{s[0]}-{s[1]}" for o, s in sorted(zip(g, spans), key=lambda x: ser_occ(x[0])))
                rootfrag = tid(t) + "|" + ",".join(sorted(map(ser_occ, g))) + "|root=" + ser_occ(g[root])
                ser = "F[" + tid(t) + "|" + gs + "|root=" + ser_occ(g[root]) + "]"
                out[key] = {"tid": tid(t), "size": len(g), "grounding": g, "spans": spans, "hull": (min(s[0] for s in spans), max(s[1] for s in spans)), "obj": obj,
                            "rootfrag": rootfrag, "ser": ser, "score": audit_score(ser)}
    return sorted(out.values(), key=lambda x: x["ser"])
def comp_score(r, rootfrag_p, rootfrag_c):
    """local composition factor: depends only on (parent root fragment, role, child root fragment) — never on other attached edges"""
    return audit_score("APPLY|" + r + "|" + rootfrag_p + "|" + rootfrag_c)
