"""HTG registered grounder preflight (spec §12, §58). Chooses the hosted grounder reasoning effort from {low, medium} on <= 8 DEV-design
scenarios, acquisition only, Arm B (SCRIPTED teacher x HOSTED grounder: identical registered lines, so the grounder is the only varying part).
FROZEN SELECTION RULE (registered before running): primary = LINE_GROUNDING_STRUCTURAL_EXACT on the scripted lines; a setting with any
WRONG_BEHAVIORAL_ACTION_EXECUTED > the other's is excluded first; if the primaries differ by < 0.02, choose 'low' (cheaper, fewer truncations).
Also recorded: truncations, provider failures, mean grounder output tokens, schema failures.
python preflight_grounder.py   (hosted endpoint must be deployed; writes results/PREFLIGHT.json)"""
import os, sys, json, glob, subprocess, shutil, collections
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT)
import htg_evaluate as HE, pdx_evaluate as PE
PICK = ["S3", "S4", "S6", "S8", "S11", "S15", "S16", "S18"]
SETTINGS = ["low", "medium"]


def main():
    allsc = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", "dev", "*.json")))]
    S = [next(s for s in allsc if s["stratum"] == k) for k in PICK]; out = {"scenarios": [s["scenario_id"] for s in S], "rule": __doc__.split("FROZEN SELECTION RULE")[1].split("Also recorded")[0].strip(), "settings": {}}
    for eff in SETTINGS:
        od = os.path.join(ROOT, "results", "preflight", eff); shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
        os.environ["HTG_GROUNDER_REASONING"] = eff
        ACQ = HE.acquire("B", S, od)
        for sid, A in ACQ.items():
            if isinstance(A, dict): A["_active_hashes"] = PE.active_hashes(od, "B", S).get(sid, {})
        REU = {s["scenario_id"]: {"turns": {}, "infos": []} for s in S}
        R = HE.htg_metrics("B", S, ACQ, REU, od, {}, {})
        lines = [r for A in ACQ.values() if isinstance(A, dict) for O in A.get("targets", []) for D in O["demos"] for r in D["results"]]
        hc = [c for A in ACQ.values() if isinstance(A, dict) for c in A.get("hosted_calls", []) if c.get("role") == "grounder"]
        out["settings"][eff] = {k: R.get(k) for k in ("LINE_GROUNDING_STRUCTURAL_EXACT", "n_LINE_GROUNDING_STRUCTURAL_EXACT", "GROUNDING_BEHAVIORAL_EXACT", "n_GROUNDING_BEHAVIORAL_EXACT",
                                                     "WRONG_BEHAVIORAL_ACTION_EXECUTED", "FALSE_CLARIFY_COUNT", "LINE_RELATION_BINDING_EXACT")}
        out["settings"][eff].update(errors=sum(1 for A in ACQ.values() if not isinstance(A, dict) or A.get("error")), provider_failures=sum(1 for A in ACQ.values() if isinstance(A, dict) for O in A.get("targets", []) if O["status"] in ("PROVIDER_FAILURE", "BUDGET_STOP")),
                                    schema_failures=sum(1 for r in lines if r.get("clarify_kind") == "SCHEMA"), truncations=sum(c.get("truncations") or 0 for c in hc), grounder_calls=len(hc),
                                    mean_output_tokens=round(sum(c.get("output_tokens") or 0 for c in hc) / max(1, len(hc)), 1))
    a, b = out["settings"]["low"], out["settings"]["medium"]
    if (a["WRONG_BEHAVIORAL_ACTION_EXECUTED"] or 0) > (b["WRONG_BEHAVIORAL_ACTION_EXECUTED"] or 0): ch = "medium"
    elif (b["WRONG_BEHAVIORAL_ACTION_EXECUTED"] or 0) > (a["WRONG_BEHAVIORAL_ACTION_EXECUTED"] or 0): ch = "low"
    else: ch = "medium" if (b["LINE_GROUNDING_STRUCTURAL_EXACT"] or 0) - (a["LINE_GROUNDING_STRUCTURAL_EXACT"] or 0) >= 0.02 else "low"
    out["selected_reasoning_effort"] = ch
    json.dump(out, open(os.path.join(ROOT, "results", "PREFLIGHT.json"), "w"), indent=1); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
