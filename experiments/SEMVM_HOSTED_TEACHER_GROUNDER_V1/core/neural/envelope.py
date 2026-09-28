"""SEMVM_POC_LANGUAGE_V1 part A: controlled-assertion envelope check (Amendment 001). Deterministic, and it NEVER decides attachment:
it verifies vocabulary, the two event blocks (trigger + a coindexation marker), the modifier phrases (cue, value, re|per, a marker), and the
function-word skeleton of a supported layout. It checks only THAT a marker follows each phrase, never WHICH event that marker names.
Returns (ok, info) with info = {n_mod, layout, reason}."""
import os, sys, json, itertools
HERE = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, os.path.join(HERE, "vendor"))
import mr_config as K, mr_generate as G
LANG = json.load(open(os.path.join(os.path.dirname(HERE), "spec", "SEMVM_POC_LANGUAGE_V1.json")))["A_controlled_assertion_language"]
VOCAB = set(LANG["vocabulary"]); TRIG = {w: c for c, w in K.TRIG.items()}; MARK = set(K.MARKERS)
VALUE_CLASS = {v: cls for cls, vals in (("PERSON", K.PERSONS), ("TIME", K.TIMES), ("PLACE", K.PLACES), ("TOPIC", K.TOPICS)) for v in vals}
CUE_SEQ = sorted(((tuple(c), r) for r, c in K.CUE.items()), key=lambda x: -len(x[0]))
TRIPLES = {tuple(t) for t in LANG["supported_relation_constructor_triples"]}


def segment(toks):
    """-> list of segments: ('EV', class, pos) | ('MOD', relation, value, pos) | ('W', token); None if a phrase is malformed"""
    out = []; i = 0; n = len(toks)
    while i < n:
        t = toks[i]
        if t in TRIG and i + 1 < n and toks[i + 1] in MARK: out.append(("EV", TRIG[t], i)); i += 2; continue
        hit = None
        for cue, rel in CUE_SEQ:
            L = len(cue)
            if tuple(toks[i:i + L]) == cue and i + L + 2 < n + 0 and i + L + 2 <= n - 1:
                v, conn, m = toks[i + L], toks[i + L + 1], toks[i + L + 2]
                if VALUE_CLASS.get(v) == K.REL_VALUE[rel][0] and conn in ("re", "per") and m in MARK: hit = (rel, v, L + 3); break
        if hit: out.append(("MOD", hit[0], hit[1], i)); i += hit[2]; continue
        out.append(("W", t)); i += 1
    return out


def skeleton(segs):
    return tuple("{O}" if s[0] == "EV" and s[1] in K.OUTER else "{I}" if s[0] == "EV" else "M" if s[0] == "MOD" else s[1] for s in segs)


def _layout_skeletons():
    sk = {}
    for n_key, lays in (("1_modifier", LANG["supported_layouts"]["1_modifier"]), ("2_modifier", LANG["supported_layouts"]["2_modifier"])):
        for frame, slots in lays:
            mods = [{"rel": "WHO", "cls": "PERSON", "value": "Alice", "attach": "outer", "fmt": "fa"}, {"rel": "WHEN", "cls": "TIME", "value": "5", "attach": "outer", "fmt": "fa"}][:len(slots)]
            it = G.render(frame, "REMINDER", "CALL", "alpha", "beta", mods, list(slots)); sk[skeleton(segment(it["tokens"]))] = (frame, tuple(slots))
    return sk


SKELETONS = _layout_skeletons()


def check(toks):
    oov = [t for t in toks if t not in VOCAB]
    if oov: return False, {"reason": "UNKNOWN_VOCABULARY", "oov": oov}
    segs = segment(toks); evs = [s for s in segs if s[0] == "EV"]; mods = [s for s in segs if s[0] == "MOD"]
    if len(evs) != 2 or sum(e[1] in K.OUTER for e in evs) != 1: return False, {"reason": "EVENT_STRUCTURE", "events": [e[1] for e in evs]}
    if not 1 <= len(mods) <= 2: return False, {"reason": "MODIFIER_COUNT", "n_mod": len(mods)}
    lay = SKELETONS.get(skeleton(segs))
    if lay is None: return False, {"reason": "LAYOUT_OUTSIDE_ENVELOPE"}
    O = next(e[1] for e in evs if e[1] in K.OUTER); I = next(e[1] for e in evs if e[1] in K.INNER)
    if len({m[1] for m in mods}) != len(mods): return False, {"reason": "DUPLICATE_RELATION"}
    for m in mods:
        if (m[1], O, I) not in TRIPLES: return False, {"reason": "RELATION_CONSTRUCTOR_OUTSIDE_ENVELOPE", "triple": [m[1], O, I]}
    return True, {"n_mod": len(mods), "layout": [lay[0], list(lay[1])], "outer": O, "inner": I}
