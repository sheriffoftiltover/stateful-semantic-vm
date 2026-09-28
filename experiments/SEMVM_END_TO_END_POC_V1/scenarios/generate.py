"""Scenario suites (spec §19-§21, Amendment 001). Assertions: NEW instances rendered by the locked generator (mr_generate.render) inside the
registered envelope (P0 1-modifier layouts / P2 straddle_o 2-modifier layouts, fa|fb, supported triples); every surface is checked against the
P0/P2 corpora (all splits) and rejected if it occurs there. Commands: SEMVM_CMD_V1. Expected outcomes (status, query result, full canonical state
after every turn) come from the independent oracle (scenarios/oracle.py), never from the runtime.
Usage: python scenarios/generate.py --suite dev|locked_test --source <parent-binding experiment dir>"""
import os, sys, json, random, argparse, hashlib, glob
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
for d in ("neural", "neural/vendor", "ir"): sys.path.insert(0, os.path.join(ROOT, d))
sys.path.insert(0, HERE)
import mr_config as K, mr_generate as G, ir as IR, envelope as EV, oracle as OR
LANG = json.load(open(os.path.join(ROOT, "spec", "SEMVM_POC_LANGUAGE_V1.json")))["A_controlled_assertion_language"]
L1 = [(f, tuple(s)) for f, s in LANG["supported_layouts"]["1_modifier"]]; L2 = [(f, tuple(s)) for f, s in LANG["supported_layouts"]["2_modifier"]]
TRI = [tuple(t) for t in LANG["supported_relation_constructor_triples"]]
VALS = {"PERSON": K.PERSONS, "TIME": K.TIMES, "PLACE": K.PLACES, "TOPIC": K.TOPICS}
SEEDS = {"dev": "SEMVM-POC-V1-DEV-20260926", "locked_test": "SEMVM-POC-V1-LOCKED-20260926"}
PLAN = {"dev": {"S1": 3, "S2": 3, "S3": 3, "S4": 3, "S5": 2, "S6": 2, "S7": 3, "S8": 2, "S9": 2, "S10": 2, "S11": 2, "S12": 2, "ROLLBACK": 1},
        "locked_test": {"S1": 2, "S2": 2, "S3": 2, "S4": 2, "S5": 1, "S6": 1, "S7": 2, "S8": 1, "S9": 2, "S10": 1, "S11": 1, "S12": 2, "ROLLBACK": 1}}


class Gen:
    def __init__(self, rng, forbidden): self.rng = rng; self.forbidden = forbidden; self.used = set()

    def assertion(self, pattern, rels=None, O=None, I=None, values=None):
        """pattern: 'O' | 'I' (1 modifier) or 'OO' | 'II' | 'OI' | 'IO' (2 modifiers, slot order); returns an ASSERT turn with gold IR + facts"""
        rng = self.rng
        for _ in range(10000):
            n = len(pattern)
            if n == 1:
                cand = [t for t in TRI if (not rels or t[0] == rels[0]) and (not O or t[1] == O) and (not I or t[2] == I)]; r, o, i = rng.choice(cand); rr = [r]; frame, slots = rng.choice(L1)
            else:
                pairs = sorted({(t[1], t[2]) for t in TRI if (not O or t[1] == O) and (not I or t[2] == I)})
                pairs = [p for p in pairs if len({t[0] for t in TRI if t[1:] == p}) >= 2 and (not rels or all((x, *p) in TRI for x in rels))]
                o, i = rng.choice(pairs); rr = list(rels) if rels else rng.sample(sorted({t[0] for t in TRI if t[1:] == (o, i)}), 2); frame, slots = rng.choice(L2)
            mo, mi = rng.sample(K.MARKERS, 2); avoid = set(); mods = []
            for k, rel in enumerate(rr):
                cls = K.REL_VALUE[rel][0]
                v = (values or {}).get(rel) or rng.choice([x for x in VALS[cls] if (cls, x) not in avoid]); avoid.add((cls, v))
                mods.append({"rel": rel, "cls": cls, "value": v, "attach": "outer" if pattern[k] == "O" else "inner", "fmt": rng.choice(K.TRAIN_FORMATS)})
            it = G.render(frame, o, i, mo, mi, mods, list(slots))
            if it["surface"] in self.forbidden or it["surface"] in self.used or not G.derivable(it): continue
            ok, info = EV.check(it["tokens"]); assert ok, (info, it["surface"])
            self.used.add(it["surface"])
            facts = {"outer": o, "inner": i, "mods": [(m["rel"], m["value"], m["attach"]) for m in mods]}
            return {"kind": "ASSERT", "text": it["surface"], "gold_ir": IR.from_gold_item(it), "facts": facts, "pattern": pattern, "layout": [frame, list(slots)]}
        raise RuntimeError("could not sample an in-envelope assertion")


def C(text): return {"kind": "COMMAND", "text": text}


def fam(g, cat):
    rng = g.rng; P = lambda: rng.choice(K.PERSONS); A = g.assertion
    def qs_for(a):
        f = a["facts"]; out = []
        for r, v, at in f["mods"]:
            own, oth = (f["outer"], f["inner"]) if at == "outer" else (f["inner"], f["outer"])
            out += [C(f"QUERY {r} OF {own}"), C(f"QUERY {r} OF {oth}")]
        return out
    if cat == "S1": a = A(rng.choice("OI")); return [a] + qs_for(a)
    if cat == "S2": a = A(rng.choice(["OO", "II"])); return [a] + qs_for(a)
    if cat in ("S3", "S4"): a = A("OI" if cat == "S3" else "IO"); return [a] + qs_for(a)
    if cat == "S5":
        a = A(rng.choice(["OI", "IO"])); f = a["facts"]; (ro, vo, _), = [m for m in f["mods"] if m[2] == "outer"]; (ri, vi, _), = [m for m in f["mods"] if m[2] == "inner"]
        return [a, C(f"QUERY {ri} OF {f['inner']} WHERE PARENT.{ro}={vo}"), C(f"QUERY {ro} OF {f['outer']} WHERE CHILD.{ri}={vi}")]
    if cat == "S6":
        a = A(rng.choice(["O", "I", "OI", "IO"])); b = A(rng.choice(["O", "I", "OO", "II"])); return [a, b] + qs_for(a)
    if cat == "S7":
        a = A(rng.choice(["O", "I", "OI", "IO"])); r, v, at = a["facts"]["mods"][0]; tgt = a["facts"]["outer" if at == "outer" else "inner"]
        cls = K.REL_VALUE[r][0]; nv = rng.choice([x for x in VALS[cls] if x != v])
        return [a, C(f"UPDATE LAST_{tgt} {r}={nv}"), C(f"QUERY {r} OF {tgt}"), C(f"QUERY {r} OF LAST_{tgt}")]
    if cat == "S8":
        p = P(); rel = rng.choice(["WHO", "RECIPIENT"])
        a = A("I", rels=[rel], values={rel: p}); b = A("I", rels=[rel], values={rel: p}); return [a, b, C(f"QUERY {rel} OF {a['facts']['inner']}"), C(f"QUERY {rel} OF {b['facts']['inner']}")]
    if cat == "S9":
        I = rng.choice(["CALL", "MESSAGE"]); ps = rng.sample(K.PERSONS, 3); times = rng.sample(K.TIMES, 3); turns = []
        for p, t in zip(ps, times):     # WHEN on the outer, WHO on the inner in every turn (both orientations of the slot order)
            pat = rng.choice(["OI", "IO"]); turns.append(A(pat, rels=["WHEN", "WHO"] if pat == "OI" else ["WHO", "WHEN"], I=I, values={"WHEN": t, "WHO": p}))
        k = rng.randrange(3); return turns + [C(f"QUERY WHO OF {I} WHERE PARENT.WHEN={times[k]}"), C(f"QUERY WHO OF {I}")]
    if cat == "S10":
        p = P(); rel = rng.choice(["WHO", "RECIPIENT"]); a = A("I", rels=[rel], values={rel: rng.choice([x for x in K.PERSONS if x != p])})
        b = A("I", rels=[rel], values={rel: p})
        return [C(f"NEW PERSON {p}"), C(f"NEW PERSON {p}"), b, C(f"QUERY {rel} OF {b['facts']['inner']}"), a, C(f"QUERY {rel} OF {a['facts']['inner']}")]
    if cat == "S11":
        a = A(rng.choice(["OO", "II", "OI", "IO"])); r, v, at = a["facts"]["mods"][0]; tgt = a["facts"]["outer" if at == "outer" else "inner"]
        return [a, C(f"RETRACT LAST_{tgt} {r}"), C(f"QUERY {r} OF {tgt}"), C(f"DELETE LAST_{a['facts']['inner']}"), C(f"QUERY {a['facts']['mods'][1][0]} OF {a['facts']['inner']}")]
    if cat == "S12":
        a = A(rng.choice(["O", "I", "OI", "IO"])); r, v, at = a["facts"]["mods"][0]; tgt = a["facts"]["outer" if at == "outer" else "inner"]
        cls = K.REL_VALUE[r][0]; nv = rng.choice([x for x in VALS[cls] if x != v])
        return [a, {"kind": "RESTART"}, C(f"QUERY {r} OF {tgt}"), C(f"UPDATE LAST_{tgt} {r}={nv}"), {"kind": "RESTART"}, C(f"QUERY {r} OF {tgt}")]
    if cat == "ROLLBACK":
        a = A("I", rels=["WHO"], I="VISIT"); p = rng.choice([x for x in K.PERSONS if x != a["facts"]["mods"][0][1]])
        return [a, C(f"UPDATE LAST_VISIT WHO={p} RECIPIENT={p}"), C("QUERY WHO OF VISIT")]
    raise ValueError(cat)


def expected(turns):
    o = OR.Oracle(); exp = []
    for t in turns:
        if t["kind"] == "RESTART": exp.append(None); continue
        if t["kind"] == "ASSERT": st, res = o.assertion(t["facts"]), None
        else: st, res = o.command(t["text"])
        exp.append({"status": st, "result": res, "state": o.state()})
    return exp


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=sorted(SEEDS)); ap.add_argument("--source", default=os.path.join(ROOT, "..", "SEMVM_COINDEXATION_PARENT_BINDING_MECHANISM_V1")); a = ap.parse_args()
    forbidden = {json.loads(l)["surface"] for st in ("P0", "P2") for sp in ("train", "id_val", "id_test") for l in open(os.path.join(a.source, "data", st, "corpus", f"{sp}.jsonl"))}
    rng = random.Random(SEEDS[a.suite]); g = Gen(rng, forbidden); out = []; k = 0
    if a.suite == "locked_test":        # disjoint from DEV surfaces as well
        for p in glob.glob(os.path.join(HERE, "dev", "*.json")): g.used |= {t["text"] for t in json.load(open(p))["turns"] if t["kind"] == "ASSERT"}
    for cat, n in PLAN[a.suite].items():
        for j in range(n):
            turns = fam(g, cat); k += 1
            sc = {"scenario_id": f"{a.suite}-{k:03d}-{cat}", "suite": a.suite, "category": cat, "reference_time": f"2026-09-26T16:00:00-07:00", "turns": turns, "expected": expected(turns)}
            out.append(sc)
    d = os.path.join(HERE, a.suite); os.makedirs(d, exist_ok=True)
    for sc in out: json.dump(sc, open(os.path.join(d, f"{sc['scenario_id']}.json"), "w"), indent=1)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    man = {"suite": a.suite, "seed": SEEDS[a.suite], "n_scenarios": len(out), "categories": PLAN[a.suite], "n_assertions": sum(t["kind"] == "ASSERT" for s in out for t in s["turns"]),
           "files_sha256": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files}, "no_surface_in_P0_P2_corpora": True}
    json.dump(man, open(os.path.join(HERE, f"{a.suite.upper()}_MANIFEST.json"), "w"), indent=1); print({k: v for k, v in man.items() if k != "files_sha256"})


if __name__ == "__main__":
    main()
