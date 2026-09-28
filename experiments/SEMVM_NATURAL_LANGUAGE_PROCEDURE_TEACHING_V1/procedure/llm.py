"""Client for the frozen LLM service + the two NON-AUTHORITATIVE LLM roles (Amendment 001):
  propose(name, traces)  -> procedure text proposal (parsed by lang.parse_procedure; judged ONLY by validate + verify)
  retrieval: score(request, procedure names) + argument / plan generation (judged by deterministic checks in retrieval.py)
Few-shot examples use procedure families that are NOT in the registered scenario catalogue (anti-cheating, spec §70). Every call is logged."""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import lang as L
URL = os.environ.get("SEMVM_LLM_URL", "http://127.0.0.1:8765"); CALLS = []

PROPOSE_FEWSHOT = """# A trace is a sequence of VM steps executed with concrete values. Write the reusable procedure: keep the same steps,
# replace each value that should vary with a {parameter}, keep constants, and end with END.

TRACE 1 (declared example values: person=Kevin)
$a = FIND MESSAGE WHERE SELF.RECIPIENT=Kevin
$b = COUNT $a
RETURN $b
PROCEDURE count_messages_to(person:PERSON)
$v0 = FIND MESSAGE WHERE SELF.RECIPIENT={person}
$v1 = COUNT $v0
RETURN $v1
END

TRACE 1
$x = FIND_LAST NOTE
UPDATE $x TOPIC=lease
RETURN $x
TRACE 2
$y = FIND_LAST NOTE
UPDATE $y TOPIC=survey
RETURN $y
PROCEDURE set_last_note_topic(topic:TOPIC)
$v0 = FIND_LAST NOTE
UPDATE $v0 TOPIC={topic}
RETURN $v0
END

TRACE 1 (declared example values: place=Oslo)
$n = FIND NOTE WHERE SELF.WHERE=Oslo STATUS=OPEN
FOR $e IN $n : SET_STATUS $e CLOSED
RETURN $n
PROCEDURE close_open_notes_in(place:PLACE)
$v0 = FIND NOTE WHERE SELF.WHERE={place} STATUS=OPEN
FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED
RETURN $v0
END

"""

RETRIEVE_FEWSHOT = """# Map a request to one call of an available procedure. Arguments must be values that appear in the request.
# A call may take another call as an argument when the request needs a value that another procedure computes.

Available: count_messages_to(person:PERSON) -> INT ; person_visited_at(time:TIME) -> PERSON ; close_open_notes_in(place:PLACE) -> EVENT_LIST
Request: how many messages are going to Kevin
Call: count_messages_to(person=Kevin)
Request: close the open notes for Oslo
Call: close_open_notes_in(place=Oslo)
Request: count the messages to whoever I visit at dusk
Call: count_messages_to(person=person_visited_at(time=dusk))

"""


def _post(path, obj):
    t0 = time.time(); req = urllib.request.Request(URL + path, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=600).read()); CALLS.append({"path": path, "seconds": round(time.time() - t0, 3), "prompt_chars": len(obj.get("prompt", ""))}); return out


def info():
    return json.loads(urllib.request.urlopen(URL + "/frozen", timeout=600).read())


def trace_text(traces):
    out = []
    for i, t in enumerate(traces):
        d = t.get("declared") or {}
        out.append(f"TRACE {i + 1}" + (f" (declared example values: {', '.join(f'{k}={v}' for k, v in d.items())})" if d else ""))
        out += [L.fmt_step(s) for s in t["steps"]]
    return "\n".join(out)


def propose(name, traces):
    prompt = PROPOSE_FEWSHOT + trace_text(traces) + f"\nPROCEDURE {name}("
    text = _post("/generate", {"prompt": prompt, "max_new_tokens": 220, "stop": ["\nEND"]})["text"]
    return f"PROCEDURE {name}(" + text + "\nEND", prompt


def signature_line(procs): return " ; ".join(f"{p['name']}(" + ", ".join(f"{x['name']}:{x['type']}" for x in p["parameters"]) + f") -> {p.get('returns')}" for p in procs)


def score_names(request, procs):
    prompt = RETRIEVE_FEWSHOT + f"Available: {signature_line(procs)}\nRequest: {request}\nCall:"
    return _post("/score", {"prompt": prompt, "continuations": [f" {p['name']}(" for p in procs]})["logprobs"], prompt


def generate_call(request, procs, name):
    prompt = RETRIEVE_FEWSHOT + f"Available: {signature_line(procs)}\nRequest: {request}\nCall: {name}("
    return name + "(" + _post("/generate", {"prompt": prompt, "max_new_tokens": 60, "stop": ["\n"]})["text"], prompt
