"""RCI Stage 0C recovery-ceiling diagnostic (spec §15-§21; spec/RECOVERY_CEILING_DIAGNOSTIC_V1.json). NON-confirmatory, acquisition only.
The five parent TTP FINAL_DEV (attempt 2) Arm D targets that failed exact learning, re-run as Arm D (hosted lesson, hosted recovery, hosted
grounder) with ONLY resource ceilings relaxed: teacher max_tokens 16384, 20 teacher turns / target, 5 clarifications and 5 rephrases per slot,
5 demonstrations, teacher example-value pool >= 4 per class. Pool augmentation (frozen rule): the parent teacher pool is extended with values
of the scenario's own eval pool, in eval-pool order, preferring values for which the registered reference of the failed target has a
non-empty constrained search in the fixture (witnessed), until 4 values per class. Go / no-go: 0 of 5 recovered -> STOP (RECOVERY_CAPABILITY_LIMIT).
python rci_ceiling.py"""
import os, sys, json, glob, shutil, subprocess, copy, time, threading
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "evaluator"), os.path.join(ROOT, "scenarios"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"),
                                                                 os.path.join(ROOT, "core", "neural", "vendor"), os.path.join(ROOT, "teacher"), os.path.join(ROOT, "student")]
import behavior as BE, pdx_evaluate as PE, htg_evaluate as HE, lang as L
HE.TEACHER_APP = PE.TEACHER_APP = "semvm-rci-hosted"          # (added after the Stage 0C run: its teardown targeted the wrong app; repaired manually)
PARENT = os.path.join(os.path.dirname(ROOT), "SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1")
TARGETS = [("dev-009-S9", "count_calls_for_time_person", "provider truncation / composite"), ("dev-016-S12", "move_visit_and_parent", "false clarification / recovery budget"),
           ("dev-018-S14L", "count_open_calls_with", "evidence conflict / value-pool insufficiency"), ("dev-019-S14L", "count_open_calls_with", "evidence conflict / value-pool insufficiency"),
           ("dev-023-S15", "close_oldest_open_request", "teacher-turn budget exhaustion")]
BUDGET = {"max_teacher_turns_per_target": 20, "max_clarification_exchanges_per_slot": 5, "max_rephrase_exchanges_per_slot": 5, "max_demonstrations_per_target": 5}
MAX_TOKENS = 16384; POOL = 4
CLS = {"people": "PERSON", "times": "TIME", "places": "PLACE", "topics": "TOPIC"}


def augment(sc, target):
    it = next(i for i in sc["curriculum"] if i["name"] == target); Ws = BE.worlds(sc); pool = copy.deepcopy(sc["teacher_pool"]); added = {}
    for key, cls in CLS.items():
        cand = [v for v in sc["eval_pool"].get(key, []) if v not in pool.get(key, [])]
        par = [p for p, t in it["sig"].items() if t == cls]
        def witnessed(v):
            if not par: return False
            ex = {p: (v if p in par else (pool[[k for k, c in CLS.items() if c == t][0]][0])) for p, t in it["sig"].items()}
            ref = BE.reference_steps(sc, it, ex)
            return bool(ref) and not HE._oracle_vacuous(ref, Ws)
        order = [v for v in cand if witnessed(v)] + [v for v in cand if not witnessed(v)]
        need = max(0, POOL - len(pool.get(key, []))); pool[key] = pool.get(key, []) + order[:need]; added[key] = order[:need]
    return pool, added


def main():
    od = os.path.join(ROOT, "results", "ceiling"); shutil.rmtree(od, ignore_errors=True); os.makedirs(od); sd = os.path.join(ROOT, "scenarios", "ceiling"); shutil.rmtree(sd, ignore_errors=True); os.makedirs(sd)
    rows = {}; env0 = dict(os.environ, RCI_BUDGET_OVERRIDE=json.dumps(BUDGET))
    import client as CL
    PE.teacher_up(); meter0 = CL.meter_usd(); sec = PE.secrets_env()
    def run(sid, target, label):
        sc = json.load(open(os.path.join(PARENT, "scenarios", "dev", sid + ".json"))); pool, added = augment(sc, target)
        sc = dict(sc, teacher_pool=pool, suite="ceiling", ceiling_note={"parent_scenario_sha": None, "added_pool_values": added}); p = os.path.join(sd, sid + ".json"); json.dump(sc, open(p, "w"), indent=1)
        d = os.path.join(od, "work", "CEILING_D", sid); os.makedirs(d); o = os.path.join(d, "acq.json")
        env = PE.env_clean(PE.WORKERS[0][1], sec); env.update(RCI_BUDGET_OVERRIDE=json.dumps(BUDGET))
        cmd = [sys.executable, os.path.join(ROOT, "run_acq.py"), "--scenario", p, "--dir", d, "--mode", "TEACHER", "--out", o, "--grounder", "HOSTED", "--arm", "CEILING_D", "--recovery", "HOSTED",
               "--teacher-max-tokens", str(MAX_TOKENS), "--backend", "MODAL", "--model", "openai/gpt-oss-120b", "--reasoning", "high"]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        A = json.load(open(o)) if os.path.exists(o) else {"error": r.stderr[-2000:]}
        rows[sid] = {"target": target, "parent_failure": label, "added_pool_values": added, "acq": A}
    th = [threading.Thread(target=run, args=t) for t in TARGETS]; [t.start() for t in th]; [t.join() for t in th]
    HO = HE.teardown("ceiling"); HO["meter_usd_at_deploy"] = meter0
    try: HO["meter_usd_after"] = CL.meter_usd()
    except Exception: pass
    out = {"diagnostic": "RCI Stage 0C (non-confirmatory; cannot earn LOCKED)", "budget": BUDGET, "teacher_max_tokens": MAX_TOKENS, "pool_size": POOL, "handoff": HO, "targets": {}}
    import procstore as PS
    for sid, target, label in TARGETS:
        R = rows[sid]; A = R["acq"]; sc = json.load(open(os.path.join(sd, sid + ".json"))); it = next(i for i in sc["curriculum"] if i["name"] == target)
        if A.get("error"): out["targets"][sid] = {"target": target, "error": A["error"][-500:]}; continue
        lib = PS.Library(os.path.join(od, "work", "CEILING_D", sid, "procedures.sqlite")); act = lib.active(target); h = L.program_hash(act) if act else None; lib.close()
        learned = h == PE.gold_hash(it); O = next(o for o in A["targets"] if o["name"] == target)
        hc = [c for c in A.get("hosted_calls", [])]; qs = O["student_questions"]
        rec_start = next((k for k, l in enumerate(O.get("teacher_log", [])) if l["kind"] in ("RESTATE_SLOT", "RESTATE_OBSCURED", "CLARIFY_REFERENCE", "NEW_DEMO")), None)
        turns_after = (O["teacher_turns"] - rec_start) if rec_start is not None else 0
        out["targets"][sid] = {"target": target, "parent_failure": label, "added_pool_values": R["added_pool_values"], "RECOVERED_EXACTLY": learned, "LEARNED_EXACTLY": learned, "status": O["status"], "fail": O.get("fail"),
                               "teacher_turns": O["teacher_turns"], "teacher_turns_after_recovery_start": turns_after,
                               "cost_band": "LOW-COST" if turns_after <= 4 else "MODERATE" if turns_after <= 10 else "HIGH",
                               "grounder_calls": sum(1 for c in hc if c.get("role") == "grounder"), "grounder_retries": sum(max(0, len(r.get("attempts") or []) - 1) for D in O["demos"] for r in D["results"]),
                               "clarification_events": sum(1 for q in qs if q["kind"] == "CLARIFY_REFERENCE"), "clarification_attempts": sum(1 for q in qs if q["kind"] == "CLARIFY_REFERENCE"),
                               "rephrase_attempts": sum(1 for q in qs if q["kind"] in ("RESTATE_SLOT", "RESTATE_OBSCURED")), "demonstrations": len(O["demos"]),
                               "demo_ends": [D["end"] for D in O["demos"]], "input_tokens": sum(c.get("input_tokens") or 0 for c in hc), "output_tokens": sum(c.get("output_tokens") or 0 for c in hc),
                               "provider_truncations": sum(c.get("truncations") or 0 for c in hc), "transcript": f"teaching_traces/ceiling/CEILING_D/{sid}.json"}
    n = sum(1 for v in out["targets"].values() if v.get("RECOVERED_EXACTLY")); out["recovered_exactly"] = f"{n}/5"
    out["go_no_go"] = "GO (>= 1 of 5 recovered exactly; Stage 1 may proceed)" if n >= 1 else "STOP: RECOVERY_CAPABILITY_LIMIT"
    json.dump(out, open(os.path.join(ROOT, "results", "RECOVERY_CEILING_DIAGNOSTIC.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "targets"}, indent=1, default=str))
    for sid, v in out["targets"].items(): print(sid, {k: v.get(k) for k in ("target", "RECOVERED_EXACTLY", "status", "fail", "teacher_turns", "cost_band", "demo_ends", "provider_truncations")})


if __name__ == "__main__":
    main()
