"""PDX curriculum catalogue (spec §47-§49): the frozen parent families (scenarios/catalog.py, unchanged) + one family from the spec example
(close_oldest_open_request, spec §23; frozen primitives only: FIND / SORT / FIRST / SET_STATUS / RETURN). Each family has a registered
natural-language GOAL shown to the teacher (a behavioural description, never an AST / trace), and DEV / LOCKED request templates for
post-handoff reuse (disjoint sets, spec §41)."""
import copy
import catalog as CAT

FAMILIES = copy.deepcopy(CAT.FAMILIES)
FAMILIES["close_oldest_open_request"] = {"params": {"person": "PERSON"}, "gold": """PROCEDURE close_oldest_open_request(person:PERSON)
$v0 = FIND REQUEST WHERE SELF.WHO={person} STATUS=OPEN
$v1 = SORT $v0 WHEN
$v2 = FIRST $v1
SET_STATUS $v2 CLOSED
RETURN $v2
END""", "dev": ["close the earliest open request from {person}", "shut {person}'s first still-open request"], "locked": ["finish off the oldest open request by {person}", "close {person}'s open request that comes first in time"]}
COMPOSITE = copy.deepcopy(CAT.COMPOSITE)

GOALS = {
 "calls_with": "Given a person, return all the calls with that person.",
 "count_open_calls_with": "Given a person, return how many of the calls with that person are still open.",
 "close_calls_with": "Given a person, mark every call with that person as closed, then return how many calls there were.",
 "move_last_reminder_and_return_call_person": "Given a time, move the most recent reminder to that time, then return the person that the call it reminds about is with.",
 "retarget_last_email": "Given a person, change the most recent email so that it is addressed to that person, and return that email.",
 "replace_visit_location": "Given a place, move the most recent visit to that place and return the visit.",
 "call_people_at": "Given a time, return the list of people on the calls scheduled at that time.",
 "email_topic_report": "Group all emails by their recipient and return a report of the topics for each recipient.",
 "count_requests_by_at": "Given a person and a time, return how many requests that person made for that time.",
 "close_open_emails_to": "Given a person, close all still-open emails addressed to that person and return those emails.",
 "person_on_call_at": "Given a time, return the person on the first call scheduled at that time.",
 "count_calls_with": "Given a person, return how many calls there are with that person.",
 "move_visit_and_parent": "Given a place, move the most recent visit and also the event it belongs to (its parent) to that place, and return the visit.",
 "close_oldest_open_request": "Given a person, take that person's open requests, sort them by time, close the first one, and return it.",
 "__composite": "Given a time, find the person on the first call at that time (the saved skill person_on_call_at does this), then return how many calls there are with that person (the saved skill count_calls_with does this).",
}



# ---- HTG additions (relation-sensitive + over-constraint probes; frozen primitives only) ----
FAMILIES["all_requests_by"] = {"params": {"person": "PERSON"}, "gold": """PROCEDURE all_requests_by(person:PERSON)
$v0 = FIND REQUEST WHERE SELF.WHO={person}
RETURN $v0
END""", "dev": ["list every request {person} has made", "which requests did {person} make"], "locked": ["show all of {person}'s requests, open or not", "everything {person} requested"]}
FAMILIES["count_emails_to"] = {"params": {"person": "PERSON"}, "gold": """PROCEDURE count_emails_to(person:PERSON)
$v0 = FIND EMAIL WHERE SELF.RECIPIENT={person}
$v1 = COUNT $v0
RETURN $v1
END""", "dev": ["how many emails went to {person}", "count the emails addressed to {person}"], "locked": ["number of emails sent to {person}", "email count for recipient {person}"]}
FAMILIES["emails_about"] = {"params": {"topic": "TOPIC"}, "gold": """PROCEDURE emails_about(topic:TOPIC)
$v0 = FIND EMAIL WHERE SELF.TOPIC={topic}
RETURN $v0
END""", "dev": ["which emails are about {topic}", "show me the emails on {topic}"], "locked": ["emails concerning {topic}", "find every email whose topic is {topic}"]}
FAMILIES["count_visits_in"] = {"params": {"place": "PLACE"}, "gold": """PROCEDURE count_visits_in(place:PLACE)
$v0 = FIND VISIT WHERE SELF.WHERE={place}
$v1 = COUNT $v0
RETURN $v1
END""", "dev": ["how many visits are in {place}", "count the visits at {place}"], "locked": ["number of visits located in {place}", "visit count for {place}"]}
GOALS.update({
 "all_requests_by": "Given a person, return all the requests that person made, whether open or closed.",
 "count_emails_to": "Given a person, return how many emails are addressed to that person.",
 "emails_about": "Given a topic, return all the emails about that topic.",
 "count_visits_in": "Given a place, return how many visits there are in that place.",
})


def spec(fam): return COMPOSITE if fam == "__composite" else FAMILIES[fam]


def gold_text(fam, name):
    g = spec(fam)["gold"]; old = COMPOSITE["name"] if fam == "__composite" else fam
    return g.replace(f"PROCEDURE {old}(", f"PROCEDURE {name}(", 1)
