# SEMVM_PROCEDURE_DISCOVERY_POC_V1: Amendment 001 (registered before implementation, by the user's rulings)

## 1. Parent-system gap and the LLM role
`SEMVM_SMALL_LLM_HYBRID_POC_V1` was never built. The "small LLM" of §17 / §26 / §56 is therefore realized as follows.

**Model:** frozen local **Qwen2.5-Coder-1.5B** (base) in fp16, greedy decoding, few-shot prompts. The file hashes and a parameter hash are recorded at load and re-checked at the end. There are no optimizer and no gradient updates.

**Its outputs are proposals only.** No procedure becomes ACTIVE on the LLM's judgment.
- **Proposal (§17):** the LLM proposes a procedure (parameter list and program) from the trace(s). **Deterministic trace anti-unification runs in parallel as a second proposal path.** Every candidate from either path is statically validated and verified against the evidence derived from the traces.
- **Reporting:** LLM-only, deterministic-only and union (either verified) proposal success are reported separately.
- **Choice:** the stored candidate is the deterministic one if VERIFIED, else the LLM one if VERIFIED.
- **Retrieval (§26):** templated English paraphrase → the LLM ranks ACTIVE procedures and writes the argument list or nested plan → deterministic signature, type, vocabulary and occurs-in-request checks → a unique valid procedure, or CLARIFY. The registered ranking margin is 1.0 nat.
  - This is a **controlled natural-language retrieval probe**, not open-English understanding.
  - Paraphrase template sets for DEV and LOCKED_TEST are disjoint.
- **Anti-cheating:** the LLM few-shot prompts use only procedure families outside the registered catalogue.

## 2. Domain: minimal extension of the frozen END_TO_END_POC world
- **Kept:** the END_TO_END_POC_V1 world model and ontology, i.e. the event types, WHO / WHEN / WHERE / RECIPIENT / TOPIC, and persons.
- **Added (the domain ruling):**
  - a **STATUS** attribute on events (OPEN | CLOSED; absent = OPEN);
  - a structured **REPORT** *value* (rows of key, count and values), which is returned and never stored as a world object;
  - the smallest primitive set the registered scenarios need (`spec/PROCEDURE_PRIMITIVES_V1.json`).
- **No customer / account / notes domain is introduced.** The report / account examples of the spec are replaced by the families in `scenarios/catalog.py`.
- **Recorded tension between the two rulings:**
  - the LLM-role ruling said "no new domain concepts";
  - the domain ruling (the direct answer) authorized STATUS + REPORT.

  The minimal STATUS + REPORT extension is used, and nothing else is added.

## 3. Registered procedure families (gold ASTs are independent of the discovery code)
| family | parameters | form |
|---|---|---|
| `calls_with` | person | FIND CALL WHERE WHO = p |
| `count_open_calls_with` | person | FIND … STATUS=OPEN → COUNT |
| `close_calls_with` | person | FOR each call SET_STATUS CLOSED → COUNT |
| `move_last_reminder_and_return_call_person` | time | FIND_LAST REMINDER; UPDATE WHEN; CHILD; GET WHO |
| `retarget_last_email` | person | |
| `replace_visit_location` | place | |
| `call_people_at` | time | PARENT.WHEN constraint → SELECT WHO |
| `email_topic_report` | none | GROUP RECIPIENT → REPORT TOPIC |
| `count_requests_by_at` | person, time | |
| `close_open_emails_to` | person | constants EMAIL / OPEN / CLOSED |
| `person_on_call_at` | time | |
| `count_calls_with` | person | |
| `move_visit_and_parent` | place | rollback when the parent is a PLAN (WHERE is not allowed on PLAN) |
| **composite** `count_calls_for_time_person(time) = count_calls_with(person_on_call_at(time))` | time | |

## 4. Interfaces
- **Teaching** uses the deterministic step language SEMVM_STEP_V1 (`procedure/lang.py`).
- **Commands:** `:teach / :endteach`, `:example / :endexample / :learn`, `:revise / :endrevise`, `:propose`, `:save-last-as`, `:accept` (the explicit yes of §67), `RUN`, `REQUEST`, `:alias`, `:procedure`, and `:disable- / :enable- / :delete-procedure`.
- **World fixtures** in scenarios are applied through the gold-IR path. The binder is not what's under test here; it remains available in the interactive shell.

## 5. Verification design (fixed before scenarios)
- **Independence:** a candidate is judged only against the evidence (the recorded successful traces and the parameter interface derived from their variation, or from the declared example values for one-shot teaching), never against gold.
- **Counterfactual reference:** the *unabstracted* trace with value substitution in the evidence slots (§21), run on each trace's start state.
- **One-shot rule:** a declared example value that occurs in more than one literal slot makes the split ambiguous → REJECTED_AMBIGUOUS (need another example).
- **Stages:** see `procedure/verify.py`.

## 6. Unchanged
The gates (§45), the GOLD_PROC control (§46), DEV / LOCKED_TEST discipline, the restart hard gate, the stop conditions and the interpretation map are all as in the spec.
