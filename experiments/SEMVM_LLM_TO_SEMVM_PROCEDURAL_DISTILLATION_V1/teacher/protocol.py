"""Teacher protocol V1 (spec §16-§22, §50; spec/GROQ_TEACHER_PROTOCOL_V1.json + spec/GROQ_TEACHER_CAPABILITY_CARD_V1.json).
The capability card is generated from the frozen primitive inventory / ontology and the student's ACTIVE procedures. It never contains a
gold procedure, gold trace, expected action sequence, verifier case or locked annotation (spec §16, §21, §52). Its phrasing examples use only
MESSAGE / NOTE / PLAN events, which no curriculum target uses."""
import json, re, os, hashlib
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
VERSION = "PDX_TEACHER_PROTOCOL_V1"
BUDGET = {"max_teacher_turns_per_demonstration": 8, "max_clarification_exchanges_per_instruction": 2, "max_demonstrations_per_target": 3}   # spec §19

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
- use one of the student's saved skills by its exact name                                           ("Use messages_to for that person.")
- return the final result of the skill                                                              ("Return the count.")
The student CANNOT send, text, phone, email, print, browse, save files, schedule new events, or do arithmetic beyond counting.

HOW TO WRITE A DEMONSTRATION
EXAMPLE: <input>=<value>, <input>=<value>      (the example values you use for the skill's inputs in this demonstration)
STEP: <one instruction>
STEP: <one instruction>
...
- Use concrete example values (never placeholders). Use only values from VALUES.
- Refer to earlier results with words like "them", "it", "those calls", "the count".
- The last STEP must return the skill's result.
- Write nothing except the EXAMPLE line and STEP lines.

WHEN THE STUDENT ASKS YOU SOMETHING
- If it asks you to rephrase an instruction, reply only with the replacement STEP line(s) for that instruction.
- If it asks which earlier result you mean, reply with one line: ANSWER: <short noun phrase, e.g. "the people" or "the calls">.
- If it asks for another demonstration, reply with a new EXAMPLE line (different example values) and a complete list of STEP lines."""

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
