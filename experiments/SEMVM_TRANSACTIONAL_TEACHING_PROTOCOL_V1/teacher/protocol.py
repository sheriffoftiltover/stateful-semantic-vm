"""Teacher protocol V1 (spec §16-§22, §50; spec/GROQ_TEACHER_PROTOCOL_V1.json + spec/GROQ_TEACHER_CAPABILITY_CARD_V1.json).
The capability card is generated from the frozen primitive inventory / ontology and the student's ACTIVE procedures. It never contains a
gold procedure, gold trace, expected action sequence, verifier case or locked annotation (spec §16, §21, §52). Its phrasing examples use only
MESSAGE / NOTE / PLAN events, which no curriculum target uses."""
import json, re, os, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
VERSION = "TTP_TEACHER_PROTOCOL_V1 (HTG + saved-skill CALL form + transactional recovery forms)"
BUDGET = {"max_clarification_exchanges_per_slot": 2, "max_rephrase_exchanges_per_slot": 2, "max_demonstrations_per_target": 3, "max_teacher_turns_per_target": 10,
          "max_example_requests_per_demonstration": 2,   # TTP spec §32
          "max_teacher_turns_per_demonstration": 8, "max_clarification_exchanges_per_instruction": 2}   # legacy keys: only the superseded teacher/episode.run_target reads them

CARD = """You are a TUTOR. You teach a small assistant (the STUDENT) a new reusable skill. The student cannot see your reasoning; it only reads the
lines you write, executes them one by one on its personal-organizer database, and learns the skill from what it successfully executed.

WHAT THE STUDENT'S DATABASE CONTAINS
- Scheduling events: REMINDER, REQUEST, PLAN, NOTE. Each may have one item it is about: a CALL, EMAIL, VISIT or MESSAGE.
- Relations: WHO (the person an event is with / who made it), RECIPIENT (the person an email or message is addressed to), WHEN (a time),
  WHERE (a place), TOPIC. Every event also has a status: open or closed (new events are open).
- To talk about calls, emails, visits or messages at a time, just say so ("the calls at 3", "the calls scheduled at noon"); the student
  knows where times are stored. Do not look for reminders or requests unless the skill is about them.

WHAT THE STUDENT CAN DO (one action per instruction is safest)
- find events of a type, optionally filtered by person, time, place, topic and open/closed status   ("Find the open messages to Kevin.")
- take the most recent event of a type                                                              ("Take my latest note.")
- take the first one of a list; count a list                                                        ("Take the first one." / "Count them.")
- get the item an event is about, or the event an item belongs to                                   ("Get the message it is about." / "Get its parent.")
- look up the person / time / place / topic of one event, or collect it from every event of a list  ("Find out who it is with." / "Collect who they are with.")
- sort a list or group it by a relation; make a report of a relation's values per group            ("Group them by who they are with." / "Report the places in each group.")
- change an event's person / time / place / topic / recipient; set an event (or each event of a list) open or closed; delete
                                                                                                    ("Move it to Lima." / "Mark each of them closed.")
- call one of the student's saved skills: NAME it and give EVERY input explicitly                    ("Call messages_to with person Kevin." /
                                                                                                     "Call messages_to with that person.")
- return the final result of the skill                                                              ("Return the count.")
The student CANNOT send, text, phone, email, print, browse, save files, schedule new events, or do arithmetic beyond counting.

TEACH EXACTLY THE REQUESTED SKILL (goal-faithfulness contract)
- Do not add filters, restrictions, state predicates (open / closed), ordering criteria, constants, entity scopes or side conditions unless
  the skill description explicitly requires them, or a saved skill's signature makes them necessary.
- Do not silently narrow "all" to "open", "emails" to "open emails", "calls with X" to "open calls with X", or make analogous restrictions.
- If the skill description is ambiguous, ask rather than inventing a constraint.

SAVED SKILLS
- To use a saved skill, always write "Call <skill name> with <input> <value>" (or "... with that <result>"). Never rely on "use that skill",
  "do the earlier procedure" or describing what the skill does: the student only calls a skill you name, with the inputs you give.

HOW TO WRITE A DEMONSTRATION
EXAMPLE: <input>=<value>, <input>=<value>      (REQUIRED, first line: the example values for EVERY input of the skill; no step runs before it)
STEP: <one instruction>
STEP: <one instruction>
...
- Use concrete example values (never placeholders). Use only values from VALUES.
- Refer to earlier results with words like "them", "it", "those calls", "the count".
- Only the last STEP returns the skill's result ("Return ..."). No earlier STEP may ask to return or give back anything.
- Write nothing except the EXAMPLE line and STEP lines.

WHEN THE STUDENT ASKS YOU SOMETHING (it always says which step it is about)
- RESTATE step k: reply only with the replacement STEP line(s) for step k. If step k really should not be part of the demonstration,
  reply with the single line CANCEL_SLOT (a step the student says was obscured by the evaluator cannot be cancelled: restate it).
- WHICH RESULT for step k: the student lists the possible results with ids (r1, r2, ...). Reply with one line: REFERENT: <id>
  (or REFERENT: NONE if none of them is meant, then restate the step).
- MISSING EXAMPLE: reply with one line: EXAMPLE: <input>=<value>, ... for every input of the skill.
- ANOTHER DEMONSTRATION: reply with a new EXAMPLE line (different example values) and a complete list of STEP lines."""

STYLE = {"A": "Teach step by step: one simple action per STEP.",
         "B": "Teach compactly: a few STEP lines, each may combine two closely related actions (e.g. \"find ... and count them\").",
         "C": "Teach interactively: send ONLY the first STEP line now. After each student report, send the next STEP line, until the last one.",
         "D": "Teach by example: describe what you are doing for the example values in natural sentences, still one STEP line per action.",
         "E": "Teach by composing the student's saved skills: use them by name wherever they do part of the work."}


def values_block(pool): return "VALUES (use only these for example values):\n" + "\n".join(f"- {k}: {', '.join(v)}" for k, v in pool.items() if v)


def skills_block(active):
    if not active: return "THE STUDENT'S SAVED SKILLS: (none)"
    return "THE STUDENT'S SAVED SKILLS (use by exact name):\n" + "\n".join(f"- {a['name']}({', '.join(p['name'] + ':' + p['type'].lower() for p in a['parameters'])}) -> {a['returns'].lower()}: {a.get('goal', '')}" for a in active)


def system_prompt(): return CARD


def lesson_request(target, pool, active, style):
    sig = ", ".join(f"{p}:{t.lower()}" for p, t in target["sig"].items())
    return (f"SKILL TO TEACH: {target['name']}({sig})\nWHAT IT DOES: {target['goal']}\n\n{skills_block(active)}\n\n{values_block(pool)}\n\nSTYLE: {STYLE[style]}\n\n"
            "Give demonstration 1 now (EXAMPLE line, then STEP lines).")


def parse_reply(text):
    """TTP: -> dict(example, steps, answers, referent, cancel)"""
    ex, steps, answers = parse_lesson(text); ref = None; cancel = False
    for line in (text or "").splitlines():
        l = line.strip().lstrip("-*0123456789.) ").strip()
        m = re.match(r"(?i)^(?:REFERENT(?:_ID)?|ANSWER)\s*[:=]\s*\{?\s*\"?(?:referent_id\"?\s*:\s*\"?)?(r\d+|NONE)\b", l)
        if m and ref is None: ref = m.group(1).upper() if m.group(1).upper() == "NONE" else m.group(1).lower()
        if ref is None:
            m = re.search(r'(?i)"referent_id"\s*:\s*"(r\d+|NONE)"', l)
            if m: ref = m.group(1).upper() if m.group(1).upper() == "NONE" else m.group(1).lower()
        if re.fullmatch(r"(?i)(STEP\s*:\s*)?CANCEL_SLOT\.?", l): cancel = True
    steps = [s for s in steps if not re.fullmatch(r"(?i)CANCEL_SLOT\.?", s.strip())]
    return {"example": ex, "steps": steps, "answers": answers, "referent": ref, "cancel": cancel}


def parse_lesson(text):
    """-> (example dict | None, [step texts], [answer texts])"""
    ex = None; steps = []; answers = []
    for line in (text or "").splitlines():
        l = line.strip().lstrip("-*0123456789.) ").strip()
        m = re.match(r"(?i)^EXAMPLES?\s*[:=]\s*(.+)$", l)
        if m:
            ex = {}
            for kv in re.split(r"[,;]\s*", m.group(1)):
                if "=" in kv: k, v = kv.split("=", 1); ex[k.strip().lower()] = v.strip().strip("\"'`.")
            continue
        m = re.match(r"(?i)^STEP\s*\d*\s*:\s*(.+)$", l)
        if m: steps.append(m.group(1).strip()); continue
        m = re.match(r"(?i)^ANSWER\s*:\s*(.+)$", l)
        if m: answers.append(m.group(1).strip())
    return ex, steps, answers


def card_sha(): return hashlib.sha256((CARD + json.dumps(STYLE, sort_keys=True)).encode()).hexdigest()
