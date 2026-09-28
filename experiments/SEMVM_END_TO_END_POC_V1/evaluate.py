"""POC evaluation (spec §22-§25, §30-§33, M3-M7). Phases:
 1. neural pass: every assertion of the suite through envelope + FROZEN binder -> results/<suite>/NEURAL_OUTPUTS.json (frozen-state check)
 2. runtime replay from the cached neural outputs, FULL and GOLD_IR, each restart segment in a fresh process (run_segment.py) -> traces/
 3. metrics vs the independent oracle: IR_EXACT, PARENT_ACC (single / same / mixed), ENTITY / TIME / REFERENCE resolution, VM_PROGRAM_EXACT,
    STATE_EXACT, QUERY_RESULT_EXACT, SCENARIO_EXACT, render check, failure taxonomy; determinism replay (bit-identical traces)
python evaluate.py --suite dev|locked_test"""
import os, sys, json, glob, subprocess, argparse, hashlib, shutil, time, collections, platform
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT)
WORK = ROOT   # output base (results/, traces/); set by --work (backend job output directory)
import pipeline as PL
GATES = {"IR_EXACT": .95, "PARENT_ACC": .97, "VM_PROGRAM_EXACT": 1.0, "STATE_EXACT": .95, "QUERY_RESULT_EXACT": .95, "SCENARIO_EXACT": .90}
m_ = lambda v: round(sum(v) / len(v), 4) if v else None


def load_suite(suite): return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", suite, "*.json")))]


def neural_pass(suite, S, out_dir):
    import binder as BN, torch
    b = BN.Binder(); cache = {}; sess = PL.Session(":memory:", "FULL", binder=b, cache=cache); t0 = time.time()
    for sc in S:
        for t in sc["turns"]:
            if t["kind"] == "ASSERT": sess.neural(t["text"])
    frozen = b.assert_frozen()
    meta = {"checkpoint_sha256": BN.MANIFEST["checkpoint"]["sha256"], "state_hash_before": b.state_hash0, "state_hash_after": b.state_hash(), "frozen_ok": frozen, "requires_grad_any": any(p.requires_grad for p in b.model.parameters()),
            "optimizer": None, "device": b.dev, "torch": torch.__version__, "python": platform.python_version(), "machine": platform.machine(), "n_assertions": len(cache), "seconds": round(time.time() - t0, 1)}
    json.dump(cache, open(os.path.join(out_dir, "NEURAL_OUTPUTS.json"), "w"), indent=1, sort_keys=True); json.dump(meta, open(os.path.join(out_dir, "NEURAL_PASS.json"), "w"), indent=1); return meta


def replay(suite, S, mode, out_dir, tag=""):
    cache = os.path.join(out_dir, "NEURAL_OUTPUTS.json"); dbd = os.path.join(out_dir, f"db_{mode}{tag}"); td = os.path.join(WORK, "traces", suite, f"{mode}{tag}")
    shutil.rmtree(dbd, ignore_errors=True); shutil.rmtree(td, ignore_errors=True); os.makedirs(dbd); os.makedirs(td); T = {}
    for sc in S:
        p = os.path.join(ROOT, "scenarios", suite, f"{sc['scenario_id']}.json"); db = os.path.join(dbd, f"{sc['scenario_id']}.sqlite"); cuts = [i for i, t in enumerate(sc["turns"]) if t["kind"] == "RESTART"]
        segs = []; a = 0
        for c in cuts + [len(sc["turns"])]: segs.append((a, c)); a = c + 1
        tr = []
        for a, b in segs:
            if a >= b: continue
            o = os.path.join(td, f"{sc['scenario_id']}_{a}_{b}.json")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "run_segment.py"), "--scenario", p, "--db", db, "--mode", mode, "--cache", cache, "--start", str(a), "--end", str(b), "--out", o], capture_output=True, text=True)
            if r.returncode: raise SystemExit(f"segment failed {sc['scenario_id']} {a}-{b}: {r.stderr[-2000:]}")
            tr += json.load(open(o)); os.remove(o)
        json.dump(tr, open(os.path.join(td, f"{sc['scenario_id']}.json"), "w"), indent=1, default=str); T[sc["scenario_id"]] = tr
    return T


def mod_parent_eval(gold, pred):
    """per gold non-TODO relation: (correct parent?) — matched in pred by predicate + object surface"""
    gs = {o["local_id"]: o.get("surface") for o in gold["objects"]}; ps = {o["local_id"]: o.get("surface") for o in pred["objects"]} if pred else {}
    out = []
    for r in gold["relations"]:
        if r["predicate"] == "TODO": continue
        hit = [q for q in (pred or {"relations": []})["relations"] if q["predicate"] == r["predicate"] and ps.get(q["object"]) == gs[r["object"]]]
        out.append(bool(hit) and hit[0]["subject"] == r["subject"])
    return out


def ref_target(tr):
    prog = tr.get("VM_PROGRAM") or []
    for ins in prog:
        if ins[0] == "MATCH": return ins[1]["target"]
        if ins[0] in ("RETRACT", "DELETE", "ASSERT"): return ins[1]
    return None


def expected_response(e):
    if e["status"] != "OK": return None
    if e["result"] is None: return "OK."
    return ", ".join(sorted(e["result"])) if e["result"] else "No matching item."


def metrics(S, TF, TG):
    M = collections.defaultdict(list); tax = collections.Counter(); per = {}; gold_ok = []
    for sc in S:
        sid = sc["scenario_id"]; tf = {t["turn"]: t for t in TF[sid]}; tg = {t["turn"]: t for t in TG[sid]}; ok_f = ok_g = True; first = None
        for i, (t, e) in enumerate(zip(sc["turns"], sc["expected"])):
            if t["kind"] == "RESTART": continue
            f, g = tf[i], tg[i]
            def turn_ok(x):
                good = x["status"] == e["status"] and x["STATE_CANONICAL_AFTER"] == e["state"]
                if t["kind"] == "COMMAND" and t["text"].startswith("QUERY") and e["status"] == "OK": good = good and x.get("RETURN_RENDERED") == e["result"]
                return good
            gi, fi = turn_ok(g), turn_ok(f); ok_g &= gi
            M["STATE_EXACT"].append(f["STATE_CANONICAL_AFTER"] == e["state"])
            if t["kind"] == "COMMAND" and t["text"].startswith("QUERY"): M["QUERY_RESULT_EXACT"].append(f["status"] == e["status"] and (e["status"] != "OK" or f.get("RETURN_RENDERED") == e["result"]))
            er = expected_response(e)
            if er is not None: M["RESPONSE_EXACT"].append(f["status"] == "OK" and f["RESPONSE"] == er)          # end-to-end answer vs oracle
            if f["status"] == "OK":                                                                                 # render correctness of the returned result itself
                own = "OK." if f.get("RETURN") is None else (", ".join(f["RETURN_RENDERED"]) if f["RETURN_RENDERED"] else "No matching item.")
                M["RENDER_EXACT"].append(f["RESPONSE"] == own)
            if t["kind"] == "ASSERT":
                pred = f.get("CANONICAL_IR"); M["IR_EXACT"].append(pred == t["gold_ir"]); pa = mod_parent_eval(t["gold_ir"], pred)
                kind = "single" if len(t["pattern"]) == 1 else "same" if t["pattern"] in ("OO", "II") else "mixed"
                M["PARENT_ACC"] += pa; M[f"PARENT_ACC_{kind}"] += pa
                if f.get("RESOLUTION") and g.get("RESOLUTION"):
                    fe = [d for d in f["RESOLUTION"] if d[0] == "ENTITY"]; ge = [d for d in g["RESOLUTION"] if d[0] == "ENTITY"]
                    if fe or ge: M["ENTITY_RESOLUTION_ACC"].append(fe == ge)
                    ft = [d for d in f["RESOLUTION"] if d[0] == "TIME"]; gt = [d for d in g["RESOLUTION"] if d[0] == "TIME"]
                    if ft or gt: M["TIME_RESOLUTION_ACC"].append(ft == gt)
            if t["kind"] == "COMMAND" and "LAST_" in t["text"]: M["REFERENCE_RESOLUTION_ACC"].append(f["status"] == g["status"] == e["status"] and ref_target(f) == ref_target(g))
            if f["STATE_BEFORE"] == g["STATE_BEFORE"] and (t["kind"] == "COMMAND" or f.get("CANONICAL_IR") == t["gold_ir"]) and "VM_PROGRAM" in g:
                M["VM_PROGRAM_EXACT"].append(f.get("VM_PROGRAM") == g["VM_PROGRAM"])
            if not fi and ok_f:
                ok_f = False
                if not gi: first = "RUNTIME:" + ("QUERY" if t["text"].startswith("QUERY") else "VM_EXEC")
                elif t["kind"] == "ASSERT":
                    pred = f.get("CANONICAL_IR")
                    if f["status"] == "UNSUPPORTED_INPUT": first = "UNSUPPORTED"
                    elif pred is None or f["status"] == "IR_VALIDATION_ERROR": first = "IR_INVALID"
                    elif pred != t["gold_ir"]:
                        strip = lambda ir: (sorted(o["type"] for o in ir["objects"]), sorted((r["predicate"], {o["local_id"]: o.get("surface") for o in ir["objects"]}[r["object"]]) for r in ir["relations"]))
                        first = "N_BIND" if strip(pred) == strip(t["gold_ir"]) else "N_PARSE"
                    elif f.get("RESOLUTION") != g.get("RESOLUTION"): first = "RESOLVE_ENTITY"
                    else: first = "STORE"
                else: first = "RESOLVE_REFERENCE" if f["status"] == "RESOLVE_REFERENCE" else ("QUERY" if t["text"].startswith("QUERY") else "VM_EXEC")
        M["SCENARIO_EXACT"].append(ok_f); gold_ok.append(ok_g); per[sid] = {"category": sc["category"], "FULL_exact": ok_f, "GOLD_IR_exact": ok_g, "first_failure": first}
        if not ok_f: tax[first] += 1
    R = {k: m_(v) for k, v in M.items()}; R.update({f"n_{k}": len(v) for k, v in M.items()}); R["GOLD_IR_SCENARIO_EXACT"] = m_(gold_ok)
    R["gates"] = {k: {"threshold": th, "value": R.get(k), "pass": R.get(k) is not None and R[k] >= th} for k, th in GATES.items()}; R["gates"]["GOLD_IR_SCENARIO_EXACT"] = {"threshold": 1.0, "value": R["GOLD_IR_SCENARIO_EXACT"], "pass": R["GOLD_IR_SCENARIO_EXACT"] == 1.0}
    R["all_gates_pass"] = all(v["pass"] for v in R["gates"].values()); R["failure_taxonomy"] = dict(tax); R["per_scenario"] = per
    R["by_category"] = {c: {"n": sum(1 for v in per.values() if v["category"] == c), "FULL_exact": m_([v["FULL_exact"] for v in per.values() if v["category"] == c])} for c in sorted({v["category"] for v in per.values()})}
    return R


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True, choices=["dev", "locked_test"]); ap.add_argument("--skip-neural", action="store_true"); ap.add_argument("--work"); a = ap.parse_args()
    global WORK
    WORK = os.path.abspath(a.work) if a.work else ROOT
    out = os.path.join(WORK, "results", a.suite); os.makedirs(out, exist_ok=True); S = load_suite(a.suite); t0 = time.time()
    NP = json.load(open(os.path.join(out, "NEURAL_PASS.json"))) if a.skip_neural else neural_pass(a.suite, S, out)
    TG = replay(a.suite, S, "GOLD_IR", out); TF = replay(a.suite, S, "FULL", out); TF2 = replay(a.suite, S, "FULL", out, tag="_rerun")
    strip = lambda T: json.dumps({k: [{x: y for x, y in t.items() if x != "pid"} for t in v] for k, v in T.items()}, sort_keys=True, default=str)
    R = metrics(S, TF, TG); R["neural_pass"] = NP; R["determinism_full_replay_bit_identical"] = strip(TF) == strip(TF2)
    R["restart_segments_fresh_process"] = {sid: sorted({t["pid"] for t in v}) != [] and len({t["pid"] for t in v}) for sid, v in TF.items() if any(t["kind"] == "RESTART" for t in next(s for s in S if s["scenario_id"] == sid)["turns"])}
    R["seconds"] = round(time.time() - t0, 1); json.dump(R, open(os.path.join(out, "EVAL.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in R.items() if k not in ("per_scenario", "neural_pass")}, indent=1, default=str))


if __name__ == "__main__":
    main()
