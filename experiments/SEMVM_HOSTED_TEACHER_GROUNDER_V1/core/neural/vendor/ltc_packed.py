"""Packed hypergraph (unrestricted), inside / Viterbi / output marginals, and the gold-compatibility RESTRICTION of the SAME hypergraph.
Chart items combine iff their surface hulls are disjoint (tokens between them are SKIPPED, score 0). A packed node's key =
(hull, occurrence set, edge set, root, root fragment, canonical-order state). Canonical APPLY order: for each head, attachments on the SAME side are
forced near->far by the hulls; when a left and a right attachment commute, the smaller edge key (role, parent_occ, child_occ) must come first —
implemented as the order state (last side, max key of the current same-side run): switching sides requires new key > run max."""
import math, collections, time
import ltc_core as C
def lse(xs):
    xs = list(xs)
    if not xs: return -math.inf
    m = max(xs); return m + math.log(sum(math.exp(x - m) for x in xs)) if m > -math.inf else -math.inf
class Node:
    __slots__ = ("key", "hull", "obj", "rootfrag", "ostate", "leaves", "hedges")
    def __init__(s, key, hull, obj, rootfrag, ostate): s.key, s.hull, s.obj, s.rootfrag, s.ostate, s.leaves, s.hedges = key, hull, obj, rootfrag, ostate, [], []
def build(toks, insts, ceiling=None):
    t0 = time.time(); N = {}; byhull = collections.defaultdict(list); n = len(toks); nh = 0
    def get(hull, obj, rootfrag, ostate):
        k = (hull, obj.occs, obj.edges, obj.root, rootfrag, ostate)
        if k not in N: N[k] = Node(k, hull, obj, rootfrag, ostate); byhull[hull].append(k)
        return N[k]
    for ins in insts: get(ins["hull"], ins["obj"], ins["rootfrag"], None).leaves.append(ins)
    for L in range(2, n + 1):
        for i in range(0, n - L + 1):
            l = i + L; new = []
            for j in range(i + 1, l):
                for k in range(j, l):
                    for a in list(byhull.get((i, j), ())):
                        for b in list(byhull.get((k, l), ())):
                            A, B = N[a], N[b]
                            for P, Cn, side in ((A, B, "R"), (B, A, "L")):
                                for r in C.ROLES:
                                    try: obj = C.apply(r, P.obj, Cn.obj)
                                    except C.IllegalApply: continue
                                    ek = C.edge_key((r, P.obj.root, Cn.obj.root))
                                    if P.ostate is None or P.ostate[0] == side: os = (side, ek if P.ostate is None else max(P.ostate[1], ek))
                                    elif ek > P.ostate[1]: os = (side, ek)
                                    else: continue
                                    new.append(((i, l), obj, P.rootfrag, os, (r, P.key, Cn.key, C.comp_score(r, P.rootfrag, Cn.rootfrag))))
            for hull, obj, rf, os, he in new: get(hull, obj, rf, os).hedges.append(he); nh += 1
            if ceiling and (len(N) > ceiling[0] or nh > ceiling[1] or time.time() - t0 > ceiling[2]): raise RuntimeError("FOREST_INTRACTABLE")
    return {"nodes": N, "n_nodes": len(N), "n_hedges": nh, "build_s": time.time() - t0}
def order(F): return sorted(F["nodes"].values(), key=lambda x: (x.hull[1] - x.hull[0], x.key[0]))
def inside(F, keep=None):
    t0 = time.time(); a = {}; cnt = {}
    for nd in order(F):
        if keep is not None and nd.key not in keep: continue
        c = [ins["score"] for ins in nd.leaves]; k = len(nd.leaves)
        for r, p, ch, s in nd.hedges:
            if p in a and ch in a: c.append(a[p] + a[ch] + s); k += cnt[p] * cnt[ch]
        if c: a[nd.key] = lse(c); cnt[nd.key] = k
    return a, cnt, time.time() - t0
def viterbi(F, keep=None):
    t0 = time.time(); v = {}
    for nd in order(F):
        if keep is not None and nd.key not in keep: continue
        best = None
        for ins in nd.leaves:
            c = (ins["score"], ins["ser"])
            if best is None or c[0] > best[0] or (c[0] == best[0] and c[1] < best[1]): best = c
        for r, p, ch, s in nd.hedges:
            if p in v and ch in v:
                c = (v[p][0] + v[ch][0] + s, "A(" + r + "," + v[p][1] + "," + v[ch][1] + ")")
                if best is None or c[0] > best[0] or (c[0] == best[0] and c[1] < best[1]): best = c
        if best: v[nd.key] = best
    return v, time.time() - t0
def outputs(F, a):
    """complete derivations = every packed node (tokens outside its hull are SKIPPED); mass grouped by exact executed output"""
    by = collections.defaultdict(list)
    for k, x in a.items(): by[C.out_key(F["nodes"][k].obj)].append(x)
    return {y: lse(v) for y, v in by.items()}
def compatible(obj, gold):
    """partial gold compatibility: occurrences map (by identity) into gold occurrences, edges subset, connected, root is a gold occurrence"""
    if not obj.occs <= gold.occs or not obj.edges <= gold.edges or obj.root not in gold.occs: return False
    adj = collections.defaultdict(set)
    for _, p, c in obj.edges: adj[p].add(c); adj[c].add(p)
    s = next(iter(obj.occs)); seen = {s}; st = [s]
    while st:
        x = st.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    return len(seen) == len(obj.occs)
def restrict(F, gold):
    return {k for k, nd in F["nodes"].items() if compatible(nd.obj, gold)}
def enumerate_derivations(F, key, keep=None, cap=200000):
    """explicit derivations packed into a node (for factorization auditing): list of (ser, score, instances, apply_edges)"""
    memo = {}
    def rec(k):
        if k in memo: return memo[k]
        nd = F["nodes"][k]; out = [(ins["ser"], ins["score"], (ins,), (), ins["obj"]) for ins in nd.leaves]
        for r, p, ch, s in nd.hedges:
            if keep is not None and (p not in keep or ch not in keep): continue
            for dp in rec(p):
                for dc in rec(ch):
                    out.append(("A(" + r + "," + dp[0] + "," + dc[0] + ")", dp[1] + dc[1] + s, dp[2] + dc[2], dp[3] + dc[3] + ((r, dp[4].root, dc[4].root),), C.apply(r, dp[4], dc[4])))
                    if len(out) > cap: raise RuntimeError("enumeration cap")
        memo[k] = out; return out
    return rec(key)
