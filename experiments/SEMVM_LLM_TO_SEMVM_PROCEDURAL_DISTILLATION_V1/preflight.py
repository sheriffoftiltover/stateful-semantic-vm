"""Teacher-selection preflight (Amendment 001 A3): acquisition only, TEACHER mode, reasoning low / medium / high on 8 registered DEV scenarios."""
import os, sys, json, glob, time
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path.insert(0, ROOT)
import pdx_evaluate as EV
IDS = ["dev-001-S1", "dev-005-S3", "dev-009-S5", "dev-011-S6", "dev-017-S9", "dev-021-S11", "dev-023-S12", "dev-030-S15"]
S = [json.load(open(os.path.join(ROOT, "scenarios", "dev", i + ".json"))) for i in IDS]; out = {}
for w in EV.WORKERS: EV.svc("restart", w)
EV.teacher_up(); import client as CL; m0 = CL.meter_usd()
for eff in ["low", "medium", "high"]:
    t0 = time.time(); od = os.path.join(ROOT, "results", "preflight", eff); os.makedirs(od, exist_ok=True)
    ACQ = EV.acquire("TEACHER", S, od, ["--backend", "MODAL", "--model", "openai/gpt-oss-120b", "--reasoning", eff]); rows = []
    for sc in S:
        A = ACQ[sc["scenario_id"]]
        if "error" in A: rows.append({"scenario": sc["scenario_id"], "error": A["error"][-300:]}); continue
        H = EV.active_hashes(od, "TEACHER", [sc]).get(sc["scenario_id"], {})
        for O in A["targets"]:
            it = next(c for c in sc["curriculum"] if c["name"] == O["name"]); ex = H.get(O["name"]) == EV.gold_hash(it)
            toks = sum((r["provenance"].get("input_tokens") or 0) + (r["provenance"].get("output_tokens") or 0) for r in O["teacher_log"] if not r["provenance"].get("cached"))
            rows.append({"scenario": sc["scenario_id"], "target": O["name"], "status": O["status"], "learned_exact": ex, "teacher_turns": O["teacher_turns"], "demos": len(O["demos"]),
                         "questions": len(O["student_questions"]), "tokens": toks, "unsupported_lines": sum(1 for D in O["demos"] for r in D["results"] if r["status"] == "UNSUPPORTED"),
                         "lines_ok": sum(1 for D in O["demos"] for r in D["results"] if r["status"] == "OK"), "lines": sum(len(D["results"]) for D in O["demos"])})
    ok = [r for r in rows if "error" not in r]
    out[eff] = {"learned_exact": sum(r["learned_exact"] for r in ok), "targets": len(ok), "active": sum(r["status"] == "ACTIVE" for r in ok), "tokens": sum(r["tokens"] for r in ok),
                "student_trace_line_ok": round(sum(r["lines_ok"] for r in ok) / max(1, sum(r["lines"] for r in ok)), 3), "questions": sum(r["questions"] for r in ok),
                "unsupported_lines": sum(r["unsupported_lines"] for r in ok), "errors": len(rows) - len(ok), "seconds": round(time.time() - t0, 1), "rows": rows}
    print(eff, {k: v for k, v in out[eff].items() if k != "rows"}, flush=True)
best = sorted(out, key=lambda e: (-out[e]["learned_exact"], out[e]["tokens"]))[0]
out["selected"] = best; out["meter_usd_delta"] = round(CL.meter_usd() - m0, 3)
json.dump(out, open(os.path.join(ROOT, "results", "TEACHER_PREFLIGHT.json"), "w"), indent=1); print("SELECTED", best, "meter delta", out["meter_usd_delta"])
for w in EV.WORKERS: EV.svc("stop", w)
