"""Local backend: runs JobSpecs as subprocesses of the experiment's own interpreter. Infrastructure only: device selection via CUDA_VISIBLE_DEVICES
(from JobSpec.local_device), bounded parallelism, logs into results/<job_id>/job_stdout.log. Output: results/<job_id>/ directly."""
import os, sys, json, time, subprocess


class LocalBackend:
    name = "local"

    def __init__(self, root, profiles, python=sys.executable):
        self.root, self.profiles, self.python = root, profiles, python; self.handles = {}

    def _start(self, spec):
        out = os.path.join(self.root, "results", spec.job_id)
        if os.path.exists(os.path.join(out, "RUN_MANIFEST.json")): raise RuntimeError(f"job directory already used: {spec.job_id}")
        os.makedirs(out, exist_ok=True); env = dict(os.environ)
        if spec.local_device is not None: env["CUDA_VISIBLE_DEVICES"] = str(spec.local_device)
        cmd = [self.python, os.path.join(self.root, "run_job.py"), "--spec-json", spec.to_json(), "--output", out, "--backend-label", "local"]
        p = subprocess.Popen(cmd, env=env, stdout=open(os.path.join(out, "job_stdout.log"), "w"), stderr=subprocess.STDOUT)
        self.handles[spec.job_id] = (p, time.time(), spec); return spec.job_id

    def run(self, spec): jid = self._start(spec); return self.wait([jid])[0]

    def map(self, specs, max_parallel=None):
        mp = max_parallel or min(self.profiles[s.profile]["local"]["max_parallel"] for s in specs); pending = list(specs); running = []; res = []
        while pending or running:
            while pending and len(running) < mp: running.append(self._start(pending.pop(0)))
            time.sleep(2)
            for jid in list(running):
                if self.handles[jid][0].poll() is not None: running.remove(jid); res += self.wait([jid])
        return res

    def wait(self, job_ids):
        out = []
        for jid in job_ids:
            p, t0, spec = self.handles[jid]; rc = p.wait()
            out.append({"job_id": jid, "backend": "local", "rc": rc, "wall_s": round(time.time() - t0, 1), "est_cost_usd": 0.0})
        return out

    def collect(self, job_ids): return [os.path.join(self.root, "results", j) for j in job_ids]   # already in place
