# SEMVM execution backend v1

This is the reusable **LOCAL ⇄ MODAL** execution layer, implementing §25–§47 of `SEMVM_MULTI_RELATION_V1_1_MODAL_LOCAL_DEVELOPMENT_PROTOCOL.md`. It is integrated with `infrastructure/semvm_portability_kit_v1/`, which provides the bundle, verifier, isolation harness and resumable-trainer pattern.

**Principle.** The scientific experiment definition is separate from the execution backend.
- A job is a `JobSpec`. Its scientific part is `job_type` + `args`. Its infrastructure part is `profile`, `timeout_s` and `local_device`.
- On every backend the job runs **the same command**: `python <experiment>/run_job.py --spec-json <spec> --output results/<job_id>`.
- Backends differ only in where that command runs and how its output directory is transported back.

| File | Role |
|---|---|
| `jobspec.py` | `JobSpec` dataclass; `scientific_hash()` covers only the scientific fields |
| `profiles.json` | provider-neutral resource profiles (`cpu-small`, `cpu-large`, `gpu-small`, `gpu-medium`), mapped separately for local and Modal |
| `backends/local.py` | subprocesses with bounded parallelism; device through `CUDA_VISIBLE_DEVICES` |
| `backends/modal_backend.py` | the **only** module importing `modal`: the image comes from the experiment's own `requirements-lock.txt`, the experiment tree is mounted at `/exp`, outputs go to a Volume at `/results/<job_id>`, and `collect()` restores the local layout |
| `cost.py` | budget state, pre-submission guard (hard cap, review threshold, per-stage caps, safety margin), job registry |
| `equivalence.py` | compares two job directories from the same spec on different backends. Required equal: config hash, inputs, init, batch order, per-step batches, objective components, artifact schema. Loss and parameter drift is reported. |

**Rules for experiments that use it:**
1. `run_job.py` is the single scientific entry point, and it dispatches on `job_type`.
2. Scientific code never imports `modal` and never branches on the backend.
3. Operational state lives under `results/`, which is not hashed.
4. Every experiment **vendors** a byte-identical copy of this package under `backends_vendor/`, so its portable bundle is self-contained. Hashes are in `EXEC_BACKEND_SHA256SUMS`.
5. Future providers (SLURM, RunPod, AWS …) add `backends/<name>.py` with the same `run` / `map` / `wait` / `collect` methods, and no scientific code changes.
