"""Modal backend (the ONLY module that imports modal). Named modal_backend.py so it never shadows the `modal` package.
Image: debian_slim(python 3.10) + pip install from the experiment's environment/requirements-lock.txt (the same lock used locally) + the experiment
tree added at /exp (results/, outputs/, .venv*, __pycache__ excluded). Each JobSpec runs in its own container as
`python /exp/run_job.py --spec-json <spec> --output /results/<job_id>` on a Volume; collect() downloads results/<job_id>/ into the local layout,
so a Modal-produced job directory looks like a local one. Resource profile -> gpu / cpu / memory. Cost = container seconds x recorded rates."""
import os, json, time, subprocess


class ModalBackend:
    name = "modal"

    def __init__(self, root, profiles, app_name, volume_name, rates):
        import modal
        self.modal, self.root, self.profiles, self.rates = modal, root, profiles, rates; self.volume_name = volume_name
        self.app = modal.App(app_name)
        image = (modal.Image.debian_slim(python_version="3.10").pip_install_from_requirements(os.path.join(root, "environment", "requirements-lock.txt"))
                 .add_local_dir(root, "/exp", ignore=["results", "results/**", "outputs", "outputs/**", ".venv*", ".venv*/**", "**/__pycache__", "**/__pycache__/**"]))
        self.vol = modal.Volume.from_name(volume_name, create_if_missing=True)
        vol = self.vol

        @self.app.function(image=image, timeout=6 * 3600, volumes={"/results": vol}, serialized=True)
        def run_remote(spec_json: str) -> dict:
            import os, json, time, subprocess
            spec = json.loads(spec_json); out = os.path.join("/results", spec["job_id"]); t0 = time.time()
            if os.path.exists(os.path.join(out, "RUN_MANIFEST.json")): raise RuntimeError("job directory already used: " + spec["job_id"])
            os.makedirs(out, exist_ok=True)
            r = subprocess.run(["python", "/exp/run_job.py", "--spec-json", spec_json, "--output", out, "--backend-label", "modal"], capture_output=True, text=True)
            open(os.path.join(out, "job_stdout.log"), "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
            info = {"job_id": spec["job_id"], "rc": r.returncode, "container_s": round(time.time() - t0, 1), "modal_task_id": os.environ.get("MODAL_TASK_ID")}
            json.dump(info, open(os.path.join(out, "MODAL_JOB.json"), "w"), indent=1); vol.commit(); return info
        self.fn = run_remote; self.calls = {}; self.ctx = None

    def _opts(self, spec):
        p = self.profiles[spec.profile]["modal"]; o = {"cpu": p["cpu"], "memory": p["memory_mib"]}
        if p["gpu"]: o["gpu"] = p["gpu"]
        return o

    def __enter__(self): self.ctx = self.app.run(); self.ctx.__enter__(); return self

    def __exit__(self, *a): self.ctx.__exit__(*a)

    def map(self, specs, max_parallel=None):
        for s in specs:
            c = self.fn.with_options(**self._opts(s)).spawn(s.to_json()); self.calls[s.job_id] = (c, s, time.time()); print(f"[modal] spawned {s.job_id} ({s.profile}) call={c.object_id}", flush=True)
        return self.wait([s.job_id for s in specs])

    def run(self, spec): return self.map([spec])[0]

    def wait(self, job_ids):
        out = []
        for jid in job_ids:
            c, s, t0 = self.calls[jid]
            try: info = c.get(); err = None if info.get("rc") == 0 else f"rc={info.get('rc')}"
            except Exception as e: info, err = {"exception": repr(e), "container_s": round(time.time() - t0, 1)}, repr(e)
            p = self.profiles[s.profile]["modal"]; cs = info.get("container_s") or 0
            cost = cs * ((self.rates["gpu"].get(p["gpu"], 0) if p["gpu"] else 0) + p["cpu"] * self.rates["cpu_core"] + p["memory_mib"] / 1024 * self.rates["mem_gib"])
            out.append({"job_id": jid, "backend": "modal", "rc": info.get("rc"), "error": err, "container_s": cs, "profile": s.profile, "gpu": p["gpu"], "call_id": c.object_id, "est_cost_usd": round(cost, 5)})
            print(f"[modal] done {jid}: {err or 'ok'} {cs:.0f}s ~${cost:.3f}", flush=True)
        return out

    def collect(self, job_ids):
        paths = []
        for jid in job_ids:
            dst = os.path.join(self.root, "results", os.path.dirname(jid)); os.makedirs(dst, exist_ok=True)
            subprocess.run(["modal", "volume", "get", self.volume_name, jid, dst], check=False, capture_output=True); paths.append(os.path.join(self.root, "results", jid))
        return paths
