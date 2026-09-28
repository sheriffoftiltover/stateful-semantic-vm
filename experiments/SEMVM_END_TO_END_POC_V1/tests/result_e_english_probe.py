"""RESULT-E: English interface gap (Amendment 001; descriptive only). Ordinary-English paraphrases of SUPPORTED semantics are fed to the frozen binder
WITHOUT preprocessing (the envelope is deliberately bypassed; OOV tokens map to <unk> exactly as the binder's tokenizer does), using the inventory of
the gold modifier count (the most favourable choice). Also records what the registered pipeline does with them (UNSUPPORTED_INPUT)."""
import os, sys, json
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import pipeline as PL, binder as BN, ir as IR, envelope as EV
CASES = [  # (english, outer, inner, [(rel, value, attach)])
    ("Remind me to call Alice", "REMINDER", "CALL", [("WHO", "Alice", "inner")]),
    ("Remind me at 5 to call", "REMINDER", "CALL", [("WHEN", "5", "outer")]),
    ("Remind me to email Bob about the budget", "REMINDER", "EMAIL", [("RECIPIENT", "Bob", "inner"), ("TOPIC", "budget", "inner")]),
    ("Remind me at noon to call Alice", "REMINDER", "CALL", [("WHEN", "noon", "outer"), ("WHO", "Alice", "inner")]),
    ("Request that Dave calls at 3", "REQUEST", "CALL", [("WHO", "Dave", "inner"), ("WHEN", "3", "inner")]),
    ("Make a note in Paris to message Carol", "NOTE", "MESSAGE", [("WHERE", "Paris", "outer"), ("RECIPIENT", "Carol", "inner")]),
    ("Plan at dawn to visit", "PLAN", "VISIT", [("WHEN", "dawn", "outer")]),
    ("Remind me tomorrow to call Alice and email Bob on Friday", "REMINDER", "CALL", [("WHO", "Alice", "inner")]),
]
VC = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}


def gold_ir(O, I, mods):
    occs = [(O, None, 0), (I, None, 1)] + [(VC[r], v, 2 + k) for k, (r, v, _) in enumerate(mods)]
    return IR.from_graph(occs, [("TODO", occs[0], occs[1])] + [(r, occs[0] if a == "outer" else occs[1], occs[2 + k]) for k, (r, v, a) in enumerate(mods)])


def main():
    b = BN.Binder(); sess = PL.Session(":memory:", "FULL", binder=b); rows = []
    for text, O, I, mods in CASES:
        toks = text.split(); g = gold_ir(O, I, mods); oov = [t for t in toks if t not in b.vocab]; ok, env = EV.check(toks)
        p = b.parse(toks, max(1, min(2, len(mods)))); graph = PL.graph_to_json(p["graph"])
        try: ir_ = IR.from_graph(*PL.graph_from_json(graph)); IR.validate(ir_); ir_ok = True
        except IR.IRError as e: ir_, ir_ok = None, e.reason
        pipe = sess.process(f"E{len(rows)}", {"kind": "ASSERT", "text": text}, "ts")
        rows.append({"english": text, "tokens": len(toks), "oov": oov, "oov_fraction": round(len(oov) / len(toks), 3), "envelope": env, "pipeline_status": pipe["status"],
                     "direct_binder_output_graph": graph, "direct_ir_valid": ir_ok, "direct_ir_exact": ir_ == g, "gold_ir": g})
    b.assert_frozen()
    out = {"note": "descriptive only; outside V1 scope; nothing tuned after viewing", "n": len(rows), "pipeline_UNSUPPORTED_INPUT": sum(r["pipeline_status"] == "UNSUPPORTED_INPUT" for r in rows),
           "direct_ir_valid": sum(r["direct_ir_valid"] is True for r in rows), "direct_ir_exact": sum(r["direct_ir_exact"] for r in rows), "mean_oov_fraction": round(sum(r["oov_fraction"] for r in rows) / len(rows), 3), "cases": rows}
    json.dump(out, open(os.path.join(ROOT, "results", "RESULT_E_ENGLISH_PROBE.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "cases"}, indent=1)); [print(r["english"], "| oov", r["oov"], "| valid", r["direct_ir_valid"], "| exact", r["direct_ir_exact"], "|", r["pipeline_status"]) for r in rows]


if __name__ == "__main__":
    main()
