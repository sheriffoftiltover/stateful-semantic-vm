"""Backend-equivalence helper: compare two job directories produced from the same JobSpec on different backends.
REQUIRED equal: scientific-config hash, dataset / input hashes, init hash, batch order + per-step batch ids, objective-component keys, artifact schema
(set of relative file paths, excluding backend-specific logs). REPORTED: max |diff| of per-step losses and of parameters (bit equality across GPU
architectures is not required; drift is shown, never silently accepted)."""
import os, json, glob

BACKEND_ONLY = {"MODAL_JOB.json", "job_stdout.log"}


def schema(d): return sorted(os.path.relpath(p, d) for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p) and os.path.basename(p) not in BACKEND_ONLY and "file_access_audit" not in p)


def rd(p): return [json.loads(l) for l in open(p) if l.strip()]


def compare(a, b, tag):
    import torch
    R = {}; ca = json.load(open(os.path.join(a, "runs", f"{tag}_scientific_config.json"))); cb = json.load(open(os.path.join(b, "runs", f"{tag}_scientific_config.json")))
    R["config_hash_equal"] = ca["sha256"] == cb["sha256"]; R["inputs_equal"] = ca["config"]["inputs"] == cb["config"]["inputs"]; R["init_equal"] = ca["config"]["init"] == cb["config"]["init"]
    R["batch_order_equal"] = json.load(open(os.path.join(a, "runs", f"{tag}_batch_order.json"))) == json.load(open(os.path.join(b, "runs", f"{tag}_batch_order.json")))
    sa, sb = rd(os.path.join(a, "runs", f"{tag}_steps.jsonl")), rd(os.path.join(b, "runs", f"{tag}_steps.jsonl"))
    R["step_batches_equal"] = [x["batch_sha256"] for x in sa] == [x["batch_sha256"] for x in sb]; R["objective_components_equal"] = [sorted(x) for x in sa] == [sorted(x) for x in sb]
    R["step_loss_max_abs_diff"] = max((abs(x["loss"] - y["loss"]) for x, y in zip(sa, sb)), default=None)
    ka = torch.load(os.path.join(a, "checkpoints", f"{tag}.pt"), weights_only=False)["state"]; kb = torch.load(os.path.join(b, "checkpoints", f"{tag}.pt"), weights_only=False)["state"]
    R["param_max_abs_diff"] = max(float((ka[k].double() - kb[k].double()).abs().max()) for k in ka)
    R["artifact_schema_equal"] = schema(a) == schema(b); R["schema_diff"] = sorted(set(schema(a)) ^ set(schema(b)))[:20]
    req = ("config_hash_equal", "inputs_equal", "init_equal", "batch_order_equal", "step_batches_equal", "objective_components_equal", "artifact_schema_equal")
    R["pass"] = all(R[k] for k in req); return R
