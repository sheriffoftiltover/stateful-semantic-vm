"""Generator for SEMVM_MULTI_RELATION_BINDING_CORPUS_V1 (frozen matrix: mr_config.py). Never trains anything.
Item: two events (OUTER --TODO--> INNER, each followed by its own coindexation tag) + 1 or 2 coindexed modifier phrases (relation, value,
parent). A modifier names its PARENT's tag, which is the only attachment signal. Every retained item is verified DERIVABLE (gold reachable) in the
projective packed forest of the unchanged engine (primitive templates only -> independent of the fragment inventory).
Determinism: candidates are produced by one seeded RNG per split in a fixed order; derivability is computed in parallel but acceptance is a
sequential greedy pass over the candidate order, so the corpus is independent of the worker count.
Usage: python code/corpus/mr_generate.py --out data/corpus_candidate [--workers 8]"""
import os, sys, json, random, argparse, collections, hashlib, time
HERE = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, HERE)
import mr_config as K
import ltc_core as C, ltc_packed as PK

PRIMS = None


def render(frame, O, I, mo, mi, mods, slots):
    """mods: list of dicts {rel, cls, value, attach, fmt}; slots: which frame slots they occupy (['M1'], ['M2'], or ['M1','M2'])"""
    parts = list(K.FRAMES[frame]["parts"]); used = dict(zip(slots, mods))
    # drop unused slots together with the separator adjacent to them (between the two slots, or next to the event block)
    for s in ("M1", "M2"):
        if s in used: continue
        i = parts.index(s)
        if s == "M2": j = i - 1 if parts[i - 1] not in ("{O}", "{I}") else None
        else: j = i + 1 if parts[i + 1] not in ("{O}", "{I}") else None
        parts = [p for k, p in enumerate(parts) if k not in (i, j)]
    toks, anc = [], {}
    for p in parts:
        if p in ("{O}", "{I}"):
            ev, tag = (O, mo) if p == "{O}" else (I, mi); anc["O" if p == "{O}" else "I"] = len(toks); toks += [K.TRIG[ev], tag]
        elif p in used:
            m = used[p]; tag = mo if m["attach"] == "outer" else mi
            for x in K.PHRASE_FORMATS[m["fmt"]]:
                if x == "{CUE}": toks += K.CUE[m["rel"]]
                elif x == "{V}": anc[("MOD", p)] = len(toks); toks.append(m["value"])
                elif x == "{m}": toks.append(tag)
                else: toks.append(x)
        else: toks.append(p)
    order = [s for s in ("M1", "M2") if s in used]
    occs = [[O, None, anc["O"]], [I, None, anc["I"]]] + [[used[s]["cls"], used[s]["value"], anc[("MOD", s)]] for s in order]
    edges = [["TODO", 0, 1]] + [[used[s]["rel"], 0 if used[s]["attach"] == "outer" else 1, 2 + k] for k, s in enumerate(order)]
    mod_meta = []
    for k, s in enumerate(order):
        m = used[s]; vp = anc[("MOD", s)]; dO, dI = abs(vp - anc["O"]), abs(vp - anc["I"]); near = "outer" if dO < dI else "inner"
        par = O if m["attach"] == "outer" else I
        mod_meta.append({"slot": s, "rel": m["rel"], "value": m["value"], "attach": m["attach"], "parent": par, "cell": f"{m['rel']}|{par}", "fmt": m["fmt"],
                         "withheld": (m["rel"], par) in K.WITHHELD_CELLS, "dist_outer": dO, "dist_inner": dI, "nearest_event": near, "nearest_correct": near == m["attach"]})
    return {"tokens": toks, "surface": " ".join(toks), "gold": {"occs": occs, "edges": edges, "root": 0},
            "meta": {"frame": frame, "event_order": K.FRAMES[frame]["order"], "outer": O, "inner": I, "markers": [mo, mi], "n_mod": len(order), "mods": mod_meta}}


def gold_obj(it):
    occs = [tuple(o) for o in it["gold"]["occs"]]
    return C.Obj(frozenset(occs), frozenset((r, occs[p], occs[c]) for r, p, c in it["gold"]["edges"]), occs[it["gold"]["root"]])


def derivable(it):
    global PRIMS
    if PRIMS is None: PRIMS = C.primitive_templates()
    gold = gold_obj(it); F = PK.build(it["tokens"], C.instances(it["tokens"], PRIMS), (400_000, 3_000_000, 120.0)); N = F["nodes"]
    return any(C.out_key(N[k].obj) == C.out_key(gold) for k in PK.restrict(F, gold))


def pick_value(rng, cls, avoid):
    vals = next(v for c, v in K.REL_VALUE.values() if c == cls)
    return rng.choice([v for v in vals if (cls, v) not in avoid])


def mk_mod(rng, rel, attach, fmt, avoid):
    cls = K.REL_VALUE[rel][0]; v = pick_value(rng, cls, avoid); avoid.add((cls, v)); return {"rel": rel, "cls": cls, "value": v, "attach": attach, "fmt": fmt}


def pick_frame(rng):
    return rng.choice(sorted(K.FRAMES))            # uniform (amendment 001)


def slots_for(rng, n):
    return ["M1", "M2"] if n == 2 else [rng.choice(["M1", "M2"])]


def cand_id(rng, allowed, first_cell=None):
    """in-distribution candidate: every modifier on an allowed (non-withheld, valid) cell. If first_cell=(r, c) is given, the first modifier is
    r attached to constructor c (deficit-driven sampling, amendment 001); the other event and any second modifier are drawn at random."""
    mo, mi = rng.sample(K.MARKERS, 2); n = 2 if rng.random() < K.P_TWO_MOD else 1; avoid = set(); mods = []
    if first_cell:
        r0, c0 = first_cell
        if c0 in K.OUTER: O, I = c0, rng.choice(K.INNER)
        else: O, I = rng.choice(K.OUTER), c0
        mods.append(mk_mod(rng, r0, "outer" if c0 in K.OUTER else "inner", rng.choice(K.TRAIN_FORMATS), avoid)); chosen = [r0]
    else: O, I = rng.choice(K.OUTER), rng.choice(K.INNER); chosen = []
    rels = [r for r in K.PRIMARY if r not in chosen and (allowed(r, O) or allowed(r, I))]
    for r in rng.sample(rels, max(0, min(n - len(chosen), len(rels)))):
        sides = [s for s, c in (("outer", O), ("inner", I)) if allowed(r, c)]; mods.append(mk_mod(rng, r, rng.choice(sides), rng.choice(K.TRAIN_FORMATS), avoid))
    rng.shuffle(mods)
    return render(pick_frame(rng), O, I, mo, mi, mods, slots_for(rng, len(mods)))


def cand_pair(rng, rel, O, I, target_fmt, allowed_other):
    """minimal pair: target modifier `rel` attached to OUTER in a, INNER in b; everything else identical"""
    mo, mi = rng.sample(K.MARKERS, 2); avoid = set(); tgt = mk_mod(rng, rel, "outer", target_fmt, avoid); mods = [tgt]
    if rng.random() < K.P_TWO_MOD:
        others = [(r, s) for r in K.PRIMARY if r != rel for s, c in (("outer", O), ("inner", I)) if allowed_other(r, c)]
        if others: r2, s2 = rng.choice(others); mods.append(mk_mod(rng, r2, s2, rng.choice(K.TRAIN_FORMATS), avoid))
    rng.shuffle(mods); frame = pick_frame(rng); sl = slots_for(rng, len(mods)); ti = mods.index(tgt)
    a = render(frame, O, I, mo, mi, mods, sl)
    mods_b = [dict(m) for m in mods]; mods_b[ti]["attach"] = "inner"; b = render(frame, O, I, mo, mi, mods_b, sl)
    for x in (a, b): x["meta"]["target_slot"] = sl[ti] if len(sl) > 1 else sl[0]; x["meta"]["target_rel"] = rel
    return a, b


def batch_derivable(pool, items):
    return pool.map(derivable, items, chunksize=8)


def main(argv=None):
    """V1.1: --candidate C20|C30|C40 builds TRAIN / ID_VAL / ID_TEST (one quota sampler, disjoint items) + ID_PAIR (pair diagnostic).
    --systematic (FREEZE STEP ONLY, blinded) adds RECOMB / SURFACE_RECOMB to an existing ID corpus without altering it."""
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--candidate", required=True, choices=sorted(K.CANDIDATES))
    ap.add_argument("--systematic", action="store_true"); a = ap.parse_args(argv)
    out = os.path.join(K.ROOT, a.out) if not os.path.isabs(a.out) else a.out; os.makedirs(out, exist_ok=True); m_s = None; t_mix = K.CANDIDATES[a.candidate]["mixed_target"]   # m_s: superseded by global running control (calibration fix)
    import multiprocessing as mp
    pool = mp.get_context("fork").Pool(a.workers); t0 = time.time(); shortfall = {}; used = set(); S = collections.defaultdict(list); rej = collections.Counter(); tried = collections.Counter()
    if a.systematic:
        for sp in ("train", "id_val", "id_test", "id_pair"):
            for l in open(os.path.join(out, f"{sp}.jsonl")): used.add(json.loads(l)["surface"])
    # ---------- TRAIN / ID_VAL / ID_TEST: ONE quota sampler (cells x nearest band, frame x n_mod attachment-pattern caps), disjoint items ----------
    for split, n_items in ((() if a.systematic else (("train", K.SIZES["train"]), ("id_val", K.SIZES["id_val"]), ("id_test", K.SIZES["id_test"])))):
        rng = random.Random(f"{K.SEED}-{split}"); cells = [(r, c) for r in K.PRIMARY for c in K.EVENTS if K.train_cell(r, c)]
        slots_total = n_items * (1 + K.P_TWO_MOD); qc = int(slots_total / len(cells)) + 1; qn = int(qc * K.NEAREST_BAND)   # per cell / per (cell, nearest_correct)
        have = collections.Counter(); hc = collections.Counter(); nmod = collections.Counter(); got = []; stall = 0; last = 0; patc = collections.Counter(); patn = collections.Counter(); g2 = collections.Counter(); ecnt = collections.Counter()
        while len(got) < n_items:
            deficit = [max(0, qc - hc[f"{r}|{c}"]) for r, c in cells]                      # counts at batch start -> deterministic
            wts = deficit if sum(deficit) else [1] * len(cells)
            cands = [cand_id(rng, K.train_cell, rng.choices(cells, weights=wts)[0]) for _ in range(2000)]; ok = batch_derivable(pool, cands); tried[split] += len(cands)
            for it, d in zip(cands, ok):
                if len(got) >= n_items: break
                if not d: rej[(split, "nonprojective", it["meta"]["frame"], it["meta"]["n_mod"])] += 1; continue
                if it["surface"] in used: rej[(split, "duplicate")] += 1; continue
                keys = [(m["cell"], m["nearest_correct"]) for m in it["meta"]["mods"]]
                # dynamic band (amendment 001): after adding, neither nearest value may exceed SELECT_BAND of the cell's RUNNING count (+2 slack)
                if any(hc[k[0]] >= qc for k in keys) or any(have[k] + 1 > K.SELECT_BAND * (hc[k[0]] + 1) + 2 for k in keys): continue
                if nmod[it["meta"]["n_mod"]] >= n_items * 0.55 + 1: continue
                # amendment 001: attachment balanced WITHIN each shallow surface position (frame x n_mod), running-count caps (+2 slack)
                fr = it["meta"]["frame"]; at = [m["attach"] for m in it["meta"]["mods"]]      # slot order (M1, M2)
                # V1.1 calibration fix (D0-round-1 overshoot): the static per-frame m_s assumed uniform frame shares; instead the GLOBAL running
                # two-modifier mixed share is held at the candidate target (+2 slack), and straddle frames balance each orientation / same-parent
                # side at <= 1/2 of that frame's own mixed / same count (+2 slack). V1 frames keep the V1 caps.
                if it["meta"]["n_mod"] == 2:
                    mixed = at[0] != at[1]; gk = "mixed" if mixed else "same"
                    if g2[gk] + 1 > (t_mix if mixed else 1 - t_mix) * (g2["all"] + 1) + 2: continue
                if it["meta"]["n_mod"] == 2 and fr in K.STRADDLE_FRAMES:                          # V1.1: both mixed orientations exist -> balance them
                    pat = ("mixed_" + at[0][0] + at[1][0]) if mixed else "same_" + at[0]; cap = 0.5; nk = (fr, 2, gk)
                elif it["meta"]["n_mod"] == 2: pat = "mixed" if mixed else "same_" + at[0]; cap = K.MIXED_PATTERN_CAP if pat == "mixed" else K.SAME_PATTERN_CAP; nk = (fr, 2)
                else: pat = "one_" + at[0]; cap = K.ONE_MOD_ATTACH_CAP; nk = (fr, 1)
                pk = (fr, it["meta"]["n_mod"], pat)
                if patc[pk] + 1 > cap * (patn[nk] + 1) + 2: continue
                # Amendment D0-2: ELIGIBLE mixed items (both orientations projective + TRAIN-valid) are orientation-balanced within EVERY audit
                # stratum (frame, relation pair, constructor pair, modifier-order family, format family): each orientation <= 1/2 (+2 slack).
                # STRUCTURALLY_ONE_SIDED items stay outside this pool (the per-frame straddle cap above still applies to them).
                elig = []
                if it["meta"]["n_mod"] == 2 and mixed and K.orientation_status(it["meta"])[0] == "ELIGIBLE":
                    elig = [(lv, v) for lv, v in K.orientation_strata(it["meta"]).items()]
                    if any(ecnt[(lv, v, pat)] + 1 > 0.5 * (ecnt[(lv, v)] + 1) + 2 for lv, v in elig): continue
                for lv, v in elig: ecnt[(lv, v, pat)] += 1; ecnt[(lv, v)] += 1
                for k in keys: have[k] += 1; hc[k[0]] += 1
                patc[pk] += 1; patn[nk] += 1
                if it["meta"]["n_mod"] == 2:
                    g2[gk] += 1; g2["all"] += 1
                nmod[it["meta"]["n_mod"]] += 1; used.add(it["surface"]); got.append(it)
            print(split, len(got), "/", n_items, round(time.time() - t0), "s", flush=True)
            stall = stall + 1 if len(got) == last else 0; last = len(got)
            if stall >= 15:                                                            # deterministic tail rule: quotas cannot be completed
                shortfall[split] = n_items - len(got); print(f"{split}: closed at {len(got)} (quota-limited tail, shortfall {n_items - len(got)})", flush=True); break
            if tried[split] > 600_000: raise SystemExit(f"CORPUS_CAPACITY_INSUFFICIENT {split}: " + json.dumps({f"{k[0]}|{k[1]}": v for k, v in have.items()}))
        S[split] = got
    # ---------- paired splits ----------
    def pairs(split, n_pairs_per, relations, OI_for, target_fmts, allowed_other):
        rng = random.Random(f"{K.SEED}-{split}"); got = []; pid = 0
        for rel in relations:
            O, I = OI_for(rel); have = collections.Counter(); n = 0
            while n < n_pairs_per:
                cands = [cand_pair(rng, rel, O, I, rng.choice(target_fmts), allowed_other) for _ in range(300)]
                flat = [x for ab in cands for x in ab]; ok = batch_derivable(pool, flat); tried[split] += len(flat)
                for k, (a_, b_) in enumerate(cands):
                    if n >= n_pairs_per: break
                    if not (ok[2 * k] and ok[2 * k + 1]): rej[(split, "nonprojective_pair", a_["meta"]["frame"])] += 1; continue
                    if a_["surface"] in used or b_["surface"] in used: rej[(split, "duplicate")] += 1; continue
                    tk = [m for m in a_["meta"]["mods"] if m["rel"] == rel][0]; key = tk["nearest_correct"]
                    if have[key] >= n_pairs_per // 2 + 1: continue
                    have[key] += 1; pid += 1; n += 1
                    for x, side in ((a_, "outer"), (b_, "inner")):
                        x["meta"]["pair_id"] = f"{split}-{pid:04d}"; x["meta"]["pair_side"] = side; used.add(x["surface"]); got.append(x)
            print(split, rel, n, round(time.time() - t0), "s", flush=True)
        S[split] = got
    # ID_PAIR (secondary pair-structured diagnostic; the former V1 ID_TEST design): any (O, I) on which the target relation is a TRAIN cell at BOTH attachments
    def pairs_id():
        rng = random.Random(f"{K.SEED}-id_pair"); got = []; pid = 0; per = K.SIZES["id_pair_pairs"] // len(K.PRIMARY)
        for rel in K.PRIMARY:
            OIs = [(o, i) for o in K.OUTER for i in K.INNER if K.train_cell(rel, o) and K.train_cell(rel, i)]; n = 0; have = collections.Counter()
            while n < per:
                cands = [cand_pair(rng, rel, *rng.choice(OIs), rng.choice(K.TRAIN_FORMATS), K.train_cell) for _ in range(300)]
                flat = [x for ab in cands for x in ab]; ok = batch_derivable(pool, flat); tried["id_pair"] += len(flat)
                for k, (a_, b_) in enumerate(cands):
                    if n >= per: break
                    if not (ok[2 * k] and ok[2 * k + 1]) or a_["surface"] in used or b_["surface"] in used: continue
                    tk = [m for m in a_["meta"]["mods"] if m["rel"] == rel][0]
                    if have[tk["nearest_correct"]] >= per // 2 + 1: continue
                    have[tk["nearest_correct"]] += 1; pid += 1; n += 1
                    for x, side in ((a_, "outer"), (b_, "inner")): x["meta"]["pair_id"] = f"id_pair-{pid:04d}"; x["meta"]["pair_side"] = side; used.add(x["surface"]); got.append(x)
            print("id_pair", rel, n, round(time.time() - t0), "s", flush=True)
        S["id_pair"] = got
    if not a.systematic: pairs_id()
    else:
        pairs("recomb", K.SIZES["recomb_pairs_per_relation"], K.PRIMARY, lambda r: K.WITHHELD[r], K.TRAIN_FORMATS, K.train_cell)
        pairs("surface_recomb", K.SIZES["surface_recomb_pairs_per_relation"], K.PRIMARY, lambda r: K.WITHHELD[r], K.HELDOUT_FORMATS, K.train_cell)
    pool.close()
    for s, items in S.items():
        for k, it in enumerate(items): it["id"] = f"{s}-{k:05d}"; it["split"] = s
        with open(f"{out}/{s}.jsonl", "w") as f:
            for it in items: f.write(json.dumps(it) + "\n")
    if a.systematic:     # blinded: counts only are printed; nothing is decoded or summarised
        json.dump({"systematic_seed_rule": "random.Random(f'{SEED}-{split}')", "counts": {s: len(v) for s, v in S.items()}, "generator_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()},
                  open(f"{out}/generation_config_systematic.json", "w"), indent=1); print("systematic splits written:", {s: len(v) for s, v in S.items()}); return
    json.dump(K.frozen_matrix(), open(f"{out}/relation_constructor_matrix.json", "w"), indent=1)
    json.dump({"frames": K.FRAMES, "phrase_formats": K.PHRASE_FORMATS, "train_formats": K.TRAIN_FORMATS, "heldout_formats": K.HELDOUT_FORMATS, "cues": K.CUE, "markers": K.MARKERS,
               "triggers": K.TRIG, "note": "attachment is signalled only by the coindexation tag inside the modifier phrase (it names the parent's tag)"}, open(f"{out}/surface_template_inventory.json", "w"), indent=1)
    json.dump({"persons": K.PERSONS, "times": K.TIMES, "places": K.PLACES, "topics": K.TOPICS}, open(f"{out}/value_vocabularies.json", "w"), indent=1)
    json.dump({"candidate": a.candidate, "candidate_spec": K.CANDIDATES[a.candidate], "straddle_mixed_share": "global_running_control", "mixed_target": t_mix, "v1_frame_mixed_cap": K.V1_FRAME_MIXED_CAP,
               "seed": K.SEED, "split_rng": "random.Random(f'{SEED}-{split}') (common random numbers across candidates)", "sizes": K.SIZES, "p_two_mod": K.P_TWO_MOD, "tried": dict(tried),
               "rejections": {"|".join(map(str, k)): v for k, v in sorted(rej.items(), key=str)}, "counts": {s: len(v) for s, v in S.items()}, "quota_limited_shortfall": shortfall, "seconds": round(time.time() - t0),
               "generator_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "config_sha256": hashlib.sha256(open(os.path.join(HERE, "mr_config.py"), "rb").read()).hexdigest()},
              open(f"{out}/generation_config.json", "w"), indent=1)
    print(json.dumps({s: len(v) for s, v in S.items()}), round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
