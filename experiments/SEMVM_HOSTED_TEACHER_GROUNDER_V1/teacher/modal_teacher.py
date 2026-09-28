"""HTG: the SAME frozen checkpoint (parent Volume semvm-pdx-gptoss120b, manifest locks/HOSTED_CHECKPOINT_MANIFEST.json) serves the TEACHER and the GROUNDER roles (separate prompts / requests / caches; no shared context). Parent docstring:
Frozen hosted TEACHER for SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1 (Amendment 001): openai/gpt-oss-120b, self-hosted on ONE Modal H100
with vLLM (OpenAI-compatible endpoint), weights frozen in a Modal Volume and hashed file-by-file (sha256) at download.
  modal run teacher/modal_teacher.py::download          # CPU container: fetch + hash the checkpoint into the volume (once)
  modal deploy teacher/modal_teacher.py                  # endpoint; scales to zero when idle (billed only while a container runs)
  modal app stop semvm-pdx-teacher                       # HARD TEACHER DISCONNECT (the teacher no longer exists)
The endpoint requires an API key (vLLM --api-key) held in the Modal secret 'semvm-pdx-teacher-key'; it is never logged.
A heartbeat thread writes container-alive timestamps to the Modal Dict 'semvm-pdx-meter' (the local cost meter / hard budget cap)."""
import os, json, time, hashlib, subprocess, threading
import modal

APP = "semvm-htg-hosted"; MODEL = "openai/gpt-oss-120b"; WDIR = "/w/gpt-oss-120b"; PORT = 8000
VLLM_VERSION = "0.11.0"; HF_HUB_VERSION = "0.35.3"
app = modal.App(APP)
vol = modal.Volume.from_name("semvm-pdx-gptoss120b", create_if_missing=True)
meter = modal.Dict.from_name("semvm-htg-meter", create_if_missing=True)
dl_image = modal.Image.debian_slim(python_version="3.12").pip_install(f"huggingface_hub[hf_transfer]=={HF_HUB_VERSION}").env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
vllm_image = (modal.Image.debian_slim(python_version="3.12").pip_install(f"vllm=={VLLM_VERSION}", f"huggingface_hub=={HF_HUB_VERSION}")
              .env({"VLLM_USE_V1": "1", "HF_HUB_OFFLINE": "1"}))


@app.function(image=dl_image, volumes={"/w": vol}, timeout=4 * 3600, cpu=8, memory=16384)
def download():
    from huggingface_hub import snapshot_download, HfApi
    info = HfApi().model_info(MODEL); rev = info.sha
    snapshot_download(MODEL, revision=rev, local_dir=WDIR, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja", "LICENSE*", "*.md"],
                      ignore_patterns=["original/*", "metal/*"])
    files = {}
    for root, _, fs in os.walk(WDIR):
        for f in sorted(fs):
            p = os.path.join(root, f); rel = os.path.relpath(p, WDIR)
            if rel.startswith(".cache"): continue
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for b in iter(lambda: fh.read(1 << 24), b""): h.update(b)
            files[rel] = {"sha256": h.hexdigest(), "bytes": os.path.getsize(p)}
    man = {"model": MODEL, "hf_revision": rev, "files": files, "total_bytes": sum(v["bytes"] for v in files.values()),
           "checkpoint_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(), "downloaded": time.strftime("%FT%TZ", time.gmtime())}
    json.dump(man, open("/w/WEIGHTS_MANIFEST.json", "w"), indent=1); vol.commit(); return man


def _heartbeat(cid):
    t0 = time.time()
    while True:
        try: meter[cid] = {"start": t0, "last": time.time(), "gpu": "H100"}
        except Exception: pass
        time.sleep(15)


@app.function(image=vllm_image, gpu="H100", volumes={"/w": vol}, secrets=[modal.Secret.from_name("semvm-pdx-teacher-key")],
              scaledown_window=180, timeout=6 * 3600, max_containers=1, min_containers=0)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PORT, startup_timeout=30 * 60)
def serve():
    cid = os.environ.get("MODAL_TASK_ID", f"c{int(time.time())}"); threading.Thread(target=_heartbeat, args=(cid,), daemon=True).start()
    cmd = ["vllm", "serve", WDIR, "--served-model-name", "gpt-oss-120b", "--host", "0.0.0.0", "--port", str(PORT), "--api-key", os.environ["TEACHER_API_KEY"],
           "--max-model-len", "16384", "--gpu-memory-utilization", "0.92", "--max-num-seqs", "32", "--seed", "0"]
    subprocess.Popen(cmd)


@app.local_entrypoint()
def main():
    print(json.dumps({k: v for k, v in download.remote().items() if k != "files"}, indent=1))
