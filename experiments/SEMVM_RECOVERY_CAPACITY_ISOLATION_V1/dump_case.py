"""Full evidence dump for one scenario x arm (read-only): hosted teacher messages, hosted-grounder raw outputs, slot ledger + transaction,
committed traces, learned procedure AST, verification result, ACTIVE DB record, post-handoff reuse trace.
python dump_case.py --suite dev_a --scenario dev_a-022-S15 --arm D [--out results/examples/<sid>_<arm>.md]"""
import os, sys, json, glob, sqlite3, argparse
ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path[:0] = [os.path.join(ROOT, d) for d in ("procedure", "core", "core/neural/vendor")]
import lang as L


def j(o): return json.dumps(o, indent=1, default=str)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", default="dev_a"); ap.add_argument("--scenario", required=True); ap.add_argument("--arm", default="D"); ap.add_argument("--out", default=None); a = ap.parse_args()
    sid, arm, su = a.scenario, a.arm, a.suite; R = os.path.join(ROOT, "results", su); W = os.path.join(R, "work", arm, sid); ART = os.path.join(R, "acq_artifacts", arm, sid)
    sc = json.load(open(os.path.join(ROOT, "scenarios", su, sid + ".json"))); A = json.load(open(os.path.join(W, "acq.json")))
    T = json.load(open(os.path.join(ROOT, "teaching_traces", su, arm, sid + ".json"))); out = []
    P = lambda *x: out.append(" ".join(str(y) for y in x))
    P(f"# {sid} — arm {arm} ({su})\n"); P(f"Stratum {sc['stratum']}: {sc['stratum_name']}. Arm {arm}: {A.get('mode')} lesson, recovery {A.get('recovery')}, grounder {A.get('grounder')}, teacher max_tokens {A.get('teacher_max_tokens')}.\n")
    for it in sc["curriculum"]:
        P(f"Target `{it['name']}({', '.join(f'{p}:{t}' for p, t in it['sig'].items())})` — goal: {it['goal']}\n\nReference (gold) procedure:\n```\n{it['gold']}\n```\n")
    # 1 teacher messages
    P("## 1. Hosted teacher messages (visible dialogue; the teacher's hidden reasoning is not part of the protocol)\n")
    for tg in T["targets"]:
        P(f"### target {tg['name']} — final status {tg['status']}\n")
        P("**System prompt (teacher card):** see `teacher/protocol.py` CARD (sha in `locks/FINAL_CONFIG_FREEZE.json`).\n")
        for k, m in enumerate(tg["transcript"][1:]):
            P(f"**{'TEACHER' if m['role'] == 'assistant' else 'STUDENT → teacher'}:**\n```\n{m['content']}\n```")
        P("\nTeacher-call provenance:")
        for l in tg["teacher_log"]:
            pv = l.get("provenance") or {}
            P(f"- {l['kind']}: role {pv.get('role')}, route {pv.get('route')}, request {str(pv.get('request_hash'))[:16]}…, cached {pv.get('cached')}, tokens in/out {pv.get('input_tokens')}/{pv.get('output_tokens')}, finish {pv.get('finish_reason')}, latency {pv.get('latency_s')} s, reasoning chars {pv.get('reasoning_chars')}")
    # 2 grounder outputs
    P("\n## 2. Hosted-grounder outputs (one isolated request per line; raw envelope + deterministic checks)\n")
    for O in A["targets"]:
        for D in O["demos"]:
            for r in D["results"]:
                P(f"### line `{r['line']}` (slot {r.get('slot_id')}, terminal_allowed={r.get('terminal_allowed')}, reference_choice={r.get('reference_choice')}) → **{r['status']}**" + (f" ({r.get('clarify_kind')}: {r.get('reason')})" if r['status'] != 'OK' else ""))
                for k, at in enumerate(r.get("attempts") or []):
                    rh = at.get("request_hash"); f = os.path.join(ROOT, "grounder_responses", f"{rh}.json") if rh else None
                    raw = json.load(open(f))["text"] if f and os.path.exists(f) else r.get("grounding_raw")
                    P(f"- attempt {k + 1}: status {at.get('status')}; feedback {at.get('feedback')}\n```json\n{raw}\n```")
                if r.get("executed_steps"): P("  executed (parent step AST):\n```\n" + "\n".join(L.fmt_step(s) for s in r["executed_steps"]) + "\n```")
    # 3 ledger + transaction
    P("\n## 3. Transaction and slot ledger\n")
    P("Transaction record:\n```json\n" + j(json.load(open(os.path.join(ROOT, "teaching_transactions", su, arm, sid + ".json")))) + "\n```")
    P("Slot ledger:\n```json\n" + j(json.load(open(os.path.join(ROOT, "slot_ledgers", su, arm, sid + ".json")))) + "\n```")
    # 4 committed traces
    P("\n## 4. Committed traces (learning evidence admitted at COMMIT)\n")
    ex = json.load(open(os.path.join(ART, "examples.json")))
    for name, trs in ex.items():
        for k, tr in enumerate(trs):
            P(f"### {name} — example {k + 1} (interaction {tr.get('interaction_id')}), declared {tr.get('declared')}\n```\n" + "\n".join(L.fmt_step(s) for s in tr["steps"]) + f"\n```\nresult at commit: `{json.dumps(tr.get('result'))}`")
    for f in sorted(glob.glob(os.path.join(ART, "teaching_traces", "*.json"))):
        t = json.load(open(f)); P(f"\nStudent teaching-trace record `{os.path.basename(f)}`: trace_sha256 {t.get('trace_sha256')}, start snapshot sha {str(t.get('start_snapshot_sha256'))[:16]}…, {len(t.get('utterances', []))} utterance records")
    # 5-6 candidates / verification
    P("\n## 5. Learned procedure AST and 6. verification result\n")
    for f in sorted(glob.glob(os.path.join(ART, "candidates", "*.json"))):
        C = json.load(open(f)); ch = (C.get("paths") or {}).get(C.get("chosen") or "deterministic", {})
        P(f"### candidate `{os.path.basename(f)}` — status **{C.get('status')}**" + (f", origin {C.get('origin') or C.get('source')}" if (C.get('origin') or C.get('source')) else ""))
        prog = ch.get("program") or C.get("program")
        if prog:
            try: P("```\n" + L.fmt_procedure(prog) + "\n```")
            except Exception: P("```json\n" + j(prog) + "\n```")
            P("AST (JSON):\n```json\n" + j(prog) + "\n```")
        tests = ch.get("tests") or []
        P(f"verifier: {sum(1 for _, o, *_ in tests if o)}/{len(tests)} tests passed; status {ch.get('status')}; reason {ch.get('reason')}")
        for t in tests: P(f"- {t[0]}: {'PASS' if t[1] else 'FAIL'} {json.dumps(t[2])[:220] if len(t) > 2 and t[2] else ''}")
    P("\nFalse-accept probes run against the same evidence (must be rejected):\n```json\n" + j(A.get("false_accept_probes")) + "\n```")
    # 7 ACTIVE DB record
    P("\n## 7. ACTIVE DB record (`procedures.sqlite`, read-only)\n")
    db = sqlite3.connect(f"file:{os.path.join(W, 'procedures.sqlite')}?mode=ro", uri=True)
    for (tname,) in db.execute("select name from sqlite_master where type='table'"):
        cols = [c[1] for c in db.execute(f"pragma table_info({tname})")]; rows = db.execute(f"select * from {tname}").fetchall()
        P(f"### table `{tname}` ({len(rows)} rows)\ncolumns: {cols}\n```")
        for row in rows: P(" | ".join((str(v)[:600] if not isinstance(v, bytes) else f"<{len(v)} bytes>") for v in row))
        P("```")
    db.close()
    # 8 reuse
    P("\n## 8. Post-handoff reuse (teacher destroyed, fresh student processes, network guard)\n")
    HO = json.load(open(os.path.join(R, "HANDOFF.json"))); P(f"handoff: app {HO.get('app')}, stop rc {HO.get('modal_app_stop_rc')}, endpoint after stop {HO.get('endpoint_after_stop')}, destroyed {HO.get('teacher_destroyed')}\n")
    E = json.load(open(os.path.join(R, f"RCI_{arm}.json"))); RU = E["reuse"][sid]
    for i, (t, e) in enumerate(zip(sc["post_turns"], sc["post_expected"])):
        if t["kind"] == "RESTART": P("- **[RESTART: student process + local LLM service restarted; learn/ transcripts absent]**"); continue
        g = RU["turns"].get(str(i)) or RU["turns"].get(i) or {}
        ok = g.get("status") == (e or {}).get("status") and g.get("STATE") == (e or {}).get("state") and ("return" not in (e or {}) or g.get("return") == e.get("return"))
        P(f"- `{t['text']}` → status {g.get('status')}, plan `{g.get('plan')}`, return `{json.dumps(g.get('return'))}` | expected {e.get('status')} `{json.dumps(e.get('return'))}` | world state {'==' if g.get('STATE') == e.get('state') else '!='} oracle → **{'EXACT' if ok else 'MISMATCH'}**")
    for inf in RU.get("infos", []): P(f"\nreuse process audit: `{json.dumps(inf.get('audit'))}`")
    P(f"\nnetwork-guard blocked connection attempts: {len(RU.get('netguard_blocked', []))}; student weight hashes across restarts: {sorted(set(RU.get('student_hashes', [])))}")
    op = a.out or os.path.join(ROOT, "results", "examples", f"{sid}_{arm}.md"); os.makedirs(os.path.dirname(op), exist_ok=True); open(op, "w").write("\n".join(out)); print(op, len(out), "lines")


if __name__ == "__main__":
    main()
