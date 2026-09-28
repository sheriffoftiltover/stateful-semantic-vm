"""PDX evaluation (spec §24-§40, §53-§55, §61-§66). Phase-separated:
  1 ACQUISITION  all scenarios (parallel student workers); teacher online only in TEACHER mode
  2 HANDOFF      TEACHER mode: `modal app stop semvm-pdx-teacher` (the teacher no longer exists) + unreachability check; every mode: the
                 student's teaching artefacts (learn/: transcripts, examples, snapshots) are moved out of the scenario directory
  3 REUSE        fresh processes, env scrubbed of TEACHER_* / GROQ_API_KEY, network guard (netguard/sitecustomize.py) blocks + logs every
                 non-loopback connection; the local student LLM service is killed + restarted at every RESTART
python pdx_evaluate.py --suite dev --modes GOLD_TRACE,FORMAL_TEACH,SCRIPTED,TEACHER [--out results/dev] [--rescore]"""
import os, sys, json, glob, subprocess, argparse, shutil, time, collections, signal, urllib.request, copy, threading, queue, re
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "student"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core"), os.path.join(ROOT, "teacher")]
import lang as L, abstraction as AB, retrieval as RT
LLM_PY = os.environ.get("SEMVM_LLM_PYTHON", sys.executable)  # release portability edit (was an absolute venv path); TEACHER_APP = "semvm-pdx-teacher"
WORKERS = [tuple(x.split(":")) for x in os.environ.get("PDX_WORKERS", "0:8766,0:8767").split(",")]
SECRET_ENV = ("TEACHER_URL", "TEACHER_API_KEY", "GROQ_API_KEY")
m_ = lambda v: round(sum(v) / len(v), 4) if v else None
GATES = {"GOLD_TRACE": {"LEARNED_PROCEDURE_EXACT": ("==", 1.0)}, "FORMAL_TEACH": {"LEARNED_PROCEDURE_EXACT": ("==", 1.0)},
         "_arm": {"WRONG_TEACHER_ACTION_EXECUTED": ("==", 0), "BAD_TEACHER_SUGGESTION_EXECUTED": ("==", 0), "BAD_PROCEDURE_ACTIVATED": ("==", 0), "VERIFY_FALSE_ACCEPT": ("==", 0),
                  "STUDENT_TRACE_EXACT": (">=", .90), "LEARNED_PROCEDURE_EXACT": (">=", .90), "SOURCE_REPLAY_EXACT": ("==", 1.0), "COUNTERFACTUAL_EXACT": ("==", 1.0),
                  "ROLLBACK_EXACT": ("==", 1.0), "PROCEDURE_RETRIEVAL_EXACT": (">=", .95), "ARGUMENT_BINDING_EXACT": (">=", .95), "UNSEEN_ARGUMENT_EXACT": ("==", 1.0),
                  "RESTART_PROCEDURE_EXACT": ("==", 1.0), "TEACHER_DISCONNECT_REUSE_EXACT": ("==", 1.0), "STORED_PROCEDURE_REUSE_EXACT": ("==", 1.0), "DISTILLED_SKILL_EXACT": (">=", .90),
                  "POST_HANDOFF_TEACHER_CALLS": ("==", 0), "INSUFFICIENT_EVIDENCE_DETECTED": ("==", 1.0), "STUDENT_NEURAL_HASH_INVARIANT": ("==", 1.0)}}


def env_clean(port, extra=None):
    e = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}; e["SEMVM_LLM_URL"] = f"http://127.0.0.1:{port}"; e.update(extra or {}); return e


def svc(action, w):
    gpu, port = w; pf = os.path.join(ROOT, "results", f"student_service_{port}.pid")
    if action in ("stop", "restart") and os.path.exists(pf):
        try: os.kill(int(open(pf).read()), signal.SIGTERM)
        except (ProcessLookupError, ValueError): pass
        for _ in range(60):
            try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1); time.sleep(1)
            except Exception: break
    if action in ("start", "restart"):
        log = open(os.path.join(ROOT, "results", f"student_service_{port}.log"), "a")
        p = subprocess.Popen([LLM_PY, os.path.join(ROOT, "student", "nl_llm_service.py"), "--port", str(port)], stdout=log, stderr=log,
                             env={k: v for k, v in dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True").items() if k not in SECRET_ENV})
        open(pf, "w").write(str(p.pid))
        for _ in range(300):
            try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2); return frozen(w)
            except Exception: time.sleep(1)
        raise SystemExit(f"student service {w} did not start")


def frozen(w): return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{w[1]}/frozen", timeout=600).read())


def secrets_env():
    """teacher credentials for the ACQUISITION phase of TEACHER mode only (read from files outside the repository; never logged)"""
    e = {}
    for k, p in (("TEACHER_URL", "PDX_TEACHER_URL_FILE"), ("TEACHER_API_KEY", "PDX_TEACHER_KEY_FILE")):
        if os.environ.get(p): e[k] = open(os.environ[p]).read().strip()
    return e


def teacher_up():
    """(re)deploy the frozen teacher endpoint and wait until it serves (cold start is billed; scale-to-zero afterwards)"""
    subprocess.run(["modal", "deploy", os.path.join(ROOT, "teacher", "modal_teacher.py")], capture_output=True, text=True)
    url = open(os.environ["PDX_TEACHER_URL_FILE"]).read().strip(); key = open(os.environ["PDX_TEACHER_KEY_FILE"]).read().strip()
    for _ in range(120):
        try: urllib.request.urlopen(urllib.request.Request(url + "/v1/models", headers={"Authorization": "Bearer " + key}), timeout=120); return
        except Exception: time.sleep(10)
    raise SystemExit("teacher endpoint did not come up")


def pool_run(items, fn):
    Q = queue.Queue(); [Q.put(x) for x in items]; out = {}; lk = threading.Lock()
    def work(w):
        while True:
            try: x = Q.get_nowait()
            except queue.Empty: return
            r = fn(x, w)
            with lk: out[x["scenario_id"]] = r; print(f"  {x['scenario_id']} on gpu{w[0]}:{w[1]} ({len(out)}/{len(items)})", flush=True)
    th = [threading.Thread(target=work, args=(w,)) for w in WORKERS]; [t.start() for t in th]; [t.join() for t in th]; return out


def acquire(mode, S, out_dir, teacher_args):
    def fn(sc, w):
        d = os.path.join(out_dir, "work", mode, sc["scenario_id"]); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        o = os.path.join(d, "acq.json"); env = env_clean(w[1], secrets_env() if mode == "TEACHER" else None)
        cmd = [sys.executable, os.path.join(ROOT, "run_acq.py"), "--scenario", os.path.join(ROOT, "scenarios", sc["suite"], sc["scenario_id"] + ".json"), "--dir", d, "--mode", mode, "--out", o] + teacher_args
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode: return {"error": r.stderr[-3000:]}
        return json.load(open(o))
    return pool_run(S, fn)


def handoff(mode, S, out_dir):
    A = {"mode": mode, "time": time.time()}
    if mode == "TEACHER":
        r = subprocess.run(["modal", "app", "stop", "--yes", TEACHER_APP], capture_output=True, text=True); A["modal_app_stop_rc"] = r.returncode
        url = open(os.environ["PDX_TEACHER_URL_FILE"]).read().strip() if os.environ.get("PDX_TEACHER_URL_FILE") else None; A["endpoint_after_stop"] = None
        if url:
            try: urllib.request.urlopen(url + "/v1/models", timeout=60); A["endpoint_after_stop"] = "REACHABLE"
            except urllib.error.HTTPError as e: A["endpoint_after_stop"] = f"HTTP {e.code}"
            except Exception as e: A["endpoint_after_stop"] = type(e).__name__
        A["teacher_destroyed"] = A["modal_app_stop_rc"] == 0 and A["endpoint_after_stop"] != "REACHABLE"
    for sc in S:
        d = os.path.join(out_dir, "work", mode, sc["scenario_id"]); arch = os.path.join(out_dir, "acq_artifacts", mode, sc["scenario_id"])
        if os.path.exists(os.path.join(d, "learn")): os.makedirs(os.path.dirname(arch), exist_ok=True); shutil.rmtree(arch, ignore_errors=True); shutil.move(os.path.join(d, "learn"), arch)
    json.dump(A, open(os.path.join(ROOT, "network_audit", f"handoff_{os.path.basename(out_dir)}_{mode}.json"), "w"), indent=1); return A


def reuse(mode, S, out_dir):
    ndir = os.path.join(ROOT, "network_audit", os.path.basename(out_dir), mode); os.makedirs(ndir, exist_ok=True)
    def fn(sc, w):
        d = os.path.join(out_dir, "work", mode, sc["scenario_id"]); turns = sc["post_turns"]; cuts = [i for i, t in enumerate(turns) if t["kind"] == "RESTART"]
        segs = []; a = 0
        for c in cuts + [len(turns)]: segs.append((a, c)); a = c + 1
        res = {}; infos = []; hashes = []; nlog = os.path.join(ndir, sc["scenario_id"] + ".jsonl"); open(nlog, "w").close()
        for j, (a, b) in enumerate(segs):
            if j == 0 and b == 0: continue
            if a > 0 or turns[0]["kind"] == "RESTART": fz = svc("restart", w); hashes.append(fz.get("weights_sha256"))     # every RESTART: student process + local LLM service
            if a >= b: continue
            o = os.path.join(d, f"reuse_{a}_{b}.json")
            env = env_clean(w[1], {"PYTHONPATH": os.path.join(ROOT, "netguard"), "NETGUARD_LOG": nlog})
            r = subprocess.run([sys.executable, os.path.join(ROOT, "run_reuse.py"), "--scenario", os.path.join(ROOT, "scenarios", sc["suite"], sc["scenario_id"] + ".json"), "--dir", d, "--start", str(a), "--end", str(b), "--out", o],
                               capture_output=True, text=True, env=env)
            if r.returncode: return {"error": r.stderr[-3000:]}
            R = json.load(open(o)); infos.append(R["info"])
            for t in R["turns"]: res[t["turn"]] = t
        blocked = [json.loads(l) for l in open(nlog) if l.strip()]
        return {"turns": res, "infos": infos, "student_hashes": hashes, "netguard_blocked": blocked}
    return pool_run(S, fn)


# ---------------------------------------------------------------- metrics ----------------------------------------------------------------
def gold_hash(it): return L.program_hash(L.parse_procedure(it["gold"]))


def trace_exact(steps, gold_text):
    """teaching trace = gold procedure body with ANY values at parameter slots (constants must match); variables normalized"""
    g = L.parse_procedure(gold_text); body = copy.deepcopy(g["body"])
    def sub(o):
        if isinstance(o, dict):
            if set(o) == {"param"}: return {"const": "__P__"}
            return {k: sub(v) for k, v in o.items()}
        if isinstance(o, list): return [sub(x) for x in o]
        return o
    body = sub(body); a = AB.normalize_vars(steps); b = AB.normalize_vars(body)
    try:
        if AB.skeleton(a) != AB.skeleton(b): return False
        sa, sb = AB.slots(a), AB.slots(b)
    except Exception: return False
    return len(sa) == len(sb) and all(vb == "__P__" or va == vb for (_, _, va), (_, _, vb) in zip(sa, sb))


def demo_trace(D):
    return [s for r in D["results"] if r["status"] == "OK" for s in r["executed_steps"]]


def metrics(mode, S, ACQ, REU, out_dir, HO=None):
    M = collections.defaultdict(list); acct = collections.defaultdict(list); tax = collections.Counter(); per = {}; strata = collections.defaultdict(list)
    for sc in S:
        sid = sc["scenario_id"]; A = ACQ.get(sid) or {}; R = REU.get(sid) or {}; ok_all = True; first = None
        if A.get("error") or R.get("error"): per[sid] = {"error": (A.get("error") or R.get("error"))[-500:]}; M["SCENARIO_EXACT"].append(False); continue
        active = {a["name"]: a for a in A.get("active", [])}; items = {it["name"]: it for it in sc["curriculum"]}
        # ---- acquisition ----
        if mode in ("GOLD_TRACE", "FORMAL_TEACH"):
            for t, r in zip(sc[("gold" if mode == "GOLD_TRACE" else "formal") + "_acq_turns"], A["acq_turns"]):
                if t["kind"] == "CMD" and t["text"].split()[0] in (":endteach", ":learn") and t.get("expect") == "VERIFIED":
                    D = r.get("discovery") or {}; ch = (D.get("paths") or {}).get("deterministic", {})
                    M["LEARNED_PROCEDURE_EXACT"].append(r["status"] == "VERIFIED" and ch.get("program_hash") == gold_hash(items[t["name"]]))
                    if r["status"] == "VERIFIED" and ch.get("tests"): _verif(M, ch)
        else:
            for O in A.get("targets", []):
                it = items[O["name"]]; inj = it.get("injection") or {}; acts = O["status"] == "ACTIVE"
                learned = acts and active.get(O["name"]) is not None and _active_hash(A, O["name"]) == gold_hash(it)
                M["TEACHER_EPISODE_SUCCESS"].append(acts); M["LEARNED_PROCEDURE_EXACT"].append(learned); strata[f"style_{sc['style']}"].append(learned); strata[f"stratum_{sc['stratum']}"].append(learned)
                acct["teacher_turns_per_skill"].append(O["teacher_turns"]); acct["demonstrations_per_skill"].append(len(O["demos"])); acct["student_questions_per_skill"].append(len(O["student_questions"]))
                for D in O["demos"]:
                    injected = any(x["demo"] == D["index"] for x in O["injections"])
                    legal = injected and inj.get("kind") in ("DROPPED_FILTER", "CONSTANT_SWAP") and any(x.get("applied") for x in O["injections"])
                    tr = demo_trace(D); exact = D.get("end") in ("VERIFIED", "OK", "REQUIRE_SECOND_DEMONSTRATION") and trace_exact(tr, it["gold"])
                    if not legal:
                        M["STUDENT_TRACE_EXACT"].append(exact)
                        if D.get("returned") and not exact and not injected: M["WRONG_TEACHER_ACTION_EXECUTED"].append(1)
                        elif D.get("returned") and not exact and injected and inj.get("kind") not in ("VAGUE_STEP",): M["WRONG_TEACHER_ACTION_EXECUTED"].append(1)
                    else: M["LEGAL_BAD_SANDBOX_EXECUTED"].append(any(r["status"] == "OK" for r in D["results"]))
                    for r in D["results"]:
                        acct["student_grounding_seconds"].append(r.get("seconds") or 0); acct["student_llm_calls_per_line"].append(r.get("llm_calls") or 0)
                        M["TEACHER_INSTRUCTION_GROUNDED"].append(r["status"] == "OK")
                        if inj.get("kind") in ("UNSUPPORTED_PRIMITIVE", "PREMATURE_RETURN", "WRONG_ARGUMENT_TYPE", "INVALID_VALUE") and any(x.get("line") == r["line"] for x in O["injections"]):
                            M["BAD_TEACHER_SUGGESTION_EXECUTED"].append(1 if r["status"] == "OK" else 0)
                            if inj["kind"] == "UNSUPPORTED_PRIMITIVE": M["UNSUPPORTED_TEACHER_ACTION_BLOCKED"].append(r["status"] != "OK")
                        if inj.get("kind") == "UNSUPPORTED_PRIMITIVE" and sc["stratum"] == "S13" and any(x.get("line") == r["line"] for x in O["injections"]): M["UNSUPPORTED_REJECTION"].append(r["status"] in ("UNSUPPORTED", "CLARIFY"))
                if inj.get("kind") in ("DROPPED_FILTER", "CONSTANT_SWAP"):
                    applied = any(x.get("applied") for x in O["injections"]); M["LEGAL_BAD_INJECTION_APPLIED"].append(applied)
                    if applied:
                        M["CROSS_DEMO_INCONSISTENCY_DETECTED"].append("INCONSISTENCY_DETECTED" in O["classes"]); M["BAD_PROCEDURE_ACTIVATED"].append(1 if (acts and not learned) else 0)
                if inj.get("kind") == "VAGUE_STEP": M["TEACHER_REPHRASE_SUCCESS"].append(learned and any(q["kind"] == "REPHRASE" for q in O["student_questions"]))
                if sc["stratum"] == "S12": M["INSUFFICIENT_EVIDENCE_DETECTED"].append(any(D.get("end") == "REQUIRE_SECOND_DEMONSTRATION" or D.get("learn") == "REQUIRE_SECOND_DEMONSTRATION" for D in O["demos"]) or "SECOND_DEMO_REQUESTED" in O["classes"])
                if sc["stratum"] == "S12": M["SECOND_DEMO_REQUEST_EXACT"].append("SECOND_DEMO_REQUESTED" in O["classes"] and learned)
                cls = "FIRST_LESSON_SUCCESS" if (learned and not O["student_questions"] and len(O["demos"]) <= (2 if it["protocol"]["two_demo"] else 1)) else \
                      "CLARIFICATION_SUCCESS" if (learned and "CLARIFICATION_SUCCESS" in O["classes"]) else "REPHRASE_SUCCESS" if (learned and any(q["kind"] == "REPHRASE" for q in O["student_questions"])) else \
                      "SECOND_DEMO_SUCCESS" if learned else "FAILED:" + O["status"]
                M["class_" + cls].append(1); M["DISTILLATION_FIRST_PASS"].append(cls == "FIRST_LESSON_SUCCESS")
                for rec in O.get("teacher_log", []):
                    p = rec.get("provenance") or {}
                    if p.get("provider") == "modal-vllm" or p.get("provider") == "groq":
                        acct["teacher_calls"].append(1); acct["teacher_cached"].append(1 if p.get("cached") else 0); acct["teacher_input_tokens"].append(p.get("input_tokens") or 0)
                        acct["teacher_output_tokens"].append(p.get("output_tokens") or 0); acct["teacher_latency_s"].append(p.get("latency_s") or 0)
                if not learned and ok_all: ok_all = False; first = _acq_fail(O, it)
        for pr in A.get("false_accept_probes", []): M["VERIFY_FALSE_ACCEPT"].append(1 if pr["status"] == "VERIFIED" else 0)
        # ---- verification detail of every learned candidate (from the archived learn/candidates) ----
        for f in glob.glob(os.path.join(out_dir, "acq_artifacts", mode, sid, "candidates", "*.json")):
            C = json.load(open(f)); ch = (C.get("paths") or {}).get(C.get("chosen") or "deterministic", {})
            if C.get("status") == "VERIFIED" and ch.get("tests") and mode not in ("GOLD_TRACE", "FORMAL_TEACH"): _verif(M, ch)
        # ---- reuse ----
        hs = R.get("student_hashes") or []; M["STUDENT_NEURAL_HASH_INVARIANT"].append(len(set(h for h in hs + [(A.get("student_hash_before") or {}).get("weights_sha256")] if h)) == 1)
        M["POST_HANDOFF_TEACHER_CALLS"] += [1 for _ in R.get("netguard_blocked", [])]
        audits = [i.get("audit") for i in R.get("infos", [])]; clean = all(a and a["netguard_active"] and not a["teacher_env_present"] and not a["learn_dir_present_at_start"] and not a["teacher_modules_loaded"] for a in audits)
        if mode == "TEACHER": clean = clean and bool((HO or {}).get("teacher_destroyed"))       # the teacher must no longer exist
        M["TEACHER_REMOVAL_AUDIT_CLEAN"].append(clean)
        demo_vals = _demo_values(A, mode, sc); teacher_lines = _teacher_lines(A)
        after_restart = False; skill_ok = collections.defaultdict(list)
        for i, (t, e) in enumerate(zip(sc["post_turns"], sc["post_expected"])):
            if t["kind"] == "RESTART": after_restart = True; continue
            g = R["turns"].get(i) or R["turns"].get(str(i))
            if g is None: ok = False
            else: ok = (g["status"] == e["status"] or (e["status"] == "REJECTED" and g["status"].startswith("REJECTED"))) and g["STATE"] == e["state"] and ("return" not in e or g.get("return") == e.get("return"))
            if t["kind"] in ("RUN", "REQUEST") and t.get("plan"):
                lits = _lits(t["plan"]); novel = any(v not in demo_vals for v in lits) or not lits
                (M["UNSEEN_ARGUMENT_EXACT"] if novel else M["DEMONSTRATED_ARGUMENT_EXACT"]).append(ok); M["COUNTERFACTUAL_EXACT"].append(ok) if novel else None
                if after_restart: M["RESTART_PROCEDURE_EXACT"].append(ok)
                M["TEACHER_DISCONNECT_REUSE_EXACT"].append(ok and clean and not R.get("netguard_blocked"))
                if e["status"] == "VM_EXEC_ERROR": M["ROLLBACK_EXACT"].append(ok)
                skill_ok[t["plan"]["call"]].append(ok)
                if t.get("family") == "__composite" and t.get("composition") != "L1": M["COMPOSITION_L2_REUSE_EXACT"].append(ok)
            if t["kind"] == "REQUEST" and g is not None:
                gp = g.get("plan"); M["PROCEDURE_RETRIEVAL_EXACT"].append(bool(gp) and gp.split("(")[0] == t["plan"]["call"])
                if gp and gp.split("(")[0] == t["plan"]["call"]: M["ARGUMENT_BINDING_EXACT"].append(gp == RT.plan_str(t["plan"]))
                if t["plan"]["call"] == "count_calls_for_time_person": M["STORED_PROCEDURE_REUSE_EXACT"].append(bool(gp) and gp.split("(")[0] == "count_calls_for_time_person")
                M["POST_HANDOFF_SURFACE_GENERALIZATION_EXACT"].append(ok and t["text"][len("REQUEST "):].lower().strip() not in teacher_lines)
            if t.get("composition") == "L1": M["COMPOSITION_L1_EXACT"].append(ok)
            if t.get("composition") == "L2": M["COMPOSITION_L2_SAVE_EXACT"].append(ok)
            if not ok and ok_all: ok_all = False; first = _reuse_fail(t, g, e)
        last = max((int(k) for k in R["turns"]), default=None)
        if last is not None: M["FINAL_STATE_EXACT"].append((R["turns"].get(last) or R["turns"].get(str(last)))["STATE"] == sc["post_expected"][last]["state"])
        for it in sc["curriculum"]:
            if it["name"] in skill_ok:
                ds = (mode in ("GOLD_TRACE", "FORMAL_TEACH") or any(O["name"] == it["name"] and O["status"] == "ACTIVE" for O in A.get("targets", []))) and all(skill_ok[it["name"]]) and clean
                M["DISTILLED_SKILL_EXACT"].append(ds)
        M["SCENARIO_EXACT"].append(ok_all); per[sid] = {"stratum": sc["stratum"], "style": sc["style"], "exact": ok_all, "first_failure": first}
        if not ok_all: tax[first] += 1
        acct["library_bytes_after"].append(A.get("library_bytes_after") or 0); acct["active_after"].append(A.get("active_after") or 0); acct["acquisition_seconds"].append(A.get("seconds") or 0)
    R0 = {}
    for k, v in M.items():
        if k in ("WRONG_TEACHER_ACTION_EXECUTED", "BAD_TEACHER_SUGGESTION_EXECUTED", "BAD_PROCEDURE_ACTIVATED", "POST_HANDOFF_TEACHER_CALLS", "VERIFY_FALSE_ACCEPT") or k.startswith("class_"): R0[k] = sum(v); R0["n_" + k] = len(v)
        else: R0[k] = m_(v); R0["n_" + k] = len(v)
    for k in ("WRONG_TEACHER_ACTION_EXECUTED", "BAD_TEACHER_SUGGESTION_EXECUTED", "BAD_PROCEDURE_ACTIVATED", "POST_HANDOFF_TEACHER_CALLS", "VERIFY_FALSE_ACCEPT"): R0.setdefault(k, 0)
    R0["accounting"] = {k: {"mean": m_(v), "sum": round(sum(v), 3), "n": len(v)} for k, v in acct.items()}; R0["strata"] = {k: {"acc": m_(v), "n": len(v)} for k, v in sorted(strata.items())}
    R0["failure_taxonomy"] = dict(tax); R0["per_scenario"] = per
    G = GATES.get(mode) or GATES["_arm"]
    R0["gates"] = {k: {"rule": f"{op} {th}", "value": R0.get(k), "pass": R0.get(k) is not None and ((R0[k] == th) if op == "==" else (R0[k] >= th))} for k, (op, th) in G.items()}
    return R0


def _verif(M, ch):
    M["SOURCE_REPLAY_EXACT"].append(all(o for n, o in ch["tests"] if n.startswith("replay"))); M["NEGATIVE_CASE_SAFE"] += [o for n, o in ch["tests"] if n.startswith(("neg_", "txn_"))]
    M["ROLLBACK_EXACT"] += [o for n, o in ch["tests"] if n.startswith("txn_")]


def _active_hash(A, name):
    import sqlite3
    return (A.get("_active_hashes") or {}).get(name)


def _lits(pl): return [v for v in pl["args"].values() if isinstance(v, str)] + [x for v in pl["args"].values() if isinstance(v, dict) for x in _lits(v)]


def _demo_values(A, mode, sc):
    vals = set()
    for O in A.get("targets", []):
        for D in O["demos"]:
            for s in demo_trace(D):
                for c in re.findall(r'"const": "([^"]+)"', json.dumps(s)): vals.add(c)
    if mode in ("GOLD_TRACE", "FORMAL_TEACH"):
        for it in sc["curriculum"]:
            for v in it["demo_values"]: vals |= set(v.values())
    return vals


def _teacher_lines(A): return {r["line"].lower().strip().rstrip(".") for O in A.get("targets", []) for D in O["demos"] for r in D["results"]}


def _acq_fail(O, it):
    if O["status"] in ("PROVIDER_FAILURE", "BUDGET_STOP"): return O["status"]
    if O["status"] != "ACTIVE":
        if "budget" in (O.get("fail") or ""): return "GT_TURN_BUDGET"
        return "PD_INSUFFICIENT_EVIDENCE" if any(D.get("end") == "REQUIRE_SECOND_DEMONSTRATION" for D in O["demos"]) else "GT_INCOMPLETE"
    D = O["demos"][-1]; tr = demo_trace(D)
    if any(r["status"] == "CLARIFY" for r in D["results"]): return "SG_FALSE_CLARIFY"
    return "PD_PROGRAM" if tr else "GT_INCOMPLETE"


def _reuse_fail(t, g, e):
    if g is None: return "RESTART"
    if t["kind"] == "REQUEST":
        gp = g.get("plan")
        if t.get("composition") == "L1" and gp != RT.plan_str(t["plan"]): return "PR_COMPOSE"
        if not gp or gp.split("(")[0] != t["plan"]["call"]: return "PR_RETRIEVE"
        if gp != RT.plan_str(t["plan"]): return "PR_ARGUMENT"
    if t["kind"] == "CMD": return "PR_COMPOSE" if t.get("composition") else "STORE"
    return "PD_PROGRAM"


def active_hashes(out_dir, mode, S):
    """program hashes of the ACTIVE procedures in every scenario's procedures.sqlite (read-only, after reuse)"""
    import procstore as PS
    H = {}
    for sc in S:
        p = os.path.join(out_dir, "work", mode, sc["scenario_id"], "procedures.sqlite")
        if not os.path.exists(p): continue
        lib = PS.Library(p); H[sc["scenario_id"]] = {a["name"]: L.program_hash(lib.active(a["name"])) for a in lib.list_active()}; lib.close()
    return H


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True); ap.add_argument("--modes", default="GOLD_TRACE,FORMAL_TEACH,SCRIPTED,TEACHER"); ap.add_argument("--out", default=None)
    ap.add_argument("--rescore", action="store_true"); ap.add_argument("--teacher-args", default="--backend MODAL --model openai/gpt-oss-120b --reasoning medium"); ap.add_argument("--only", default=None); a = ap.parse_args()
    out_dir = a.out or os.path.join(ROOT, "results", a.suite); os.makedirs(out_dir, exist_ok=True)
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]
    if a.only: S = [s for s in S if s["scenario_id"] in a.only.split(",")]
    for mode in a.modes.split(","):
        fn = os.path.join(out_dir, f"PDX_{mode}.json")
        if a.rescore:
            E = json.load(open(fn)); ACQ, REU = E["acq"], E["reuse"]
        else:
            t0 = time.time(); print(f"[{mode}] acquisition", flush=True)
            for w in WORKERS: svc("restart", w)
            if mode == "TEACHER": teacher_up()
            ACQ = acquire(mode, S, out_dir, a.teacher_args.split() if mode == "TEACHER" else []); ta = time.time() - t0
            print(f"[{mode}] handoff", flush=True); HO = handoff(mode, S, out_dir)
            print(f"[{mode}] reuse", flush=True); REU = reuse(mode, S, out_dir)
            E = {"acq": ACQ, "reuse": REU, "handoff": HO, "seconds": {"acquisition": round(ta, 1), "total": round(time.time() - t0, 1)}}
        H = active_hashes(out_dir, mode, S)
        for sid, A in ACQ.items():
            if isinstance(A, dict): A["_active_hashes"] = H.get(sid, {})
        R = metrics(mode, S, ACQ, REU, out_dir, E.get("handoff")); R["handoff"] = E.get("handoff"); R["seconds"] = E.get("seconds"); E["results"] = R
        json.dump(E, open(fn, "w"), indent=1, default=str)
        print(mode, json.dumps({k: v for k, v in R.items() if k not in ("per_scenario",)}, default=str)[:6000], flush=True)
    for w in WORKERS: svc("stop", w)


if __name__ == "__main__":
    main()
