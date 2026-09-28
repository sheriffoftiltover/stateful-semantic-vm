"""NL_TEACH frontend (spec §9-§19, §33, §36-§37). Natural-language teaching instruction -> typed candidate actions -> deterministic validation.
The frozen LLM is NON-AUTHORITATIVE: it only RANKS legal typed options. Grounding = grammar-constrained beam search over the NL_TEACH action
schema (spec/NL_TEACH_ACTION_SCHEMA.json): at every field the option set is generated deterministically from (a) the frozen primitive
inventory, (b) the frozen ontology legality matrix, (c) vocabulary values that occur in the instruction, (d) type-compatible prior results of
the current demonstration, (e) ACTIVE procedure signatures; the LLM scores the options (log P(option | prompt + text so far)).
After decoding, deterministic checks run (reference grammar R0-R3, coverage, margin); the result is OK (actions), CLARIFY or UNSUPPORTED.
The prompt NEVER contains the procedure being taught, the gold procedure, future demonstrations or parameterization (spec §34).
Few-shot examples use only MESSAGE / NOTE / PLAN and non-catalogue procedure names."""
import os, sys, re, json, copy, time, math
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
for d in ("procedure", "core", "core/neural/vendor"): sys.path.insert(0, os.path.join(ROOT, d))
import lang as L, executor as X, mr_config as K
import nllm
LANG = json.load(open(os.path.join(ROOT, "spec", "NL_TEACH_LANGUAGE_V1.json")))
INNER = ["CALL", "EMAIL", "VISIT", "MESSAGE"]; OUTER = ["REMINDER", "PLAN", "REQUEST", "NOTE"]
VALUE_CLASSES = ["PERSON", "TIME", "PLACE", "TOPIC"]; COVERED = ["PERSON", "TIME", "PLACE"]
REL_OF_CLASS = {"PERSON": ["WHO", "RECIPIENT"], "TIME": ["WHEN"], "PLACE": ["WHERE"], "TOPIC": ["TOPIC"]}
PRODUCES = {"FIND", "FIND_LAST", "FIRST", "COUNT", "CHILD", "PARENT", "GET", "SELECT", "GROUP", "REPORT", "FILTER", "SORT", "CALL"}
OPS = ["FIND", "FIND_LAST", "FIRST", "COUNT", "CHILD", "PARENT", "GET", "SELECT", "GROUP", "REPORT", "FILTER", "SORT", "UPDATE", "SET_STATUS", "DELETE", "RETRACT", "CALL", "RETURN"]
LIST_T = ("EVENT_LIST", "VALUE_LIST"); MAX_ACTIONS = 4; BEAM = 3
MARGIN = 1.0      # nats; registered before DEV (the same value as the parent retrieval margin)

HEAD = '''# Translate a teaching instruction into Semantic VM actions: one JSON action per line, then a blank line. Write exactly the actions the instruction asks for.
# Event types: REMINDER PLAN REQUEST NOTE (outer events) and CALL EMAIL VISIT MESSAGE (inner events; an inner event is the TODO item of an outer event).
# Relations: WHO (the person an event is with, or who made it) RECIPIENT (the person something is addressed to) WHEN (time) WHERE (place) TOPIC. Status: OPEN or CLOSED.
# The time of an inner event is stored on its outer event: write "PARENT.WHEN".
# An action that produces a result is written "rN = {...}" with the next result number. Earlier results are referred to as "rN".
# FIND: all events of a type matching "where" (and "status"); FIND_LAST: the most recent event of a type; FIRST / COUNT of a list; CHILD: the TODO item of an event;
# PARENT: the event whose TODO item it is; GET / SELECT: the value of a relation of one event / of every event of a list; GROUP a list by a relation;
# REPORT: the values of a relation per group; UPDATE: set a relation; SET_STATUS; DELETE; CALL an available procedure; RETURN the final result.
# "each": do it for every event of a list. Add "status" only when the instruction asks for open or closed events.
# If the VM cannot do what is asked, write {"op": "UNSUPPORTED"}. If it is unclear what is meant, write {"op": "CLARIFY"}.
'''
R_ = lambda name, text, desc: f"{name} = {text}   # {desc}"
FEWSHOT = [   # MESSAGE / NOTE / PLAN and non-catalogue combinations only; no DEV / LOCKED template strings (anti-shortcut, spec §34 / §64)
 ("(none)", [], "Show every call about the budget.", ['r1 = {"op": "FIND", "type": "CALL", "where": {"TOPIC": "budget"}}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "VISIT", "where": {"WHERE": "Oslo"}}', "list of 3 VISIT")], "Tally them up.", ['r2 = {"op": "COUNT", "of": "r1"}']),
 ("(none)", [], "Bring up the visits in Oslo that are still open.", ['r1 = {"op": "FIND", "type": "VISIT", "where": {"WHERE": "Oslo"}, "status": "OPEN"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "REQUEST"}', "REQUEST")], "Push it to 4:30, then return it.", ['{"op": "UPDATE", "target": "r1", "rel": "WHEN", "value": "4:30"}', '{"op": "RETURN", "value": "r1"}']),
 ("(none)", [], "List the emails to Kevin about the lease.", ['r1 = {"op": "FIND", "type": "EMAIL", "where": {"RECIPIENT": "Kevin", "TOPIC": "lease"}}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "NOTE", "where": {"TOPIC": "survey"}}', "list of 3 NOTE"), R_("r2", '{"op": "COUNT", "of": "r1"}', "number")], "Now give me the notes themselves.", ['{"op": "RETURN", "value": "r1"}']),
 ("(none)", [], "Grab the newest request.", ['r1 = {"op": "FIND_LAST", "type": "REQUEST"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "REQUEST", "where": {"WHO": "Uma"}}', "list of 2 REQUEST")], "Mark all of them as done.", ['{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}']),
 ("(none)", [], "Fetch the visits planned for dawn and count how many there are.", ['r1 = {"op": "FIND", "type": "VISIT", "where": {"PARENT.WHEN": "dawn"}}', 'r2 = {"op": "COUNT", "of": "r1"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "REMINDER"}', "REMINDER")], "Open the item it is about.", ['r2 = {"op": "CHILD", "of": "r1"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "MESSAGE", "where": {"WHO": "Uma"}}', "list of 2 MESSAGE"), R_("r2", '{"op": "FIND", "type": "NOTE", "where": {"TOPIC": "lease"}}', "list of 1 NOTE")], "Delete them.", ['{"op": "CLARIFY"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "PLAN", "where": {"WHO": "Kevin"}}', "list of 2 PLAN"), R_("r2", '{"op": "COUNT", "of": "r1"}', "number")], "Hand over the total.", ['{"op": "RETURN", "value": "r2"}']),
 ("(none)", [], "Pull up the closed messages from Uma.", ['r1 = {"op": "FIND", "type": "MESSAGE", "where": {"WHO": "Uma"}, "status": "CLOSED"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "CALL", "where": {"TOPIC": "launch"}}', "list of 3 CALL")], "Take the earliest one and tell me what place it has.", ['r2 = {"op": "FIRST", "of": "r1"}', 'r3 = {"op": "GET", "of": "r2", "rel": "WHERE"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "VISIT"}', "VISIT")], "Look up what it belongs to.", ['r2 = {"op": "PARENT", "of": "r1"}']),
 ("(none)", [], "Locate the reminders set for dusk.", ['r1 = {"op": "FIND", "type": "REMINDER", "where": {"WHEN": "dusk"}}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "NOTE"}', "NOTE"), R_("r2", '{"op": "CHILD", "of": "r1"}', "EMAIL")], "Check who that email is addressed to.", ['r3 = {"op": "GET", "of": "r2", "rel": "RECIPIENT"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "NOTE", "where": {"WHO": "Kevin"}}', "list of 2 NOTE")], "Print them on paper.", ['{"op": "UNSUPPORTED"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "MESSAGE"}', "MESSAGE")], "Retarget it at Uma.", ['{"op": "UPDATE", "target": "r1", "rel": "RECIPIENT", "value": "Uma"}']),
 ("(none)", [], "Count the visits in Rome and hand back the number.", ['r1 = {"op": "FIND", "type": "VISIT", "where": {"WHERE": "Rome"}}', 'r2 = {"op": "COUNT", "of": "r1"}', '{"op": "RETURN", "value": "r2"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "PLAN", "where": {"WHERE": "Lima"}}', "list of 2 PLAN")], "Collect who each of those plans is with.", ['r2 = {"op": "SELECT", "of": "r1", "rel": "WHO"}']),
 ("messages_to(person:PERSON) -> EVENT_LIST ; visitor_at(time:TIME) -> PERSON", [], "Figure out with visitor_at who visits at dusk.", ['r1 = {"op": "CALL", "procedure": "visitor_at", "args": {"time": "dusk"}}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "MESSAGE", "where": {"WHO": "Kevin"}}', "list of 2 MESSAGE")], "Delete them all.", ['{"op": "DELETE", "each": "r1"}']),
 ("(none)", [], "Gather all requests and bucket them by who made them.", ['r1 = {"op": "FIND", "type": "REQUEST"}', 'r2 = {"op": "GROUP", "of": "r1", "by": "WHO"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "REQUEST"}', "list of 4 REQUEST"), R_("r2", '{"op": "GROUP", "of": "r1", "by": "WHO"}', "groups")], "Summarize the places for each bucket.", ['r3 = {"op": "REPORT", "of": "r2", "rel": "WHERE"}']),
 ("(none)", [], "Text Kevin on WhatsApp.", ['{"op": "UNSUPPORTED"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "CALL"}', "CALL")], "Change its topic to invoice.", ['{"op": "UPDATE", "target": "r1", "rel": "TOPIC", "value": "invoice"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "NOTE", "where": {"WHERE": "Oslo"}}', "list of 2 NOTE")], "Close each one and then give me back the notes.", ['{"op": "SET_STATUS", "each": "r1", "value": "CLOSED"}', '{"op": "RETURN", "value": "r1"}']),
 ("messages_to(person:PERSON) -> EVENT_LIST ; visitor_at(time:TIME) -> PERSON", [R_("r1", '{"op": "CALL", "procedure": "visitor_at", "args": {"time": "dusk"}}', "person")], "Now run messages_to for that person and return the result.", ['r2 = {"op": "CALL", "procedure": "messages_to", "args": {"person": "r1"}}', '{"op": "RETURN", "value": "r2"}']),
 ("(none)", [R_("r1", '{"op": "FIND_LAST", "type": "PLAN"}', "PLAN"), R_("r2", '{"op": "CHILD", "of": "r1"}', "VISIT")], "Who is that visit with? Return the person.", ['r3 = {"op": "GET", "of": "r2", "rel": "WHO"}', '{"op": "RETURN", "value": "r3"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "EMAIL", "where": {"TOPIC": "trip"}}', "list of 3 EMAIL")], "Keep just the first one.", ['r2 = {"op": "FIRST", "of": "r1"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "VISIT", "where": {"WHERE": "Lima"}, "status": "CLOSED"}', "list of 2 VISIT")], "Reopen every one of them.", ['{"op": "SET_STATUS", "each": "r1", "value": "OPEN"}']),
]


FEWSHOT += [
 ("(none)", [], "Show the calls with Kevin about the budget.", ['r1 = {"op": "FIND", "type": "CALL", "where": {"WHO": "Kevin", "TOPIC": "budget"}}']),
 ("(none)", [], "Count the requests from Uma.", ['r1 = {"op": "FIND", "type": "REQUEST", "where": {"WHO": "Uma"}}', 'r2 = {"op": "COUNT", "of": "r1"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "VISIT", "where": {"PARENT.WHEN": "dawn"}}', "list of 2 VISIT")], "Check which place the first one is in.", ['r2 = {"op": "FIRST", "of": "r1"}', 'r3 = {"op": "GET", "of": "r2", "rel": "WHERE"}']),
 ("(none)", [R_("r1", '{"op": "FIND", "type": "PLAN", "where": {"WHERE": "Rome"}}', "list of 3 PLAN")], "Let me know how many that makes.", ['r2 = {"op": "COUNT", "of": "r1"}', '{"op": "RETURN", "value": "r2"}']),
 ("(none)", [], "Locate the reminders from Uma for dusk.", ['r1 = {"op": "FIND", "type": "REMINDER", "where": {"WHO": "Uma", "WHEN": "dusk"}}']),
]


def block(procs, results, utt):
    return f"Procedures: {procs}\nResults:" + ("\n" + "\n".join(results) if results else " (none)") + f"\nInstruction: {utt}\n"


def prompt_prefix():
    return HEAD + "\n" + "".join(block(p, r, u) + "\n".join(a) + "\n\n" for p, r, u, a in FEWSHOT)


# ---------------------------------------------------------------- instruction analysis (closed-class, registered) ----------------------------
def canon_value(tok, cls):
    t = tok.strip(".,!?;'\"")
    m = re.fullmatch(r"(\d{1,2}):00", t) or re.fullmatch(r"(\d{1,2})o'?clock", t)
    if cls == "TIME" and m: t = m.group(1)
    for v in sorted(X.VOCAB[cls]):
        if v.lower() == t.lower(): return v
    return None


def mentioned_values(utt):
    """vocabulary values occurring in the instruction, per class (order of first occurrence)"""
    toks = re.findall(r"[\w:']+", utt.replace("o'clock", "oclock")); out = {c: [] for c in VALUE_CLASSES}
    for t in toks:
        t2 = t[:-2] if t.endswith("'s") else t
        for c in VALUE_CLASSES:
            v = canon_value(t2, c)
            if v and v not in out[c]: out[c].append(v)
    return out


def _has_phrase(utt, ph):
    return re.search(r"(?<![\w-])" + re.escape(ph) + r"(?![\w-])", utt.lower()) is not None


def nouns_in(utt):
    ks = set()
    for t, ws in LANG["type_nouns"].items():
        if any(_has_phrase(utt, w) for w in ws): ks.add(("EVENT", t))
    for k, ws in LANG["result_nouns"].items():
        if any(_has_phrase(utt, w) for w in ws): ks.add(("KIND", k))
    return ks


def answers_clarification(text, pend):
    """an utterance consumes a pending REFERENCE clarification only if it names exactly one of its legal answers"""
    if not pend or pend.get("kind") != "REFERENCE": return False
    nk = nouns_in(text); names = set(re.findall(r"\br\d+\b", text)); cands = [Result(c["name"], "", c["kind"], c.get("etype")) for c in pend.get("legal_answers") or []]
    hit = [c for c in cands if c.name in names or any(c.matches_noun(k) for k in nk)]
    return len(hit) == 1


def status_cue(utt):
    toks = re.findall(r"[a-z]+", utt.lower()); return any(t.startswith(tuple(LANG["status_cue_roots"])) for t in toks)


def named_procs(utt, procs): return [p["name"] for p in procs if re.search(r"(?<![\w])" + re.escape(p["name"]) + r"(?![\w])", utt)]


def has_singular_pronoun(utt): return any(_has_phrase(utt, w) for w in LANG["pronouns"]["singular"])


# ---------------------------------------------------------------- typed context ----------------------------------------------------------------
class Result:
    """one prior result of the current demonstration: name, JSON action text, kind (EVENT_LIST/EVENT/INT/VALUE_LIST/PERSON/...), event type"""
    def __init__(self, name, action_text, kind, etype=None, n=None):
        self.name, self.text, self.kind, self.etype, self.n = name, action_text, kind, etype, n

    def line(self):
        if self.kind == "EVENT_LIST": d = f"list of {self.n} {self.etype or 'event'}"
        elif self.kind == "EVENT": d = self.etype or "event"
        elif self.kind == "NONE": d = "nothing"
        elif self.kind == "INT": d = "number"
        elif self.kind == "VALUE_LIST": d = f"list of {self.n} values"
        elif self.kind == "PERSON": d = "person"
        elif self.kind == "GROUPS": d = "groups"
        elif self.kind == "REPORT": d = "report"
        else: d = self.kind.lower()
        return f"{self.name} = {self.text}   # {d}"

    def matches_noun(self, nk):
        a, b = nk
        if a == "EVENT": return self.kind in ("EVENT", "EVENT_LIST") and self.etype == b
        if b == "PERSON": return self.kind == "PERSON"
        if b == "VALUE_LIST": return self.kind == "VALUE_LIST"
        return self.kind == b


NEEDS = {"FIRST": LIST_T, "COUNT": LIST_T, "CHILD": ("EVENT", "NONE"), "PARENT": ("EVENT", "NONE"), "GET": ("EVENT", "NONE"), "SELECT": ("EVENT_LIST",), "GROUP": ("EVENT_LIST",),
         "SORT": ("EVENT_LIST",), "FILTER": ("EVENT_LIST",), "REPORT": ("GROUPS",), "target": ("EVENT", "NONE"), "each": ("EVENT_LIST",), "RETURN": None}


FIRST_STAGE = {"FIND": "type", "FIND_LAST": "type", "CALL": "proc"}
FIRST_STAGE.update({op: "ref" for op in OPS if op not in FIRST_STAGE})
AFTER_REF = {"FIRST": "END", "COUNT": "END", "CHILD": "END", "PARENT": "END", "RETURN": "END", "DELETE": "END", "GET": "rel", "SELECT": "rel", "REPORT": "rel", "RETRACT": "rel",
             "GROUP": "by", "SORT": "by", "FILTER": "filter_c", "UPDATE": "relval", "SET_STATUS": "svalue"}


def compatible(results, need):
    return [r for r in results if need is None or r.kind in need]


# ---------------------------------------------------------------- grammar-constrained beam search ----------------------------------------------
class Hyp:
    def __init__(self):
        self.text = ""; self.score = 0.0; self.actions = []; self.cur = None; self.stage = None; self.done = False; self.used = set(); self.produced = []; self.terminal = False

    def clone(self): h = copy.copy(self); h.actions = copy.deepcopy(self.actions); h.cur = copy.deepcopy(self.cur); h.used = set(self.used); h.produced = list(self.produced); return h


def q(s): return json.dumps(s)


class Grounder:
    def __init__(self, beam=BEAM, margin=MARGIN):
        self.beam, self.margin = beam, margin; self.prefix = prompt_prefix()

    # ---- options for the next decision of a hypothesis. Every option text ENDS WITH ITS DELIMITER (',' / '}\n' / '},' / '}}\n') so that
    #      decisions split the line at natural token boundaries; the delimiter encodes what may follow. ----
    def options(self, h, ctx):
        res = ctx["results"] + h.produced; vals = ctx["values"]; procs = ctx["procs"]; out = []
        self._ctx_named = any(k[0] == "EVENT" for k in ctx.get("nouns", set()))
        if h.cur is None:                                        # start of a line
            if h.actions: out.append(("\n", ("END",), None))
            if h.terminal or len(h.actions) >= MAX_ACTIONS or (h.actions and h.actions[-1]["op"] == "RETURN"): return out
            if not h.actions:
                out += [('{"op": "UNSUPPORTED"}\n', ("SPECIAL", "UNSUPPORTED"), None), ('{"op": "CLARIFY"}\n', ("SPECIAL", "CLARIFY"), None)]
            n = len(res) + 1
            for op in OPS:
                if self._op_possible(op, res, vals, procs):
                    out.append(((f"r{n} = " if op in PRODUCES else "") + '{"op": ' + q(op) + ",", ("OP", op), FIRST_STAGE[op]))
            return out
        a = h.cur; op = a["op"]; st = h.stage
        if st == "type":                                         # EVENT_TYPE values: those named in the instruction (registered type nouns), else all
            named = [t for t in L.EVENT_TYPES if ("EVENT", t) in ctx["nouns"]]      # V1.2: an event search must NAME its event type
            for t in named:
                if op == "FIND_LAST": out.append((f' "type": {q(t)}}}\n', ("SET", {"type": t}), "END"))
                else:
                    out.append((f' "type": {q(t)},', ("SET", {"type": t}), "find_opt"))
                    out.append((f' "type": {q(t)}}}\n', ("SET", {"type": t}), "END"))
            return out
        if st in ("find_opt", "where_more", "filter_c"):
            T = a.get("type") or a.get("_ltype"); have = a.get("where", {}); kvs = self._where_options(T, vals, have)
            for k, v in kvs:
                body = (f' "where": {{{q(k)}: {q(v)}' if st != "where_more" else f' {q(k)}: {q(v)}')
                upd = ("WHERE", k, v)
                if st == "filter_c": out.append((body + "}}\n", upd, "END")); continue
                if len(kvs) > 1: out.append((body + ",", upd, "where_more"))
                if ctx["status_cue"]: out.append((body + "},", upd, "status"))
                out.append((body + "}}\n", upd, "END"))
            if st in ("find_opt", "filter_c") and ctx["status_cue"]:
                out += [(f' "status": {q(s)}}}\n', ("SET", {"status": s}), "END") for s in L.STATUSES]
            return out
        if st == "status":
            return [(f' "status": {q(s)}}}\n', ("SET", {"status": s}), "END") for s in L.STATUSES]
        if st == "ref":
            keys = ["target", "each"] if op in ("UPDATE", "SET_STATUS", "DELETE", "RETRACT") else ["value"] if op == "RETURN" else ["of"]
            nxt = AFTER_REF[op]
            for k in keys:
                need = NEEDS["RETURN"] if op == "RETURN" else NEEDS[k] if k in ("target", "each") else NEEDS[op]
                for r in compatible(res, need):
                    out.append((f' {q(k)}: {q(r.name)}' + ("}\n" if nxt == "END" else ","), ("SET", {k: r.name}), nxt))
            return out
        ref = self._ref_result(a, res)
        if st == "rel":
            for rel in L.RELS:
                if op in ("GET", "RETRACT") and ref and ref.etype and not K.valid(rel, ref.etype): continue
                out.append((f' "rel": {q(rel)}}}\n', ("SET", {"rel": rel}), "END"))
            return out
        if st == "by":
            return [(f' "by": {q(rel)}}}\n', ("SET", {"by": rel}), "END") for rel in L.RELS]
        if st == "relval":
            for c in VALUE_CLASSES:
                for v in vals[c]:
                    for rel in REL_OF_CLASS[c]:
                        if ref and ref.etype and not K.valid(rel, ref.etype): continue
                        out.append((f' "rel": {q(rel)}, "value": {q(v)}}}\n', ("SET", {"rel": rel, "value": v}), "END"))
            return out
        if st == "svalue":
            return [(f' "value": {q(s)}}}\n', ("SET", {"value": s}), "END") for s in L.STATUSES]
        if st == "proc":
            return [(f' "procedure": {q(p["name"])},', ("SET", {"procedure": p["name"]}), "args") for p in procs if self._call_possible(p, res, vals)]
        if st == "args":
            p = next(x for x in procs if x["name"] == a["procedure"]); done = a.get("args", {}); todo = [x for x in p["parameters"] if x["name"] not in done]
            par = todo[0]; last = len(todo) == 1; first = not done
            opts = [(v, "const") for v in vals.get(par["type"], [])] + [(r.name, "var") for r in res if r.kind == par["type"]]
            for v, how in opts:
                out.append(((' "args": {' if first else " ") + f'{q(par["name"])}: {q(v)}' + ("}}\n" if last else ","), ("ARG", par["name"], v, how), "END" if last else "args"))
            return out
        raise RuntimeError(f"no options for {op} at {st}")

    def _call_possible(self, p, res, vals):
        return all(vals.get(x["type"]) or any(r.kind == x["type"] for r in res) for x in p["parameters"])

    def _op_possible(self, op, res, vals, procs):
        if op in ("FIND", "FIND_LAST"): return bool(self._ctx_named)
        if op == "CALL": return any(self._call_possible(p, res, vals) for p in procs)
        if op == "RETURN": return bool(res)
        if op in ("UPDATE", "SET_STATUS", "DELETE", "RETRACT"):
            if not (compatible(res, NEEDS["target"]) or compatible(res, NEEDS["each"])): return False
            if op == "UPDATE": return any(vals[c] for c in VALUE_CLASSES)
            return True
        if op == "FILTER": return bool(compatible(res, NEEDS[op]))
        return bool(compatible(res, NEEDS[op]))

    def _where_options(self, T, vals, have):
        out = []
        for c in VALUE_CLASSES:
            for v in vals[c]:
                for rel in REL_OF_CLASS[c]:
                    if T in INNER: scopes = ["PARENT"] if rel == "WHEN" else ["SELF"]
                    elif T in OUTER: scopes = ["SELF"] + (["CHILD"] if rel != "WHEN" else [])
                    else: scopes = ["SELF"]
                    for sc in scopes:
                        if sc == "SELF" and T and not K.valid(rel, T): continue
                        k = rel if sc == "SELF" else f"{sc}.{rel}"
                        if k in have or v in have.values(): continue
                        out.append((k, v))
        return out

    def _ref_result(self, a, res):
        n = a.get("of") or a.get("target") or a.get("each")
        return next((r for r in res if r.name == n), None)

    # ---- apply an option ----
    def apply(self, h, opt, ctx):
        text, o, nxt = opt; h = h.clone(); h.text += text; kind = o[0]; res = ctx["results"] + h.produced
        if kind == "END": h.done = True; return h
        if kind == "SPECIAL": h.actions.append({"op": o[1]}); h.terminal = True; return h
        if kind == "OP": h.cur = {"op": o[1]}; h.stage = nxt; return h
        a = h.cur
        if kind == "SET":
            a.update(o[1])
            if a["op"] == "FILTER" and "of" in o[1]:
                ref = self._ref_result(a, res); a["_ltype"] = ref.etype if ref else None
        elif kind == "WHERE": a.setdefault("where", {})[o[1]] = o[2]; h.used.add(o[2])
        elif kind == "ARG":
            a.setdefault("args", {})[o[1]] = o[2]
            if o[3] == "const": h.used.add(o[2])
        if a["op"] == "UPDATE" and "value" in a: h.used.add(a["value"])
        if nxt == "END": return self._finish(h, ctx)
        h.stage = nxt; return h

    def _finish(self, h, ctx):
        a = h.cur; a.pop("_ltype", None); res = ctx["results"] + h.produced
        if a["op"] in PRODUCES:
            a["bind"] = f"r{len(res) + 1}"; h.produced.append(result_of_action(a, res, ctx))
        h.actions.append(a); h.cur = None; h.stage = None; return h

    # ---- beam search ----
    def decode(self, utt, ctx):
        base = self.prefix + block(ctx["procs_line"], [r.line() for r in ctx["results"]], utt); beams = [Hyp()]; finished = []; calls = 0
        for _ in range(60):
            cand = []
            for h in beams:
                opts = self.options(h, ctx)
                if not opts: continue
                if len(opts) == 1: lps = [0.0]                   # forced choice: no LLM call (probability 1 under the grammar)
                else:                                             # the LLM's choice distribution RENORMALIZED over the legal options
                    raw = nllm.choose(base + h.text, [o[0] for o in opts]); calls += 1; mx = max(raw)
                    z = mx + math.log(sum(math.exp(x - mx) for x in raw)); lps = [x - z for x in raw]
                for opt, lp in zip(opts, lps):
                    c = self.apply(h, opt, ctx); c.score = h.score + lp; cand.append(c)
            finished += [c for c in cand if c.done]; live = sorted([c for c in cand if not c.done], key=lambda c: -c.score)[:self.beam]
            if not live: break
            best_f = max([f.score for f in finished], default=None)
            if best_f is not None and all(l.score < best_f for l in live) and len(finished) >= 2: break
            beams = live
        finished.sort(key=lambda c: -c.score)
        return finished, calls, base


def q_line(s): return s + "\n"


def result_of_action(a, res, ctx):
    """STATIC result kind of an action during decoding (runtime kinds replace these after execution)"""
    op = a["op"]; by = {r.name: r for r in res}; txt = action_text(a)
    if op == "FIND": return Result(a["bind"], txt, "EVENT_LIST", a["type"], "?")
    if op == "FILTER": src = by.get(a.get("of")); return Result(a["bind"], txt, "EVENT_LIST", src.etype if src else None, "?")
    if op == "SORT": src = by.get(a.get("of")); return Result(a["bind"], txt, "EVENT_LIST", src.etype if src else None, "?")
    if op == "FIND_LAST": return Result(a["bind"], txt, "EVENT", a["type"])
    if op == "FIRST": src = by.get(a.get("of")); return Result(a["bind"], txt, "EVENT", src.etype if src else None)
    if op in ("CHILD", "PARENT"): return Result(a["bind"], txt, "EVENT", None)
    if op == "COUNT": return Result(a["bind"], txt, "INT")
    if op == "GET": return Result(a["bind"], txt, "PERSON" if a.get("rel") in ("WHO", "RECIPIENT") else "VALUE")
    if op == "SELECT": return Result(a["bind"], txt, "VALUE_LIST", None, "?")
    if op == "GROUP": return Result(a["bind"], txt, "GROUPS")
    if op == "REPORT": return Result(a["bind"], txt, "REPORT")
    if op == "CALL":
        p = next((x for x in ctx["procs"] if x["name"] == a.get("procedure")), None); rt = p.get("returns") if p else None
        return Result(a["bind"], txt, rt or "VALUE")
    raise RuntimeError(op)


KEY_ORDER = ["op", "type", "procedure", "of", "target", "each", "where", "status", "rel", "by", "value", "args"]


def action_text(a):
    d = {k: a[k] for k in KEY_ORDER if k in a}; body = json.dumps(d)
    return (f"{a['bind']} = " if a.get("bind") else "") + body


# ---------------------------------------------------------------- parsing of action text (schema parsing; used for decoded text + diagnostics) ----
class SchemaError(Exception): pass


def parse_actions(text):
    acts = []
    for line in [l.strip() for l in text.strip().splitlines() if l.strip()]:
        m = re.fullmatch(r"(?:(r\d+)\s*=\s*)?(\{.*\})", line)
        if not m: raise SchemaError(f"not an action line: {line!r}")
        try: a = json.loads(m.group(2))
        except json.JSONDecodeError as e: raise SchemaError(f"bad JSON: {line!r}")
        if not isinstance(a, dict) or "op" not in a: raise SchemaError(f"no op: {line!r}")
        a["op"] = str(a["op"]).upper()
        if a["op"] not in OPS + ["UNSUPPORTED", "CLARIFY"]: raise SchemaError(f"unknown op {a['op']}")
        if m.group(1): a["bind"] = m.group(1)
        acts.append(a)
    return acts


# ---------------------------------------------------------------- deterministic post-checks ------------------------------------------------------
def ref_keys(a):
    return [k for k in ("of", "target", "each") if k in a] + (["value"] if a["op"] == "RETURN" else []) + [f"args.{k}" for k, v in a.get("args", {}).items() if isinstance(v, str) and re.fullmatch(r"r\d+", v)]


def reference_check(actions, ctx, utt):
    """registered reference grammar R0-R4 (spec §19, §69). -> (actions (possibly repaired), notes, clarify_reason|None)"""
    res = list(ctx["results"]); produced_here = list(ctx.get("here", [])); nouns = nouns_in(utt); sing = has_singular_pronoun(utt); notes = []
    by_procs = {p["name"]: p for p in ctx["procs"]}
    for a in actions:
        for k in ref_keys(a):
            if k.startswith("args."):
                pn = k[5:]; p = by_procs[a["procedure"]]; need = (next(x["type"] for x in p["parameters"] if x["name"] == pn),); cur = a["args"][pn]
            else:
                need = NEEDS["RETURN"] if a["op"] == "RETURN" else NEEDS[k] if k in ("target", "each") else NEEDS[a["op"]]; cur = a[k]
            comp = compatible(res, need); names = [r.name for r in comp]; lic = None; rule = None
            if a["op"] == "RETURN" and nouns and not any(r.matches_noun(nk) for r in comp for nk in nouns):     # R4
                return actions, notes, f"RETURN asks for {sorted(k for _, k in nouns)} but no such result exists"
            if len(comp) == 1: lic, rule = comp[0].name, "R0"
            else:
                here = [r for r in comp if r.name in produced_here]
                if here and cur == here[-1].name: lic, rule = cur, "R1"
                if lic is None:
                    nm = [r for r in comp if any(r.matches_noun(nk) for nk in nouns)]
                    if len(nm) == 1: lic, rule = nm[0].name, "R2"
                if lic is None and sing:
                    single = [r for r in comp if r.kind not in LIST_T]
                    if single: lic, rule = single[-1].name, "R3"
            if lic is None:
                notes.append({"unresolved_slot": f"{a['op']}.{k}", "candidates": [{"name": r.name, "kind": r.kind, "etype": r.etype} for r in comp]})
                return actions, notes, f"reference for {a['op']}.{k} is ambiguous among {names}"
            if lic != cur:
                notes.append(f"{a['op']}.{k}: {cur} -> {lic} ({rule})")
                if k.startswith("args."): a["args"][k[5:]] = lic
                else: a[k] = lic
            else: notes.append(f"{a['op']}.{k}={cur} licensed by {rule}")
        if a.get("bind"):
            r = result_of_action(a, res, ctx); res.append(r); produced_here.append(r.name)
    return actions, notes, None


def dangling(actions):
    """an intermediate result produced by an instruction must be consumed by a later action of the same instruction"""
    prod = [i for i, a in enumerate(actions) if a.get("bind") and i < len(actions) - 1]      # only the instruction's LAST action may leave its result
    for i in prod:
        b = actions[i]["bind"]
        if not any(b in [a.get(k) for k in ("of", "target", "each", "value")] + list((a.get("args") or {}).values()) for a in actions[i + 1:]): return True
    return False


def has_pronoun(utt): return any(_has_phrase(utt, w) for w in LANG["antecedent_pronouns"])


def antecedent_missing(actions, ctx, utt):
    """V1.2: a clause with an anaphor must reference an existing result (prior context, an earlier clause, or an earlier action of the plan;
    event searches can no longer be invented since FIND / FIND_LAST require a named type)"""
    if not has_pronoun(utt): return False
    refs = [a.get(k) for a in actions for k in ("of", "target", "each")] + [a.get("value") for a in actions if a["op"] == "RETURN"] + [v for a in actions for v in (a.get("args") or {}).values()]
    return not any(isinstance(r, str) and re.fullmatch(r"r\d+", r) for r in refs)


def output_request(utt): return any(re.search(p, utt, re.I) for p in LANG["output_request_cues"])


def output_missing(actions, utt):
    """V1.2: an utterance carrying an OUTPUT_REQUEST must be grounded to a plan that ends by RETURNing a result (its type is checked by R4)"""
    return output_request(utt) and not (actions and actions[-1]["op"] == "RETURN")


def coverage_ok(actions, vals):
    used = set()
    for a in actions:
        for v in list((a.get("where") or {}).values()) + [a.get("value")] + list((a.get("args") or {}).values()):
            if isinstance(v, str): used.add(v)
    missing = [v for c in COVERED for v in vals[c] if v not in used]
    return missing


def to_steps(actions, loop_counter):
    """NL action objects -> parent SEMVM_STEP_V1 ASTs (canonical constraint order: SELF < PARENT < CHILD, then lang.RELS order)"""
    steps = []; sco = {"SELF": 0, "PARENT": 1, "CHILD": 2}
    C = lambda v: {"const": v}; V = lambda v: {"var": v}
    for a in actions:
        op = a["op"]
        if op == "FIND":
            w = []
            for k, v in (a.get("where") or {}).items():
                sc, rel = (k.split(".") if "." in k else ("SELF", k)); w.append([sc, rel, C(v)])
            w.sort(key=lambda x: (sco[x[0]], L.RELS.index(x[1])))
            steps.append({"op": "FIND", "bind": a["bind"], "type": C(a["type"]), "where": w, "status": C(a["status"]) if a.get("status") else None})
        elif op == "FIND_LAST": steps.append({"op": "FIND_LAST", "bind": a["bind"], "type": C(a["type"])})
        elif op in ("FIRST", "COUNT"): steps.append({"op": op, "bind": a["bind"], "list": V(a["of"])})
        elif op in ("CHILD", "PARENT"): steps.append({"op": op, "bind": a["bind"], "obj": V(a["of"])})
        elif op == "GET": steps.append({"op": "GET", "bind": a["bind"], "obj": V(a["of"]), "rel": a["rel"]})
        elif op in ("SELECT", "SORT", "GROUP"): steps.append({"op": op, "bind": a["bind"], "list": V(a["of"]), "rel": a.get("rel") or a.get("by")})
        elif op == "REPORT": steps.append({"op": "REPORT", "bind": a["bind"], "groups": V(a["of"]), "rel": a["rel"]})
        elif op == "FILTER":
            if a.get("status"): steps.append({"op": "FILTER", "bind": a["bind"], "list": V(a["of"]), "rel": "STATUS", "value": C(a["status"])})
            else:
                (k, v), = a["where"].items(); steps.append({"op": "FILTER", "bind": a["bind"], "list": V(a["of"]), "rel": k, "value": C(v)})
        elif op in ("UPDATE", "SET_STATUS", "DELETE", "RETRACT"):
            loop = "each" in a; obj = V(f"e{loop_counter[0]}") if loop else V(a["target"])
            body = {"op": op, "obj": obj}
            if op == "UPDATE": body.update(rel=a["rel"], value=C(a["value"]))
            if op == "SET_STATUS": body["value"] = C(a["value"])
            if op == "RETRACT": body["rel"] = a["rel"]
            if loop: steps.append({"op": "FOR", "as": f"e{loop_counter[0]}", "list": V(a["each"]), "body": [body]}); loop_counter[0] += 1
            else: steps.append(body)
        elif op == "CALL":
            steps.append({"op": "CALL", "bind": a["bind"], "procedure": a["procedure"], "args": {k: (V(v) if re.fullmatch(r"r\d+", v) else C(v)) for k, v in a["args"].items()}})
        elif op == "RETURN": steps.append({"op": "RETURN", "value": V(a["value"])})
        else: raise SchemaError(op)
    return steps


def validate_actions(actions, ctx, utt):
    """static validation of a candidate action list (spec §14): ops, arguments, typed values occurring in the instruction, legality, refs"""
    vals = mentioned_values(utt); res = list(ctx["results"]); errs = []
    procs = {p["name"]: p for p in ctx["procs"]}
    for a in actions:
        op = a["op"]
        if op in ("UNSUPPORTED", "CLARIFY"): continue
        for k in ref_keys(a):
            nm = a["args"][k[5:]] if k.startswith("args.") else a[k]
            if not any(r.name == nm for r in res): errs.append(f"{op}: unknown result {nm}")
        for k, v in (a.get("where") or {}).items():
            rel = k.split(".")[-1]
            if rel not in L.RELS: errs.append(f"unknown relation {k}"); continue
            if canon_value(v, L.REL_CLASS[rel]) != v: errs.append(f"{v!r} is not a {L.REL_CLASS[rel]} value")
            elif v not in vals[L.REL_CLASS[rel]]: errs.append(f"{v!r} does not occur in the instruction")
        if op in ("FIND", "FIND_LAST") and a.get("type") not in L.EVENT_TYPES: errs.append(f"bad type {a.get('type')}")
        elif op in ("FIND", "FIND_LAST") and ("EVENT", a["type"]) not in nouns_in(utt): errs.append(f"event search for {a['type']} not named in the instruction (V1.2)")
        if op == "UPDATE":
            cls = L.REL_CLASS.get(a.get("rel"))
            if not cls or canon_value(a.get("value", ""), cls) != a.get("value") or a.get("value") not in vals[cls]: errs.append(f"UPDATE value {a.get('value')!r} invalid for {a.get('rel')}")
        if op == "CALL":
            p = procs.get(a.get("procedure"))
            if p is None: errs.append(f"CALL to non-ACTIVE procedure {a.get('procedure')}")
            elif set(a.get("args", {})) != {x["name"] for x in p["parameters"]}: errs.append("CALL arguments do not match the signature")
        if a.get("bind"): res.append(result_of_action(a, res, ctx))
    return errs


# ---------------------------------------------------------------- top level ----------------------------------------------------------------------
def ground(utt, ctx, grounder):
    """-> dict(status OK|CLARIFY|UNSUPPORTED|NO_PARSE, actions, steps?, provenance)"""
    t0 = time.time(); vals = mentioned_values(utt); ctx = dict(ctx, values=vals, nouns=nouns_in(utt), status_cue=status_cue(utt), named_procs=named_procs(utt, ctx["procs"]))
    fin, calls, _ = grounder.decode(utt, ctx); P = {"instruction": utt, "values": vals, "llm_calls": calls,
                                                  "top": [{"text": f.text, "score": round(f.score, 3)} for f in fin[:5]]}
    if not fin: P["seconds"] = round(time.time() - t0, 2); return {"status": "CLARIFY", "reason": "no complete grounding", "provenance": P}
    best = fin[0]; raw = copy.deepcopy(best.actions); P["raw_text"] = best.text; P["raw_actions"] = raw
    # every complete hypothesis is passed through the SAME deterministic checks; hypotheses with identical canonical outcomes are ONE candidate
    # (log-sum-exp of their scores). The margin is measured between distinct canonical outcomes (a score gap never implies equivalence).
    groups = {}; detail = {}
    for f in fin:
        key, out = outcome(f, ctx, utt)
        if key is None: continue                                   # statically invalid -> not a candidate action
        g = groups.setdefault(key, []); g.append(f.score); detail.setdefault(key, out)
    if not groups: P["seconds"] = round(time.time() - t0, 2); return {"status": "CLARIFY", "reason": "no valid grounding", "provenance": P}
    lse = lambda xs: max(xs) + math.log(sum(math.exp(x - max(xs)) for x in xs))
    ranked = sorted(((lse(v), k) for k, v in groups.items()), reverse=True); bk = ranked[0][1]; out = detail[bk]
    P["candidates"] = [{"outcome": k[:200], "score": round(sc, 3), "n": len(groups[k])} for sc, k in ranked[:5]]
    P["margin"] = round(ranked[0][0] - ranked[1][0], 3) if len(ranked) > 1 else None
    P["reference_notes"] = [n for n in (out.get("notes") or []) if not isinstance(n, dict)]; P["seconds"] = round(time.time() - t0, 2)
    if out["status"] != "OK": return dict(out, provenance=P)
    if P["margin"] is not None and P["margin"] < grounder.margin:
        P["runner_up"] = ranked[1][1][:300]; return {"status": "CLARIFY", "reason": f"low margin {P['margin']} < {grounder.margin}", "provenance": P, "clarify_kind": "MARGIN"}
    P["repaired"] = any("->" in n for n in out.get("notes") or [])
    return {"status": "OK", "actions": out["actions"], "provenance": P}


def outcome(f, ctx, utt):
    """deterministic checks of one complete hypothesis -> (canonical key, outcome) ; key None = statically invalid"""
    if f.actions[0]["op"] in ("UNSUPPORTED", "CLARIFY"):
        op = f.actions[0]["op"]; return ("SPECIAL:" + op), {"status": "UNSUPPORTED" if op == "UNSUPPORTED" else "CLARIFY", "reason": "frontend: " + op}
    acts = copy.deepcopy(f.actions)
    if validate_actions(acts, ctx, utt) or dangling(acts) or antecedent_missing(acts, ctx, utt) or output_missing(acts, utt): return None, None
    acts, notes, why = reference_check(acts, ctx, utt)
    if why:
        info = next((n for n in notes if isinstance(n, dict)), None)
        return "REFERENCE_AMBIGUOUS", {"status": "CLARIFY", "reason": why, "clarify_kind": "REFERENCE" if info else "RESULT_NOT_COMPUTED", "clarify_info": info, "notes": [n for n in notes if not isinstance(n, dict)]}
    miss = coverage_ok(acts, ctx["values"]) + [p for p in ctx.get("named_procs", []) if not any(a.get("procedure") == p for a in acts)]
    if miss: return "COVERAGE_INCOMPLETE", {"status": "CLARIFY", "reason": f"instruction mentions {miss} but the grounding does not use it", "clarify_kind": "COVERAGE", "notes": notes}
    key = json.dumps(to_steps(copy.deepcopy(acts), [0]), sort_keys=True)
    return key, {"status": "OK", "actions": acts, "notes": notes}


# ---------------------------------------------------------------- registered sequencing (V1.1; spec §11 simple conjunctions / sequencing words, §33) ----
def _split(utt, conns):
    t = " " + utt.strip().rstrip(".!") + " "
    for c in sorted(conns, key=len, reverse=True): t = re.sub(re.escape(c), " \x00 ", t, flags=re.I)
    segs = []
    for x in t.split("\x00"):
        x = re.sub(r"^\s*(first|then|next|finally|and)\b[\s,]*", "", x.strip(), flags=re.I).strip(" ,;")
        if x: segs.append(x[0].upper() + x[1:] + ".")
    return segs


def segments(utt):
    """candidate segmentations: STRONG (explicit sequencing markers) and FULL (strong + weak plain 'and')"""
    strong = _split(utt, LANG["sequence_connectors_strong"]); full = _split(utt, LANG["sequence_connectors_strong"] + LANG["sequence_connectors_weak"])
    return strong, full


def _ground_clauses(segs, ctx, grounder):
    c = dict(ctx); c["results"] = list(ctx["results"]); c["here"] = []; acts = []; parts = []
    for sg in segs:
        g = ground(sg, c, grounder); parts.append({"segment": sg, "status": g["status"], "provenance": g.get("provenance"), "reason": g.get("reason"), "clarify_kind": g.get("clarify_kind"), "clarify_info": g.get("clarify_info")})
        if g["status"] != "OK": return None, parts
        for a in g["actions"]:
            if a.get("bind"):
                r = result_of_action(a, c["results"], c); c["results"].append(r); c["here"].append(r.name)
            acts.append(a)
    return acts, parts


def plan_ok(acts, utt, n_clauses, ctx):
    """whole-plan validation (same authority for every path): liveness, coverage (values + named procedures), RETURN last, clause coverage"""
    if acts is None: return False, "a clause did not ground"
    if dangling(acts): return False, "DEAD_PURE_RESULT"
    miss = coverage_ok(acts, mentioned_values(utt)) + [p for p in named_procs(utt, ctx["procs"]) if not any(a.get("procedure") == p for a in acts)]
    if miss: return False, f"coverage {miss}"
    if any(a["op"] == "RETURN" for a in acts[:-1]): return False, "RETURN not last"
    if output_missing(acts, utt): return False, "OUTPUT_OBLIGATION: the requested result is not returned"
    if len(acts) < n_clauses: return False, f"CLAUSE_COVERAGE {len(acts)} actions < {n_clauses} clauses"
    return True, None


def ground_instruction(utt, ctx, grounder):
    """V1.1: candidate segmentation -> non-executable plan fragments per clause -> combined plan -> whole-plan validation. Precedence: the FINEST
    segmentation whose clauses all ground and whose combined plan validates; a weak 'and' that does not yield valid clauses is not a boundary.
    The whole-utterance reading is also grounded; if it too validates, covers every clause and DIFFERS, segmentation is uncertain -> CLARIFY.
    Nothing executes before the complete plan is validated (execution = one transaction, in nlsystem)."""
    strong, full = segments(utt); cands = []
    for segs in ([full] if len(full) > len(strong) else []) + ([strong] if len(strong) >= 2 else []):
        acts, parts = _ground_clauses(segs, ctx, grounder); ok, why = plan_ok(acts, utt, len(segs), ctx); cands.append((segs, acts, parts, ok, why))
        if ok: break
    chosen = next((c for c in cands if c[3]), None)
    whole = ground(utt, ctx, grounder); n_req = len(chosen[0]) if chosen else len(strong)
    wok, wwhy = plan_ok(whole.get("actions") if whole["status"] == "OK" else None, utt, n_req, ctx)
    seginfo = {"input_clause_count": len(full), "strong_clause_count": len(strong),
               "tried": [{"segments": c[0], "valid": c[3], "why": c[4], "parts": [{k: v for k, v in p.items() if k != "provenance"} for p in c[2]]} for c in cands],
               "whole_status": whole["status"], "whole_valid": wok, "whole_why": wwhy}
    if chosen:
        segs, acts, parts, _, _ = chosen
        key = lambda A: json.dumps(to_steps(copy.deepcopy(A), [0]), sort_keys=True)
        if whole["status"] == "OK" and wok and key(whole["actions"]) != key(acts):
            P = dict(whole.get("provenance") or {}); P["segmentation"] = seginfo; P["segmentation_disagree"] = True
            return {"status": "CLARIFY", "reason": "segmentation uncertain: clause-wise and whole-utterance plans differ", "clarify_kind": "SEGMENTATION", "provenance": P}
        P = {"instruction": utt, "segmented": True, "segmentation": seginfo, "grounded_clause_count": len(segs),
             "llm_calls": sum((p["provenance"] or {}).get("llm_calls", 0) for p in parts) + (whole.get("provenance") or {}).get("llm_calls", 0),
             "seconds": round(sum((p["provenance"] or {}).get("seconds", 0) for p in parts) + (whole.get("provenance") or {}).get("seconds", 0), 2),
             "raw_actions": [x for p in parts for x in ((p["provenance"] or {}).get("raw_actions") or [])], "raw_text": "".join(((p["provenance"] or {}).get("raw_text") or "") for p in parts),
             "whole_raw_actions": (whole.get("provenance") or {}).get("raw_actions"), "margin": min(((p["provenance"] or {}).get("margin") or 99) for p in parts),
             "reference_notes": [n for p in parts for n in ((p["provenance"] or {}).get("reference_notes") or [])]}
        return {"status": "OK", "actions": acts, "provenance": P}
    P = dict(whole.get("provenance") or {}); P["segmentation"] = seginfo; P["grounded_clause_count"] = len(whole.get("actions") or []) if whole["status"] == "OK" else 0
    if whole["status"] == "OK" and not wok:
        return {"status": "CLARIFY", "reason": f"whole-plan validation: {wwhy}", "clarify_kind": "PLAN", "provenance": P}
    whole["provenance"] = P; return whole
