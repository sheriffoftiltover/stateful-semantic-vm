"""HTG hosted grounder (spec §9-§14, §46-§47, §61; spec/HOSTED_GROUNDER_PROTOCOL.json). The SAME frozen gpt-oss-120b checkpoint as the hosted
teacher, used as a SEPARATE agent: its own system prompt (the grounder card below), its own request per instruction (no dialogue history, no
teacher context), its own response cache (grounder_responses/). It sees exactly: one instruction, the currently defined results with their static
types, the primitive inventory, ACTIVE procedure signatures. It emits a typed JSON envelope (PLAN / CLARIFY / UNSUPPORTED); it cannot execute.

Authority: the envelope is only a CANDIDATE. Every PLAN goes through (1) the local grammar's legality constraints (grammar_errors: the exact
option constraints of frontend.Grounder.options, restated as checks: named event types, ontology-legal relation/scope pairs, values that occur in
the instruction, status only when cued, type-compatible references, callable ACTIVE procedures) and (2) the unchanged NL_TEACH / PDX deterministic
checks (validate_actions, antecedent / output obligations, reference grammar R0-R4, value / procedure coverage, whole-plan liveness, RETURN last,
clause coverage). A plan failing any check is NOT executed (status CLARIFY, clarify_kind PLAN_INVALID). There is no score margin (a hosted plan
has no calibrated alternative-outcome scores); this is registered, not a relaxation of any check that applies to both grounders."""
import os, sys, re, json, copy, time, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, "teacher")]
import frontend as F, lang as L, mr_config as K
import client as CL

SCHEMA_VERSION = "TTP_GROUNDER_ENVELOPE_V1 (HTG envelope + structured legality feedback, one retry)"
MAX_PLAN_ACTIONS = 8
RETRIES = 1                                                                                         # spec §35: one retry after a structured rejection, same slot
GEN = {"reasoning_effort": os.environ.get("HTG_GROUNDER_REASONING", "low"), "max_tokens": 4096}     # frozen by the grounder preflight (results/PREFLIGHT.json)

CARD = '''You are the GROUNDER of a small Semantic VM. You translate ONE natural-language teaching instruction into a typed candidate plan of VM
actions. You never execute anything; a deterministic checker validates your plan before anything runs.

WORLD
- Event types: REMINDER PLAN REQUEST NOTE (outer events) and CALL EMAIL VISIT MESSAGE (inner events; an inner event is the TODO item of an outer event).
- Relations: WHO (the person an event is with, or who made it), RECIPIENT (the person something is addressed / sent to), WHEN (time),
  WHERE (place), TOPIC (what it is about). Status: OPEN or CLOSED.
- The time of an inner event (CALL EMAIL VISIT MESSAGE) is stored on its outer event: write "PARENT.WHEN".

ACTIONS (JSON objects; an action that produces a result has "bind": "rN" with the next free result number)
- FIND {"type", optional "where": {REL or PARENT.REL or CHILD.REL: value}, optional "status"}: all events of a type that match
- FIND_LAST {"type"}: the most recent event of a type
- FIRST {"of"} / COUNT {"of"}: first element / number of elements of a list
- CHILD {"of"}: the TODO item of an event;  PARENT {"of"}: the event whose TODO item it is
- GET {"of", "rel"}: a relation value of one event;  SELECT {"of", "rel"}: that value for every event of a list
- GROUP {"of", "by"}; SORT {"of", "by"}; REPORT {"of" (groups), "rel"}; FILTER {"of", "where": {REL: value}} or {"of", "status"}
- UPDATE {"target" or "each", "rel", "value"}; SET_STATUS {"target" or "each", "value"}; DELETE {"target" or "each"}
- CALL {"procedure", "args": {name: value or rN}} (only the listed available procedures); RETURN {"value": rN}
"each" applies the action to every event of a list result.

RULES (literal semantic fidelity)
- Write exactly the actions the instruction asks for, in order. Do not add operations, filters, status conditions, orderings or constants that
  the instruction does not state. Add "status" only when the instruction explicitly says open / closed (or an equivalent).
- Choose relations by their meaning: something addressed or sent TO a person is RECIPIENT; an event WITH a person or BY / FROM a person is WHO;
  AT / IN a place is WHERE; ABOUT / ON a subject is TOPIC; a time is WHEN (PARENT.WHEN for inner events).
- Use only values that occur in the instruction. Refer to earlier results only by their names (r1, r2, ...) from the Results list.
- Never guess what a pronoun or "the result" refers to: if it could mean more than one earlier result, or no suitable result exists, answer CLARIFY.
- Never reconstruct a missing earlier step; if a required result was not computed, answer CLARIFY.
- If the VM has no action for what is asked (for example sending, texting, printing, anything outside the world above), answer UNSUPPORTED.
- RETURN is terminal: emit RETURN only when the instruction itself explicitly asks to return / give back / hand over / tell the result.
  Never add a RETURN because the work seems finished.
- Saved procedures: when the instruction names an available procedure, emit CALL with that procedure and its arguments (values from the
  instruction or earlier results); do not rebuild its steps. Never CALL a procedure the instruction does not name. If an argument the
  procedure needs is not given, answer CLARIFY.
- If the checker rejects your plan it tells you why (for example where a relation is legally stored); then re-ground the SAME instruction.

OUTPUT: exactly one JSON object and nothing else:
  {"status": "PLAN", "steps": [ {"bind": "r1", "op": "FIND", "type": "...", ...}, {"op": "RETURN", "value": "r1"} ]}
  {"status": "CLARIFY", "question": "..."}
  {"status": "UNSUPPORTED", "reason": "..."}
'''


def _fewshot():
    """the frozen local-frontend few-shot bank (MESSAGE / NOTE / PLAN and non-catalogue names only), re-serialized into the envelope"""
    out = []
    for procs, results, utt, acts in F.FEWSHOT:
        A = F.parse_actions("\n".join(acts))
        if A and A[0]["op"] in ("UNSUPPORTED", "CLARIFY"):
            env = {"status": A[0]["op"]} | ({"question": "Which earlier result is meant?"} if A[0]["op"] == "CLARIFY" else {"reason": "No VM action does this."})
        else:
            env = {"status": "PLAN", "steps": [dict({"bind": a["bind"]} if a.get("bind") else {}, **{k: v for k, v in a.items() if k != "bind"}) for a in A]}
        out.append((F.block(procs, results, utt), json.dumps(env)))
    return out


FEW = _fewshot()
CARD_SHA = hashlib.sha256((CARD + json.dumps(FEW)).encode()).hexdigest()


def messages(utt, ctx):
    m = [{"role": "system", "content": CARD}]
    for u, a in FEW: m += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    m.append({"role": "user", "content": F.block(ctx["procs_line"], [r.line() for r in ctx["results"]], utt)})
    return m


def parse_envelope(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i: raise F.SchemaError("no JSON object")
    try: env = json.loads(t[i:j + 1])
    except json.JSONDecodeError: raise F.SchemaError("bad JSON")
    st = str(env.get("status", "")).upper()
    if st not in ("PLAN", "CLARIFY", "UNSUPPORTED"): raise F.SchemaError(f"bad status {env.get('status')!r}")
    if st != "PLAN": return st, [], env
    steps = env.get("steps")
    if not isinstance(steps, list) or not steps: raise F.SchemaError("PLAN without steps")
    acts = []
    for s in steps:
        if not isinstance(s, dict) or "op" not in s: raise F.SchemaError("step without op")
        a = {k: v for k, v in s.items() if k in F.KEY_ORDER + ["bind"]}
        if isinstance(s.get("args"), dict) and str(s["op"]).upper() != "CALL":           # tolerate {"op", "args": {...}} nesting (spec §13 example)
            a.update({k.lower() if k.lower() in F.KEY_ORDER else k: v for k, v in s["args"].items()}); a.pop("args", None)
        a["op"] = str(a["op"]).upper()
        if a["op"] not in F.OPS: raise F.SchemaError(f"unknown op {a['op']}")
        acts.append(a)
    return st, acts, env


def renumber(acts, ctx):
    """mechanical: result names follow the next free numbers (binds are names, not semantics); a reference to a name bound EARLIER IN THE PLAN
    is remapped to that action's new name, any other reference is kept (it must then name an existing result)"""
    n = len(ctx["results"]); mp = {}
    for a in acts:
        rm = lambda v: mp.get(v, v) if isinstance(v, str) else v
        for k in ("of", "target", "each"):
            if k in a: a[k] = rm(a[k])
        if a["op"] == "RETURN" and "value" in a: a["value"] = rm(a["value"])
        if isinstance(a.get("args"), dict): a["args"] = {k: rm(v) for k, v in a["args"].items()}
        if a["op"] in F.PRODUCES:
            n += 1; old = a.get("bind"); a["bind"] = f"r{n}"
            if old: mp[old] = a["bind"]
        else: a.pop("bind", None)
    return acts


STRUCT = []
# required fields per op (the local grammar can never omit them; a hosted plan can) -- TTP amendment 002
REQUIRED = {"FIND": ["type"], "FIND_LAST": ["type"], "FIRST": ["of"], "COUNT": ["of"], "CHILD": ["of"], "PARENT": ["of"], "GET": ["of", "rel"], "SELECT": ["of", "rel"],
            "GROUP": ["of", "by|rel"], "SORT": ["of", "by|rel"], "REPORT": ["of", "rel"], "FILTER": ["of", "where|status"], "UPDATE": ["target|each", "rel", "value"],
            "SET_STATUS": ["target|each", "value"], "DELETE": ["target|each"], "RETRACT": ["target|each", "rel"], "CALL": ["procedure"], "RETURN": ["value"]}


def grammar_errors(acts, ctx, utt):
    """the local grammar's option constraints (frontend.Grounder.options) as checks on a complete plan (structured legality facts -> STRUCT)"""
    G = F.Grounder.__new__(F.Grounder); vals = ctx["values"]; res = list(ctx["results"]); errs = []
    named = [t for t in L.EVENT_TYPES if ("EVENT", t) in ctx["nouns"]]; procs = {p["name"]: p for p in ctx["procs"]}
    if len(acts) > MAX_PLAN_ACTIONS: errs.append(f"plan longer than {MAX_PLAN_ACTIONS} actions")
    for a in acts:
        op = a["op"]; allowed = set(F.KEY_ORDER + ["bind"])
        miss = [f for f in REQUIRED.get(op, []) if not (any(a.get(x) not in (None, "", {}) for x in f.split("|")))]
        if miss: errs.append(f"{op}: missing required field(s) {miss}"); STRUCT.append({"error": "SCHEMA", "detail": f"{op} requires {miss}"}); continue
        if set(a) - allowed: errs.append(f"{op}: unknown fields {sorted(set(a) - allowed)}")
        ref = G._ref_result(a, res)
        for k in F.ref_keys(a):
            if k.startswith("args."): continue
            need = F.NEEDS["RETURN"] if op == "RETURN" else F.NEEDS[k] if k in ("target", "each") else F.NEEDS.get(op)
            if not any(r.name == a[k] for r in F.compatible(res, need)): errs.append(f"{op}.{k}={a[k]!r} is not a type-compatible earlier result")
        if op in ("UPDATE", "SET_STATUS", "DELETE", "RETRACT") and ("target" in a) == ("each" in a): errs.append(f"{op}: exactly one of target / each")
        if op in ("FIND", "FIND_LAST"):
            if a.get("type") not in named: errs.append(f"{op}: event type {a.get('type')!r} is not named in the instruction")
            if op == "FIND_LAST" and (a.get("where") or a.get("status")): errs.append("FIND_LAST takes only a type")
        if op in ("FIND", "FILTER"):
            T = a.get("type") if op == "FIND" else (ref.etype if ref else None); have = {}
            w = a.get("where") or {}
            if not isinstance(w, dict): errs.append(f"{op}: where must be an object"); w = {}
            if op == "FILTER" and len(w) + (1 if a.get("status") else 0) != 1: errs.append("FILTER takes exactly one condition")
            for k, v in w.items():
                if (k, v) not in G._where_options(T, vals, have):
                    rel = k.split(".")[-1]; alt = [f"{sc}.{rel}" for sc in ("PARENT", "CHILD") if (f"{sc}.{rel}", v) in G._where_options(T, vals, have)]
                    if "." not in k and alt: STRUCT.append({"error": "ILLEGAL_RELATION_LOCATION", "object_type": T, "relation": rel, "legal_path": alt[0]})
                    errs.append(f"{op}: condition {k}={v!r} is not legal here (value not in the instruction, or relation/scope illegal for {T})")
                have[k] = v
            if a.get("status") is not None:
                if not ctx["status_cue"]: errs.append(f"{op}: status {a['status']!r} without an open / closed cue in the instruction")
                elif a["status"] not in L.STATUSES: errs.append(f"{op}: bad status {a['status']!r}")
        if op in ("GET", "RETRACT") and (a.get("rel") not in L.RELS or (ref and ref.etype and not K.valid(a["rel"], ref.etype))): errs.append(f"{op}: relation {a.get('rel')!r} illegal")
        if op == "SELECT" and a.get("rel") not in L.RELS: errs.append("SELECT: bad relation")
        if op in ("GROUP", "SORT") and (a.get("by") or a.get("rel")) not in L.RELS: errs.append(f"{op}: bad 'by' relation")
        if op == "REPORT" and a.get("rel") not in L.RELS: errs.append("REPORT: bad relation")
        if op == "UPDATE":
            c = next((c for c in F.VALUE_CLASSES if a.get("value") in vals[c]), None)
            if c is None or a.get("rel") not in F.REL_OF_CLASS[c] or (ref and ref.etype and not K.valid(a["rel"], ref.etype)): errs.append(f"UPDATE {a.get('rel')}={a.get('value')!r} illegal")
        if op == "SET_STATUS" and a.get("value") not in ctx.get("set_status_cues", []): errs.append(f"SET_STATUS {a.get('value')!r} not cued by the instruction")
        if op == "CALL":
            p = procs.get(a.get("procedure"))
            if p is None: errs.append(f"CALL: {a.get('procedure')!r} is not an ACTIVE procedure")
            else:
                args = a.get("args") or {}
                for x in p["parameters"]:
                    v = args.get(x["name"])
                    if not (v in vals.get(x["type"], []) or any(r.name == v and r.kind == x["type"] for r in res)):
                        errs.append(f"CALL {p['name']}: argument {x['name']}={v!r} illegal"); STRUCT.append({"error": "CALL_ARGUMENT", "procedure": p["name"], "parameter": x["name"], "type": x["type"]})
        if op == "RETURN" and not any(r.name == a.get("value") for r in res): errs.append("RETURN of an unknown result")
        if a.get("bind"): res.append(F.result_of_action(a, res, ctx))
    return errs


class HostedGrounder:
    """drop-in replacement for frontend.Grounder at the ground_instruction level"""
    kind = "HOSTED"
    margin = None

    def __init__(self, gen=None): self.gen = dict(GEN, **(gen or {}))

    def ground_instruction(self, utt, ctx):
        t0 = time.time(); vals = F.mentioned_values(utt)
        ctx = dict(ctx, values=vals, nouns=F.nouns_in(utt), status_cue=F.status_cue(utt), named_procs=F.named_procs(utt, ctx["procs"]), set_status_cues=F.set_status_cues(utt))
        msgs = messages(utt, ctx); P = {"instruction": utt, "values": vals, "grounder": "HOSTED", "llm_calls": 0, "hosted_calls": 0, "attempts": []}
        def done(d): P["seconds"] = round(time.time() - t0, 2); d["provenance"] = P; return d
        for attempt in range(1 + RETRIES):
            r = CL.chat(msgs, gen=self.gen, role="grounder", meta={"kind": "GROUND" if attempt == 0 else "GROUND_RETRY", "schema": SCHEMA_VERSION, "card_sha256": CARD_SHA})
            P["llm_calls"] += 1; P["hosted_calls"] += 1
            P.update(raw_text=r["text"][:2000], request_hash=r["provenance"].get("request_hash"), cached=r["cached"], input_tokens=r["provenance"].get("input_tokens"), output_tokens=r["provenance"].get("output_tokens"))
            out, feedback = self._check(r["text"], ctx, utt, P)
            P["attempts"].append({"status": out["status"], "reason": out.get("reason"), "feedback": feedback, "request_hash": P["request_hash"]})
            if out["status"] == "OK" or not feedback or attempt == RETRIES: P["retried"] = attempt > 0; return done(out)
            msgs = msgs + [{"role": "assistant", "content": r["text"]},
                           {"role": "user", "content": "The checker rejected this plan: " + json.dumps(feedback) + "\nRe-ground the SAME instruction. Reply with one JSON object only."}]

    def _check(self, text, ctx, utt, P):
        """-> (outcome dict, structured feedback list or None). Feedback is schema/legality facts only (spec §26): never gold content."""
        try: st, acts, env = parse_envelope(text)
        except F.SchemaError as e:
            P["schema_error"] = str(e)
            return {"status": "CLARIFY", "reason": f"grounder output not in the schema ({e})", "clarify_kind": "SCHEMA"}, [{"error": "SCHEMA", "detail": str(e)[:120], "rule": "reply with exactly one valid JSON object in the envelope format"}]
        P["envelope_status"] = st
        if st == "UNSUPPORTED": return {"status": "UNSUPPORTED", "reason": "grounder: " + str(env.get("reason", ""))[:300]}, None
        if st == "CLARIFY":
            P["question"] = str(env.get("question", ""))[:300]; return {"status": "CLARIFY", "reason": "grounder asks: " + P["question"], "clarify_kind": "GROUNDER"}, None
        acts = renumber(acts, ctx); P["raw_actions"] = copy.deepcopy(acts); del STRUCT[:]
        errs = grammar_errors(acts, ctx, utt) + F.validate_actions(acts, ctx, utt); fb = list(STRUCT)
        if F.unrequested_return(acts, utt): errs.append("UNREQUESTED_RETURN"); fb.append({"error": "UNREQUESTED_RETURN", "rule": "RETURN is allowed only when the instruction asks to return / give back the result"})
        un = F.unnamed_call(acts, utt, ctx["procs"])
        if un: errs.append(f"UNNAMED_CALL {un}"); fb.append({"error": "UNNAMED_CALL", "procedures": un, "rule": "CALL only procedures the instruction names"})
        if not errs and F.antecedent_missing(acts, ctx, utt): errs.append("antecedent: an anaphor without a referenced earlier result")
        if errs:
            P["plan_errors"] = errs[:8]; kind = "MISSING_ARGUMENT" if any(f["error"] == "CALL_ARGUMENT" for f in fb) else "PLAN_INVALID"
            if any(f["error"] == "ILLEGAL_RELATION_LOCATION" for f in fb): kind = "RELATION_LOCATION_ERROR"
            if any(f["error"] == "UNREQUESTED_RETURN" for f in fb): kind = "UNREQUESTED_RETURN"
            return {"status": "CLARIFY", "reason": "hosted plan rejected: " + "; ".join(errs[:3]), "clarify_kind": kind, "structured": fb}, [f for f in fb if f["error"] != "CALL_ARGUMENT"] or None
        acts, notes, why = F.reference_check(acts, ctx, utt); P["reference_notes"] = [n for n in notes if not isinstance(n, dict)]
        if why:
            info = next((n for n in notes if isinstance(n, dict)), None)
            return {"status": "CLARIFY", "reason": why, "clarify_kind": "REFERENCE" if info else "RESULT_NOT_COMPUTED", "clarify_info": info}, None
        strong, _ = F.segments(utt); ok, why = F.plan_ok(acts, utt, len(strong), ctx)
        if not ok: P["plan_errors"] = [why]; return {"status": "CLARIFY", "reason": f"whole-plan validation: {why}", "clarify_kind": "PLAN"}, None
        P["repaired"] = any("->" in n for n in P["reference_notes"])
        return {"status": "OK", "actions": acts}, None
