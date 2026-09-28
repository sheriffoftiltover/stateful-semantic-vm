"""HTG evaluator-side lesson judge (spec §17, §31, §63-§65). EVALUATION ONLY: it sees the registered goal, the gold procedure and the teacher's
visible lesson lines, and labels whether the lesson, read literally, teaches exactly the target behaviour. Its output never reaches the student,
the teacher or the grounder (own prompt, own requests, own cache namespace evaluator/judge_responses/). Runs before the hosted teardown.
It is combined with a deterministic lexical rule (unrequested status predicate) that alone defines TEACHER_UNREQUESTED_CONSTRAINT_RATE."""
import os, sys, re, json
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, "teacher")]
import client as CL

GEN = {"reasoning_effort": "low", "max_tokens": 4096}
KINDS = ["UNREQUESTED_CONSTRAINT", "WRONG_SKILL", "MISSING_STEP", "WRONG_STEP", "WRONG_ARGUMENT", "WRONG_RELATION", "UNSUPPORTED", "AMBIGUOUS"]
STATUS_WORDS = re.compile(r"(?i)\b(open|opened|closed|still|unresolved|pending|outstanding|active|not (?:yet )?(?:closed|done|finished|resolved))\b")

SYSTEM = '''You are an EVALUATOR of teaching lessons for a small Semantic VM. You are given a registered skill goal, the reference procedure that
implements it, the example values used, and the lesson lines a teacher wrote. Decide whether the lesson, read LITERALLY, describes exactly the
reference behaviour for these example values: the same searches (event type, relations, values, status conditions), the same operations in an
order with the same effect, and the same returned result. Paraphrase is fine. Harmless reordering with identical effect is fine.
Unfaithful: an added filter / status condition / constant / ordering the goal does not require; a missing or wrong step; a wrong relation
(e.g. "with X" where the reference uses the recipient); a wrong value; a different skill. Answer with one JSON object only:
{"faithful": true|false, "issues": [{"kind": one of ''' + json.dumps(KINDS) + ''', "line": <1-based line number or null>, "note": "..."}]}'''


def lexical_unrequested(goal, lines):
    """deterministic: a status predicate in the lesson when the registered goal states none"""
    if STATUS_WORDS.search(goal): return []
    return [i + 1 for i, l in enumerate(lines) if STATUS_WORDS.search(l)]


def judge(goal, gold, example, lines):
    user = f"GOAL: {goal}\nREFERENCE PROCEDURE:\n{gold}\nEXAMPLE VALUES: {json.dumps(example)}\nLESSON LINES:\n" + "\n".join(f"{i + 1}. {l}" for i, l in enumerate(lines))
    r = CL.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], gen=GEN, role="judge", meta={"kind": "JUDGE"})
    t = r["text"]; i, j = t.find("{"), t.rfind("}")
    try: out = json.loads(t[i:j + 1]); ok = bool(out.get("faithful")); iss = [x for x in out.get("issues") or [] if isinstance(x, dict)]
    except Exception: return {"faithful": None, "issues": [], "parse_error": True, "request_hash": r["provenance"].get("request_hash")}
    return {"faithful": ok, "issues": iss, "request_hash": r["provenance"].get("request_hash"), "cached": r["cached"]}
