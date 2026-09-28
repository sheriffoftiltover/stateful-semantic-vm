"""DIRECT_TEACHER_AST diagnostic (spec §31, §64) — descriptive only, NEVER activated. The frozen teacher writes the final procedure directly
(SEMVM_STEP_V1 text) from the goal + signature + capability card + the student's saved skills; the proposal is parsed, statically validated
against the library of the TEACHER-mode run, and verified by the frozen verifier against the evidence recorded in that run (archived examples).
Compared with TRACE_MEDIATED_TEACHER_PROCEDURE_EXACT. python direct_teacher_ast.py --suite dev --run-dir results/dev"""
import os, sys, json, glob, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, d) for d in ("student", "procedure", "core", "teacher")]
import lang as L, validate as VD, abstraction as AB, verify as VF, procstore as PS, client as CL, protocol as PR

LANGDOC = """Write the skill as a program in the student's step language. Output ONLY the program, starting with PROCEDURE and ending with END.
PROCEDURE <name>(<input>:<TYPE>, ...)        TYPE is PERSON, TIME, PLACE or TOPIC
$v = FIND <TYPE> [WHERE <SCOPE>.<REL>=<X> ...] [STATUS=<OPEN|CLOSED>]     TYPE: REMINDER PLAN REQUEST NOTE CALL EMAIL VISIT MESSAGE;
                                                                        SCOPE: SELF | PARENT (the scheduling event) | CHILD; REL: WHO WHEN WHERE RECIPIENT TOPIC
$v = FIND_LAST <TYPE>        $v = FIRST $list        $v = COUNT $list        $v = CHILD $x        $v = PARENT $x        $v = GET $x <REL>
$v = SELECT $list <REL>      $v = SORT $list <REL>   $v = GROUP $list <REL>  $v = REPORT $groups <REL>                $v = FILTER $list <REL>=<X> | STATUS=<X>
UPDATE $x <REL>=<X>          SET_STATUS $x <OPEN|CLOSED>                    DELETE $x                                RETRACT $x <REL>
FOR $e IN $list : <one step>                                                $v = CALL <saved skill> <input>=<X> ...  RETURN $x
<X> is an input written {input}, a variable $v, or a literal value. The time of a call / email / visit / message is WHEN on its PARENT event.
Example:
PROCEDURE open_messages_to(person:PERSON)
$v0 = FIND MESSAGE WHERE SELF.RECIPIENT={person} STATUS=OPEN
RETURN $v0
END"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True); ap.add_argument("--run-dir", required=True); ap.add_argument("--reasoning", default="medium"); a = ap.parse_args()
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json"))):
        sc = json.load(open(p)); sid = sc["scenario_id"]; wd = os.path.join(a.run_dir, "work", "TEACHER", sid); arch = os.path.join(a.run_dir, "acq_artifacts", "TEACHER", sid)
        if not os.path.exists(os.path.join(wd, "procedures.sqlite")): continue
        lib = PS.Library(os.path.join(wd, "procedures.sqlite")); ex = json.load(open(os.path.join(arch, "examples.json"))) if os.path.exists(os.path.join(arch, "examples.json")) else {}
        for i, it in enumerate(sc["curriculum"]):
            prior = sc["curriculum"][:i]
            skills = "\n".join(f"- {c['name']}(" + ", ".join(f"{k}:{t}" for k, t in c["sig"].items()) + f"): {c['goal']}" for c in prior) or "(none)"
            msg = [{"role": "system", "content": PR.system_prompt() + "\n\n" + LANGDOC},
                   {"role": "user", "content": f"SKILL: {it['name']}(" + ", ".join(f"{k}:{t}" for k, t in it["sig"].items()) + f")\nWHAT IT DOES: {it['goal']}\nSAVED SKILLS:\n{skills}\nWrite the PROCEDURE now."}]
            try: r = CL.chat(msg, gen={"reasoning_effort": a.reasoning}, meta={"kind": "DIRECT_AST"}); txt = r["text"]
            except (CL.ProviderFailure, CL.BudgetStop) as e: rows.append({"scenario": sid, "name": it["name"], "error": str(e)}); continue
            import re
            m = re.search(r"PROCEDURE.*?\nEND", txt, re.S); row = {"scenario": sid, "name": it["name"], "family": it["family"], "proposal": txt}
            gh = L.program_hash(L.parse_procedure(it["gold"]))
            try:
                c = L.parse_procedure(m.group(0) if m else txt); c["name"] = it["name"]; row.update(parsed=True, direct_exact=L.program_hash(c) == gh)
                try: VD.validate(c, lib); row["static_valid"] = True
                except Exception as e: row.update(static_valid=False, static_error=str(e)[:200])
                trs = ex.get(it["name"]) or []
                if row["static_valid"] and trs:
                    for t in trs:
                        if t.get("snapshot") and not os.path.exists(t["snapshot"]): t["snapshot"] = os.path.join(arch, "snapshots", os.path.basename(t["snapshot"]))
                    try: det, ev = AB.abstract(it["name"], trs, lib); st, tests, _ = VF.verify(c, ev, trs, lib); row.update(verified=st == "VERIFIED", verify_status=st)
                    except AB.AbstractionError as e: row.update(verified=False, verify_status="NO_EVIDENCE: " + e.reason)
                else: row["verified"] = False
            except L.LangError as e: row.update(parsed=False, direct_exact=False, static_valid=False, verified=False, parse_error=e.reason)
            act = lib.active(it["name"]); row["trace_mediated_exact"] = act is not None and L.program_hash(act) == gh; rows.append(row)
        lib.close()
    ok = [r for r in rows if "error" not in r]; m = lambda k: round(sum(1 for r in ok if r.get(k)) / len(ok), 4) if ok else None
    R = {"n": len(ok), "DIRECT_TEACHER_AST_PARSED": m("parsed"), "DIRECT_TEACHER_AST_STATIC_VALID": m("static_valid"), "DIRECT_TEACHER_AST_VERIFIED": m("verified"),
         "DIRECT_TEACHER_AST_EXACT": m("direct_exact"), "TRACE_MEDIATED_TEACHER_PROCEDURE_EXACT": m("trace_mediated_exact"),
         "direct_exact_where_trace_failed": sum(1 for r in ok if r.get("direct_exact") and not r.get("trace_mediated_exact")),
         "trace_exact_where_direct_failed": sum(1 for r in ok if r.get("trace_mediated_exact") and not r.get("direct_exact")), "note": "descriptive; nothing activated", "rows": rows}
    json.dump(R, open(os.path.join(a.run_dir, "DIRECT_TEACHER_AST_DIAGNOSTIC.json"), "w"), indent=1); print(json.dumps({k: v for k, v in R.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
