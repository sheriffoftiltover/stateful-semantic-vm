"""Neural regression suite (spec §40, M1). The POC's gold-free binder path must reproduce, item by item, the A-005 R20 epoch-40 decisions obtained
with the original evaluation path (original P0/P2 forests, union-remapped; pb_a004.decode). Compared per item: exact flag and, for every gold
modifier, (predicted parent, predicted role). Also reports the alternative 'union inventory for every input' policy (diagnostic only).
Usage: python tests/neural_regression.py [--limit N] [--out results/NEURAL_REGRESSION.json] [--source <parent-binding experiment dir>]"""
import os, sys, json, argparse, collections
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE); sys.path[:0] = [os.path.join(ROOT, "neural")]
import binder as BN, mr_generate as G, ltc_core as C


def mod_labels(graph, gold):
    """per gold modifier occurrence (in gold order): (parent label outer/inner/other/absent, role) in the predicted graph"""
    occs = [tuple(o) for o in gold["gold"]["occs"]]; gO, gI = occs[0], occs[1]; out = []
    for mo in occs[2:]:
        hit = sorted([(r, p) for r, p, c in graph[1] if c == mo], key=str)
        if not hit: out.append(("absent", None)); continue
        r, p = hit[0]; out.append(("outer" if p == gO else "inner" if p == gI else "other", r))
    return out


def run(limit=None, source=None, union_policy=False):
    b = BN.Binder(); R = {}
    for stage, n_mod in (("P0", 1), ("P2", 2)):
        items = [json.loads(l) for l in open(os.path.join(source, "data", stage, "corpus", "id_val.jsonl"))][:limit]; rows = []
        for it in items:
            p = b.parse(it["tokens"], 2 if union_policy else n_mod) if not union_policy else None
            if union_policy:
                inv_backup = b.inv[2]; b.inv[2] = [BN._tpl(t) for t in b.union]; p = b.parse(it["tokens"], 2); b.inv[2] = inv_backup
            g = G.gold_obj(it); rows.append({"id": it["id"], "exact": p["graph"] == C.out_key(g), "mods": mod_labels(p["graph"], it)})
        R[stage] = rows
    b.assert_frozen(); return R


def reference(source, limit=None):
    """the original A-005 evaluation path on the same checkpoint"""
    sys.path[:0] = [os.path.join(source, "code", d) for d in ("model", "corpus", "analysis")]
    import torch, pb_a005 as A5, pb_a004 as A4
    uv = json.load(open(os.path.join(source, "data", "A005_union", "union_vocab.json"))); ut = json.load(open(os.path.join(source, "data", "A005_union", "union_inventory.json")))
    m = A5.scorer(len(uv), len(ut)); m.load_state_dict(torch.load(BN.CKPT, map_location="cpu", weights_only=False)["state"]); m.eval(); R = {}
    for stage in ("P0", "P2"):
        F, meta = A5.load_task(stage, ["id_val"], uv, ut); F["id_val"] = F["id_val"][:limit] if limit else F["id_val"]
        R[stage] = [{"id": r["id"], "exact": r["exact"], "mods": [(q["pred_parent"], q["pred_role"]) for q in r["mods"]]} for r in A4.decode(m, F, uv, meta, "id_val", "cpu")]
    return R


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); ap.add_argument("--out", default=os.path.join(ROOT, "results", "NEURAL_REGRESSION.json"))
    ap.add_argument("--source", default=os.path.join(ROOT, "..", "SEMVM_COINDEXATION_PARENT_BINDING_MECHANISM_V1")); ap.add_argument("--union-policy", action="store_true"); a = ap.parse_args()
    mine = run(a.limit, a.source, a.union_policy); ref = reference(a.source, a.limit); out = {"policy": "union inventory for all inputs (diagnostic)" if a.union_policy else "stage-matched inventory (registered)"}
    for st in ("P0", "P2"):
        same = [x["exact"] == y["exact"] and [tuple(m) for m in x["mods"]] == [tuple(m) for m in y["mods"]] for x, y in zip(mine[st], ref[st])]
        out[st] = {"n": len(same), "identical_decisions": sum(same), "poc_exact": sum(x["exact"] for x in mine[st]) / len(same), "reference_exact": sum(y["exact"] for y in ref[st]) / len(same),
                   "mismatch_ids": [x["id"] for x, s in zip(mine[st], same) if not s][:20]}
    out["all_identical"] = all(out[st]["identical_decisions"] == out[st]["n"] for st in ("P0", "P2"))
    os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
