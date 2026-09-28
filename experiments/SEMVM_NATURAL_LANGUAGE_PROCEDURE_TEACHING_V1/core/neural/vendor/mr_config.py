"""SEMVM_MULTI_RELATION_BINDING_CORPUS_V1 — FROZEN relation x constructor matrix + generator configuration.
Frozen 2026-09-25 from CANDIDATE_MATRIX_AUDIT.md revision 2 plus the user's rulings (Q1: WHO = agent/initiator, RECIPIENT = addressee;
Q2: WHERE allowed on REMINDER / REQUEST / NOTE, never on PLAN; TOPIC passes; SOURCE not added; TODO = infrastructure only).
The typed-composition engine (vendored ltc_core / ltc_packed, byte-identical to the predecessor) is used unchanged; this module installs the
ontology into its DATA tables only (the same mechanism the predecessor used for WHERE / PLACE).
SEMANTIC NOTE: WHO here is the AGENT (the person performing / initiating the event). The predecessor's WHO was overloaded (object in one
inner-clause template, agent in the other); that overloading is intentionally NOT preserved."""
import os, sys
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
VEND = os.path.join(ROOT, "code", "vendor", "predecessor_src")
for d in ("ltc", "ltcn"):
    p = os.path.join(VEND, d)
    if p not in sys.path: sys.path.insert(0, p)
import ltc_core as C

CORPUS = "SEMVM_MULTI_RELATION_BINDING_CORPUS_V1_1"   # V1.1: ontology / matrix / withheld cells / cues / formats UNCHANGED from V1
OUTER = ["REMINDER", "PLAN", "REQUEST", "NOTE"]; INNER = ["CALL", "EMAIL", "VISIT", "MESSAGE"]; EVENTS = OUTER + INNER
TRIG = {"REMINDER": "remind", "PLAN": "plan", "REQUEST": "request", "NOTE": "note", "CALL": "call", "EMAIL": "email", "VISIT": "visit", "MESSAGE": "message"}
PERSONS = ["Alice", "Bob", "Carol", "Dave", "Erin", "Frank", "Grace", "Heidi", "Ivan", "Judy", "Kevin", "Laura", "Mallory", "Nina", "Oscar", "Peggy",
           "Quinn", "Rita", "Sam", "Trent", "Uma", "Victor", "Wendy", "Xena", "Yves", "Zoe", "Mom", "Dad", "Aunt", "Uncle", "Grandma", "Grandpa"]
TIMES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "noon", "midnight", "dawn", "dusk", "1:30", "2:45", "3:15", "4:30", "5:45", "6:15", "7:45", "9:30"]
PLACES = ["Paris", "Oslo", "Rome", "Cairo", "Lima", "Tokyo", "Delhi", "Dublin", "Prague", "Vienna", "Madrid", "Seoul"]
TOPICS = ["budget", "report", "trip", "party", "contract", "schedule", "invoice", "launch", "survey", "lease"]
MARKERS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]   # coindexation tags: a modifier names its parent's tag

# relation -> (child constructor class, value list)
REL_VALUE = {"WHEN": ("TIME", TIMES), "WHO": ("PERSON", PERSONS), "RECIPIENT": ("PERSON", PERSONS), "WHERE": ("PLACE", PLACES), "TOPIC": ("TOPIC", TOPICS)}
PRIMARY = ["WHEN", "WHO", "RECIPIENT", "TOPIC", "WHERE"]            # TODO is infrastructure, never primary
SUBGROUPS = {"same_argument_type_identity": ["WHO", "RECIPIENT"], "attachment_generalization": ["WHEN", "WHERE", "TOPIC"]}   # descriptive only
MEANING = {"WHEN": "time at which the event occurs", "WHO": "agent: the person performing / initiating the event",
           "RECIPIENT": "the person to whom the event is directed / addressed", "WHERE": "location at which the event itself occurs",
           "TOPIC": "what the event is about", "TODO": "clause embedding: the OUTER event's content is the INNER event (infrastructure)"}

# ---------------- FROZEN semantic-validity matrix (True = primary-eligible cell) ----------------
VALID = {
    "WHEN":      {"REMINDER": 1, "PLAN": 1, "REQUEST": 1, "NOTE": 1, "CALL": 1, "EMAIL": 1, "VISIT": 1, "MESSAGE": 1},
    "WHO":       {"REMINDER": 1, "PLAN": 1, "REQUEST": 1, "NOTE": 0, "CALL": 1, "EMAIL": 1, "VISIT": 1, "MESSAGE": 1},
    "RECIPIENT": {"REMINDER": 1, "PLAN": 0, "REQUEST": 1, "NOTE": 1, "CALL": 1, "EMAIL": 1, "VISIT": 0, "MESSAGE": 1},
    "TOPIC":     {"REMINDER": 1, "PLAN": 0, "REQUEST": 1, "NOTE": 1, "CALL": 1, "EMAIL": 1, "VISIT": 0, "MESSAGE": 1},
    "WHERE":     {"REMINDER": 1, "PLAN": 0, "REQUEST": 1, "NOTE": 1, "CALL": 1, "EMAIL": 1, "VISIT": 1, "MESSAGE": 1}}
EXCLUSION_REASONS = {
    ("WHO", "NOTE"): "user ruling: no reinterpretation of WHO as note author / recipient / topic",
    ("RECIPIENT", "PLAN"): "a plan is not addressed to anyone ('plan for P' = beneficiary)",
    ("RECIPIENT", "VISIT"): "the visited person is not a recipient",
    ("TOPIC", "PLAN"): "'plan about X' is unnatural", ("TOPIC", "VISIT"): "'visit about X' is unnatural",
    ("WHERE", "PLAN"): "planning location vs planned-activity location is ambiguous (user ruling Q2)"}
# ---------------- FROZEN withholding (RECOMB cells): one OUTER + one INNER cell per primary relation ----------------
WITHHELD = {"WHEN": ("REMINDER", "VISIT"), "WHO": ("PLAN", "EMAIL"), "RECIPIENT": ("NOTE", "CALL"), "TOPIC": ("REMINDER", "MESSAGE"), "WHERE": ("REQUEST", "CALL")}
WITHHELD_CELLS = {(r, c) for r, cs in WITHHELD.items() for c in cs}


def valid(r, c): return bool(VALID[r][c])
def train_cell(r, c): return valid(r, c) and (r, c) not in WITHHELD_CELLS


# ---------------- surface ----------------
CUE = {"WHEN": ["at"], "WHO": ["by"], "RECIPIENT": ["to"], "WHERE": ["while", "in"], "TOPIC": ["about"]}
# modifier phrase formats: V = value, m = the PARENT's coindexation tag. fa/fb in every split; fc held out (SURFACE_RECOMB only)
PHRASE_FORMATS = {"fa": ["{CUE}", "{V}", "re", "{m}"], "fb": ["{CUE}", "{V}", "per", "{m}"], "fc": ["{m}", "re", "{CUE}", "{V}"]}
# fc (held out) is a NEW ORDER of TRAIN tokens only (tag first); it must not introduce unseen tokens (they would become UNK and confound SURFACE_RECOMB)
TRAIN_FORMATS = ["fa", "fb"]; HELDOUT_FORMATS = ["fc"]
# sentence frames. {O}/{I} = trigger + own tag; M1/M2 = modifier phrase slots; plain strings = function words.
# Every frame admits BOTH attachments of a single modifier (tag-determined); two-modifier items are verified by derivability (crossing combos are rejected).
FRAMES = {
    "after_o1":   {"order": "outer_first", "parts": ["{O}", "to", "{I}", ",", "M1", ";", "M2"]},
    "after_o2":   {"order": "outer_first", "parts": ["{O}", "then", "{I}", ".", "M1", "and", "M2"]},
    "before_i1":  {"order": "inner_first", "parts": ["M1", ";", "M2", ",", "{I}", "is", "to", "{O}"]},
    "before_i2":  {"order": "inner_first", "parts": ["M1", "and", "M2", ":", "{I}", "so", "{O}"]},
    "between_o1": {"order": "outer_first", "parts": ["{O}", ",", "M1", ";", "M2", ";", "so", "then", ",", "{I}"]},
    "between_o2": {"order": "outer_first", "parts": ["{O}", ";", "so", "then", ",", "M1", ";", "M2", ",", "{I}"]},
    "between_i1": {"order": "inner_first", "parts": ["{I}", ",", "M1", ";", "M2", ";", "and", "then", ",", "{O}"]},
    "between_i2": {"order": "inner_first", "parts": ["{I}", ";", "and", "then", ",", "M1", ";", "M2", ",", "{O}"]},
    # amendment 001: additional 'between' frames (function-word padding only) so outer-near and inner-near frames are equally numerous
    # (o3/o4/i3/i4: padding on the far-event side is long enough that BOTH slots of a two-modifier item are nearer the OUTER trigger)
    "between_o3": {"order": "outer_first", "parts": ["{O}", ":", "M1", "and", "M2", ";", "and", "so", "then", "later", "again", "soon", ",", "{I}"]},
    "between_o4": {"order": "outer_first", "parts": ["{O}", ",", "M1", ",", "M2", ";", "and", "later", "so", "then", "again", "soon", ",", "{I}"]},
    "between_i3": {"order": "inner_first", "parts": ["{I}", ";", "so", "and", "then", "later", "again", ",", "M1", "and", "M2", ":", "{O}"]},
    "between_i4": {"order": "inner_first", "parts": ["{I}", ";", "later", "and", "so", "then", "again", ",", "M1", ",", "M2", ",", "{O}"]},
    # ---- V1.1 additions (development protocol §5-§8) ----
    # before-both-event variants (more phrasings of the before_i geometry; modifiers precede both events, inner-first)
    "before_i3":  {"order": "inner_first", "parts": ["M1", "and", "then", "M2", ";", "{I}", "is", "for", "{O}"]},
    "before_i4":  {"order": "inner_first", "parts": ["first", "M1", ",", "M2", ",", "then", "{I}", "to", "{O}"]},
    # STRADDLE frames: one slot between the events, one slot outside on the NON-head side. All four attachment combinations (OO, OI, IO, II) are
    # projective here, so mixed-parent items can be orientation-balanced WITHIN a frame (no slot -> parent shortcut).
    # outer-first: {O} .. M1 .. {I} .. M2 ; M1 (between) is nearer O in every variant, M2 (after I) is nearer I -> one O-near + one I-near slot each
    "straddle_o1": {"order": "outer_first", "parts": ["{O}", ",", "M1", ";", "and", "so", "then", "later", ",", "{I}", ",", "M2"]},
    "straddle_o2": {"order": "outer_first", "parts": ["{O}", ":", "M1", ";", "so", "then", "again", "soon", ",", "{I}", ";", "M2"]},
    "straddle_o3": {"order": "outer_first", "parts": ["{O}", "M1", ",", "and", "after", "that", "then", ",", "{I}", "and", "M2"]},
    "straddle_o4": {"order": "outer_first", "parts": ["{O}", ";", "M1", ":", "next", "and", "then", "so", ";", "{I}", ":", "M2"]},
    # inner-first: M1 .. {I} .. M2 .. {O} ; M1 precedes BOTH events (before-both geometry, nearer I); M2 (between) is nearer O in every variant
    "straddle_i1": {"order": "inner_first", "parts": ["M1", ",", "{I}", ";", "and", "so", "then", "later", ",", "M2", ",", "{O}"]},
    "straddle_i2": {"order": "inner_first", "parts": ["M1", ";", "{I}", ";", "so", "then", "again", "soon", ":", "M2", ";", "{O}"]},
    "straddle_i3": {"order": "inner_first", "parts": ["M1", "and", "{I}", ",", "after", "that", "and", "then", ",", "M2", "{O}"]},
    "straddle_i4": {"order": "inner_first", "parts": ["M1", ":", "{I}", ";", "next", "and", "then", "so", ";", "M2", ":", "{O}"]}}
STRADDLE_FRAMES = sorted(f for f in FRAMES if f.startswith("straddle"))
BEFORE_BOTH_FRAMES = sorted(f for f in FRAMES if f.startswith("before_i") or f.startswith("straddle_i"))   # frames with a modifier slot before both events
# (split frames with a slot outside the event span on the head side were REMOVED before generation: a single modifier there can only attach to
#  the head (the other attachment is non-projective), i.e. position rather than the tag would determine attachment)
# amendment 001: frames are sampled UNIFORMLY (no oversampling); nearest-event balance is a bounded band per cell
NEAREST_BAND = 0.625                               # per cell, neither nearest value may exceed 62.5 % of the cell quota  (=> 37.5 % <= outer-near <= 62.5 %)
SELECT_BAND = 0.60                                 # selection-time target (stricter than the audited 0.625 so the final corpus lands inside the band)
# per frame, two-modifier attachment patterns (running-count caps). Only ONE mixed orientation is projective per frame, so any mixed share c biases
# slot attachment to (1+c)/2; c = 0.10 bounds it at 55 %. Same-outer / same-inner are kept equal (0.45 each).
MIXED_PATTERN_CAP = 0.10          # V1-type (single-orientation) frames
SAME_PATTERN_CAP = 0.45
ONE_MOD_ATTACH_CAP = 0.55                          # per frame, single-modifier items: neither attachment above 55 % (running count)
# ---------------- sizes / seeds ----------------
SEED = 20260926
# V1.1 splits: ordinary TRAIN / ID_VAL / ID_TEST (same quota sampler, disjoint items) + ID_PAIR (the former pair-structured test; secondary diagnostic)
SIZES = {"train": 5600, "id_val": 1000, "id_test": 1000, "id_pair_pairs": 500, "recomb_pairs_per_relation": 80, "surface_recomb_pairs_per_relation": 40}
# V1.1 development candidates: target MIXED-parent fraction among two-modifier TRAIN items (bands per protocol §5.2)
CANDIDATES = {"C20": {"mixed_target": 0.20, "band": [0.175, 0.225]}, "C30": {"mixed_target": 0.30, "band": [0.275, 0.325]}, "C40": {"mixed_target": 0.40, "band": [0.375, 0.425]}}
V1_FRAME_MIXED_CAP = 0.10          # single-orientation frames keep the V1 cap (their only projective mixed orientation would bias the slot)


def straddle_mixed_share(candidate):
    """per-straddle-frame mixed share m_s so that the overall two-modifier mixed fraction hits the target:
       t = (S*m_s + O*V1_FRAME_MIXED_CAP) / (S + O)  with frames sampled uniformly (S straddle frames, O other frames)"""
    S = len(STRADDLE_FRAMES); O = len(FRAMES) - S; t = CANDIDATES[candidate]["mixed_target"]
    return min(0.95, max(0.0, (t * (S + O) - O * V1_FRAME_MIXED_CAP) / S))
# ---------------- Amendment D0-2 (2026-09-25, user-approved, before D0 round 2): orientation strata ----------------
ORIENTATION_LEVELS = ("frame", "relation_pair", "constructor_pair", "modifier_order_family", "format_family")


def orientation_status(meta):
    """mixed two-modifier item -> ('ELIGIBLE', None) if BOTH mixed orientations of its (frame, slot relations, outer, inner) are projective and
    TRAIN-valid; else ('STRUCTURALLY_ONE_SIDED', reason): PROJECTIVITY (V1-type frame: one projective mixed orientation), VALIDITY (the flipped
    orientation puts a relation on a constructor where the frozen matrix forbids it), WITHHELD (flip valid but a withheld RECOMB cell).
    Derivability of the flipped ELIGIBLE item is verified by the D0 audit (failures are reclassified DERIVABILITY there)."""
    m1, m2 = meta["mods"]; O, I = meta["outer"], meta["inner"]
    if meta["frame"] not in STRADDLE_FRAMES: return "STRUCTURALLY_ONE_SIDED", "PROJECTIVITY"
    flip = [(m1["rel"], I if m1["attach"] == "outer" else O), (m2["rel"], I if m2["attach"] == "outer" else O)]
    if all(train_cell(r, c) for r, c in flip): return "ELIGIBLE", None
    return "STRUCTURALLY_ONE_SIDED", ("VALIDITY" if not all(valid(r, c) for r, c in flip) else "WITHHELD")


def orientation_strata(meta):
    """audit / balancing strata of a mixed item (slot order M1, M2)"""
    m1, m2 = meta["mods"]
    return {"frame": meta["frame"], "relation_pair": m1["rel"] + ">" + m2["rel"], "constructor_pair": meta["outer"] + ">" + meta["inner"],
            "modifier_order_family": "M1_between__M2_after_inner" if meta["frame"].startswith("straddle_o") else "M1_before_both__M2_between",
            "format_family": m1["fmt"] + "/" + m2["fmt"]}


P_TWO_MOD = 0.5                       # fraction of items with two modifiers (rest: one)
POOL_PER_SPLIT = 12                   # candidate pool multiplier


def install():
    """install the ontology into the (vendored, unchanged) typed-composition engine's data tables"""
    C.TYPES.clear(); C.TYPES.update({**{e: "V" for e in EVENTS}, "PERSON": "E", "TIME": "T", "PLACE": "L", "TOPIC": "X"})
    C.SIG.clear(); C.SIG.update({"TODO": ("V", "V"), "WHO": ("V", "E"), "RECIPIENT": ("V", "E"), "WHEN": ("V", "T"), "WHERE": ("V", "L"), "TOPIC": ("V", "X")})
    C.ROLES[:] = sorted(C.SIG)
    C.PAYLOAD_CLASSES.clear(); C.PAYLOAD_CLASSES.update({"PERSON", "TIME", "PLACE", "TOPIC"})
    C.LEX.clear()
    for k, w in TRIG.items(): C.LEX[w] = (k, None)
    for cls, vals in (("PERSON", PERSONS), ("TIME", TIMES), ("PLACE", PLACES), ("TOPIC", TOPICS)):
        for v in vals: C.LEX[v] = (cls, v)


install()


def frozen_matrix():
    cells = {}
    for r in PRIMARY:
        for c in EVENTS:
            cells[f"{r}|{c}"] = {"valid": valid(r, c), "withheld": (r, c) in WITHHELD_CELLS, "position": "OUTER" if c in OUTER else "INNER",
                                 "exclusion_reason": EXCLUSION_REASONS.get((r, c))}
    contrasts = {r: {"valid_outer": [c for c in OUTER if valid(r, c)], "valid_inner": [c for c in INNER if valid(r, c)],
                     "attachment_contrast_pairs": sum(valid(r, o) for o in OUTER) * sum(valid(r, i) for i in INNER),
                     "train_outer": [c for c in OUTER if train_cell(r, c)], "train_inner": [c for c in INNER if train_cell(r, c)], "withheld": list(WITHHELD[r])} for r in PRIMARY}
    return {"corpus": CORPUS, "primary_relations": PRIMARY, "infrastructure_relations": ["TODO"], "coarse_signatures": {r: list(C.SIG[r]) for r in C.ROLES},
            "shared_argument_type": {"PERSON (E)": ["WHO", "RECIPIENT"]}, "meanings": MEANING, "subgroups_descriptive": SUBGROUPS, "cells": cells, "per_relation": contrasts,
            "semantic_notes": ["WHO = agent/initiator; the predecessor's overloaded WHO (object vs agent by template) is intentionally NOT preserved",
                               "WHERE = location at which the event itself occurs; never SOURCE / DESTINATION / visit target / message origin",
                               "attachment is expressed ONLY by the coindexation tag naming the parent's tag; every modifier's parent is therefore unambiguous in the surface"]}
