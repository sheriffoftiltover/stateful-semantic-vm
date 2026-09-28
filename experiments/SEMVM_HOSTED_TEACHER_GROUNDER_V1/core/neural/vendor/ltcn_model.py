"""Neural scorer + exact batched inference over the FROZEN packed hypergraphs (built once by ltc_packed.build; structure never changes).
Encoder: token emb 128 + learned pos emb 128, 2 bidirectional layers (4 heads, FFN 512, GELU, dropout 0). Span MLP, fragment MLP (+64-d template emb),
composition MLP ([h_p, h_c, e_r(32), h_p*h_c, h_ctx] -> 256 -> 1). Scores: S(d) = sum s_f + sum s_c; SKIP 0.
LOCALITY: s_c depends only on (parent root fragment, role, child root fragment, x). Root-fragment representations use the members' TRIGGER-token
spans, so s_c is a function of the packed key's root-fragment identity (template + grounding) — exactly the symbolic V1 contract; s_f uses aligned spans.
Inference in log space: inside (logsumexp) and max-plus (Viterbi) level by level (level = hull length), deterministic gathers only."""
import math, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
D, DE, DR = 128, 64, 32
NEG = -1e30
def mlp(i, h, o): return nn.Sequential(nn.Linear(i, h), nn.GELU(), nn.Linear(h, o))
class Scorer(nn.Module):
    def __init__(self, vocab, max_len, n_templates, n_roles):
        super().__init__()
        self.tok = nn.Embedding(vocab, D); self.pos = nn.Embedding(max_len, D)
        layer = nn.TransformerEncoderLayer(D, 4, 512, dropout=0.0, activation="gelu", batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 2, enable_nested_tensor=False)
        self.span = mlp(4 * D, D, D); self.temb = nn.Embedding(n_templates, DE); self.frag = mlp(2 * D + DE + D, D, D); self.fs = nn.Linear(D, 1)
        self.remb = nn.Embedding(n_roles, DR); self.comp = mlp(4 * D + DR, 256, 1)
    def encode(self, tok, mask):
        pos = torch.arange(tok.shape[1], device=tok.device)[None].expand_as(tok)
        H = self.enc(self.tok(tok) + self.pos(pos), src_key_padding_mask=~mask); m = mask.unsqueeze(-1).float()
        return H, (H * m).sum(1) / m.sum(1)
    def scores(self, b):
        """b: collated batch dict of tensors -> (fscore [NI], cscore [NC], ctx)"""
        H, hc = self.encode(b["tok"], b["mask"]); B, L, _ = H.shape
        tri = torch.tril(torch.ones(L + 1, L, device=H.device, dtype=H.dtype), diagonal=-1)       # prefix sums via matmul (deterministic; cumsum CUDA is not)
        cs = torch.einsum("ij,bjd->bid", tri, H); it, a, e = b["sp_item"], b["sp_a"], b["sp_b"]
        mean = (cs[it, e] - cs[it, a]) / (e - a).unsqueeze(-1).float()
        S = self.span(torch.cat([mean, H[it, a], H[it, e - 1], hc[it]], -1))
        def fragrep(members, mmask, root, tid, item):
            mm = mmask.unsqueeze(-1).float(); memb = (S[members.clamp(min=0)] * mm).sum(1) / mm.sum(1)
            return self.frag(torch.cat([memb, S[root], self.temb(tid), hc[item]], -1))
        hf = fragrep(b["in_mem"], b["in_mmask"], b["in_root"], b["in_tid"], b["in_item"]); fscore = self.fs(hf).squeeze(-1)
        hr = fragrep(b["rf_mem"], b["rf_mmask"], b["rf_root"], b["rf_tid"], b["rf_item"])
        hp, hcn = hr[b["cp_p"]], hr[b["cp_c"]]
        cscore = self.comp(torch.cat([hp, hcn, self.remb(b["cp_r"]), hp * hcn, hc[b["cp_item"]]], -1)).squeeze(-1)
        return fscore, cscore
def run_semiring(b, fscore, cscore, mode):
    """mode 'lse' (inside) or 'max' (Viterbi value). Returns alpha over all batch nodes (+1 padding slot at the end = NEG)."""
    N = b["n_nodes"]; alpha = torch.full((N + 1,), NEG, device=fscore.device, dtype=fscore.dtype)
    for lv in b["levels"]:
        hv = alpha[lv["hp"]] + alpha[lv["hc"]] + cscore[lv["hcomp"]]
        cand = torch.cat([fscore[lv["leaf_inst"]], hv, torch.full((1,), NEG, device=fscore.device, dtype=fscore.dtype)])
        M = cand[lv["mat"]]
        vals = torch.logsumexp(M, 1) if mode == "lse" else M.max(1).values
        alpha = alpha.index_copy(0, lv["nodes"], vals)
    return alpha
def item_reduce(alpha, idxmat, mode):
    M = alpha[idxmat]; return torch.logsumexp(M, 1) if mode == "lse" else M.max(1).values
def fixed_score(fscore, cscore, b, arm):
    return (torch.cat([fscore, fscore.new_zeros(1)])[b[f"{arm}_inst"]]).sum(1) + (torch.cat([cscore, cscore.new_zeros(1)])[b[f"{arm}_comp"]]).sum(1)
def losses(model, b, arm):
    fscore, cscore = model.scores(b); ins = run_semiring(b, fscore, cscore, "lse"); logZ = item_reduce(ins, b["all_nodes"], "lse")
    if arm == "C": num = item_reduce(ins, b["acc_nodes"], "lse")
    elif arm == "B": vit = run_semiring(b, fscore, cscore, "max"); num = item_reduce(vit, b["acc_nodes"], "max")
    else: num = fixed_score(fscore, cscore, b, "alex" if arm == "A-LEX" else "acomp")
    return (logZ - num), logZ, num, (fscore, cscore, ins)
@torch.no_grad()
def decode(model, b):
    """-> per item: marginal output id, Viterbi output id, log output masses (dict), logZ, logZ_y"""
    fscore, cscore = model.scores(b); ins = run_semiring(b, fscore, cscore, "lse"); vit = run_semiring(b, fscore, cscore, "max")
    logZ = item_reduce(ins, b["all_nodes"], "lse"); logZy = item_reduce(ins, b["acc_nodes"], "lse")
    om = item_reduce(ins, b["out_nodes"], "lse")                     # [n_outputs_total]
    vnode = vit[b["all_nodes"]].argmax(1); vnode_g = b["all_nodes"].gather(1, vnode[:, None]).squeeze(1)
    return {"fscore": fscore, "cscore": cscore, "inside": ins, "logZ": logZ, "logZy": logZy, "out_mass": om, "viterbi_node": vnode_g}
# ---------------- collation ----------------
class Batcher:
    def __init__(self, items, vocab, dev):
        self.items = items; self.vocab = vocab; self.dev = dev
    def __call__(self, idx):
        its = [self.items[i] for i in idx]; B = len(its); L = max(len(it["tokens"]) for it in its); dev = self.dev
        tok = np.zeros((B, L), np.int64); mask = np.zeros((B, L), bool)
        spk = {}; sp_item, sp_a, sp_b = [], [], []
        def sp(bi, a, e):
            k = (bi, a, e)
            if k not in spk: spk[k] = len(sp_item); sp_item.append(bi); sp_a.append(a); sp_b.append(e)
            return spk[k]
        in_mem, in_root, in_tid, in_item = [], [], [], []; rf_mem, rf_root, rf_tid, rf_item = [], [], [], []; cp_p, cp_r, cp_c, cp_item = [], [], [], []
        node_off = 0; inst_off = 0; comp_off = 0; out_off = 0; rf_off = 0
        lvl = {}; all_nodes, acc_nodes, out_nodes = [], [], []; alex_i, alex_c, acomp_i, acomp_c = [], [], [], []; outputs = []
        for bi, it in enumerate(its):
            t = it["tok_ids"]; tok[bi, :len(t)] = t; mask[bi, :len(t)] = True
            for tid, spans, rootm, rf in it["instances"]:
                ms = [sp(bi, a, e) for a, e in spans]; in_mem.append(ms + [-1] * (3 - len(ms))); in_root.append(ms[rootm]); in_tid.append(tid); in_item.append(bi)
            for tid, anchors, root in it["rootfrags"]:
                ms = [sp(bi, a, a + 1) for a in anchors]; rf_mem.append(ms + [-1] * (3 - len(ms))); rf_root.append(sp(bi, root, root + 1)); rf_tid.append(tid); rf_item.append(bi)
            for p, r, c in it["comps"]: cp_p.append(p + rf_off); cp_r.append(r); cp_c.append(c + rf_off); cp_item.append(bi)
            for ni, (level, leaves, hedges, oid) in enumerate(it["nodes"]):
                g = ni + node_off; d = lvl.setdefault(level, {"nodes": [], "leaf": [], "hedge": []}); d["nodes"].append(g)
                for x in leaves: d["leaf"].append((g, x + inst_off))
                for p, c, cp in hedges: d["hedge"].append((g, p + node_off, c + node_off, cp + comp_off))
            nn_ = len(it["nodes"]); all_nodes.append(list(range(node_off, node_off + nn_))); acc_nodes.append([a + node_off for a in it["accepted"]])
            byo = {}
            for ni, (_, _, _, oid) in enumerate(it["nodes"]): byo.setdefault(oid, []).append(ni + node_off)
            for oid in range(len(it["outputs"])): out_nodes.append(byo[oid]); outputs.append((bi, it["outputs"][oid]))
            alex_i.append([x + inst_off for x in it["alex"]["inst"]]); alex_c.append([x + comp_off for x in it["alex"]["comp"]])
            acomp_i.append([x + inst_off for x in it["acomp"]["inst"]]); acomp_c.append([x + comp_off for x in it["acomp"]["comp"]])
            node_off += nn_; inst_off += len(it["instances"]); comp_off += len(it["comps"]); rf_off += len(it["rootfrags"])
        N = node_off; T = lambda x, dt=torch.long: torch.tensor(x, dtype=dt, device=dev)
        def pad(ls, fill): m = max(len(x) for x in ls); a = np.full((len(ls), m), fill, np.int64)
        def padm(ls, fill):
            m = max(len(x) for x in ls); a = np.full((len(ls), m), fill, np.int64)
            for i, x in enumerate(ls): a[i, :len(x)] = x
            return torch.tensor(a, device=dev)
        levels = []
        for level in sorted(lvl):
            d = lvl[level]; nodes = d["nodes"]; pos = {g: i for i, g in enumerate(nodes)}; cols = [[] for _ in nodes]
            nl = len(d["leaf"])
            for j, (g, _) in enumerate(d["leaf"]): cols[pos[g]].append(j)
            for j, (g, _, _, _) in enumerate(d["hedge"]): cols[pos[g]].append(nl + j)
            padidx = nl + len(d["hedge"])
            levels.append({"nodes": T(nodes), "leaf_inst": T([x for _, x in d["leaf"]]), "hp": T([p for _, p, _, _ in d["hedge"]]), "hc": T([c for _, _, c, _ in d["hedge"]]), "hcomp": T([c for _, _, _, c in d["hedge"]]), "mat": padm(cols, padidx)})
        b = {"tok": T(tok), "mask": T(mask, torch.bool), "sp_item": T(sp_item), "sp_a": T(sp_a), "sp_b": T(sp_b),
             "in_mem": T(in_mem), "in_mmask": T(in_mem) >= 0, "in_root": T(in_root), "in_tid": T(in_tid), "in_item": T(in_item),
             "rf_mem": T(rf_mem), "rf_mmask": T(rf_mem) >= 0, "rf_root": T(rf_root), "rf_tid": T(rf_tid), "rf_item": T(rf_item),
             "cp_p": T(cp_p), "cp_r": T(cp_r), "cp_c": T(cp_c), "cp_item": T(cp_item), "n_nodes": N, "levels": levels,
             "all_nodes": padm(all_nodes, N), "acc_nodes": padm(acc_nodes, N), "out_nodes": padm(out_nodes, N),
             "alex_inst": padm(alex_i, inst_off), "alex_comp": padm(alex_c, comp_off), "acomp_inst": padm(acomp_i, inst_off), "acomp_comp": padm(acomp_c, comp_off), "outputs": outputs, "B": B}
        b["in_mem"] = b["in_mem"].clamp(min=0) * b["in_mmask"] + 0; b["rf_mem"] = b["rf_mem"].clamp(min=0)
        return b
