"""Registered procedure families (Amendment 001), expressed ONLY in the frozen END_TO_END_POC ontology + STATUS + REPORT.
Each family: gold procedure text (independent of the discovery implementation; procedure/ never imports scenarios/), parameter classes, and
the paraphrase templates used for controlled natural-language REQUESTs (DEV and LOCKED_TEST use DISJOINT template sets, spec §71).
None of these families appears in the LLM few-shot prompts (procedure/llm.py uses MESSAGE / NOTE families only)."""
FAMILIES = {
  "calls_with": {"params": {"person": "PERSON"}, "gold": """PROCEDURE calls_with(person:PERSON)
$v0 = FIND CALL WHERE SELF.WHO={person}
RETURN $v0
END""", "dev": ["which calls are with {person}", "show me the calls with {person}"], "locked": ["list every call involving {person}", "find {person} calls"]},
  "count_open_calls_with": {"params": {"person": "PERSON"}, "gold": """PROCEDURE count_open_calls_with(person:PERSON)
$v0 = FIND CALL WHERE SELF.WHO={person} STATUS=OPEN
$v1 = COUNT $v0
RETURN $v1
END""", "dev": ["how many open calls with {person}", "count the open calls for {person}"], "locked": ["number of still open calls with {person}", "open call count for {person}"]},
  "close_calls_with": {"params": {"person": "PERSON"}, "gold": """PROCEDURE close_calls_with(person:PERSON)
$v0 = FIND CALL WHERE SELF.WHO={person}
FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED
$v2 = COUNT $v0
RETURN $v2
END""", "dev": ["close all the calls with {person}", "mark calls with {person} as closed"], "locked": ["close out every call with {person}", "shut the calls involving {person}"]},
  "move_last_reminder_and_return_call_person": {"params": {"time": "TIME"}, "gold": """PROCEDURE move_last_reminder_and_return_call_person(time:TIME)
$v0 = FIND_LAST REMINDER
UPDATE $v0 WHEN={time}
$v1 = CHILD $v0
$v2 = GET $v1 WHO
RETURN $v2
END""", "dev": ["move my last reminder to {time} and tell me who the call is with", "reschedule the last reminder to {time} and return the call person"], "locked": ["push the latest reminder to {time}, who is its call with", "set the last reminder time to {time} and report the caller"]},
  "retarget_last_email": {"params": {"person": "PERSON"}, "gold": """PROCEDURE retarget_last_email(person:PERSON)
$v0 = FIND_LAST EMAIL
UPDATE $v0 RECIPIENT={person}
RETURN $v0
END""", "dev": ["send the last email to {person} instead", "retarget the last email to {person}"], "locked": ["address my latest email to {person}", "change the last email recipient to {person}"]},
  "replace_visit_location": {"params": {"place": "PLACE"}, "gold": """PROCEDURE replace_visit_location(place:PLACE)
$v0 = FIND_LAST VISIT
UPDATE $v0 WHERE={place}
RETURN $v0
END""", "dev": ["move the last visit to {place}", "change the visit location to {place}"], "locked": ["the latest visit should be in {place}", "relocate my last visit to {place}"]},
  "call_people_at": {"params": {"time": "TIME"}, "gold": """PROCEDURE call_people_at(time:TIME)
$v0 = FIND CALL WHERE PARENT.WHEN={time}
$v1 = SELECT $v0 WHO
RETURN $v1
END""", "dev": ["who do I call at {time}", "list the people on calls at {time}"], "locked": ["whom am I phoning at {time}", "people I call at {time}"]},
  "email_topic_report": {"params": {}, "gold": """PROCEDURE email_topic_report()
$v0 = FIND EMAIL
$v1 = GROUP $v0 RECIPIENT
$v2 = REPORT $v1 TOPIC
RETURN $v2
END""", "dev": ["give me the email topic report", "report email topics by recipient"], "locked": ["summarize my email topics per recipient", "email topics grouped by recipient please"]},
  "count_requests_by_at": {"params": {"person": "PERSON", "time": "TIME"}, "gold": """PROCEDURE count_requests_by_at(person:PERSON, time:TIME)
$v0 = FIND REQUEST WHERE SELF.WHO={person} SELF.WHEN={time}
$v1 = COUNT $v0
RETURN $v1
END""", "dev": ["how many requests by {person} at {time}", "count requests from {person} at {time}"], "locked": ["number of requests {person} made for {time}", "requests by {person} at {time} count"]},
  "close_open_emails_to": {"params": {"person": "PERSON"}, "gold": """PROCEDURE close_open_emails_to(person:PERSON)
$v0 = FIND EMAIL WHERE SELF.RECIPIENT={person} STATUS=OPEN
FOR $v1 IN $v0 : SET_STATUS $v1 CLOSED
RETURN $v0
END""", "dev": ["close the open emails to {person}", "finish all open emails for {person}"], "locked": ["mark open emails addressed to {person} closed", "wrap up the open emails to {person}"]},
  "person_on_call_at": {"params": {"time": "TIME"}, "gold": """PROCEDURE person_on_call_at(time:TIME)
$v0 = FIND CALL WHERE PARENT.WHEN={time}
$v1 = FIRST $v0
$v2 = GET $v1 WHO
RETURN $v2
END""", "dev": ["who is on the call at {time}", "person on my {time} call"], "locked": ["who am I calling at {time}", "the {time} call is with whom"]},
  "count_calls_with": {"params": {"person": "PERSON"}, "gold": """PROCEDURE count_calls_with(person:PERSON)
$v0 = FIND CALL WHERE SELF.WHO={person}
$v1 = COUNT $v0
RETURN $v1
END""", "dev": ["how many calls with {person}", "count calls involving {person}"], "locked": ["number of calls with {person}", "total calls with {person}"]},
  "move_visit_and_parent": {"params": {"place": "PLACE"}, "gold": """PROCEDURE move_visit_and_parent(place:PLACE)
$v0 = FIND_LAST VISIT
UPDATE $v0 WHERE={place}
$v1 = PARENT $v0
UPDATE $v1 WHERE={place}
RETURN $v0
END""", "dev": ["move the last visit and its parent to {place}", "put the visit and its parent in {place}"], "locked": ["relocate the latest visit plus parent to {place}", "both the visit and its parent go to {place}"]},
}
# composition (P7 / P12): P3(time) = count_calls_with(person_on_call_at(time))
COMPOSITE = {"name": "count_calls_for_time_person", "params": {"time": "TIME"}, "gold": """PROCEDURE count_calls_for_time_person(time:TIME)
$v0 = CALL person_on_call_at time={time}
$v1 = CALL count_calls_with person=$v0
RETURN $v1
END""", "dev": ["how many calls with the person on my {time} call", "count calls with whoever is on the {time} call"], "locked": ["number of calls with the person I call at {time}", "total calls with the {time} call person"]}
