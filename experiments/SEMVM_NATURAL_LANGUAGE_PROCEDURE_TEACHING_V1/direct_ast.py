"""DIRECT_AST_DIAGNOSTIC (spec §38, §54) — descriptive only, NEVER activated. The same frozen 1.5B model writes the final procedure directly
from the full natural-language teaching text (all demonstrations, with their :teach / :example headers); the proposal is parsed, statically
validated against the library the NL_TEACH run ended with, and verified by the frozen parent verifier against the evidence of the traces the
NL_TEACH run recorded for that procedure. Compared with TRACE_MEDIATED_PROCEDURE_EXACT (= LEARNED_PROCEDURE_EXACT of NL_TEACH).
python direct_ast.py --suite dev|locked_test [--port 8766]"""
import os, sys, json, glob, argparse, copy, urllib.request
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "nlteach"), os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import lang as L, validate as VD, abstraction as AB, verify as VF, procstore as PS

FEWSHOT = """# Write the reusable procedure that the teaching session describes. Values that differ between examples, or that are given in the
# header, become {parameters}; everything else stays constant. Use the Semantic VM step language and end with END.

TEACHING
:teach count_messages_to(person=Kevin)
Look up the messages to Kevin.
Count them and hand back the number.
PROCEDURE count_messages_to(person:PERSON)
$v0 = FIND MESSAGE WHERE SELF.RECIPIENT={person}
$v1 = COUNT $v0
RETURN $v1
END

TEACHING
:example set_last_note_topic
Take my newest note and change its topic to lease, then return it.
:example set_last_note_topic
Grab my latest note, set its topic to survey and give it back.
PROCEDURE set_last_note_topic(topic:TOPIC)
$v0 = FIND_LAST NOTE
UPDATE $v0 TOPIC={topic}
RETURN $v0
END

TEACHING
:teach close_open_notes_in(place=Oslo)
Bring up the notes in Oslo that are still open.
Mark every one of them as done.
Give me back the notes.
PROCEDURE close_open_notes_in(place:PLACE)
$v0 = FIND NOTE WHERE SELF.WHERE={place} STATUS=OPEN
FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED
RETURN $v0
END

"""


def post(port, path, obj):
    return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"}), timeout=600).read())


def teaching_text(sc, name):
    out = []; cur = None
    for t in sc["turns"]:
        if t["kind"] == "CMD" and t["text"].split()[0] in (":teach", ":example", ":revise"):
            cur = t["text"].split()[1].split("(")[0]
            if cur == name: out.append(t["text"])
        elif t["kind"] == "NL" and cur == name and t["gold"]["status"] != "UNSUPPORTED" and t.get("designed") not in ("failing",): out.append(t["text"])
        elif t["kind"] == "CMD" and t["text"].split()[0] in (":endteach", ":endexample", ":endrevise"): cur = None if cur != name else cur
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suite", required=True); ap.add_argument("--port", default="8766"); a = ap.parse_args()
    S = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "scenarios", a.suite, "*.json")))]; rows = []
    E = json.load(open(os.path.join(ROOT, "results", a.suite, "EVAL_NL_TEACH.json")))
    for sc in S:
        sid = sc["scenario_id"]; work = os.path.join(ROOT, "results", a.suite, "work", "NL_TEACH", sid); tr = E["traces"][sid]
        exs = json.load(open(os.path.join(work, "learn", "examples.json"))) if os.path.exists(os.path.join(work, "learn", "examples.json")) else {}
        lib = PS.Library(os.path.join(work, "procedures.sqlite"))
        for i, t in enumerate(sc["turns"]):
            if not (t["kind"] == "CMD" and t["text"].split()[0] in (":endteach", ":learn") and t.get("expect") == "VERIFIED"): continue
            name = t["name"]; gold = next(x["gold"] for x in sc["turns"] if x["kind"] == "CMD" and x["text"].startswith(":accept ") and x.get("name") == name)
            gh = L.program_hash(L.parse_procedure(gold)); text = teaching_text(sc, name); prompt = FEWSHOT + "TEACHING\n" + text + f"\nPROCEDURE {name}("
            gen = post(a.port, "/generate_stop", {"prompt": prompt, "max_new_tokens": 220, "stop": ["\nEND"]})["text"]; ptxt = f"PROCEDURE {name}(" + gen + "\nEND"
            row = {"scenario": sid, "name": name, "family": t.get("family"), "teaching_text": text, "proposal": ptxt}
            g = tr[str(i)]; ch = (g.get("discovery") or {}).get("paths", {}).get("deterministic", {}); row["trace_mediated_exact"] = g.get("status") == "VERIFIED" and ch.get("program_hash") == gh
            try:
                cand = L.parse_procedure(ptxt); cand["name"] = name; row["parsed"] = True; row["direct_exact"] = L.program_hash(cand) == gh
                try: VD.validate(cand, lib); row["static_valid"] = True
                except Exception as e: row["static_valid"] = False; row["static_error"] = str(e)[:200]
                trs = exs.get(name) or []
                if row["static_valid"] and trs:
                    try: det, ev = AB.abstract(name, trs, lib); st, tests, _ = VF.verify(cand, ev, trs, lib); row["verified"] = st == "VERIFIED"; row["verify_status"] = st
                    except AB.AbstractionError as e: row["verified"] = False; row["verify_status"] = "NO_EVIDENCE: " + e.reason
                else: row["verified"] = False
            except L.LangError as e: row.update(parsed=False, direct_exact=False, static_valid=False, verified=False, parse_error=e.reason)
            rows.append(row)
        lib.close()
    m = lambda k: round(sum(1 for r in rows if r.get(k)) / len(rows), 4) if rows else None
    R = {"n": len(rows), "DIRECT_AST_PARSED": m("parsed"), "DIRECT_AST_STATIC_VALID": m("static_valid"), "DIRECT_AST_VERIFIED": m("verified"), "DIRECT_AST_EXACT": m("direct_exact"),
         "TRACE_MEDIATED_PROCEDURE_EXACT": m("trace_mediated_exact"), "direct_verified_but_not_exact": sum(1 for r in rows if r.get("verified") and not r.get("direct_exact")),
         "direct_exact_where_trace_failed": sum(1 for r in rows if r.get("direct_exact") and not r.get("trace_mediated_exact")), "note": "descriptive diagnostic; nothing activated", "rows": rows}
    json.dump(R, open(os.path.join(ROOT, "results", a.suite, "DIRECT_AST_DIAGNOSTIC.json"), "w"), indent=1); print(json.dumps({k: v for k, v in R.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
