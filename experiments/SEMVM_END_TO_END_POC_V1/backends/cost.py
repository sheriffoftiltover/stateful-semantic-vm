"""Budget state + guard (before submission) + job registry + cost report. State lives in results/ (never hashed as a scientific input)."""
import os, json, time


class Budget:
    def __init__(self, root, policy):
        self.root = root; self.state_p = os.path.join(root, "results", "MODAL_BUDGET_STATE.json"); self.reg_p = os.path.join(root, "results", "MODAL_JOB_REGISTRY.json"); self.policy = policy

    def state(self):
        if not os.path.exists(self.state_p): raise SystemExit("STOP — MODAL_BUDGET_STATE.json missing (record current rates first)")
        return json.load(open(self.state_p))

    def registry(self): return json.load(open(self.reg_p)) if os.path.exists(self.reg_p) else {"jobs": []}

    def spent(self, stage=None): return sum(j.get("est_cost_usd", 0) for j in self.registry()["jobs"] if stage is None or j.get("stage") == stage)

    def guard(self, projected, stage):
        s = self.spent(); st = self.spent(stage); tot = s + projected * (1 + self.policy["safety_margin"]); cap = self.policy["stage_caps_usd"].get(stage)
        print(f"[budget] total spent {s:.3f}; stage {stage} spent {st:.3f}; projected {projected:.3f} (+{int(self.policy['safety_margin'] * 100)}%) -> total {tot:.3f} "
              f"(stage cap {cap}, review {self.policy['review_threshold_usd']}, hard cap {self.policy['hard_cap_usd']})", flush=True)
        if tot > self.policy["hard_cap_usd"]: raise SystemExit("STOP — MODAL_HARD_BUDGET_GUARD")
        if tot > self.policy["review_threshold_usd"]: raise SystemExit("STOP — MODAL_REVIEW_THRESHOLD")
        if cap is not None and st + projected * (1 + self.policy["safety_margin"]) > cap: raise SystemExit(f"STOP — STAGE_BUDGET_GUARD ({stage} cap {cap})")

    def record(self, results, stage):
        R = self.registry()
        for r in results: R["jobs"].append({**r, "stage": stage, "recorded": time.strftime("%F %T %z")})
        json.dump(R, open(self.reg_p, "w"), indent=1)
        S = self.state(); S["current_estimated_spend_usd"] = round(self.spent(), 5); S["spend_by_stage"] = {k: round(self.spent(k), 5) for k in {j.get("stage") for j in R["jobs"]}}
        S["updated"] = time.strftime("%F %T %z"); json.dump(S, open(self.state_p, "w"), indent=1)
