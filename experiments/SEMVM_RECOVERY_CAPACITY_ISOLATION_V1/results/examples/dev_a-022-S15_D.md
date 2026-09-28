# dev_a-022-S15 — arm D (dev_a)

Stratum S15: sort (spec §23 example family). Arm D: TEACHER lesson, recovery HOSTED, grounder HOSTED, teacher max_tokens 8192.

Target `close_oldest_open_request(person:PERSON)` — goal: Given a person, take that person's open requests, sort them by time, close the first one, and return it.

Reference (gold) procedure:
```
PROCEDURE close_oldest_open_request(person:PERSON)
$v0 = FIND REQUEST WHERE SELF.WHO={person} STATUS=OPEN
$v1 = SORT $v0 WHEN
$v2 = FIRST $v1
SET_STATUS $v2 CLOSED
RETURN $v2
END
```

## 1. Hosted teacher messages (visible dialogue; the teacher's hidden reasoning is not part of the protocol)

### target close_oldest_open_request — final status ACTIVE

**System prompt (teacher card):** see `teacher/protocol.py` CARD (sha in `locks/FINAL_CONFIG_FREEZE.json`).

**STUDENT → teacher:**
```
SKILL TO TEACH: close_oldest_open_request(person:person)
WHAT IT DOES: Given a person, take that person's open requests, sort them by time, close the first one, and return it.

THE STUDENT'S SAVED SKILLS: (none)

VALUES (use only these for example values):
- people: Frank, Grace, Peggy, Yves
- times: 7, 4:30, 2:45, 12
- places: Seoul, Delhi, Madrid, Tokyo
- topics: schedule, report, survey, budget

STYLE: Teach compactly: a few STEP lines, each may combine two closely related actions (e.g. "find ... and count them").

Give demonstration 1 now (EXAMPLE line, then STEP lines).
```
**TEACHER:**
```
EXAMPLE: person=Frank
STEP: Find the open requests with person Frank and sort them by when.
STEP: Take the first one.
STEP: Mark it closed.
STEP: Return it.
```
**STUDENT → teacher:**
```
For step 2 ("Take the first one.") more than one earlier result fits:
  r1: the requests found (who=Frank, status open) (1 element), from the step "Find the open requests with person Frank and sort them by when."
  r2: r1 sorted by when (1 element), from the step "Find the open requests with person Frank and sort them by when."
Reply with one line: REFERENT: <id>
```
**TEACHER:**
```
REFERENT: r2
```

Teacher-call provenance:
- LESSON: role initial_teacher, route HOSTED, request 83e63f83143728e1…, cached False, tokens in/out 1285/1129, finish stop, latency 8.619 s, reasoning chars 4566
- CLARIFY_REFERENCE: role recovery_teacher, route HOSTED, request 5428bd6218eed1de…, cached False, tokens in/out 1427/216, finish stop, latency 2.121 s, reasoning chars 825

## 2. Hosted-grounder outputs (one isolated request per line; raw envelope + deterministic checks)

### line `Find the open requests with person Frank and sort them by when.` (slot demo1-slot1, terminal_allowed=False, reference_choice=None) → **OK**
- attempt 1: status OK; feedback None
```json
{
  "status": "PLAN",
  "steps": [
    {
      "bind": "r1",
      "op": "FIND",
      "type": "REQUEST",
      "where": {
        "WHO": "Frank"
      },
      "status": "OPEN"
    },
    {
      "bind": "r2",
      "op": "SORT",
      "of": "r1",
      "by": "WHEN"
    }
  ]
}
```
  executed (parent step AST):
```
$r1 = FIND REQUEST WHERE SELF.WHO=Frank STATUS=OPEN
$r2 = SORT $r1 WHEN
```
### line `Take the first one.` (slot demo1-slot2, terminal_allowed=False, reference_choice=None) → **CLARIFY** (REFERENCE: reference for FIRST.of is ambiguous among ['r1', 'r2'])
- attempt 1: status CLARIFY; feedback None
```json
{"status": "PLAN", "steps": [{"bind": "r3", "op": "FIRST", "of": "r2"}]}
```
### line `Take the first one.` (slot demo1-slot2, terminal_allowed=False, reference_choice={'chosen': 'r2', 'offered': ['r1', 'r2']}) → **OK**
- attempt 1: status OK; feedback None
```json
{"status": "PLAN", "steps": [{"bind": "r3", "op": "FIRST", "of": "r2"}]}
```
  executed (parent step AST):
```
$r3 = FIRST $r2
```
### line `Mark it closed.` (slot demo1-slot3, terminal_allowed=False, reference_choice=None) → **OK**
- attempt 1: status OK; feedback None
```json
{"status": "PLAN", "steps": [{"op": "SET_STATUS", "target": "r3", "value": "CLOSED"}]}
```
  executed (parent step AST):
```
SET_STATUS $r3 CLOSED
```
### line `Return it.` (slot demo1-slot4, terminal_allowed=True, reference_choice=None) → **OK**
- attempt 1: status OK; feedback None
```json
{"status": "PLAN", "steps": [{"op": "RETURN", "value": "r3"}]}
```
  executed (parent step AST):
```
RETURN $r3
```

## 3. Transaction and slot ledger

Transaction record:
```json
[
 {
  "target": "close_oldest_open_request",
  "status": "ACTIVE",
  "demos": [
   {
    "index": 0,
    "states": [
     "NEW",
     "OPEN",
     "WAITING_FOR_GROUNDING",
     "WAITING_FOR_GROUNDING",
     "WAITING_FOR_CLARIFICATION",
     "WAITING_FOR_GROUNDING",
     "WAITING_FOR_GROUNDING",
     "WAITING_FOR_GROUNDING",
     "WAITING_FOR_GROUNDING",
     "READY_TO_COMMIT",
     "COMMITTED"
    ],
    "end": "VERIFIED",
    "end_detail": {},
    "learn": null,
    "events": [
     {
      "event": "CLARIFY_REFERENCE",
      "slot": "demo1-slot2",
      "offered": [
       "r1",
       "r2"
      ],
      "answer": "r2"
     }
    ],
    "example": {
     "person": "Frank"
    }
   }
  ]
 }
]
```
Slot ledger:
```json
[
 {
  "target": "close_oldest_open_request",
  "status": "ACTIVE",
  "demos": [
   {
    "index": 0,
    "slots": [
     {
      "slot_id": "demo1-slot1",
      "source": "TEACHER",
      "status": "RESOLVED",
      "original_text": "Find the open requests with person Frank and sort them by when.",
      "text": "Find the open requests with person Frank and sort them by when.",
      "replacement_for": null,
      "grounded_plan": [
       {
        "op": "FIND",
        "bind": "r1",
        "type": {
         "const": "REQUEST"
        },
        "where": [
         [
          "SELF",
          "WHO",
          {
           "const": "Frank"
          }
         ]
        ],
        "status": {
         "const": "OPEN"
        }
       },
       {
        "op": "SORT",
        "bind": "r2",
        "list": {
         "var": "r1"
        },
        "rel": "WHEN"
       }
      ],
      "clarification_count": 0,
      "rephrase_count": 0,
      "required": true,
      "lesson_index": 0,
      "family": "demo1-slot1",
      "displaced": false,
      "history": [
       {
        "status": "OK",
        "clarify_kind": null,
        "reason": ""
       }
      ],
      "reference_choice": null
     },
     {
      "slot_id": "demo1-slot2",
      "source": "TEACHER",
      "status": "RESOLVED",
      "original_text": "Take the first one.",
      "text": "Take the first one.",
      "replacement_for": null,
      "grounded_plan": [
       {
        "op": "FIRST",
        "bind": "r3",
        "list": {
         "var": "r2"
        }
       }
      ],
      "clarification_count": 1,
      "rephrase_count": 0,
      "required": true,
      "lesson_index": 1,
      "family": "demo1-slot2",
      "displaced": false,
      "history": [
       {
        "status": "CLARIFY",
        "clarify_kind": "REFERENCE",
        "reason": "reference for FIRST.of is ambiguous among ['r1', 'r2']"
       },
       {
        "status": "OK",
        "clarify_kind": null,
        "reason": ""
       }
      ],
      "reference_choice": {
       "chosen": "r2",
       "offered": [
        "r1",
        "r2"
       ]
      }
     },
     {
      "slot_id": "demo1-slot3",
      "source": "TEACHER",
      "status": "RESOLVED",
      "original_text": "Mark it closed.",
      "text": "Mark it closed.",
      "replacement_for": null,
      "grounded_plan": [
       {
        "op": "SET_STATUS",
        "obj": {
         "var": "r3"
        },
        "value": {
         "const": "CLOSED"
        }
       }
      ],
      "clarification_count": 0,
      "rephrase_count": 0,
      "required": true,
      "lesson_index": 2,
      "family": "demo1-slot3",
      "displaced": false,
      "history": [
       {
        "status": "OK",
        "clarify_kind": null,
        "reason": ""
       }
      ],
      "reference_choice": null
     },
     {
      "slot_id": "demo1-slot4",
      "source": "TEACHER",
      "status": "RESOLVED",
      "original_text": "Return it.",
      "text": "Return it.",
      "replacement_for": null,
      "grounded_plan": [
       {
        "op": "RETURN",
        "value": {
         "var": "r3"
        }
       }
      ],
      "clarification_count": 0,
      "rephrase_count": 0,
      "required": true,
      "lesson_index": 3,
      "family": "demo1-slot4",
      "displaced": false,
      "history": [
       {
        "status": "OK",
        "clarify_kind": null,
        "reason": ""
       }
      ],
      "reference_choice": null
     }
    ]
   }
  ]
 }
]
```

## 4. Committed traces (learning evidence admitted at COMMIT)

### close_oldest_open_request — example 1 (interaction dev_a-022-S15:close_oldest_open_request:d0:hdr), declared {'person': 'Frank'}
```
$r1 = FIND REQUEST WHERE SELF.WHO=Frank STATUS=OPEN
$r2 = SORT $r1 WHEN
$r3 = FIRST $r2
SET_STATUS $r3 CLOSED
RETURN $r3
```
result at commit: `{"event": "request:000011"}`

Student teaching-trace record `dev_a-022-S15_close_oldest_open_request_d0_hdr.json`: trace_sha256 d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb, start snapshot sha b4f1e465cde76905…, 5 utterance records

## 5. Learned procedure AST and 6. verification result

### candidate `proc_close_oldest_open_request_v1.json` — status **VERIFIED**
```json
"PROCEDURE close_oldest_open_request(person:PERSON)\n$v0 = FIND REQUEST WHERE SELF.WHO={person} STATUS=OPEN\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
AST (JSON):
```json
"PROCEDURE close_oldest_open_request(person:PERSON)\n$v0 = FIND REQUEST WHERE SELF.WHO={person} STATUS=OPEN\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
verifier: 20/20 tests passed; status VERIFIED; reason None
- static_validation: PASS 
- interface: PASS 
- replay_0: PASS 
- counterfactual_t0_0: PASS 
- counterfactual_t0_1: PASS 
- perturb_all_closed_t0_src: PASS 
- perturb_all_closed_t0_cf: PASS 
- perturb_alternate_closed_t0_src: PASS 
- perturb_alternate_closed_t0_cf: PASS 
- neg_missing_input: PASS 
- neg_wrong_type: PASS 
- neg_empty_result: PASS 
- neg_ambiguous_entity: PASS 
- neg_deleted_object: PASS 
- neg_empty_world_precondition: PASS 
- txn_inject_after_1: PASS 
- txn_inject_after_2: PASS 
- txn_inject_after_3: PASS 
- txn_inject_after_4: PASS 
- determinism: PASS 
### candidate `proc_close_oldest_open_request_v2.json` — status **REJECTED_FAILED_COUNTERFACTUAL**
```json
"PROCEDURE close_oldest_open_request()\n$v0 = FIND REQUEST WHERE SELF.WHO=Frank STATUS=OPEN\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
AST (JSON):
```json
"PROCEDURE close_oldest_open_request()\n$v0 = FIND REQUEST WHERE SELF.WHO=Frank STATUS=OPEN\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
verifier: 1/2 tests passed; status REJECTED_FAILED_COUNTERFACTUAL; reason None
- static_validation: PASS 
- interface: FAIL 
### candidate `proc_close_oldest_open_request_v3.json` — status **REJECTED_FAILED_COUNTERFACTUAL**
```json
"PROCEDURE close_oldest_open_request(person:PERSON)\n$v0 = FIND REQUEST WHERE SELF.WHO={person}\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
AST (JSON):
```json
"PROCEDURE close_oldest_open_request(person:PERSON)\n$v0 = FIND REQUEST WHERE SELF.WHO={person}\n$v1 = SORT $v0 WHEN\n$v2 = FIRST $v1\nSET_STATUS $v2 CLOSED\nRETURN $v2\nEND"
```
verifier: 5/6 tests passed; status REJECTED_FAILED_COUNTERFACTUAL; reason None
- static_validation: PASS 
- interface: PASS 
- replay_0: PASS 
- counterfactual_t0_0: PASS 
- counterfactual_t0_1: PASS 
- perturb_all_closed_t0_src: FAIL 

False-accept probes run against the same evidence (must be rejected):
```json
[
 {
  "target": "close_oldest_open_request",
  "variant": "FROZEN_VALUE",
  "status": "REJECTED_FAILED_COUNTERFACTUAL"
 },
 {
  "target": "close_oldest_open_request",
  "variant": "DROPPED_CONSTANT_FILTER",
  "status": "REJECTED_FAILED_COUNTERFACTUAL"
 }
]
```

## 7. ACTIVE DB record (`procedures.sqlite`, read-only)

### table `procedures` (3 rows)
columns: ['procedure_id', 'name', 'version', 'status', 'program_json', 'parameters_json', 'preconditions_json', 'postconditions_json', 'created_at', 'source_hash', 'program_hash', 'effect', 'returns', 'parent_version', 'change_reason', 'proposer']
```
proc:close_oldest_open_request:v1 | close_oldest_open_request | 1 | ACTIVE | {"body":[{"bind":"v0","op":"FIND","status":{"const":"OPEN"},"type":{"const":"REQUEST"},"where":[["SELF","WHO",{"param":"person"}]]},{"bind":"v1","list":{"var":"v0"},"op":"SORT","rel":"WHEN"},{"bind":"v2","list":{"var":"v1"},"op":"FIRST"},{"obj":{"var":"v2"},"op":"SET_STATUS","value":{"const":"CLOSED"}},{"op":"RETURN","value":{"var":"v2"}}],"name":"close_oldest_open_request","parameters":[{"name":"person","type":"PERSON"}]} | [{"name": "person", "type": "PERSON"}] | [] | [] | t | d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb | c93e9cea8c8d080e97e4499e5efe3ad8ce5d53a436763494cb5dcbac11894c48 | STATEFUL | EVENT | None | None | deterministic
proc:close_oldest_open_request:v2 | close_oldest_open_request | 2 | REJECTED_FAILED_COUNTERFACTUAL | {"body":[{"bind":"v0","op":"FIND","status":{"const":"OPEN"},"type":{"const":"REQUEST"},"where":[["SELF","WHO",{"const":"Frank"}]]},{"bind":"v1","list":{"var":"v0"},"op":"SORT","rel":"WHEN"},{"bind":"v2","list":{"var":"v1"},"op":"FIRST"},{"obj":{"var":"v2"},"op":"SET_STATUS","value":{"const":"CLOSED"}},{"op":"RETURN","value":{"var":"v2"}}],"name":"close_oldest_open_request","parameters":[]} | [] | [] | [] | t | d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb | e564142275538f4016f4df53e8b2d9077ab5f2deb0ec6eaac29aac8b004a6ad7 | None | None | None | None | external
proc:close_oldest_open_request:v3 | close_oldest_open_request | 3 | REJECTED_FAILED_COUNTERFACTUAL | {"body":[{"bind":"v0","op":"FIND","status":null,"type":{"const":"REQUEST"},"where":[["SELF","WHO",{"param":"person"}]]},{"bind":"v1","list":{"var":"v0"},"op":"SORT","rel":"WHEN"},{"bind":"v2","list":{"var":"v1"},"op":"FIRST"},{"obj":{"var":"v2"},"op":"SET_STATUS","value":{"const":"CLOSED"}},{"op":"RETURN","value":{"var":"v2"}}],"name":"close_oldest_open_request","parameters":[{"name":"person","type":"PERSON"}]} | [{"name": "person", "type": "PERSON"}] | [] | [] | t | d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb | 6144cf6db53ee1237ffe23ca05c0fa69134f7a4779af7321a6c05821a5a1f853 | None | None | None | None | external
```
### table `procedure_examples` (3 rows)
columns: ['procedure_id', 'interaction_id', 'role']
```
proc:close_oldest_open_request:v1 | dev_a-022-S15:close_oldest_open_request:d0:hdr | source
proc:close_oldest_open_request:v2 | dev_a-022-S15:close_oldest_open_request:d0:hdr | source
proc:close_oldest_open_request:v3 | dev_a-022-S15:close_oldest_open_request:d0:hdr | source
```
### table `procedure_tests` (20 rows)
columns: ['procedure_id', 'test_id', 'passed', 'result_json']
```
proc:close_oldest_open_request:v1 | static_validation | 1 | {"calls": [], "depth": 0, "effect": "STATEFUL", "primitive_calls": 5, "returns": "EVENT"}
proc:close_oldest_open_request:v1 | interface | 1 | {"person": "person"}
proc:close_oldest_open_request:v1 | replay_0 | 1 | {"got": {"event": "request:000011"}, "status": "OK", "want": {"event": "request:000011"}}
proc:close_oldest_open_request:v1 | counterfactual_t0_0 | 1 | {"args": {"person": "Grace"}, "got": ["OK", {"event": "request:000013"}], "ref": ["OK", {"event": "request:000013"}]}
proc:close_oldest_open_request:v1 | counterfactual_t0_1 | 1 | {"args": {"person": "Ivan"}, "got": ["NOT_FOUND", null], "ref": ["NOT_FOUND", null]}
proc:close_oldest_open_request:v1 | perturb_all_closed_t0_src | 1 | {"got": ["NOT_FOUND", null], "ref": ["NOT_FOUND", null]}
proc:close_oldest_open_request:v1 | perturb_all_closed_t0_cf | 1 | {"got": ["NOT_FOUND", null], "ref": ["NOT_FOUND", null]}
proc:close_oldest_open_request:v1 | perturb_alternate_closed_t0_src | 1 | {"got": ["OK", {"event": "request:000011"}], "ref": ["OK", {"event": "request:000011"}]}
proc:close_oldest_open_request:v1 | perturb_alternate_closed_t0_cf | 1 | {"got": ["OK", {"event": "request:000013"}], "ref": ["OK", {"event": "request:000013"}]}
proc:close_oldest_open_request:v1 | neg_missing_input | 1 | {"status": "MISSING_ARGUMENT"}
proc:close_oldest_open_request:v1 | neg_wrong_type | 1 | {"status": "TYPE_ERROR"}
proc:close_oldest_open_request:v1 | neg_empty_result | 1 | {"got": "NOT_FOUND", "ref": "NOT_FOUND"}
proc:close_oldest_open_request:v1 | neg_ambiguous_entity | 1 | {"status": "RESOLUTION_AMBIGUOUS"}
proc:close_oldest_open_request:v1 | neg_deleted_object | 1 | {"got": "OK", "ref": "OK"}
proc:close_oldest_open_request:v1 | neg_empty_world_precondition | 1 | {"got": "NOT_FOUND", "ref": "NOT_FOUND"}
proc:close_oldest_open_request:v1 | txn_inject_after_1 | 1 | {}
proc:close_oldest_open_request:v1 | txn_inject_after_2 | 1 | {}
proc:close_oldest_open_request:v1 | txn_inject_after_3 | 1 | {}
proc:close_oldest_open_request:v1 | txn_inject_after_4 | 1 | {}
proc:close_oldest_open_request:v1 | determinism | 1 | {}
```
### table `procedure_aliases` (0 rows)
columns: ['procedure_id', 'alias']
```
```
### table `active_pointer` (1 rows)
columns: ['name', 'procedure_id', 'enabled']
```
close_oldest_open_request | proc:close_oldest_open_request:v1 | 1
```
### table `provenance` (3 rows)
columns: ['procedure_id', 'json']
```
proc:close_oldest_open_request:v1 | {"binder": "A-005 R20 s17 ep40 (frozen)", "llm_model": null, "paths": {"deterministic": "VERIFIED"}, "proposer": "deterministic", "runtime": "SEMVM_PROCEDURE_DISCOVERY_POC_V1", "source_interactions": ["dev_a-022-S15:close_oldest_open_request:d0:hdr"], "source_trace_sha256": ["d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb"], "timestamp": "2026-09-27 21:18:07", "verification_suite": "verify.py stages 0-6"}
proc:close_oldest_open_request:v2 | {"binder": "A-005 R20 s17 ep40 (frozen)", "llm_model": null, "paths": {"deterministic": null, "external": "REJECTED_FAILED_COUNTERFACTUAL"}, "proposer": "external", "runtime": "SEMVM_PROCEDURE_DISCOVERY_POC_V1", "source_interactions": ["dev_a-022-S15:close_oldest_open_request:d0:hdr"], "source_trace_sha256": ["d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb"], "timestamp": "2026-09-27 21:18:13", "verification_suite": "verify.py stages 0-6"}
proc:close_oldest_open_request:v3 | {"binder": "A-005 R20 s17 ep40 (frozen)", "llm_model": null, "paths": {"deterministic": null, "external": "REJECTED_FAILED_COUNTERFACTUAL"}, "proposer": "external", "runtime": "SEMVM_PROCEDURE_DISCOVERY_POC_V1", "source_interactions": ["dev_a-022-S15:close_oldest_open_request:d0:hdr"], "source_trace_sha256": ["d8b352aa9a42a3c44ef041f7070dbe2bcf7daea7455624f9798281cda82d03cb"], "timestamp": "2026-09-27 21:18:16", "verification_suite": "verify.py stages 0-6"}
```
### table `lib_log` (10 rows)
columns: ['n', 'event', 'json']
```
1 | CANDIDATE | {"id": "proc:close_oldest_open_request:v1"}
2 | TESTING | {"id": "proc:close_oldest_open_request:v1"}
3 | VERIFIED | {"id": "proc:close_oldest_open_request:v1"}
4 | ACTIVATE | {"id": "proc:close_oldest_open_request:v1", "retired": null}
5 | CANDIDATE | {"id": "proc:close_oldest_open_request:v2"}
6 | TESTING | {"id": "proc:close_oldest_open_request:v2"}
7 | REJECTED_FAILED_COUNTERFACTUAL | {"id": "proc:close_oldest_open_request:v2"}
8 | CANDIDATE | {"id": "proc:close_oldest_open_request:v3"}
9 | TESTING | {"id": "proc:close_oldest_open_request:v3"}
10 | REJECTED_FAILED_COUNTERFACTUAL | {"id": "proc:close_oldest_open_request:v3"}
```
### table `sqlite_sequence` (1 rows)
columns: ['name', 'seq']
```
lib_log | 10
```

## 8. Post-handoff reuse (teacher destroyed, fresh student processes, network guard)

handoff: app semvm-rci-hosted, stop rc 0, endpoint after stop HTTP 404, destroyed True

- **[RESTART: student process + local LLM service restarted; learn/ transcripts absent]**
- `REQUEST shut Trent's first still-open request` → status OK, plan `close_oldest_open_request(person=Trent)`, return `{"event": "request:000006"}` | expected OK `{"event": "request:000006"}` | world state == oracle → **EXACT**
- `RUN close_oldest_open_request person=Ivan` → status NOT_FOUND, plan `close_oldest_open_request(person=Ivan)`, return `null` | expected NOT_FOUND `null` | world state == oracle → **EXACT**
- **[RESTART: student process + local LLM service restarted; learn/ transcripts absent]**
- `REQUEST close the earliest open request from Rita` → status NOT_FOUND, plan `close_oldest_open_request(person=Rita)`, return `null` | expected NOT_FOUND `null` | world state == oracle → **EXACT**

reuse process audit: `{"netguard_active": true, "teacher_env_present": [], "teacher_modules_loaded": [], "learn_dir_present_at_start": false}`

reuse process audit: `{"netguard_active": true, "teacher_env_present": [], "teacher_modules_loaded": [], "learn_dir_present_at_start": false}`

network-guard blocked connection attempts: 0; student weight hashes across restarts: ['9b3db05bd8eb1ea1e7a7f7725b73ac5e7ca16c08ea6659e013f0f59a2bb746b6']