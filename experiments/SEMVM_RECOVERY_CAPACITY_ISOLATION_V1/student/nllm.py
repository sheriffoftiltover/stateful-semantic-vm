"""Client for the NL_TEACH frozen LLM service (nl_llm_service.py). Every call is logged (CALLS)."""
import json, os, time, urllib.request
URL = os.environ.get("SEMVM_LLM_URL", "http://127.0.0.1:8765"); CALLS = []


def _post(path, obj):
    t0 = time.time(); req = urllib.request.Request(URL + path, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=600).read()); CALLS.append({"path": path, "seconds": round(time.time() - t0, 3), "n": len(obj.get("continuations", []))}); return out


def choose(prompt, continuations): return _post("/choose", {"prompt": prompt, "continuations": continuations})["logprobs"]


def generate(prompt, max_new_tokens=200, stop=("\n\n",)): return _post("/generate_stop", {"prompt": prompt, "max_new_tokens": max_new_tokens, "stop": list(stop)})["text"]


def info(): return json.loads(urllib.request.urlopen(URL + "/frozen", timeout=600).read())
