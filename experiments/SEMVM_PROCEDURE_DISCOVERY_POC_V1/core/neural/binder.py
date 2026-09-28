"""Frozen neural binder (SEMVM_BINDER_POC_V1 = A-005 R20 s17 ep40). Gold-free inference for arbitrary controlled assertions.
Pipeline per assertion: tokens -> envelope check (neural/envelope.py) -> packed forest built with the STAGE-MATCHED inventory the binder was trained
with (1 modifier -> P0 inventory, 2 modifiers -> P2 inventory; template indices = union indices) -> frozen scorer -> argmax output marginal
(the exact decoding used in every evaluation) -> decoded semantic graph (occurrences + edges). The forest construction reproduces
mr_forest.process line for line minus every gold-dependent field. The model is frozen: eval mode, requires_grad False, no optimizer; the state
hash is checked at load and after every inference session."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, os.path.join(HERE, "vendor"))
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import mr_config as K                      # installs the frozen ontology into the engine tables
import ltc_core as C, ltc_packed as PK
ART = os.path.join(HERE, "artifacts"); CKPT = os.path.join(ART, "binder_A005_R20_s17_ep40.pt")
MANIFEST = json.load(open(os.path.join(HERE, "BINDER_MANIFEST.json"))); CEIL = (400_000, 3_000_000, 120.0); MAX_LEN = 40


def _tpl(tid):
    c, e, r = json.loads(tid); return (tuple(tuple(x) for x in c), tuple(tuple(x) for x in e), r)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


class Binder:
    def __init__(self, device="cpu"):
        import torch, ltcn_model as M
        if sha(CKPT) != MANIFEST["checkpoint"]["sha256"]: raise SystemExit("STOP — S1: binder checkpoint hash mismatch")
        self.torch, self.M, self.dev = torch, M, device
        self.vocab = json.load(open(os.path.join(ART, "union_vocab.json"))); self.union = json.load(open(os.path.join(ART, "union_inventory.json")))
        self.uidx = {t: i for i, t in enumerate(self.union)}
        self.inv = {1: [_tpl(t) for t in json.load(open(os.path.join(ART, "p0_inventory_tids.json")))], 2: [_tpl(t) for t in json.load(open(os.path.join(ART, "p2_inventory_tids.json")))]}
        for n, inv in self.inv.items(): assert all(C.tid(t) in self.uidx for t in inv)
        torch.use_deterministic_algorithms(True)
        a = MANIFEST["architecture"]["args"]; self.model = M.Scorer(a["n_vocab"], a["max_len"], a["n_templates"], a["n_roles"])
        self.model.load_state_dict(torch.load(CKPT, map_location="cpu", weights_only=False)["state"]); self.model.to(device).eval()
        for p in self.model.parameters(): p.requires_grad_(False)
        self.state_hash0 = self.state_hash()

    def state_hash(self):
        h = hashlib.sha256()
        for k, v in sorted(self.model.state_dict().items()): h.update(k.encode()); h.update(v.detach().cpu().numpy().tobytes())
        return h.hexdigest()

    def assert_frozen(self):
        if self.state_hash() != self.state_hash0: raise SystemExit("STOP — frozen binder state changed")
        return True

    def encode(self, toks, n_mod):
        """gold-free packed-forest encoding (mr_forest.process minus gold); template indices are union indices"""
        inv = self.inv[n_mod]; C.tid_index = {C.tid(t): self.uidx[C.tid(t)] for t in inv}
        ins = C.instances(toks, inv); F = PK.build(toks, ins, CEIL); N = F["nodes"]
        node_keys = sorted(N, key=lambda k: (N[k].hull[1] - N[k].hull[0], k[0])); nix = {k: i for i, k in enumerate(node_keys)}
        ins_ix = {x["ser"]: i for i, x in enumerate(ins)}; rf_ix = {}; comp_ix = {}; out_ix = {}; outs = []
        def rfid(rf):
            if rf not in rf_ix: rf_ix[rf] = len(rf_ix)
            return rf_ix[rf]
        for x in ins: rfid(x["rootfrag"])
        rf_members = {}
        for x in ins: rf_members.setdefault(x["rootfrag"], (C.tid_index[x["tid"]], [o[2] for o in x["grounding"]], x["obj"].root[2]))
        def cid(c):
            if c not in comp_ix: comp_ix[c] = len(comp_ix)
            return comp_ix[c]
        enc_nodes = []
        for k in node_keys:
            nd = N[k]; y = C.out_key(nd.obj)
            if y not in out_ix: out_ix[y] = len(outs); outs.append(y)
            enc_nodes.append((nd.hull[1] - nd.hull[0], [ins_ix[x["ser"]] for x in nd.leaves], [(nix[p], nix[ch], cid((N[p].rootfrag, r, N[ch].rootfrag))) for r, p, ch, s in nd.hedges], out_ix[y]))
        comps = [None] * len(comp_ix)
        for (rp, r, rc), i in comp_ix.items(): comps[i] = (rf_ix[rp], C.ROLES.index(r), rf_ix[rc])
        rfs = [None] * len(rf_ix)
        for rf, i in rf_ix.items(): rfs[i] = rf_members[rf]
        return {"id": "q", "tokens": toks, "tok_ids": [self.vocab.get(t, 1) for t in toks],
                "instances": [(C.tid_index[x["tid"]], list(x["spans"]), [o[2] for o in x["grounding"]].index(x["obj"].root[2]), rf_ix[x["rootfrag"]]) for x in ins],
                "rootfrags": rfs, "comps": comps, "nodes": enc_nodes, "accepted": [], "outputs": [{"y": y} for y in outs], "alex": {"inst": [], "comp": []}, "acomp": {"inst": [], "comp": []}}, outs

    def parse(self, toks, n_mod):
        """-> dict(graph=(occs, edges, root) of the argmax output marginal, margin to the runner-up output, n_outputs)"""
        torch = self.torch
        enc, outs = self.encode(toks, n_mod)
        with torch.no_grad():
            b = self.M.Batcher([enc], self.vocab, self.dev)([0]); d = self.M.decode(self.model, b); om = d["out_mass"].tolist()
        order = sorted(range(len(om)), key=lambda i: -om[i]); best = outs[order[0]]
        return {"graph": best, "log_mass": om[order[0]], "logZ": float(d["logZ"][0]), "margin_to_runner_up": om[order[0]] - (om[order[1]] if len(om) > 1 else float("-inf")), "n_outputs": len(outs)}
