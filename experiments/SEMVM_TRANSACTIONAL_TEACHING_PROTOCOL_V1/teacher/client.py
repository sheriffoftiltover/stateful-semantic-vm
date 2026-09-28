"""Teacher client (spec §10-§13, §65, §74-§76; Amendment 001). OpenAI-compatible chat completions over plain HTTP (stdlib only):
  backend MODAL : the frozen self-hosted gpt-oss-120b vLLM endpoint (primary teacher; URL + key from env TEACHER_URL / TEACHER_API_KEY)
  backend GROQ  : Groq-hosted models, used ONLY for the registered teacher-selection preflight (key from env GROQ_API_KEY)
Every response is cached by request hash (teacher_responses/<sha>.json) and replayed on identical requests (spec §74), so reruns never pay
for, or depend on, a second generation. Provenance per call: provider, model, request id, timestamp, prompt hash, generation settings,
token counts, latency, response hash, retry count, cache hit. Secrets are never written anywhere.
Hard budget: before every UNCACHED Modal call the live cost meter (Modal Dict 'semvm-ttp-meter', container-alive seconds x H100 rate) is
checked; at or above HARD_CAP_USD the client refuses (PROVIDER_BUDGET_STOP) and the caller stops the run."""
import os, json, time, hashlib, urllib.request, urllib.error, threading
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
CACHES = {"teacher": os.path.join(ROOT, "teacher_responses"), "grounder": os.path.join(ROOT, "grounder_responses"), "judge": os.path.join(ROOT, "judge_responses")}
for _d in CACHES.values(): os.makedirs(_d, exist_ok=True)
CACHE = CACHES["teacher"]
H100_USD_PER_S = 3.95 / 3600; CPU_MEM_USD_PER_S = (0.0473 * 2 + 0.008 * 16) / 3600      # frozen from `modal billing rates` 2026-09-27
REVIEW_USD = float(os.environ.get("TTP_REVIEW_USD", "6")); HARD_CAP_USD = float(os.environ.get("TTP_HARD_CAP_USD", "9"))
RETRY = {"max_tries": 6, "backoff_s": [5, 10, 20, 40, 60, 90], "timeout_s": 600}                  # frozen retry policy (spec §75)
GEN = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 4096, "reasoning_effort": "low", "seed": 0}   # 1200 truncated 31% of high-effort replies (ENGINEERING_LOG #4)  # frozen generation settings (spec §13)
TRUNCATION_TRIES = 2                                                                                 # HTG frozen: a truncated reply is re-requested once, then PROVIDER_FAILURE
LOG = []; _lock = threading.Lock()


class ProviderFailure(Exception): pass
class BudgetStop(Exception): pass


def sha(s): return hashlib.sha256(s.encode()).hexdigest()


def meter_usd():
    """live spend estimate for this experiment's teacher containers (heartbeats written by teacher/modal_teacher.py)"""
    import modal
    d = modal.Dict.from_name("semvm-ttp-meter", create_if_missing=True); tot = 0.0
    for k, v in d.items():
        if isinstance(v, dict) and "start" in v: tot += max(0.0, v["last"] - v["start"] + 15) * (H100_USD_PER_S + CPU_MEM_USD_PER_S)
    return round(tot, 3)


def _endpoint(backend, model):
    if backend == "MODAL": return os.environ["TEACHER_URL"].rstrip("/") + "/v1/chat/completions", os.environ["TEACHER_API_KEY"], "gpt-oss-120b"
    if backend == "GROQ": return "https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"], model
    raise ValueError(backend)


def chat(messages, backend="MODAL", model="openai/gpt-oss-120b", gen=None, meta=None, role="teacher"):
    """-> dict(text, cached, provenance). Raises ProviderFailure / BudgetStop."""
    g = dict(GEN, **(gen or {})); url, key, served = _endpoint(backend, model)
    body = {"model": served, "messages": messages, "temperature": g["temperature"], "top_p": g["top_p"], "max_tokens": g["max_tokens"], "seed": g["seed"]}
    if "gpt-oss" in model: body["reasoning_effort"] = g["reasoning_effort"]
    if "qwen" in model and backend == "GROQ": body["reasoning_effort"] = "none"
    req_key = sha(json.dumps({"role": role, "backend": backend, "model": model, "checkpoint": "0fc58fd24ef9", "body": body}, sort_keys=True)); cpath = os.path.join(CACHES[role], f"{req_key}.json")
    prov = {"role": role, "provider": "modal-vllm" if backend == "MODAL" else "groq", "model": model, "request_hash": req_key, "prompt_sha256": sha(json.dumps(messages, sort_keys=True)),
            "generation": {k: body[k] for k in body if k not in ("messages",)}, **(meta or {})}
    if os.path.exists(cpath):
        c = json.load(open(cpath)); prov.update(c["provenance"], cached=True); LOG.append(prov); return {"text": c["text"], "cached": True, "provenance": prov}
    if backend == "MODAL":
        spend = meter_usd(); prov["meter_usd_before"] = spend
        if spend >= HARD_CAP_USD: raise BudgetStop(f"teacher spend {spend} >= hard cap {HARD_CAP_USD}")
    data = json.dumps(body).encode(); err = None
    for k in range(RETRY["max_tries"]):
        t0 = time.time()
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}), timeout=RETRY["timeout_s"])
            out = json.loads(r.read()); lat = round(time.time() - t0, 3); msg = out["choices"][0]["message"]; text = msg.get("content") or ""
            u = out.get("usage") or {}
            prov.update(request_id=r.headers.get("x-request-id") or out.get("id"), timestamp=time.strftime("%FT%TZ", time.gmtime()), latency_s=lat, retry_count=k,
                        input_tokens=u.get("prompt_tokens"), output_tokens=u.get("completion_tokens"), finish_reason=out["choices"][0].get("finish_reason"),
                        response_sha256=sha(text), reasoning_chars=len(msg.get("reasoning_content") or msg.get("reasoning") or ""), cached=False)
            if prov["finish_reason"] == "length" or not text.strip():          # HTG truncation rule (spec §49): never parsed; retried; not cached
                err = "HOSTED_TRUNCATION"; prov["truncations"] = prov.get("truncations", 0) + 1; LOG.append(dict(prov, truncated=True))
                if prov["truncations"] >= TRUNCATION_TRIES: raise ProviderFailure(f"HOSTED_TRUNCATION x{prov['truncations']} (finish_reason={prov['finish_reason']})")
                continue
            with _lock: json.dump({"text": text, "provenance": prov, "messages_sha256": prov["prompt_sha256"]}, open(cpath, "w"), indent=1)
            LOG.append(prov); return {"text": text, "cached": False, "provenance": prov}
        except urllib.error.HTTPError as e:
            code = e.code; err = f"HTTP {code}"
            if code in (429, 500, 502, 503, 504, 408): time.sleep(float(e.headers.get("retry-after") or RETRY["backoff_s"][k])); continue
            raise ProviderFailure(err)
        except ProviderFailure: raise
        except Exception as e:
            err = type(e).__name__; time.sleep(RETRY["backoff_s"][k]); continue
    raise ProviderFailure(f"no response after {RETRY['max_tries']} tries ({err})")
