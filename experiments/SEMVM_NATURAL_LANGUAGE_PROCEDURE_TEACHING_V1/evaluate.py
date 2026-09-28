"""NL_TEACH evaluation (spec §53-§60, §74-§81). Modes: GOLD_TRACE (gold actions -> frozen learner), FORMAL_TEACH (parent step language),
NL_TEACH (natural language -> frozen 1.5B frontend -> validated actions). Each RESTART terminates the scenario process; in NL_TEACH the frozen
LLM service is ALSO killed and restarted (spec §46). Expected outcomes: independent oracle (scenarios/nl_generate.py + scenarios/oracle.py).
python evaluate.py --suite dev|locked_test [--modes GOLD_TRACE,FORMAL_TEACH,NL_TEACH] [--rescore]"""
import os, sys, json, glob, subprocess, argparse, shutil, time, collections, signal, urllib.request, copy
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "nlteach"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import retrieval as RT, lang as L
import nlsystem as NS, frontend as F
sys.path.insert(0, os.path.join(ROOT, "scenarios")); import catalog as _CAT; COMPOSITE_NAME = _CAT.COMPOSITE["name"]    # evaluator-only
LLM_PY = os.environ.get("SEMVM_LLM_PYTHON", sys.executable)  # release portability edit (was an absolute venv path); PORT = 8765
GATES = {"GOLD_TRACE": {"LEARNED_PROCEDURE_EXACT": ("==", 1.0)}, "FORMAL_TEACH": {"LEARNED_PROCEDURE_EXACT": ("==", 1.0)},
         "NL_TEACH": {"WRONG_LLM_ACTION_EXECUTED": ("==", 0), "VERIFY_FALSE_ACCEPT": ("==", 0), "TEACH_TRACE_EXACT": (">=", .90), "LEARNED_PROCEDURE_EXACT": (">=", .90),
                      "ACTION_OP_EXACT": (">=", .95), "ACTION_ARGUMENT_EXACT_AFTER_REPAIR": (">=", .95), "SOURCE_REPLAY_EXACT": ("==", 1.0), "COUNTERFACTUAL_EXACT": ("==", 1.0),
                      "ROLLBACK_EXACT": ("==", 1.0), "PROCEDURE_RETRIEVAL_EXACT": (">=", .95), "ARGUMENT_BINDING_EXACT": (">=", .95), "RESTART_PROCEDURE_EXACT": ("==", 1.0),
                      "STORED_PROCEDURE_REUSE_EXACT": ("==", 1.0), "NL_TEACH_SCENARIO_EXACT": (">=", .90)}}
m_ = lambda v: round(sum(v) / len(v), 4) if v else None
WORKERS = [tuple(x.split(":")) for x in os.environ.get("SEMVM_WORKERS", "0:8766,0:8767").split(",")]      # (CUDA device, port); registered per run
PROCS = {}


def llm_start(w):
    gpu, port = w; env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"); log = open(os.path.join(ROOT, "results", f"llm_service_{port}.log"), "a")
    PROCS[port] = subprocess.Popen([LLM_PY, os.path.join(ROOT, "nlteach", "nl_llm_service.py"), "--port", str(port)], env=env, stdout=log, stderr=log)
    open(os.path.join(ROOT, "results", f"llm_service_{port}.pid"), "w").write(str(PROCS[port].pid))
    for _ in range(300):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2); return
        except Exception: time.sleep(1)
    raise SystemExit(f"LLM service {w} did not start")


def llm_stop(w):
    gpu, port = w; p = PROCS.pop(port, None); pf = os.path.join(ROOT, "results", f"llm_service_{port}.pid")
    if p: p.send_signal(signal.SIGTERM); p.wait(timeout=60)
    elif os.path.exists(pf):
        try: os.kill(int(open(pf).read()), signal.SIGTERM)
        except (ProcessLookupError, ValueError): pass
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1); time.sleep(1)
        except Exception: return


def llm_frozen(w): return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{w[1]}/frozen", timeout=600).read())


def run_scenario(suite, sc, mode, work, w):
    d = os.path.join(work, mode, sc["scenario_id"]); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    p = os.path.join(ROOT, "scenarios", suite, f"{sc['scenario_id']}.json"); turns = sc["formal_turns"] if mode == "FORMAL_TEACH" else sc["turns"]
    cuts = [i for i, t in enumerate(turns) if t["kind"] == "RESTART"]; segs = []; a = 0
    for c in cuts + [len(turns)]: segs.append((a, c)); a = c + 1
    res = {}; infos = []; env = dict(os.environ, SEMVM_LLM_URL=f"http://127.0.0.1:{w[1]}"); frozen = []
    for j, (a, b) in enumerate(segs):
        if j > 0 and mode == "NL_TEACH": llm_stop(w); llm_start(w); frozen.append(llm_frozen(w)["param_hash_at_load"])   # RESTART: every process incl. the LLM service
        o = os.path.join(d, f"seg_{a}_{b}.json"); t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(ROOT, "run_segment.py"), "--scenario", p, "--dir", d, "--mode", mode, "--start", str(a), "--end", str(b), "--out", o], capture_output=True, text=True, env=env)
        if r.returncode: raise SystemExit(f"segment failed {sc['scenario_id']} {a}-{b}: {r.stderr[-3000:]}")
        R = json.load(open(o)); R["info"]["segment_seconds"] = round(time.time() - t0, 2); R["info"]["worker"] = list(w); infos.append(R["info"])
        for t in R["turns"]: res[t["turn"]] = t
    infos[0]["restart_param_hashes"] = frozen
    return res, infos


def same(a, b): return json.dumps(NS.canon_steps(a), sort_keys=True) == json.dumps(NS.canon_steps(b), sort_keys=True)


def status_ok(exp, got): return got.startswith("REJECTED") if exp == "REJECTED" else exp == got


def nl_first(g):
    """first-pass view of an NL turn result"""
    return g.get("first_pass") or g


def raw_steps(g):
    P = (nl_first(g).get("grounding") or {}); acts = P.get("raw_actions")
    if not acts: return None
    if acts[0]["op"] in ("UNSUPPORTED", "CLARIFY"): return acts[0]["op"]
    try: return NS.canon_steps(F.to_steps(copy.deepcopy(acts), [P.get("loop0", 0)]))
    except Exception: return "UNPARSEABLE"


def loop_normal(steps):
    """loop variable names are local temporaries: normalize for comparison"""
    s = json.dumps(steps, sort_keys=True); import re
    names = sorted(set(re.findall(r'"as": "(e\d+)"', s)))
    for k, n in enumerate(names): s = s.replace(f'"{n}"', f'"E{k}"')
    return s


def eqsteps(a, b): return isinstance(a, list) and isinstance(b, list) and loop_normal(NS.canon_steps(a)) == loop_normal(NS.canon_steps(b))


def gold_program_hash(sc, name):
    for t in sc["turns"]:
        if t["kind"] == "CMD" and t["text"].startswith(":accept ") and t.get("name") == name:
            p = L.parse_procedure(t["gold"]); return L.program_hash(p)
    return None


def metrics(S, RES, mode):
    M = collections.defaultdict(list); tax = collections.Counter(); tax_fp = collections.Counter(); per = {}; acct = collections.defaultdict(list); strata = collections.defaultdict(list)
    for sc in S:
        sid = sc["scenario_id"]; tr = RES[sid][0]; turns = sc["formal_turns"] if mode == "FORMAL_TEACH" else sc["turns"]; exp = sc["formal_expected"] if mode == "FORMAL_TEACH" else sc["expected"]
        ok_all = True; fp_all = True; first = None; first_fp = None; after_restart = False; demo_ok = {}; demo_key = None; any_rescue = False
        procs = {p["name"]: p for p in sc["meta"]["procedures"]}
        for i, (t, e) in enumerate(zip(turns, exp)):
            if t["kind"] == "RESTART": after_restart = True; continue
            g = tr[i]; kind = t["kind"]; c = (t.get("text") or "").split()[:1]
            st_ok = status_ok(e["status"], g["status"]); ret_ok = ("return" not in e) or g.get("return") == e.get("return"); state_ok = g["STATE"] == e["state"]
            ver_ok = (g.get("versions") == t.get("versions")) if t.get("versions") else True; ok = st_ok and ret_ok and state_ok and ver_ok; fp_ok = ok
            if kind == "CMD" and c and c[0] in (":teach", ":example", ":revise"): demo_key = (t["text"].split()[1].split("(")[0], i); demo_ok[demo_key] = True
            # ---------------- NL teaching utterances ----------------
            if kind == "NL" and mode == "NL_TEACH":
                gold = t["gold"]; f0 = nl_first(g); rescued = g.get("first_pass") is not None; any_rescue |= rescued; P = f0.get("grounding") or {}
                fstat = f0["status"]; fexec = f0.get("executed_steps") or []; rs = raw_steps(g)
                acct["nl_llm_calls_per_utterance"].append(P.get("llm_calls", 0)); acct["nl_seconds_per_utterance"].append(P.get("seconds", 0))
                band = t.get("band"); key = f"band_{band}"
                sg = P.get("segmentation") or {}
                if sg: M["INPUT_CLAUSE_COUNT"].append(sg.get("input_clause_count", 1)); M["GROUNDED_CLAUSE_COUNT"].append(P.get("grounded_clause_count", 0))
                if P.get("segmentation_disagree"): M["SEGMENTATION_DISAGREE"].append(1)
                if gold["status"] == "OK" and len(set(t.get("pats") or [])) > 1 and fstat == "OK": M["CLAUSE_COVERAGE"].append(min(1.0, len(fexec) / max(1, len(gold["steps"]))))
                if (f0.get("grounding") or {}) and g.get("first_pass") is None and "consumed_clarification" in json.dumps(g.get("grounding") or {}): M["CLARIFY_ANSWER_CONSUMED"].append(1)
                ra = P.get("raw_actions") or []
                if ra and ra[0]["op"] not in ("UNSUPPORTED", "CLARIFY") and F.dangling(copy.deepcopy(ra)): M["DATAFLOW_DEAD_PURE_RESULT_BLOCKED"].append(1)
                if fstat == "CLARIFY" and (str(f0.get("reason", "")).startswith("RETURN asks for") or "unknown result" in str(f0.get("reason", ""))): M["DATAFLOW_USE_BEFORE_DEFINITION_BLOCKED"].append(1)
                if gold["status"] in ("OK",):
                    gsteps = gold["steps"]; exact_fp = fstat == "OK" and eqsteps(fexec, gsteps)
                    M["ACTION_OP_EXACT"].append(isinstance(rs, list) and [s["op"] for s in rs] == [s["op"] for s in gsteps])
                    M["ACTION_ARGUMENT_EXACT_RAW"].append(isinstance(rs, list) and eqsteps(rs, gsteps))
                    M["ACTION_ARGUMENT_EXACT_AFTER_REPAIR"].append(exact_fp)
                    if len(gsteps) > 1: M["ACTION_SEQUENCE_EXACT"].append(exact_fp)
                    if any(k in json.dumps(gsteps) for k in ('"var"',)) and isinstance(rs, list) and [s["op"] for s in rs] == [s["op"] for s in gsteps]:
                        M["REFERENCE_BINDING_EXACT"].append(fstat == "OK" and eqsteps(fexec, gsteps) or (fstat == "OK" and _refs(fexec) == _refs(gsteps)))
                    strata[key].append(exact_fp); strata[f"designed_{t.get('designed') or 'plain'}"].append(exact_fp)
                    # frontend contribution (spec §37)
                    if exact_fp and isinstance(rs, list) and eqsteps(rs, gsteps): cat = "A_RAW_LLM_CORRECT"
                    elif exact_fp: cat = "B_DETERMINISTIC_REPAIR"
                    elif fstat in ("CLARIFY", "UNSUPPORTED") and ok: cat = "E_CLARIFICATION_REQUIRED"
                    else: cat = "F_FAILURE"
                    M["contribution_" + cat].append(1)
                    wrong_exec = fstat == "OK" and not eqsteps(fexec, gsteps)
                    M["WRONG_LLM_ACTION_PROPOSED"].append(isinstance(rs, list) and not eqsteps(rs, gsteps) or rs in ("UNSUPPORTED", "CLARIFY", "UNPARSEABLE"))
                    if fstat in ("CLARIFY", "UNSUPPORTED"): M["FIRST_PASS_FALSE_CLARIFY"].append(1)
                    if fstat == "CLARIFY": M["CLARIFY_PRED"].append(False)
                    if t.get("designed") == "correction": M["POST_CORRECTION_TRACE_EXACT"].append(ok)
                    if t.get("designed") == "answer": M["CLARIFICATION_SUCCESS"].append(ok)
                    fp_ok = ok and exact_fp and not rescued
                elif gold["status"] == "EXEC_FAILED":
                    wrong_exec = fstat == "OK"
                    M["TEACHING_ROLLBACK_EXACT"].append(fstat == e["status"] and state_ok); fp_ok = ok and not rescued
                else:     # CLARIFY / UNSUPPORTED
                    wrong_exec = fstat == "OK"
                    M["WRONG_LLM_ACTION_PROPOSED"].append(isinstance(rs, list))
                    if gold["status"] == "CLARIFY": M["CLARIFY_GOLD"].append(fstat == "CLARIFY")
                    if fstat == "CLARIFY": M["CLARIFY_PRED"].append(gold["status"] == "CLARIFY")
                    if gold["status"] == "UNSUPPORTED": M["UNSUPPORTED_REJECTION_EXACT"].append(fstat == "UNSUPPORTED"); M["UNSUPPORTED_SAFE"].append(fstat in ("UNSUPPORTED", "CLARIFY"))
                    fp_ok = ok and fstat == gold["status"] and not rescued
                if rescued:
                    M["RESCUES"].append(g["rescue_text"][:3]); r2e = g.get("executed_steps") or []
                    if gold["status"] == "OK" and g["status"] == "OK" and not eqsteps(r2e, gold["steps"]): wrong_exec = True
                M["WRONG_LLM_ACTION_EXECUTED"].append(1 if wrong_exec else 0)
                if isinstance(rs, list) and gold["status"] == "OK" and not eqsteps(rs, gold["steps"]): M["WRONG_LLM_ACTION_BLOCKED"].append(not (fstat == "OK" and not eqsteps(fexec, gold["steps"])))
                if not fp_ok and demo_key: demo_ok[demo_key] = False
                if not fp_ok and first_fp is None: first_fp = _nl_fail(t, g, rs)
            elif kind == "NL":
                if not ok and demo_key: demo_ok[demo_key] = False
            # ---------------- discovery ----------------
            disc = kind == "CMD" and c and (c[0] in (":endteach", ":endrevise", ":learn", ":save-last-as") or c[0] == ":propose")
            if disc and g.get("discovery"):
                D = g["discovery"]; P = D["paths"]
                if c[0] == ":propose": M["VERIFY_FALSE_ACCEPT"].append(1 if g["status"] == "VERIFIED" else 0)
                elif e["status"] == "VERIFIED":
                    ch = P.get(D.get("chosen") or "deterministic", {}); gh = gold_program_hash(sc, t["name"])
                    learned = ch.get("program_hash") == gh and g["status"] == "VERIFIED"; M["LEARNED_PROCEDURE_EXACT"].append(learned)
                    pinfo = procs.get(t["name"], {}); strata["opaque" if pinfo.get("opaque") else "named"].append(learned)
                    strata["hinted" if pinfo.get("mode") in ("one_shot_hinted", "two_hinted") else "unhinted"].append(learned)
                    if D["status"] == "VERIFIED" and ch.get("tests"):
                        M["SOURCE_REPLAY_EXACT"].append(all(o for n, o in ch["tests"] if n.startswith("replay")))
                        M["NEGATIVE_CASE_SAFE"] += [o for n, o in ch["tests"] if n.startswith(("neg_", "txn_"))]; M["ROLLBACK_EXACT"] += [o for n, o in ch["tests"] if n.startswith("txn_")]
                        acct["verify_seconds"].append(ch.get("verify_seconds", 0))
            if kind == "CMD" and c and c[0] in (":endteach", ":endexample", ":endrevise") and demo_key:
                M["TEACH_TRACE_EXACT"].append(demo_ok.get(demo_key, True) and ok)
            # ---------------- invocations ----------------
            if kind in ("RUN", "REQUEST") and t.get("plan") is not None:
                if t.get("novel_args"): M["COUNTERFACTUAL_EXACT"].append(ok); M["UNSEEN_ARGUMENT_EXACT"].append(ok)
                else: M["DEMONSTRATED_ARGUMENT_EXACT"].append(ok)
                if after_restart: M["RESTART_PROCEDURE_EXACT"].append(ok)
                if e["status"] == "VM_EXEC_ERROR": M["ROLLBACK_EXACT"].append(ok)
                acct["execution_seconds" if kind == "RUN" else "retrieval_plus_execution_seconds"].append(g.get("seconds", 0))
            if kind == "REQUEST":
                M["SURFACE_GENERALIZATION_EXACT"].append(ok); gp = g.get("plan")
                M["PROCEDURE_RETRIEVAL_EXACT"].append(bool(gp) and gp.split("(")[0] == t["plan"]["call"])
                if gp and gp.split("(")[0] == t["plan"]["call"]: M["ARGUMENT_BINDING_EXACT"].append(gp == RT.plan_str(t["plan"]))
                if t["plan"]["call"] == COMPOSITE_NAME: M["STORED_PROCEDURE_REUSE_EXACT"].append(bool(gp) and gp.split("(")[0] == COMPOSITE_NAME)
                acct["retrieval_llm_calls"].append(g.get("llm_calls", 0))
            if t.get("composition") == "L1": M["COMPOSITION_EXACT"].append(ok)
            if kind == "RUN" and t.get("family") == "__composite": M["COMPOSITION_EXACT"].append(ok)
            if kind == "REQUEST" and t.get("family") == "__composite" and t.get("composition") != "L1": M["COMPOSITION_EXACT"].append(ok)
            if not ok and ok_all: ok_all = False; first = _fail(t, g, e, mode)
            if not fp_ok and fp_all:
                fp_all = False
                if first_fp is None: first_fp = first or _fail(t, g, e, mode)
        last = max(tr); M["FINAL_STATE_EXACT"].append(tr[last]["STATE"] == exp[last]["state"]); M["SCENARIO_EXACT"].append(ok_all); M["SCENARIO_EXACT_FIRST_PASS"].append(fp_all and not any_rescue)
        per[sid] = {"category": sc["category"], "band": sc["meta"]["band"], "exact": ok_all, "first_pass": fp_all and not any_rescue, "first_failure": first, "first_failure_first_pass": None if (fp_all and not any_rescue) else first_fp}
        if not ok_all: tax[first] += 1
        if not (fp_all and not any_rescue): tax_fp[first_fp] += 1
        for p in sc["meta"]["procedures"]:
            strata["scenario_" + ("opaque" if p["opaque"] else "named")].append(ok_all); strata["scenario_" + ("hinted" if p["mode"] in ("one_shot_hinted", "two_hinted") else "unhinted")].append(ok_all)
        strata[f"scenario_band_{sc['meta']['band']}"].append(ok_all); strata[f"scenario_band_{sc['meta']['band']}_first_pass"].append(fp_all and not any_rescue)
    R = {}
    for k, v in M.items():
        if k in ("WRONG_LLM_ACTION_EXECUTED", "VERIFY_FALSE_ACCEPT"): R[k] = sum(v); R[f"n_{k}"] = len(v)
        elif k.startswith("contribution_") or k.startswith("DATAFLOW_") or k in ("FIRST_PASS_FALSE_CLARIFY", "SEGMENTATION_DISAGREE", "CLARIFY_ANSWER_CONSUMED"): R[k] = len(v)
        elif k in ("INPUT_CLAUSE_COUNT", "GROUNDED_CLAUSE_COUNT"): R[k] = sum(v); R[f"n_{k}"] = len(v)
        elif k == "WRONG_LLM_ACTION_PROPOSED": R[k] = sum(1 for x in v if x); R[f"n_{k}"] = len(v)
        elif k == "WRONG_LLM_ACTION_BLOCKED": R[k] = sum(1 for x in v if x); R["n_WRONG_LLM_ACTION_BLOCKED_of_raw_wrong"] = len(v)
        elif k == "RESCUES": R["RESCUE_COUNT"] = len(v); R["RESCUE_KINDS"] = dict(collections.Counter(v))
        elif k in ("CLARIFY_GOLD", "CLARIFY_PRED"): continue
        else: R[k] = m_(v); R[f"n_{k}"] = len(v)
    if mode == "NL_TEACH":
        R["CLARIFICATION_RECALL"] = m_(M.get("CLARIFY_GOLD", [])); R["CLARIFICATION_PRECISION"] = m_(M.get("CLARIFY_PRED", [])); R["n_CLARIFY_PREDICTED_FIRST_PASS"] = len(M.get("CLARIFY_PRED", []))
        R["NL_TEACH_SCENARIO_EXACT"] = R.get("SCENARIO_EXACT"); R["NL_TEACH_SCENARIO_EXACT_FIRST_PASS"] = R.get("SCENARIO_EXACT_FIRST_PASS"); R["NL_TEACH_RESTART_EXACT"] = R.get("RESTART_PROCEDURE_EXACT")
    R["strata"] = {k: {"acc": m_(v), "n": len(v)} for k, v in sorted(strata.items())}
    R["accounting"] = {k: {"mean": m_(v), "n": len(v), "sum": round(sum(v), 3)} for k, v in acct.items()}
    R["failure_taxonomy"] = dict(tax); R["failure_taxonomy_first_pass"] = dict(tax_fp); R["per_scenario"] = per
    R["by_category"] = {c: m_([v["exact"] for v in per.values() if v["category"] == c]) for c in sorted({v["category"] for v in per.values()})}
    R["gates"] = {k: {"rule": f"{op} {th}", "value": R.get(k), "pass": R.get(k) is not None and ((R[k] == th) if op == "==" else (R[k] >= th))} for k, (op, th) in GATES[mode].items()}
    return R


def _refs(steps): import re; return re.findall(r'"var": "(r\d+)"', json.dumps(steps, sort_keys=True))


def _nl_fail(t, g, rs):
    gold = t["gold"]; f0 = nl_first(g); fs = f0["status"]; P = f0.get("grounding") or {}
    if gold["status"] == "CLARIFY": return "NL_MISSED_CLARIFY" if fs == "OK" else ("NL_UNSUPPORTED" if fs == "UNSUPPORTED" else "NL_OTHER")
    if gold["status"] == "UNSUPPORTED": return "NL_UNSUPPORTED" if fs == "OK" else "NL_FALSE_CLARIFY" if fs == "CLARIFY" else "NL_OTHER"
    if gold["status"] == "EXEC_FAILED": return "NL_OP" if fs == "OK" else ("NL_FALSE_CLARIFY" if fs in ("CLARIFY", "UNSUPPORTED") else "VM_EXEC")
    if fs in ("CLARIFY", "UNSUPPORTED"): return "NL_SCHEMA" if P.get("validation_errors") else "NL_FALSE_CLARIFY"
    ex = f0.get("executed_steps") or f0.get("attempted_steps") or []; gs = gold["steps"]
    if len(ex) != len(gs): return "NL_SEQUENCE"
    if [s["op"] for s in ex] != [s["op"] for s in gs]: return "NL_OP"
    if _refs(ex) != _refs(gs): return "NL_REFERENCE"
    if not eqsteps(ex, gs): return "NL_ARGUMENT"
    return "TRACE_MISMATCH"


def _fail(t, g, e, mode):
    kind = t["kind"]; c = (t.get("text") or "").split()[:1]
    if kind == "NL": return _nl_fail(t, g, None) if mode == "NL_TEACH" else "TRACE_MISMATCH"
    if kind == "STEP": return "TRACE_MISMATCH" if t.get("teaching") else "VM_EXEC"
    if kind == "CMD" and c and (c[0] in (":endteach", ":endrevise", ":learn", ":save-last-as") or c[0] == ":propose"):
        if e["status"] == "REJECTED": return "PD_VERIFY_FALSE_ACCEPT"
        if e["status"] in ("VERIFIED",): return "PD_VERIFY_FALSE_REJECT" if g["status"].startswith("REJECTED_") and "VERIF" in g["status"] else "PD_PARAMETER" if g["status"] == "REJECTED_AMBIGUOUS" else "PD_PROGRAM"
        return "PD_PROGRAM"
    if kind == "REQUEST":
        gp = g.get("plan")
        if t.get("composition") == "L1" and gp != RT.plan_str(t["plan"]): return "PR_COMPOSE"
        if not gp or gp.split("(")[0] != t["plan"]["call"]: return "PR_RETRIEVE"
        if gp != RT.plan_str(t["plan"]): return "PR_ARGUMENT"
        return "ROLLBACK" if e["status"] == "VM_EXEC_ERROR" else "PD_PROGRAM"
    if kind == "RUN": return "ROLLBACK" if e["status"] == "VM_EXEC_ERROR" else ("PR_COMPOSE" if t.get("family") == "__composite" else "PD_PROGRAM")
    if kind == "CMD" and c and c[0] == ":accept": return "STORE"
    return "VM_EXEC"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=["dev", "locked_test"]); ap.add_argument("--modes", default="GOLD_TRACE,FORMAL_TEACH,NL_TEACH")
    ap.add_argument("--rescore", action="store_true"); ap.add_argument("--out", default=None); a = ap.parse_args()
    out_dir = a.out or os.path.join(ROOT, "results", a.suite); os.makedirs(out_dir, exist_ok=True)
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]
    for mode in a.modes.split(","):
        fn = os.path.join(out_dir, f"EVAL_{mode}.json")
        if a.rescore:
            E = json.load(open(fn)); RES = {k: ({int(i): t for i, t in v.items()}, []) for k, v in E["traces"].items()}; R = metrics(S, RES, mode)
            for k in ("seconds", "llm_frozen", "capability"):
                if k in E["results"]: R[k] = E["results"][k]
            E["results"] = R; json.dump(E, open(fn, "w"), indent=1, default=str); print(mode, json.dumps({k: v for k, v in R.items() if k not in ("per_scenario",)}, default=str)[:4000]); continue
        work = os.path.join(out_dir, "work"); t0 = time.time(); fr0 = {}
        for w in WORKERS: llm_stop(w); llm_start(w); fr0[w] = llm_frozen(w)
        import queue, threading
        Q = queue.Queue(); [Q.put(sc) for sc in S]; RES = {}; lock = threading.Lock()
        def worker(w):
            while True:
                try: sc = Q.get_nowait()
                except queue.Empty: return
                r = run_scenario(a.suite, sc, mode, work, w)
                with lock: RES[sc["scenario_id"]] = r; print(f"[{mode}] {sc['scenario_id']} on gpu{w[0]}:{w[1]} done {round(time.time() - t0)}s ({len(RES)}/{len(S)})", flush=True)
        th = [threading.Thread(target=worker, args=(w,)) for w in WORKERS]; [x.start() for x in th]; [x.join() for x in th]
        RES = {sc["scenario_id"]: RES[sc["scenario_id"]] for sc in S}
        R = metrics(S, RES, mode); R["seconds"] = round(time.time() - t0, 1); fr1 = {w: llm_frozen(w) for w in WORKERS}
        R["llm_frozen"] = {"workers": [f"gpu{w[0]}:{w[1]}" for w in WORKERS], "per_worker": {f"gpu{w[0]}:{w[1]}": {"param_hash_at_load": fr0[w]["param_hash_at_load"], "param_hash_end": fr1[w]["param_hash_now"],
                           "weights_sha256": fr1[w].get("weights_sha256"), "frozen": fr1[w]["frozen"]} for w in WORKERS},
                           "identical_within_worker_across_restarts": all(fr1[w]["frozen"] for w in WORKERS) and all(h == fr0[tuple(v[1][0]["worker"])]["param_hash_at_load"] for v in RES.values() for h in v[1][0].get("restart_param_hashes", [])),
                           "weights_sha256_identical_all_workers": len({fr1[w].get("weights_sha256") for w in WORKERS}) == 1,
                           "files_sha256": fr1[WORKERS[0]]["files_sha256"], "n_parameters": fr1[WORKERS[0]]["n_parameters"], "optimizer": None, "transformers": fr1[WORKERS[0]]["transformers"],
                           "torch": fr1[WORKERS[0]]["torch"], "dtype": fr1[WORKERS[0]]["dtype"]}
        infos = [i for v in RES.values() for i in v[1]]
        R["capability"] = {"active_procedures_mean_final": m_([len(v[1][-1]["active"]) for v in RES.values()]), "active_procedures_max_final": max(len(v[1][-1]["active"]) for v in RES.values()),
                           "library_bytes_mean": m_([v[1][-1]["lib_bytes"] for v in RES.values()]), "world_bytes_mean": m_([v[1][-1]["world_bytes"] for v in RES.values()]),
                           "nl_llm_calls_total": sum(len(i["nl_llm_calls"]) for i in infos), "retrieval_llm_calls_total": sum(len(i["retrieval_llm_calls"]) for i in infos),
                           "teaching_segment_seconds_mean": m_([v[1][0]["segment_seconds"] for v in RES.values()]),
                           "max_dependency_depth": max((1 if any(p.get("family") == "__composite" for p in sc["meta"]["procedures"]) or sc["category"] == "T11" else 0) for sc in S)}
        json.dump({"results": R, "traces": {k: {str(i): t for i, t in v[0].items()} for k, v in RES.items()}}, open(fn, "w"), indent=1, default=str)
        print(mode, json.dumps({k: v for k, v in R.items() if k not in ("per_scenario",)}, indent=1, default=str)[:8000], flush=True)
    for w in WORKERS: llm_stop(w)


if __name__ == "__main__":
    main()
