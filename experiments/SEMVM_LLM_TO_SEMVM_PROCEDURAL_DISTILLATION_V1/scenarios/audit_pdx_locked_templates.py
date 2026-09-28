"""Blind audit of scenarios/templates_pdx_locked.json against templates_dev.json (+ pdx_generate.EXTRA_CLAUSES) and spec/NL_TEACH_LANGUAGE_V1.json.
Prints ONLY counts / booleans (never template text). Writes scenarios/PDX_LOCKED_TEMPLATE_AUDIT.json.
python3 scenarios/audit_pdx_locked_templates.py"""
import os, re, json, ast, hashlib, string

HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
LOCK_F = os.path.join(HERE, "templates_pdx_locked.json"); DEV_F = os.path.join(HERE, "templates_dev.json")
SPEC = json.load(open(os.path.join(ROOT, "spec", "NL_TEACH_LANGUAGE_V1.json")))
LOCK = json.load(open(LOCK_F)); DEV = json.load(open(DEV_F))


def load_extra():
    src = open(os.path.join(HERE, "pdx_generate.py")).read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "EXTRA_CLAUSES" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("EXTRA_CLAUSES not found")


EXTRA = load_extra()["dev"] if "dev" in load_extra() else {}
EXTRA_ALL = load_extra()
LX = LOCK.get("_pdx_extra", {})
norm = lambda s: " ".join(s.lower().split())
words = lambda s: re.findall(r"[a-z_'\-]+", s.lower())
def has_phrase(s, p): return re.search(r"(?<![a-z_])" + re.escape(p.lower()) + r"(?![a-z_])", s.lower()) is not None
def phs(s): return {f for _, f, _, _ in string.Formatter().parse(s) if f}


def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, list):
        for x in o: yield from strings(x)
    elif isinstance(o, dict):
        for x in o.values(): yield from strings(x)


# ------------- iterate template groups: (kind, key, sub, list) -------------
def clause_lists(tpl, extra):
    for pat, d in list(tpl["clauses"].items()) + list(extra.get("dev", {}).items()):
        for b, lst in d.items(): yield pat, b, lst


def return_lists(tpl, extra):
    for pat, d in list(tpl["returns"].items()) + list(extra.get("returns", {}).items()):
        for form, v in d.items():
            if isinstance(v, dict):
                for b, lst in v.items(): yield pat, form, b, lst
            else: yield pat, form, None, v


def dev_merged():
    c = dict(DEV["clauses"]); c.update(EXTRA_ALL.get("dev", {})); r = dict(DEV["returns"]); r.update(EXTRA_ALL.get("returns", {})); return c, r


def lock_merged():
    c = dict(LOCK["clauses"]); c.update(LX.get("dev", {})); r = dict(LOCK["returns"]); r.update(LX.get("returns", {})); return c, r


def shape(o):
    if isinstance(o, dict): return {k: shape(v) for k, v in o.items()}
    if isinstance(o, list): return "list"
    return type(o).__name__


checks = {}
def chk(name, ok, **counts): checks[name] = dict({"pass": bool(ok)}, **counts)


# 1 key structure
top_dev = set(DEV); top_lock = set(LOCK) - {"_pdx_extra"}
sd = shape({k: DEV[k] for k in DEV if k not in ("note", "split")}); sl = shape({k: LOCK[k] for k in LOCK if k not in ("note", "split", "_pdx_extra")})
sx_dev = shape(EXTRA_ALL); sx_lock = shape(LX)
chk("key_structure", top_dev == top_lock and sd == sl and sx_dev == sx_lock and "_pdx_extra" in LOCK,
    top_keys_equal=top_dev == top_lock, nested_shape_equal=sd == sl, extra_shape_equal=sx_dev == sx_lock,
    n_clause_patterns=len(LOCK["clauses"]) + len(LX.get("dev", {})), n_return_patterns=len(LOCK["returns"]) + len(LX.get("returns", {})), n_combos=len(LOCK["combos"]))
chk("split_is_locked_test", LOCK.get("split") == "locked_test")

# 2 minimum counts
dc, dr = dev_merged(); lc, lr = lock_merged(); short = 0; nlists = 0
for pat, d in lc.items():
    for b, lst in d.items():
        nlists += 1; need = 1 if len(dc.get(pat, {}).get(b, [])) == 1 else 2
        short += len(lst) < need
for pat, d in lr.items():
    for form, v in d.items():
        for b, lst in (v.items() if isinstance(v, dict) else [(None, v)]):
            nlists += 1; dl = dr[pat][form][b] if b else dr[pat][form]
            need = 2 if b is None else (1 if len(dl) == 1 else 2); short += len(lst) < need
for k, lst in LOCK["combos"].items(): nlists += 1; short += len(lst) < 1
chk("minimum_counts", short == 0, lists_checked=nlists, lists_short=short)

# 3 zero overlap
EXEMPT = {"", ".", LOCK["rephrase_prefix"].lower().strip()}
TAGS = set(SPEC["type_nouns"])
dev_strs = {norm(s) for s in strings({k: v for k, v in DEV.items() if k not in ("note", "split")})} | {norm(s) for s in strings(EXTRA_ALL)}
lock_strs = [norm(s) for s in strings({k: v for k, v in LOCK.items() if k not in ("note", "split", "rephrase_prefix")}) if s not in TAGS]
lock_strs = [s for s in lock_strs if s.strip() not in EXEMPT]
ov = sum(s in dev_strs for s in lock_strs)
# leading-verb collisions per pattern (informational)
lead = lambda s: s.split()[0] if s.split() else ""
lv_coll = 0; lv_tot = 0
for pat, d in lc.items():
    dv = {lead(norm(s)) for lst in dc.get(pat, {}).values() for s in lst}
    for lst in d.values():
        for s in lst: lv_tot += 1; lv_coll += lead(norm(s)) in dv
chk("zero_overlap", ov == 0, locked_strings_checked=len(lock_strs), dev_strings=len(dev_strs), exact_overlaps=ov,
    leading_verb_same_as_dev_pattern=lv_coll, leading_verb_total=lv_tot)

# 4 placeholders
bad_ph = 0; nph = 0
for pat, d in lc.items():
    want = set().union(*[phs(s) for lst in dc[pat].values() for s in lst])
    for lst in d.values():
        for s in lst: nph += 1; bad_ph += phs(s) != want
for pat, d in lr.items():
    for s in strings(d): nph += 1; bad_ph += bool(phs(s))
for k, lst in LOCK["combos"].items():
    want = set().union(*[phs(s) for s in DEV["combos"][k]])
    for s in lst: nph += 1; bad_ph += phs(s) != want
for s in LOCK["unsupported"]: nph += 1; bad_ph += not phs(s) <= {"P"}
for c in LOCK["connectors"]: nph += 1; bad_ph += phs(c) != {"a", "b"}
for s in strings([LOCK["sentence"], LOCK["clarify_answers"], LOCK["failing"], LOCK["correction_marker"]]): nph += 1; bad_ph += bool(phs(s))
chk("placeholders", bad_ph == 0, strings_checked=nph, mismatches=bad_ph)

# 5 forbidden words
FORB = [x for t in ("MESSAGE", "NOTE", "PLAN") for x in SPEC["type_nouns"][t]]
OTHER_EVENT = ["meeting", "meetings", "appointment", "appointments", "task", "tasks", "event", "events", "errand", "errands", "booking", "bookings", "planned", "planning", "noted"]
import sys
sys.path[:0] = [os.path.join(ROOT, "core", "neural", "vendor")]
try:
    import mr_config as K; VOC = [x.lower() for x in list(K.PERSONS) + list(K.TIMES) + list(K.PLACES) + list(K.TOPICS)]
    VOC = [v for v in VOC if v not in {x for vv in SPEC["result_nouns"].values() for x in vv}]   # e.g. topic "report" is also a registered result noun
except Exception: VOC = []
non_failing = [s for s in strings({k: v for k, v in LOCK.items() if k not in ("note", "split", "failing")})]
n_forb = sum(any(has_phrase(s, w) for w in FORB) for s in non_failing)
n_other = sum(any(has_phrase(s, w) for w in OTHER_EVENT) for s in non_failing)
n_voc = sum(any(has_phrase(s, w) for w in VOC + ["scheduled", "reschedule"]) for s in non_failing)
n_digit = sum(bool(re.search(r"\d", re.sub(r"\{[A-Za-z]+\}", "", s))) for s in non_failing)
n_cond = sum(any(w in words(s) for w in ("if", "unless", "when", "whenever")) and not re.search(r"\bwhen they (are|happen)\b", s) for s in non_failing)
n_sent = sum(bool(re.search(r"[.!?]", s)) for s in non_failing if s != ".")
chk("forbidden_words", n_forb == 0 and n_other == 0 and n_voc == 0 and n_digit == 0 and n_cond == 0 and n_sent == 0 and bool(VOC),
    strings_checked=len(non_failing), message_note_plan_hits=n_forb, other_event_word_hits=n_other, vocab_value_hits=n_voc, digit_hits=n_digit,
    conditional_hits=n_cond, inner_sentence_punct_hits=n_sent, vocab_loaded=bool(VOC))

# 6 return-form discipline
TN = SPEC["type_nouns"]; RN = SPEC["result_nouns"]
ALL_NOUNS = sorted({x for v in TN.values() for x in v} | {x for v in RN.values() for x in v}, key=len, reverse=True)
KIND = {"return_count": RN["INT"], "return_person": RN["PERSON"], "return_people": [x for x in RN["VALUE_LIST"] if x != "who"], "return_report": RN["REPORT"],
        "return_calls": ["calls", "phone calls"], "return_emails": ["emails", "e-mails"], "return_email": ["email", "e-mail"], "return_visit": ["visit"], "return_request": ["request"]}
SING = SPEC["pronouns"]["singular"]; PLUR = SPEC["pronouns"]["plural"]
CUES = [re.compile(c) for c in SPEC["output_request_cues"]]
cue = lambda s: any(c.search(s.lower()) for c in CUES)
rf_bad = {"noun": 0, "pronoun": 0, "plural_pronoun": 0, "missing_pattern": 0, "no_output_cue": 0}; rf_n = 0
for pat in KIND:
    if pat not in lr: rf_bad["missing_pattern"] += 1
for pat, form, b, lst in return_lists(LOCK, LX):
    for s in lst:
        rf_n += 1
        if not cue(s): rf_bad["no_output_cue"] += 1
        if form == "noun":
            ok = any(has_phrase(s, n) for n in KIND[pat])
            other = [n for n in ALL_NOUNS if has_phrase(s, n) and n not in KIND[pat] and not any(n in k for k in KIND[pat] if has_phrase(s, k))]
            if pat == "return_report": other = [n for n in other if n != "topic"]
            rf_bad["noun"] += (not ok) or bool(other)
        elif form == "pronoun":
            rf_bad["pronoun"] += not (any(has_phrase(s, p) for p in SING) and not any(has_phrase(s, n) for n in ALL_NOUNS) and not any(has_phrase(s, p) for p in PLUR))
        elif form == "plural_pronoun":
            rf_bad["plural_pronoun"] += not (any(has_phrase(s, p) for p in PLUR) and not any(has_phrase(s, n) for n in ALL_NOUNS) and not any(has_phrase(s, p) for p in SING))
chk("return_form_discipline", sum(rf_bad.values()) == 0, forms_checked=rf_n, **{f"bad_{k}": v for k, v in rf_bad.items()})

# 7 connectors
REG = SPEC["sequence_connectors_strong"] + SPEC["sequence_connectors_weak"]
con_bad = sum(not any(r in c for r in REG) for c in LOCK["connectors"])
con_dev_ov = sum(norm(c) in {norm(x) for x in DEV["connectors"]} for c in LOCK["connectors"])
unit_strs = [s for _, _, lst in clause_lists(LOCK, LX) for s in lst] + [s for *_, lst in return_lists(LOCK, LX) for s in lst] + [s for lst in LOCK["combos"].values() for s in lst]
con_inside = sum(any(r in s for r in REG) for s in unit_strs)
chk("connector_registration", con_bad == 0 and con_dev_ov == 0 and con_inside == 0 and len(LOCK["connectors"]) >= 2,
    n_connectors=len(LOCK["connectors"]), unregistered=con_bad, overlap_with_dev=con_dev_ov, clauses_containing_connector=con_inside)

# 8 status cues
ROOTS = SPEC["status_cue_roots"]; CLOSED = SPEC["set_status_cue_roots"]["CLOSED"]; OPENR = SPEC["set_status_cue_roots"]["OPEN"]
has_root = lambda s, rs: any(w.startswith(r) for w in words(s) for r in rs)
OPEN_PATS = {"find_open_calls_with", "find_open_emails_to", "find_open_requests_by"}; CLOSE_PATS = {"close_each", "close_it"}
st = {"open_missing_cue": 0, "close_missing_closed_cue": 0, "close_has_open_cue": 0, "nonstatus_has_cue": 0}; st_n = 0
for pat, b, lst in clause_lists(LOCK, LX):
    for s in lst:
        st_n += 1
        if pat in OPEN_PATS: st["open_missing_cue"] += not has_root(s, ROOTS)
        elif pat in CLOSE_PATS: st["close_missing_closed_cue"] += not has_root(s, CLOSED); st["close_has_open_cue"] += has_root(s, OPENR)
        else: st["nonstatus_has_cue"] += has_root(s, ROOTS)
for k, lst in LOCK["combos"].items():
    ps = k.split("+")
    for s in lst:
        st_n += 1
        if set(ps) & OPEN_PATS: st["open_missing_cue"] += not has_root(s, ROOTS)
        elif set(ps) & CLOSE_PATS: st["close_missing_closed_cue"] += not has_root(s, CLOSED)
        else: st["nonstatus_has_cue"] += has_root(s, ROOTS)
for *_, lst in return_lists(LOCK, LX):
    for s in lst: st_n += 1; st["nonstatus_has_cue"] += has_root(s, ROOTS)
for s in LOCK["failing"]: st_n += 1; st["close_missing_closed_cue"] += not has_root(s[0], CLOSED)
for s in strings([LOCK["sentence"]["prefixes"], LOCK["clarify_answers"], LOCK["connectors"]]): st_n += 1; st["nonstatus_has_cue"] += has_root(s, ROOTS)
chk("status_cue_compliance", sum(st.values()) == 0, strings_checked=st_n, **st)

# 9 output-cue / antecedent / skill-name hygiene
oc_leak = sum(cue(s) for _, _, lst in clause_lists(LOCK, LX) for s in lst) + sum(cue(s) for k, lst in LOCK["combos"].items() if not k.endswith("return_count") for s in lst)
oc_miss = sum(not cue(s) for k, lst in LOCK["combos"].items() if k.endswith("return_count") for s in lst)
ANTE = SPEC["antecedent_pronouns"]
ante_find = sum(any(has_phrase(s, p) for p in ANTE) for pat, _, lst in clause_lists(LOCK, LX) if pat.startswith("find_") for s in lst) + \
            sum(any(has_phrase(s, p) for p in ANTE) for k, lst in LOCK["combos"].items() if k.startswith("find_") for s in lst)
ev_miss = 0
for pat, _, lst in clause_lists(LOCK, LX):
    if pat.startswith("find_"):
        t = {"calls": "CALL", "emails": "EMAIL", "email": "EMAIL", "reminder": "REMINDER", "visit": "VISIT", "requests": "REQUEST"}
        want = [v for k, v in t.items() if k in pat.split("_")][0]
        ev_miss += sum(not any(has_phrase(s, n) for n in TN[want]) for s in lst)
skill_miss = sum("person_on_call_at" not in s for s in lc["call_person_on_call_at"]["A"] + lc["call_person_on_call_at"]["B"]) + \
             sum("count_calls_with" not in s for s in lc["call_count_calls_with"]["A"] + lc["call_count_calls_with"]["B"])
wh_again = sum(not (has_phrase(s, "that") and not any(has_phrase(s, n) for n in [x for v in TN.values() for x in v])) for lst in lc["update_where_again"].values() for s in lst)
chk("grammar_hygiene", oc_leak == 0 and oc_miss == 0 and ante_find == 0 and ev_miss == 0 and skill_miss == 0 and wh_again == 0,
    output_cue_in_nonreturn=oc_leak, output_cue_missing_in_return_combo=oc_miss, antecedent_in_find=ante_find, find_missing_type_noun=ev_miss,
    skill_name_missing=skill_miss, update_where_again_bad=wh_again)

# 10 failing
fb = 0
for x in LOCK["failing"]:
    ok = isinstance(x, list) and len(x) == 2 and x[1] in ("PLAN", "NOTE", "MESSAGE")
    if ok:
        m = re.fullmatch(r"take my most recent (\w+) and close it", x[0].lower()); ok = bool(m) and m.group(1) in TN[x[1]]
    fb += not ok
chk("failing_types", fb == 0 and len(LOCK["failing"]) >= 2, n_failing=len(LOCK["failing"]), bad=fb, types_covered=len({x[1] for x in LOCK["failing"]}))

# 11 correction markers
spec_cm = {c.strip() for c in SPEC["correction_markers"]}; dev_cm = {c.strip() for c in DEV["correction_marker"]}
cm = [c.strip() for c in LOCK["correction_marker"]]
chk("correction_markers", len(cm) >= 1 and all(c in spec_cm for c in cm) and not (set(cm) & dev_cm) and "no," not in cm and all(c.endswith(" ") for c in LOCK["correction_marker"]),
    n_markers=len(cm), subset_of_spec=all(c in spec_cm for c in cm), disjoint_from_dev=not (set(cm) & dev_cm))

# 12 rephrase prefix
chk("rephrase_prefix", LOCK["rephrase_prefix"] == "I mean: ")

# 13 misc sections
pre = LOCK["sentence"]["prefixes"]; dev_pre = {p for p in DEV["sentence"]["prefixes"] if p}
chk("sentence_prefixes", "" in pre and not ({p for p in pre if p} & dev_pre) and LOCK["sentence"]["end"] == DEV["sentence"]["end"] and all(p == "" or p.endswith(" ") for p in pre),
    n_prefixes=len(pre), n_empty=pre.count(""), overlap_with_dev=len({p for p in pre if p} & dev_pre))
ca = LOCK["clarify_answers"]["people"]
chk("clarify_answers", len(ca) >= 2 and all(has_phrase(s, "people") and len(s.split()) <= 5 for s in ca), n=len(ca))
EXT = ["whatsapp", "slack", "phone", "text", "print", "file", "web", "email them", "upload", "download", "browse", "spreadsheet", "internet", "online", "ping"]
un = LOCK["unsupported"]
chk("unsupported", len(un) >= 2 and all(any(e in s.lower() for e in EXT) for s in un), n=len(un))

allpass = all(v["pass"] for v in checks.values())
sha = hashlib.sha256(open(LOCK_F, "rb").read()).hexdigest()
out = {"templates_file": os.path.basename(LOCK_F), "templates_sha256": sha, "dev_templates_sha256": hashlib.sha256(open(DEV_F, "rb").read()).hexdigest(),
       "all_pass": allpass, "checks": checks}
json.dump(out, open(os.path.join(HERE, "PDX_LOCKED_TEMPLATE_AUDIT.json"), "w"), indent=1)
for k, v in checks.items(): print(f"{k:28s} {'PASS' if v['pass'] else 'FAIL'} " + " ".join(f"{a}={b}" for a, b in v.items() if a != "pass"))
print("ALL_PASS", allpass, "sha256", sha)
