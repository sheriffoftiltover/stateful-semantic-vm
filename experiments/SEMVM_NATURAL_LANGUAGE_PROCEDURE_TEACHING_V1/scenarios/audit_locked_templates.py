"""Audit templates_locked.json against templates_dev.json and the language spec.
Prints ONLY aggregate counts / booleans (never template text)."""
import json, os, re, hashlib, string
HERE = os.path.dirname(os.path.abspath(__file__))
DEV = json.load(open(os.path.join(HERE, "templates_dev.json")))
LP = os.path.join(HERE, "templates_locked.json"); LOC = json.load(open(LP))
SPEC = json.load(open(os.path.join(HERE, "..", "spec", "NL_TEACH_LANGUAGE_V1.json")))
PH = re.compile(r"\{(P|T|PL|a|b)\}")

def norm(s): return re.sub(r"\s+", " ", PH.sub(lambda m: "<" + m.group(1) + ">", s.lower())).strip(" .")
def phs(s): return set(PH.findall(s))
def words(s): return re.findall(r"[a-z_']+|[a-z]+-[a-z]+", s.lower())
def has(s, phrase): return re.search(r"(?<![a-z_-])" + re.escape(phrase) + r"(?![a-z_-])", s.lower()) is not None

def structure(o):
    if isinstance(o, dict): return {k: structure(v) for k, v in o.items() if k not in ("note", "split")}
    if isinstance(o, list): return "list"
    return type(o).__name__

def all_strings(T):
    """(pattern, form, text) for every template string"""
    out = []
    for p, c in T["clauses"].items():
        for b, l in c.items(): out += [(p, "clause_" + b, s) for s in l]
    for p, R in T["returns"].items():
        for f, v in R.items():
            if f == "noun":
                for b, l in v.items(): out += [(p, "noun_" + b, s) for s in l]
            else: out += [(p, f, s) for s in v]
    for p, l in T["combos"].items(): out += [(p, "combo", s) for s in l]
    out += [("connectors", "connector", s) for s in T["connectors"]]
    out += [("prefixes", "prefix", s) for s in T["sentence"]["prefixes"] if s]
    out += [("clarify", "people", s) for s in T["clarify_answers"]["people"]]
    out += [("unsupported", "unsupported", s) for s in T["unsupported"]]
    out += [("failing", "failing", s) for s, _ in T["failing"]]
    out += [("correction", "marker", s) for s in T["correction_marker"]]
    return out

checks = {}; counts = {}
L = all_strings(LOC); D = all_strings(DEV)
counts["n_locked_strings"] = len(L); counts["n_dev_strings"] = len(D)

# 1 structure
checks["identical_key_structure"] = structure(LOC) == structure(DEV)
checks["split_is_locked_test"] = LOC.get("split") == "locked_test"

# 2 exact overlaps (normalised), excluding protocol-fixed items and empty prefixes
dev_norm = {norm(s) for _, _, s in D}
ov = sum(1 for _, _, s in L if norm(s) in dev_norm)
counts["exact_overlaps"] = ov; checks["zero_exact_overlaps"] = ov == 0
dup = len(L) - len({(p, f, norm(s)) for p, f, s in L}); counts["internal_duplicates"] = dup

# leading-verb reuse per clause pattern (informational + must be low)
def lead(s): w = s.lower().split(); return w[0] if w else ""
lv = 0; lv_tot = 0
for p, c in LOC["clauses"].items():
    dv = {lead(s) for l in DEV["clauses"][p].values() for s in l}
    for l in c.values():
        for s in l: lv_tot += 1; lv += lead(s) in dv
counts["clause_leading_verb_reuse"] = lv; counts["clause_total"] = lv_tot

# 3 placeholders
bad_ph = 0
for p, c in LOC["clauses"].items():
    dset = set().union(*[phs(s) for l in DEV["clauses"][p].values() for s in l])
    for l in c.values():
        for s in l: bad_ph += phs(s) != dset
for p, R in LOC["returns"].items():
    for f, v in R.items():
        for s in (sum(v.values(), []) if f == "noun" else v): bad_ph += bool(phs(s))
for p, l in LOC["combos"].items():
    dset = set().union(*[phs(s) for s in DEV["combos"][p]])
    for s in l: bad_ph += phs(s) != dset
for s in LOC["connectors"]: bad_ph += not (phs(s) == {"a", "b"} and s.index("{a}") < s.index("{b}"))
for s in LOC["unsupported"]: bad_ph += not phs(s) <= {"P"}
for s, _ in LOC["failing"]: bad_ph += bool(phs(s))
counts["placeholder_violations"] = bad_ph; checks["placeholders_match_dev"] = bad_ph == 0

# 4 forbidden words
FORB_ALL = ["mail", "mails", "appointment", "appointments", "meeting", "meetings", "o'clock", "if", "unless", "when"]
FORB_NONFAIL = ["message", "messages", "note", "notes", "plan", "plans", "planned"]
EXTERNAL = ["send", "text", "post", "print", "browse", "download", "upload", "fax", "ring", "phone", "share", "search", "file", "web"]
fa = sum(1 for _, _, s in L if any(has(s, w) for w in FORB_ALL))
fn = sum(1 for p, _, s in L if p != "failing" and any(has(s, w) for w in FORB_NONFAIL))
# 'phone' allowed only as part of the registered noun 'phone call(s)'
def ext(s): t = re.sub(r"phone calls?", "", s.lower()); return any(has(t, w) for w in EXTERNAL)
fe = sum(1 for p, _, s in L if p not in ("unsupported",) and ext(s))
multi = sum(1 for _, _, s in L if re.search(r"[.!?]", s.replace("e-mail", "")))
counts.update(forbidden_all=fa, forbidden_type_words_outside_failing=fn, external_verbs_outside_unsupported=fe, multi_sentence=multi)
checks["forbidden_words"] = fa == 0 and fn == 0 and fe == 0 and multi == 0

# 5 returns noun/pronoun discipline
TYPE_N = sorted({w for v in SPEC["type_nouns"].values() for w in v}, key=len, reverse=True)
RES_N = sorted({w for v in SPEC["result_nouns"].values() for w in v}, key=len, reverse=True)
SING = ["it", "its", "it's", "that", "this"]; PLUR = ["them", "they", "those", "these"]
REF = {"return_count": SPEC["result_nouns"]["INT"], "return_person": ["person", "name", "caller"],
       "return_people": ["people", "names", "persons"], "return_report": SPEC["result_nouns"]["REPORT"],
       "return_calls": ["calls", "phone calls"], "return_emails": ["emails", "e-mails"],
       "return_email": ["email", "e-mail"], "return_visit": ["visit"]}
nb = 0; pb = 0; ppb = 0; npron = 0; nnoun = 0
for p, R in LOC["returns"].items():
    for s in sum(R["noun"].values(), []):
        nnoun += 1; own = [w for w in REF[p] if has(s, w)]
        others = [w for q, ws in REF.items() if q != p for w in ws if has(s, w) and w not in REF[p]]
        nb += not own or bool(others) or has(s, "who")
    for s in R.get("pronoun", []):
        npron += 1; pb += not any(has(s, w) for w in SING) or any(has(s, w) for w in TYPE_N + RES_N) or any(has(s, w) for w in PLUR)
    for s in R.get("plural_pronoun", []):
        npron += 1; ppb += not any(has(s, w) for w in PLUR) or any(has(s, w) for w in TYPE_N + RES_N) or any(has(s, w) for w in SING)
counts.update(return_noun_forms=nnoun, return_pronoun_forms=npron, noun_violations=nb, pronoun_violations=pb, plural_pronoun_violations=ppb)
checks["returns_noun_pronoun_discipline"] = nb == 0 and pb == 0 and ppb == 0

# update_where_again uses singular demonstrative and no type noun
uwa = sum(1 for l in LOC["clauses"]["update_where_again"].values() for s in l if not has(s, "that") or any(has(s, w) for w in TYPE_N))
counts["update_where_again_violations"] = uwa; checks["update_where_again_demonstrative"] = uwa == 0
# named procedures
npv = sum(1 for l in LOC["clauses"]["call_person_on_call_at"].values() for s in l if "person_on_call_at" not in s) + \
      sum(1 for l in LOC["clauses"]["call_count_calls_with"].values() for s in l if "count_calls_with" not in s)
counts["named_procedure_violations"] = npv; checks["named_procedure_literal"] = npv == 0

# 6 failing
FT = {"PLAN": ["plan"], "NOTE": ["note"], "MESSAGE": ["message"]}
fv = sum(1 for s, t in LOC["failing"] if t not in FT or not any(has(s, w) for w in FT[t]) or not (has(s, "close") or has(s, "closed") or has(s, "done")))
counts["failing_n"] = len(LOC["failing"]); counts["failing_types_distinct"] = len({t for _, t in LOC["failing"]}); counts["failing_violations"] = fv
checks["failing_types_and_nouns"] = fv == 0

# 7 correction markers
spec_cm = {m.strip() for m in SPEC["correction_markers"]}; dev_cm = {m.strip() for m in DEV["correction_marker"]}
cmv = sum(1 for m in LOC["correction_marker"] if m.strip() not in spec_cm or m.strip() in dev_cm or m != m.lower() or not m.endswith(" "))
counts["correction_markers_n"] = len(LOC["correction_marker"]); counts["correction_marker_violations"] = cmv
checks["correction_markers_subset_spec_disjoint_dev"] = cmv == 0

# 8 rephrase prefix
checks["rephrase_prefix_exact"] = LOC["rephrase_prefix"] == "I mean: "

# misc: sizes, prefixes, clarify, end
sz = 0
for p, c in LOC["clauses"].items():
    for b, l in c.items(): sz += len(l) < min(2, len(DEV["clauses"][p][b]))
for p, R in LOC["returns"].items():
    for b, l in R["noun"].items(): sz += len(l) < min(2, len(DEV["returns"][p]["noun"][b]))
    for f in ("pronoun", "plural_pronoun"):
        if f in R: sz += len(R[f]) < 2
sz += sum(1 for l in LOC["combos"].values() if len(l) < 1)
counts["size_violations"] = sz; checks["minimum_sizes"] = sz == 0
checks["sentence_end_dot"] = LOC["sentence"]["end"] == "."
checks["prefixes_have_empty_and_differ"] = "" in LOC["sentence"]["prefixes"] and not ({p for p in LOC["sentence"]["prefixes"] if p} & {p for p in DEV["sentence"]["prefixes"] if p})
checks["clarify_people"] = all(has(s, "people") for s in LOC["clarify_answers"]["people"])
checks["no_internal_duplicates"] = dup == 0

allp = all(checks.values())
rep = {"templates_locked_sha256": hashlib.sha256(open(LP, "rb").read()).hexdigest(), "all_pass": allp,
       "checks": checks, "counts": counts}
json.dump(rep, open(os.path.join(HERE, "LOCKED_TEMPLATE_AUDIT.json"), "w"), indent=1)
for k, v in checks.items(): print(f"{k}: {'PASS' if v else 'FAIL'}")
for k, v in counts.items(): print(f"{k}: {v}")
print("sha256:", rep["templates_locked_sha256"]); print("ALL_PASS:", allp)
