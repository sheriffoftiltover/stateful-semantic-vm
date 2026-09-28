"""RCI pooled Stage-1 decision (spec §41-§48, §65). Weighted pooled counts (sum of numerators / sum of denominators, never a mean of
percentages), per-replicate floors, per-replicate safety + backend gates, replicate failure-mode comparison. -> results/DEV_POOLED.json
python rci_pool.py [--a results/dev_a] [--b results/dev_b]"""
import os, sys, json, math, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT)
PRIMARY = {"LEARNED_PROCEDURE_EXACT": .90, "SCENARIO_EXACT": .90, "DISTILLED_SKILL_EXACT": .90, "GROUNDING_BEHAVIORAL_EXACT": .95}
FLOOR = .80


def pooled(reps, arm, k):
    num = sum((r["arms"][arm]["counts"].get(k) or [0, 0])[0] for r in reps); den = sum((r["arms"][arm]["counts"].get(k) or [0, 0])[1] for r in reps)
    return num, den


def decide(reps):
    out = {"arms": {}}
    for arm in ("B", "E", "F", "D"):
        if not all(arm in r["arms"] for r in reps): continue
        row = {}
        for k, th in PRIMARY.items():
            num, den = pooled(reps, arm, k); need = math.ceil(th * den) if den else None
            row[k] = {"per_replicate": [r["arms"][arm].get(k) for r in reps], "per_replicate_counts": [r["arms"][arm]["counts"].get(k) for r in reps],
                      "pooled": round(num / den, 4) if den else None, "pooled_counts": [num, den], "threshold": th, "min_successes": need, "pass": bool(den) and num >= need}
        for k in ("TEACHER_EPISODE_SUCCESS", "INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT", "RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT", "RECOVERY_TARGET_SUCCESS"):
            num, den = pooled(reps, arm, k); row[k] = {"per_replicate": [r["arms"][arm].get(k) for r in reps], "pooled": round(num / den, 4) if den else None, "pooled_counts": [num, den]}
        row["WRONG_BEHAVIORAL_ACTION_EXECUTED"] = [r["arms"][arm].get("WRONG_BEHAVIORAL_ACTION_EXECUTED") for r in reps]
        row["EARLIEST_CAUSE"] = [r["arms"][arm].get("EARLIEST_CAUSE") for r in reps]; row["WRONG_ACTION_EARLIEST_CAUSE"] = [r["arms"][arm].get("WRONG_ACTION_EARLIEST_CAUSE") for r in reps]
        row["RECOVERY_EVENT_SUCCESS"] = [r["arms"][arm].get("RECOVERY_EVENT_SUCCESS") for r in reps]; row["RECOVERY_EVENT_COUNT"] = [r["arms"][arm].get("RECOVERY_EVENT_COUNT") for r in reps]
        row["TARGETS_FAILED_AFTER_RECOVERY"] = [r["arms"][arm].get("TARGETS_FAILED_AFTER_RECOVERY", 0) for r in reps]
        row["TARGETS_FAILED_WITHOUT_RECOVERY"] = [r["arms"][arm].get("TARGETS_FAILED_WITHOUT_RECOVERY", 0) for r in reps]
        out["arms"][arm] = row
    D = [r["arms"]["D"] for r in reps if "D" in r["arms"]]
    safety = [all(g["pass"] for g in d["gates"].values() if g.get("group") == "safety") for d in D]
    backend = [all(g["pass"] for g in d["gates"].values() if g.get("group") == "backend") for d in D]
    floors = [all((d.get(k) or 0) >= FLOOR for k in PRIMARY) for d in D]
    acc = all(out["arms"]["D"][k]["pass"] for k in PRIMARY) if "D" in out["arms"] else False
    ca = [set((r["arms"]["D"].get("EARLIEST_CAUSE") or {})) for r in reps if "D" in r["arms"]]
    out["replicate_failure_modes"] = {"causes_per_replicate": [r["arms"]["D"].get("EARLIEST_CAUSE") for r in reps if "D" in r["arms"]],
                                      "repeated_causes": sorted(set.intersection(*ca)) if len(ca) == 2 else None,
                                      "replicate_specific_causes": [sorted(ca[0] - ca[1]), sorted(ca[1] - ca[0])] if len(ca) == 2 else None}
    out["decision"] = {"D_pooled_accuracy_pass": acc, "D_per_replicate_floor_pass": floors, "D_safety_pass_per_replicate": safety, "D_backend_pass_per_replicate": backend,
                       "controls_pass_per_replicate": [r.get("controls_pass") for r in reps],
                       "LOCKED_ELIGIBLE": bool(acc and all(floors) and all(safety) and all(backend) and all(r.get("controls_pass") for r in reps) and len(D) == 2)}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--a", default=os.path.join(ROOT, "results", "dev_a")); ap.add_argument("--b", default=os.path.join(ROOT, "results", "dev_b")); a = ap.parse_args()
    reps = [json.load(open(os.path.join(p, "RCI_SUMMARY.json"))) for p in (a.a, a.b)]
    out = decide(reps); json.dump(out, open(os.path.join(ROOT, "results", "DEV_POOLED.json"), "w"), indent=1, default=str); print(json.dumps(out["decision"], indent=1))


if __name__ == "__main__":
    main()
