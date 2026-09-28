"""Procedure verification (spec §19-§24). A candidate (from ANY proposer) is judged only against the EVIDENCE: the recorded successful traces
and the evidence interface derived from them (abstraction.abstract) -- never against the proposer's own claims, never against gold.
Stages (first failure decides the rejection status):
  0 static validation                        -> REJECTED_UNSAFE
  1 interface (params = evidence params)     -> REJECTED_FAILED_COUNTERFACTUAL  (over- / under-generalization)
  2 source replay: every trace, exact return + post-state                -> REJECTED_FAILED_REPLAY
  3 counterfactual: new argument values; reference = the UNABSTRACTED trace steps with value substitution in the evidence slots, executed
    on the trace's start state (and on every other trace's start state = state generalization)             -> REJECTED_FAILED_COUNTERFACTUAL
  3b state perturbation: same comparison on perturbed start states (STATUS flipped) so constants are exercised -> REJECTED_FAILED_COUNTERFACTUAL
  4 negative cases (missing input, wrong type, empty result, ambiguous entity, deleted object, empty world / precondition) -> REJECTED_UNSAFE
  5 transaction safety (injected failure after every op) + 6 determinism (two identical runs)             -> REJECTED_UNSAFE / _NONDETERMINISTIC"""
import os, sys, copy, json, shutil, tempfile, itertools
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "core", "state"))
import lang as L, executor as X, validate as V, abstraction as A, store as ST


def _copy(src, work):
    fd, p = tempfile.mkstemp(suffix=".sqlite", dir=work); os.close(fd); shutil.copy(src, p); return ST.Store(p)


def outcome(store, r): return {"status": r["status"], "return": r["return"], "post_state": store.canonical_state()}


def run_candidate(snap, work, lib, proc, args, **kw):
    s = _copy(snap, work); r = X.invoke(s, lib, proc, args, **kw); o = outcome(s, r); o["raw"] = r; s.close(); return o


def run_reference(snap, work, lib, steps):
    """the unabstracted primitive sequence (concrete trace steps), executed as one transaction"""
    return run_candidate(snap, work, lib, {"name": "__reference", "parameters": [], "body": steps}, {})


def substitute(steps, evidence, newvals):
    s = copy.deepcopy(steps)
    for p in evidence["params"]:
        if p["name"] in newvals:
            for sp in p["slots"]: A.set_path(s, tuple(sp), {"const": newvals[p["name"]]})
    return s


def map_params(cand, evidence):
    """candidate parameter -> evidence parameter. By slot path when the candidate body places the parameter in an evidence slot; else by type order."""
    cand_slots = {}
    def walk(o, path):
        if isinstance(o, dict):
            if set(o) == {"param"}: cand_slots.setdefault(o["param"], []).append(path); return
            for k, v in o.items(): walk(v, path + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, path + (i,))
    walk(cand["body"], ())
    ev = {tuple(s): e["name"] for e in evidence["params"] for s in e["slots"]}; m = {}
    for p in cand["parameters"]:
        hits = {ev.get(tuple(sp)) for sp in cand_slots.get(p["name"], [])} - {None}
        if len(hits) == 1: m[p["name"]] = hits.pop()
    if len(m) != len(cand["parameters"]) or len(set(m.values())) != len(m):
        m = {}; byt = {}
        for e in evidence["params"]: byt.setdefault(e["type"], []).append(e["name"])
        for p in cand["parameters"]:
            if byt.get(p["type"]): m[p["name"]] = byt[p["type"]].pop(0)
    return m


def cf_values(store, evidence, k=0):
    """deterministic counterfactual values: values present in the world first (meaningful), never a source value or a trace constant"""
    consts = {v for _, _, v in evidence["constants"]}; out = {}
    st = store.canonical_state(); present = {"PERSON": sorted({a for _, a in st["aliases"]}), "EVENT_TYPE": sorted({t for _, t in st["objects"] if t in L.EVENT_TYPES})}
    for vid in sorted({o for _, _, o in st["relations"] if not o.startswith(tuple(t.lower() + ":" for t in L.EVENT_TYPES)) and not o.startswith("person:")}):
        r = store.value(vid)
        if r: present.setdefault(r[0], []).append(r[2])
    for e in evidence["params"]:
        pool = [v for v in present.get(e["type"], []) if v not in e["values"] and v not in consts] + sorted(v for v in X.VOCAB[e["type"]] if v not in e["values"] and v not in consts)
        pool = list(dict.fromkeys(pool)); out[e["name"]] = pool[min(k, len(pool) - 1)]
    return out


def verify(cand, evidence, traces, library, work=None):
    work = work or tempfile.mkdtemp(prefix="pdverify_"); tests = []
    def T(tid, ok, info=None): tests.append((tid, bool(ok), info or {})); return ok
    try: vinfo = V.validate(cand, library)
    except V.ValidationError as e:
        T("static_validation", False, {"reason": e.reason}); return "REJECTED_UNSAFE", tests, None
    T("static_validation", True, vinfo)
    pm = map_params(cand, evidence)
    if sorted(p["type"] for p in cand["parameters"]) != sorted(e["type"] for e in evidence["params"]) or len(pm) != len(evidence["params"]):
        T("interface", False, {"candidate": cand["parameters"], "evidence": [(e["name"], e["type"]) for e in evidence["params"]]}); return "REJECTED_FAILED_COUNTERFACTUAL", tests, vinfo
    T("interface", True, pm); inv = {v: k for k, v in pm.items()}
    args_of = lambda vals: {inv[e]: v for e, v in vals.items()}
    # 2 source replay
    for i, tr in enumerate(traces):
        vals = {e["name"]: e["values"][i] for e in evidence["params"]}; o = run_candidate(tr["snapshot"], work, library, cand, args_of(vals))
        ok = o["status"] == "OK" and o["return"] == tr["result"] and o["post_state"] == tr["post_state"]
        if not T(f"replay_{i}", ok, {"got": o["return"], "want": tr["result"], "status": o["status"]}): return "REJECTED_FAILED_REPLAY", tests, vinfo
    norm0 = A.normalize_vars(traces[0]["steps"])
    # 3 counterfactual (all params changed; each param alone; on every trace's start state)
    if evidence["params"]:
        for i, tr in enumerate(traces):
            base = ST.Store(tr["snapshot"]); base_vals = {e["name"]: e["values"][i] for e in evidence["params"]}; norm_i = A.normalize_vars(tr["steps"])
            cases = [cf_values(base, evidence, 0), cf_values(base, evidence, 1)] + [dict(base_vals, **{e["name"]: cf_values(base, evidence, 0)[e["name"]]}) for e in evidence["params"]] if len(evidence["params"]) > 1 else [cf_values(base, evidence, 0), cf_values(base, evidence, 1)]
            base.close()
            for j, nv in enumerate(cases):
                ref = run_reference(tr["snapshot"], work, library, substitute(norm_i, evidence, nv)); got = run_candidate(tr["snapshot"], work, library, cand, args_of(nv))
                ok = {k: ref[k] for k in ("status", "return", "post_state")} == {k: got[k] for k in ("status", "return", "post_state")}
                if not T(f"counterfactual_t{i}_{j}", ok, {"args": nv, "ref": [ref["status"], ref["return"]], "got": [got["status"], got["return"]]}): return "REJECTED_FAILED_COUNTERFACTUAL", tests, vinfo
    # 3b state perturbation (added pre-DEV, ENGINEERING_LOG #1): constants must be exercised -- the candidate must agree with the unabstracted
    #    reference on perturbed copies of every start state (all events CLOSED; alternate events CLOSED), with source and counterfactual values
    for i, tr in enumerate(traces):
        base = ST.Store(tr["snapshot"]); vals_i = {e["name"]: e["values"][i] for e in evidence["params"]}; cf = cf_values(base, evidence, 0) if evidence["params"] else {}; base.close()
        norm_i = A.normalize_vars(tr["steps"])
        for pk, sel in (("all_closed", lambda k: True), ("alternate_closed", lambda k: k % 2 == 0)):
            s = _copy(tr["snapshot"], work); s.begin()
            for k, (oid, _) in enumerate(s.active_objects()):
                if oid.split(":")[0].upper() in L.EVENT_TYPES and sel(k): s.set_attr(oid, "STATUS", "CLOSED")
            s.commit(); ppath = s.path; s.close()
            for tag, vv in (("src", vals_i), ("cf", cf)):
                if tag == "cf" and not evidence["params"]: continue
                ref = run_reference(ppath, work, library, substitute(norm_i, evidence, vv)); got = run_candidate(ppath, work, library, cand, args_of(vv))
                ok = [ref["status"], ref["return"], ref["post_state"]] == [got["status"], got["return"], got["post_state"]]
                if not T(f"perturb_{pk}_t{i}_{tag}", ok, {"ref": [ref["status"], ref["return"]], "got": [got["status"], got["return"]]}): return "REJECTED_FAILED_COUNTERFACTUAL", tests, vinfo
    # 4 negative cases
    tr = traces[0]; vals0 = {e["name"]: e["values"][0] for e in evidence["params"]}; snap = tr["snapshot"]
    def unchanged(o): return o["raw"]["state_before"] == o["raw"]["state_after"]
    if evidence["params"]:
        first = evidence["params"][0]
        o = run_candidate(snap, work, library, cand, args_of({k: v for k, v in vals0.items() if k != first["name"]}))
        if not T("neg_missing_input", o["status"] == "MISSING_ARGUMENT" and unchanged(o), {"status": o["status"]}): return "REJECTED_UNSAFE", tests, vinfo
        wrong = "noon" if first["type"] != "TIME" else "Alice"
        o = run_candidate(snap, work, library, cand, args_of(dict(vals0, **{first["name"]: wrong})))
        if not T("neg_wrong_type", o["status"] == "TYPE_ERROR" and unchanged(o), {"status": o["status"]}): return "REJECTED_UNSAFE", tests, vinfo
        base = ST.Store(snap); st = base.canonical_state(); used = {a for _, a in st["aliases"]} | {base.value(o_)[2] for _, _, o_ in st["relations"] if base.value(o_)}; base.close()
        absent = {e["name"]: next((v for v in sorted(X.VOCAB[e["type"]]) if v not in used and v not in e["values"]), None) for e in evidence["params"]}
        if all(v is not None for v in absent.values()) and all(e["type"] not in ("EVENT_TYPE", "STATUS") for e in evidence["params"]):
            ref = run_reference(snap, work, library, substitute(norm0, evidence, absent)); got = run_candidate(snap, work, library, cand, args_of(absent))
            if not T("neg_empty_result", [ref["status"], ref["return"], ref["post_state"]] == [got["status"], got["return"], got["post_state"]], {"ref": ref["status"], "got": got["status"]}): return "REJECTED_UNSAFE", tests, vinfo
        pp = [e for e in evidence["params"] if e["type"] == "PERSON"]
        if pp:
            s = _copy(snap, work); dup = cf_values(s, evidence, 0)[pp[0]["name"]]
            for _ in range(2): oid = s.create_object("PERSON", "t", "t"); s.add_alias(oid, dup, "t")
            r = X.invoke(s, library, cand, args_of(dict(vals0, **{pp[0]["name"]: dup}))); s.close()
            if not T("neg_ambiguous_entity", r["status"] == "RESOLUTION_AMBIGUOUS" and r["state_before"] == r["state_after"], {"status": r["status"]}): return "REJECTED_UNSAFE", tests, vinfo
    ftype = next((s_["type"]["const"] for s_ in norm0 if s_["op"] in ("FIND", "FIND_LAST") and "const" in s_["type"]), None)
    if ftype:
        s = _copy(snap, work); last = s.last_active(ftype)
        if last:
            s.begin(); s.delete_object(last); s.commit()
        p = s.path; s.close()
        ref = run_reference(p, work, library, norm0 if not evidence["params"] else substitute(norm0, evidence, vals0)); got = run_candidate(p, work, library, cand, args_of(vals0))
        if not T("neg_deleted_object", [ref["status"], ref["return"], ref["post_state"]] == [got["status"], got["return"], got["post_state"]] and (got["status"] == "OK" or unchanged(got)), {"ref": ref["status"], "got": got["status"]}): return "REJECTED_UNSAFE", tests, vinfo
    fd, empty = tempfile.mkstemp(suffix=".sqlite", dir=work); os.close(fd); os.remove(empty); ST.Store(empty).close()
    ref = run_reference(empty, work, library, norm0 if not evidence["params"] else substitute(norm0, evidence, vals0)); got = run_candidate(empty, work, library, cand, args_of(vals0))
    if not T("neg_empty_world_precondition", [ref["status"], ref["return"], ref["post_state"]] == [got["status"], got["return"], got["post_state"]] and (got["status"] == "OK" or unchanged(got)), {"ref": ref["status"], "got": got["status"]}): return "REJECTED_UNSAFE", tests, vinfo
    # 5 transaction safety
    base = run_candidate(snap, work, library, cand, args_of(vals0)); nops = base["raw"]["ops"]
    if vinfo["effect"] == "STATEFUL":
        for k in range(1, max(1, nops)):
            o = run_candidate(snap, work, library, cand, args_of(vals0), fail_after_ops=k)
            if not T(f"txn_inject_after_{k}", o["status"] == "VM_EXEC_ERROR" and unchanged(o)): return "REJECTED_UNSAFE", tests, vinfo
    # 6 determinism
    a = run_candidate(snap, work, library, cand, args_of(vals0)); b = run_candidate(snap, work, library, cand, args_of(vals0))
    same = json.dumps([a["raw"]["trace"], a["raw"]["diff"], a["return"], a["raw"]["state_after"]], sort_keys=True) == json.dumps([b["raw"]["trace"], b["raw"]["diff"], b["return"], b["raw"]["state_after"]], sort_keys=True)
    if not T("determinism", same): return "REJECTED_NONDETERMINISTIC", tests, vinfo
    shutil.rmtree(work, ignore_errors=True); return "VERIFIED", tests, vinfo
