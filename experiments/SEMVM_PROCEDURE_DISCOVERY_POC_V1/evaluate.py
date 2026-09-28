"""Procedure-discovery evaluation (spec §43-§47, §59-§61, §69). Modes: GOLD_PROC (independent gold procedures installed / invoked directly -> tests
the runtime) and DISCOVERED (teaching -> both proposers -> verification -> :accept -> retrieval -> execution). Each RESTART = every process
terminated: the segment process exits AND (DISCOVERED) the frozen LLM service is killed and restarted. Expected outcomes: scenarios/oracle.py.
python evaluate.py --suite dev|locked_test [--modes GOLD_PROC,DISCOVERED]"""
import os, sys, json, glob, subprocess, argparse, shutil, time, collections, signal, urllib.request
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "procedure")]
import retrieval as RT
sys.path.insert(0, os.path.join(ROOT, "scenarios")); import catalog as _CAT; COMPOSITE_NAME = _CAT.COMPOSITE["name"]   # evaluator-only (the runtime never imports scenarios/)
LLM_PY = os.environ.get("SEMVM_LLM_PYTHON", sys.executable)  # release portability edit (was an absolute venv path)
GATES = {"SOURCE_REPLAY_EXACT": 1.0, "COUNTERFACTUAL_EXACT": 1.0, "ROLLBACK_EXACT": 1.0, "RESTART_PROCEDURE_EXACT": 1.0, "PROCEDURE_RETRIEVAL_EXACT": .95, "ARGUMENT_BINDING_EXACT": .95, "SCENARIO_EXACT": .90}
m_ = lambda v: round(sum(v) / len(v), 4) if v else None
SVC = {"p": None}


def llm_start():
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=os.environ.get("SEMVM_LLM_GPU", "1")); log = open(os.path.join(ROOT, "results", "llm_service.log"), "a")
    SVC["p"] = subprocess.Popen([LLM_PY, os.path.join(ROOT, "procedure", "llm_service.py"), "--port", "8765"], env=env, stdout=log, stderr=log)
    for _ in range(300):
        try: urllib.request.urlopen("http://127.0.0.1:8765/", timeout=2); return
        except Exception: time.sleep(1)
    raise SystemExit("LLM service did not start")


def llm_stop():
    if SVC["p"]: SVC["p"].send_signal(signal.SIGTERM); SVC["p"].wait(timeout=60); SVC["p"] = None


def llm_frozen():
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8765/frozen", timeout=600).read())


def run_scenario(suite, sc, mode, work):
    d = os.path.join(work, mode, sc["scenario_id"]); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    p = os.path.join(ROOT, "scenarios", suite, f"{sc['scenario_id']}.json"); cuts = [i for i, t in enumerate(sc["turns"]) if t["kind"] == "RESTART"]; segs = []; a = 0
    for c in cuts + [len(sc["turns"])]: segs.append((a, c)); a = c + 1
    turns = {}; infos = []
    for j, (a, b) in enumerate(segs):
        if j > 0 and mode == "DISCOVERED": llm_stop(); llm_start()                     # RESTART: terminate every process (incl. the LLM service)
        o = os.path.join(d, f"seg_{a}_{b}.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "run_segment.py"), "--scenario", p, "--dir", d, "--mode", mode, "--start", str(a), "--end", str(b), "--out", o], capture_output=True, text=True)
        if r.returncode: raise SystemExit(f"segment failed {sc['scenario_id']} {a}-{b}: {r.stderr[-3000:]}")
        R = json.load(open(o)); infos.append(R["info"])
        for t in R["turns"]: turns[t["turn"]] = t
    return turns, infos


def status_ok(exp, got):
    if exp == "REJECTED": return got.startswith("REJECTED")
    return exp == got


def metrics(S, RES, mode):
    M = collections.defaultdict(list); tax = collections.Counter(); per = {}; gen = collections.defaultdict(list); acct = collections.defaultdict(list)
    for sc in S:
        sid = sc["scenario_id"]; tr = RES[sid][0]; ok_all = True; first = None; after_restart = False
        for i, (t, e) in enumerate(zip(sc["turns"], sc["expected"])):
            if t["kind"] == "RESTART": after_restart = True; continue
            # GOLD_PROC: discovery turns are bypassed by definition (not under test in that mode)
            g = tr[i]; st_ok = status_ok(e["status"], g["status"]) or (mode == "GOLD_PROC" and g["status"] == "GOLD_BYPASS"); ret_ok = ("return" not in e) or g.get("return") == e.get("return"); state_ok = g["STATE"] == e["state"]
            ver_ok = (g.get("versions") == t.get("versions")) if t.get("versions") else True
            ok = st_ok and ret_ok and state_ok and ver_ok
            kind = t["kind"]; c = (t.get("text") or "").split()[:1]
            disc = kind == "CMD" and c and (c[0] in (":endteach", ":endrevise", ":learn", ":save-last-as") or c[0] == ":propose")
            if disc and mode == "DISCOVERED" and g.get("discovery"):
                D = g["discovery"]; P = D["paths"]
                if not c[0] == ":propose":
                    for path in ("deterministic", "llm"):
                        if path in P:
                            prop_valid = bool(P[path].get("tests")) and P[path]["tests"][0] == ["static_validation", True]
                            M[f"PROCEDURE_PROPOSAL_VALID_{path}"].append(prop_valid)
                            if e["status"] == "VERIFIED": M[f"DISCOVERY_VERIFIED_{path}"].append(P[path].get("status") == "VERIFIED")
                    if e["status"] == "VERIFIED": M["DISCOVERY_VERIFIED_union"].append(any(P.get(x, {}).get("status") == "VERIFIED" for x in ("deterministic", "llm")))
                    if D.get("chosen") and D["status"] == "VERIFIED":
                        ch = P[D["chosen"]]; M["SOURCE_REPLAY_EXACT"].append(all(ok_ for n, ok_ in ch["tests"] if n.startswith("replay")))
                        neg = [ok_ for n, ok_ in ch["tests"] if n.startswith(("neg_", "txn_"))]; M["NEGATIVE_CASE_SAFE"] += neg; M["ROLLBACK_EXACT"] += [ok_ for n, ok_ in ch["tests"] if n.startswith("txn_")]
                        acct["verify_seconds"].append(ch.get("verify_seconds", 0)); acct["proposal_seconds_llm"].append(P.get("llm", {}).get("seconds", 0))
                else:
                    M["VERIFY_FALSE_ACCEPT"].append(g["status"] == "VERIFIED")
            if kind in ("RUN", "REQUEST") and t.get("plan") is not None:
                if t.get("novel_args"): M["COUNTERFACTUAL_EXACT"].append(ok); gen["ARGUMENT_GENERALIZATION"].append(ok)
                else: gen["REPLAY"].append(ok)
                if after_restart: M["RESTART_PROCEDURE_EXACT"].append(ok)
                if e["status"] == "VM_EXEC_ERROR": M["ROLLBACK_EXACT"].append(ok)
                acct["execution_seconds"].append(g.get("seconds", 0)); acct["vm_ops"].append(g.get("vm_ops") or 0)
            if kind == "REQUEST":
                gen["SURFACE_GENERALIZATION"].append(ok)
                if e["status"] == "CLARIFY": M["PROCEDURE_RETRIEVAL_EXACT"].append(g["status"] == "CLARIFY"); M["NEGATIVE_CASE_SAFE"].append(g["status"] == "CLARIFY")
                else:
                    gp = g.get("plan"); M["PROCEDURE_RETRIEVAL_EXACT"].append(bool(gp) and gp.split("(")[0] == t["plan"]["call"])
                    M["PROCEDURE_RETRIEVAL_BEHAVIORAL"].append((bool(gp) and gp.split("(")[0] == t["plan"]["call"]) or ok)       # equivalent plan with identical status / return / state
                    if gp and gp.split("(")[0] == t["plan"]["call"]: M["ARGUMENT_BINDING_EXACT"].append(gp == RT.plan_str(t["plan"]))
                acct["retrieval_seconds"].append(g.get("seconds", 0)); acct["llm_calls_per_request"].append(g.get("llm_calls", 0))
                rr = g.get("retrieval") or {}
                if e["status"] != "CLARIFY":
                    M["BEHAVIORAL_PLAN_EXACT"].append(ok)
                    if g["status"] == "CLARIFY": M["FALSE_AMBIGUITY_COUNT"].append(1)
                    if t["plan"]["call"] == COMPOSITE_NAME:           # an equivalent ACTIVE stored procedure existed for this computation
                        M["STORED_PROCEDURE_REUSE_EXACT"].append(bool(g.get("plan")) and g["plan"].split("(")[0] == COMPOSITE_NAME)
                        M["DYNAMIC_RECOMPOSITION_RATE"].append(bool(g.get("plan")) and g["plan"].split("(")[0] != COMPOSITE_NAME)
                if rr.get("collapsed") or rr.get("canonicalized_to"): M["EQUIVALENT_PLAN_COLLAPSE_COUNT"].append(1)
            if t.get("composition") == "L1": M["PROCEDURE_COMPOSITION_EXACT_L1"].append(ok); gen["COMPOSITION_GENERALIZATION"].append(ok)
            if t.get("composition") == "L2": M["PROCEDURE_COMPOSITION_EXACT_L2_save"].append(ok)
            if kind == "RUN" and t.get("family") == "__composite": M["PROCEDURE_COMPOSITION_EXACT_L2_invoke"].append(ok); gen["COMPOSITION_GENERALIZATION"].append(ok)
            if kind == "CMD" and c and c[0] in (":teach", ":example", ":revise"): acct["first_time_teach_turns"].append(1)
            if not ok and ok_all:
                ok_all = False
                if kind == "STEP": first = "PD_TRACE"
                elif disc:
                    if e["status"] == "VERIFIED": first = "PD_VERIFY_FALSE_REJECT" if not (g.get("discovery") or {}).get("paths", {}).get("deterministic", {}).get("reason") else "PD_PARAMETER"
                    elif e["status"] == "REJECTED": first = "PD_VERIFY_FALSE_ACCEPT"
                    else: first = "PD_PROGRAM"
                elif kind == "REQUEST":
                    gp = g.get("plan")
                    if t.get("composition") == "L1" and gp != RT.plan_str(t["plan"] or {"call": "", "args": {}}): first = "PR_COMPOSE"
                    elif e["status"] == "CLARIFY" or not gp or gp.split("(")[0] != t["plan"]["call"]: first = "PR_RETRIEVE"
                    elif gp != RT.plan_str(t["plan"]): first = "PR_ARGUMENT"
                    else: first = "ROLLBACK" if e["status"] == "VM_EXEC_ERROR" else ("STORE" if after_restart else "PD_PROGRAM")
                elif kind == "RUN": first = "ROLLBACK" if e["status"] == "VM_EXEC_ERROR" else ("PR_COMPOSE" if t.get("family") == "__composite" else ("STORE" if after_restart and st_ok and not state_ok else "PD_PROGRAM"))
                else: first = "VM_EXEC"
        last = max(k for k in tr); M["FINAL_STATE_EXACT"].append(tr[last]["STATE"] == sc["expected"][last]["state"]); M["SCENARIO_EXACT"].append(ok_all)
        per[sid] = {"category": sc["category"], "exact": ok_all, "first_failure": first}
        if not ok_all: tax[first] += 1
    R = {k: m_(v) for k, v in M.items()}; R.update({f"n_{k}": len(v) for k, v in M.items()})
    for k in ("FALSE_AMBIGUITY_COUNT", "EQUIVALENT_PLAN_COLLAPSE_COUNT"): R[k] = len(M.get(k, []))
    R["generalization"] = {k: {"acc": m_(v), "n": len(v)} for k, v in gen.items()}; R["accounting"] = {k: {"mean": m_(v), "n": len(v), "sum": round(sum(v), 3)} for k, v in acct.items()}
    R["failure_taxonomy"] = dict(tax); R["per_scenario"] = per
    R["by_category"] = {c: m_([v["exact"] for v in per.values() if v["category"] == c]) for c in sorted({v["category"] for v in per.values()})}
    if mode == "DISCOVERED": R["gates"] = {k: {"threshold": th, "value": R.get(k), "pass": R.get(k) is not None and R[k] >= th} for k, th in GATES.items()}
    return R


def rescore(suite, mode):
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", suite, "*.json")))]; E = json.load(open(os.path.join(ROOT, "results", suite, f"EVAL_{mode}.json")))
    RES = {k: ({int(i): t for i, t in v.items()}, []) for k, v in E["traces"].items()}; R = metrics(S, RES, mode)
    for k in ("seconds", "llm_frozen", "capability"):
        if k in E["results"]: R[k] = E["results"][k]
    E["results"] = R; json.dump(E, open(os.path.join(ROOT, "results", suite, f"EVAL_{mode}.json"), "w"), indent=1, default=str); return R


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=["dev", "locked_test"]); ap.add_argument("--modes", default="GOLD_PROC,DISCOVERED"); ap.add_argument("--rescore", action="store_true"); a = ap.parse_args()
    if a.rescore:
        for mode in a.modes.split(","): R = rescore(a.suite, mode); print(mode, json.dumps({k: v for k, v in R.items() if k not in ("per_scenario",)}, default=str)[:3000])
        return
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]; work = os.path.join(ROOT, "results", a.suite, "work"); OUT = {}
    for mode in a.modes.split(","):
        t0 = time.time()
        if mode == "DISCOVERED": llm_stop(); llm_start(); fr0 = llm_frozen()
        RES = {sc["scenario_id"]: run_scenario(a.suite, sc, mode, work) for sc in S}
        R = metrics(S, RES, mode); R["seconds"] = round(time.time() - t0, 1)
        if mode == "DISCOVERED":
            fr1 = llm_frozen(); R["llm_frozen"] = {"param_hash_first_service": fr0["param_hash_at_load"], "param_hash_end": fr1["param_hash_now"], "identical_across_restarts": fr0["param_hash_at_load"] == fr1["param_hash_now"] == fr1["param_hash_at_load"],
                                                   "files_sha256": fr1["files_sha256"], "n_parameters": fr1["n_parameters"], "optimizer": None}; llm_stop()
        infos = [i for v in RES.values() for i in v[1]]
        R["capability"] = {"active_procedures_mean_final": m_([len(v[1][-1]["active"]) for v in RES.values()]), "library_bytes_mean": m_([v[1][-1]["lib_bytes"] for v in RES.values()]),
                           "world_bytes_mean": m_([v[1][-1]["world_bytes"] for v in RES.values()]), "llm_calls_total": sum(len(i["llm_calls"]) for i in infos)}
        json.dump({"results": R, "traces": {k: {str(i): t for i, t in v[0].items()} for k, v in RES.items()}}, open(os.path.join(ROOT, "results", a.suite, f"EVAL_{mode}.json"), "w"), indent=1, default=str)
        OUT[mode] = R; print(mode, json.dumps({k: v for k, v in R.items() if k not in ("per_scenario",)}, indent=1, default=str)[:6000], flush=True)
    json.dump(OUT, open(os.path.join(ROOT, "results", a.suite, "EVAL_SUMMARY.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
