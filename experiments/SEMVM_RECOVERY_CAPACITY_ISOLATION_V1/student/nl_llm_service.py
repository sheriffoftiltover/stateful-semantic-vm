"""NL_TEACH service = the parent frozen service (procedure/llm_service.py, /generate and /score code byte-identical) + ONE added read-only
endpoint /choose {prompt, continuations} -> {logprobs}: the same log P(continuation | prompt) as /score, computed with the prompt KV cache
reused across continuations (speed only; no state kept between requests). Parent docstring follows.
Frozen local LLM service (Amendment 001): Qwen2.5-Coder-1.5B (base), fp16, greedy only, eval mode, requires_grad False, no optimizer.
Stateless: every request is an independent forward pass over its own prompt (no conversation state, no KV cache kept between requests).
Endpoints (localhost JSON): POST /generate {prompt, max_new_tokens, stop} -> {text}; POST /score {prompt, continuations} -> {logprobs};
GET /frozen -> parameter hash now vs at load. Run: python procedure/llm_service.py --port 8765 [--device cuda:0]"""
import os, sys, json, hashlib, argparse, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
MODEL = "Qwen/Qwen2.5-Coder-1.5B"


def param_hash(m):
    h = hashlib.sha256()
    for k, v in sorted(m.state_dict().items()): h.update(k.encode()); h.update(v.detach().float().sum().cpu().numpy().tobytes()); h.update(str(tuple(v.shape)).encode())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); ap.add_argument("--device", default="cuda:0"); a = ap.parse_args()
    import torch, transformers as T
    torch.manual_seed(0); tok = T.AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    m = T.AutoModelForCausalLM.from_pretrained(MODEL, local_files_only=True, dtype=torch.float16).to(a.device).eval()
    for p in m.parameters(): p.requires_grad_(False)
    snap = os.path.dirname(T.utils.hub.cached_file(MODEL, "config.json", local_files_only=True))
    files = {f: hashlib.sha256(open(os.path.join(snap, f), "rb").read()).hexdigest() for f in sorted(os.listdir(snap)) if os.path.isfile(os.path.join(snap, f))}

    import copy as _copy
    LRU = []                                            # [(token ids, cache, last-position logprobs)] most recent last; speed only
    def prefix_cache(base):
        best = None
        for e in LRU:
            k = 0; n = min(len(e[0]), len(base))
            while k < n and e[0][k] == base[k]: k += 1
            if k == len(e[0]) and (best is None or k > len(best[0])): best = e
        if best is not None and len(best[0]) == len(base): LRU.remove(best); LRU.append(best); return best[1], best[2]
        if best is not None:
            cache = _copy.deepcopy(best[1]); rest = base[len(best[0]):]
            o = m(torch.tensor([rest], device=a.device), past_key_values=cache, use_cache=True)
        else:
            o = m(torch.tensor([base], device=a.device), use_cache=True); cache = o.past_key_values
        last = o.logits[0, -1].float().log_softmax(-1); LRU.append((list(base), cache, last))
        while len(LRU) > 8: LRU.pop(0)
        return cache, last
    def weights_sha256(m):                               # device-independent: exact bytes of every tensor (param_hash sums are reduction-order dependent)
        h = hashlib.sha256()
        for k, v in sorted(m.state_dict().items()): h.update(k.encode()); h.update(v.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
        return h.hexdigest()
    W0 = weights_sha256(m)
    h0 = param_hash(m); lock = threading.Lock(); stats = {"generate": 0, "score": 0, "seconds": 0.0}
    info = {"model": MODEL, "files_sha256": files, "param_hash_at_load": h0, "dtype": "float16", "decoding": "greedy", "device": a.device, "torch": torch.__version__, "transformers": T.__version__,
            "n_parameters": sum(p.numel() for p in m.parameters())}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *x): pass
        def _send(self, obj): b = json.dumps(obj).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            if self.path == "/frozen":
                with lock: h = param_hash(m); w = weights_sha256(m)
                return self._send({**info, "param_hash_now": h, "weights_sha256": w, "weights_sha256_at_load": W0, "frozen": h == h0 and w == W0, "stats": stats})
            self._send(info)
        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); t0 = time.time()
            with lock, torch.no_grad():
                if self.path == "/generate":
                    x = tok(req["prompt"], return_tensors="pt").to(a.device)
                    y = m.generate(**x, max_new_tokens=req.get("max_new_tokens", 200), do_sample=False, pad_token_id=tok.eos_token_id)
                    text = tok.decode(y[0][x.input_ids.shape[1]:], skip_special_tokens=True)
                    for s in req.get("stop", []):
                        if s in text: text = text[:text.index(s) + (len(s) if req.get("keep_stop") else 0)]
                    stats["generate"] += 1; out = {"text": text}
                elif self.path == "/choose":
                    # score(c) = log P(tok(prompt + c)) - log P(tok(prompt))  (exact under the canonical tokenization; equals the /score
                    # suffix log-probability whenever tok(prompt) is a prefix of tok(prompt + c))
                    base = tok(req["prompt"]).input_ids; cache, last = prefix_cache(base); lps = []; tails = {}
                    def tail_lp(seq, k):
                        cc = _copy.deepcopy(cache); cc.crop(k - 1)
                        lg = m(torch.tensor([seq[k - 1:]], device=a.device), past_key_values=cc, use_cache=True).logits.float().log_softmax(-1)[0]
                        return float(sum(lg[i, seq[k + i]] for i in range(len(seq) - k)))
                    for c in req["continuations"]:
                        ids = tok(req["prompt"] + c).input_ids; k = 0; n = min(len(ids), len(base))
                        while k < n and ids[k] == base[k]: k += 1
                        if k == len(base):
                            suf = ids[len(base):]; lp = float(last[suf[0]])
                            if len(suf) > 1:
                                lg = m(torch.tensor([suf[:-1]], device=a.device), past_key_values=cache, use_cache=True).logits.float().log_softmax(-1)[0]
                                lp += float(sum(lg[i, suf[i + 1]] for i in range(len(suf) - 1))); cache.crop(len(base))
                        else:
                            if k not in tails: tails[k] = tail_lp(base, k)
                            lp = tail_lp(ids, k) - tails[k]
                        lps.append(lp)
                    stats["score"] += 1; out = {"logprobs": lps}
                elif self.path == "/generate_stop":             # greedy decoding that stops at the first stop string (same argmax tokens as /generate)
                    base = tok(req["prompt"]).input_ids; cache, last = prefix_cache(base); ids = []; text = ""
                    for _ in range(req.get("max_new_tokens", 200)):
                        t = int(last.argmax()); ids.append(t); text = tok.decode(ids, skip_special_tokens=True)
                        if t == tok.eos_token_id or any(s in text for s in req.get("stop", [])): break
                        o = m(torch.tensor([[t]], device=a.device), past_key_values=cache, use_cache=True); last = o.logits[0, -1].float().log_softmax(-1)
                    cache.crop(len(base))
                    for s in req.get("stop", []):
                        if s in text: text = text[:text.index(s)]
                    stats["generate"] += 1; out = {"text": text}
                else:
                    base = tok(req["prompt"]).input_ids; lps = []
                    for c in req["continuations"]:
                        ids = tok(req["prompt"] + c).input_ids; n = len(ids) - len(base)
                        logits = m(torch.tensor([ids], device=a.device)).logits.float().log_softmax(-1)[0]
                        lps.append(float(sum(logits[len(ids) - n - 1 + i, ids[len(ids) - n + i]] for i in range(n))))
                    stats["score"] += 1; out = {"logprobs": lps}
            stats["seconds"] += time.time() - t0; self._send(out)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H); print(json.dumps({"ready": True, "port": a.port, "param_hash": h0}), flush=True); srv.serve_forever()


if __name__ == "__main__":
    main()
