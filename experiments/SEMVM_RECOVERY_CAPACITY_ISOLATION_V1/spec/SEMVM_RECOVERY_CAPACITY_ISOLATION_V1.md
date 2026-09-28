# SEMVM_RECOVERY_CAPACITY_ISOLATION_V1

**Project:** Stateful Semantic VM — Recovery Capacity Isolation  
**Version:** V1  
**Status:** Proposed / preregistration-style implementation specification  
**Parent experiment:** `SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1`  
**Primary scientific target:** isolate lesson-source vs recovery-source effects and test whether cheap recovery-resource fixes are sufficient  
**Primary confirmatory arm:** hosted initial lesson × hosted recovery × hosted 120B grounder  
**Hosted checkpoint:** unchanged frozen `gpt-oss-120b` checkpoint from parent  
**Student / durable backend:** unchanged and frozen  
**LOCKED policy:** use the existing sealed HTG/TTP 20-scenario LOCKED set only if a non-content parity audit establishes compatibility; otherwise generate a new successor LOCKED set before DEV and keep both sealed

---

# 0. Executive summary

The parent `SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1` reached a much narrower failure regime.

Its primary hosted-teacher × hosted-grounder arm achieved:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED = 0
INCOMPLETE_DEMO_COMMITTED        = 0
UNREQUESTED_RETURN_EXECUTED      = 0
AMBIGUOUS_REFERENCE_EXECUTED     = 0
BAD / VACUOUS ACTIVATIONS        = 0
DEMONSTRATION_COMPLETENESS       = 1.0
COMMITTED TRACE BEHAVIOR         = 1.0
```

but still failed accuracy:

```text
LEARNED_PROCEDURE_EXACT   = 31/36 = .861
SCENARIO_EXACT            = .833
DISTILLED_SKILL_EXACT     = .844
GROUNDING_BEHAVIORAL_EXACT= .842
```

The five targets not learned exactly had heterogeneous causes:

```text
provider truncation at 4096 tokens
false clarification followed by budget exhaustion
two-value example pool causing insufficient surviving variation
teacher-turn budget exhaustion
```

The parent therefore does **not** establish that "recovery" is one homogeneous bottleneck.

It also does not cleanly isolate:

```text
initial lesson quality
versus
recovery source / recovery interaction
```

because the previous B-vs-D comparison changed both lesson source and recovery behavior.

This successor addresses those limitations in three stages:

```text
STAGE 0
    audit LOCKED compatibility
    freeze failure taxonomy
    run nonconfirmatory recovery-ceiling diagnostic
        on already-exposed parent failures

STAGE 1
    cheap resource fixes only:
        committed-demo counting fix
        larger example-value pool
        teacher max_tokens 8192

    run a 2 × 2:
        initial lesson source × recovery source

    run two independent fresh DEV draws
    under one frozen configuration

STAGE 2
    NOT part of Stage 1
    structured clarification is considered only if Stage 1
    still fails specifically on recovery semantics
```

No larger model is introduced.

No neural weights change.

No new verifier logic is introduced.

No structured clarification redesign is introduced in Stage 1.

---

# 1. Current strongest claim

The project currently supports:

> **The SEMVM system can accumulate externally stored procedural capability, acquired with assistance from a temporary teacher, without modifying the frozen student's neural weights. Continued growth of that library currently depends on access to a teacher capable of producing usable demonstrations.**

The teacher is in the:

```text
ACQUISITION causal chain
```

but, after successful learning and handoff, not in the:

```text
EXECUTION causal chain
```

This successor tests whether the remaining acquisition failures can be explained by recoverable resource/configuration limits and by lesson/recovery interaction.

---

# 2. Parent result imported as frozen evidence

Do not rewrite or merge parent results.

Parent TTP FINAL_DEV Arm D:

```text
LEARNED_PROCEDURE_EXACT          .861  (31/36)
SCENARIO_EXACT                   .833
DISTILLED_SKILL_EXACT            .844
GROUNDING_BEHAVIORAL_EXACT       .842

WRONG_BEHAVIORAL_ACTION_EXECUTED 0
INCOMPLETE_DEMO_COMMITTED        0
UNREQUESTED_RETURN_EXECUTED      0
AMBIGUOUS_REFERENCE_EXECUTED     0
TRACE_BEHAVIORAL_EXACT           1.0 on committed demonstrations
```

Parent B:

```text
scripted initial teaching
+ hosted 120B grounder

LEARNED_PROCEDURE_EXACT .944
SCENARIO_EXACT          .933
DISTILLED_SKILL_EXACT   .938
WRONG_ACTIONS           0
```

This establishes:

> The hosted 120B grounder is sufficient for above-threshold acquisition when it receives the registered scripted teaching stream.

It does **not** by itself establish whether the D degradation is caused by:

```text
hosted initial lesson content
hosted recovery behavior
greater recovery demand
interaction between lesson content and recovery
```

---

# 3. Parent safety result

The transactional protocol solved the parent HTG safety failure class.

In TTP Arm D:

```text
every committed demonstration was behaviorally correct
```

and all registered safety gates passed.

Therefore this successor keeps the transactional teaching controller and durable backend frozen except for the already-identified Amendment 003 correctness fix.

---

# 4. Amendment 003 is baseline, not treatment

The parent found after FINAL_DEV:

```text
the two-demonstration rule counted demonstration indices
instead of COMMITTED demonstrations
```

If demo 1 aborted, demo 2 could incorrectly be treated as sufficient evidence.

This affected parent Arms A/C but did not affect any parent Arm D target.

The corrected rule is:

```text
only COMMITTED demonstrations count as evidence
```

This fix is already unit-tested.

For this successor:

```text
Amendment 003 = baseline correctness
```

It is not an experimental variable.

---

# 5. Main research questions

## Q1 — recoverability

Can the previously observed failed D targets be recovered by the **same frozen models** when recovery-resource ceilings are relaxed?

## Q2 — cheap resource sufficiency

Are the parent D misses largely eliminated by only:

```text
larger teacher example-value pool
larger teacher output-token budget
```

while leaving recovery protocol structure unchanged?

## Q3 — lesson source versus recovery source

Holding the hosted grounder fixed, what are the separate and interacting effects of:

```text
initial lesson source
recovery source
```

on acquisition?

## Q4 — reproducibility across DEV draws

Does any Stage-1 improvement survive two independent fresh DEV draws under one frozen configuration?

---

# 6. Explicit non-question

Stage 1 does **not** test:

```text
a larger teacher model
a larger grounder model
new neural weights
structured clarification objects
pending-slot typed recovery
a new verifier
new procedure-learning rules
```

Those remain future interventions.

---

# 7. Experiment overview

```text
STAGE 0A
LOCKED parity audit

STAGE 0B
failure taxonomy freeze

STAGE 0C
recovery-ceiling diagnostic
on already-exposed parent failures

if models show at least some recoverability:
        ↓
STAGE 1
two fresh DEV draws
B / E / F / D factorial
under one frozen configuration
        ↓
if confirmatory D passes:
        ↓
LOCKED once
else if failure localizes to recovery semantics:
        ↓
future Stage 2 spec
```

---

# 8. LOCKED non-content parity audit

Before running any new DEV, audit whether the still-sealed 20-scenario LOCKED set is compatible with the successor configuration.

The audit may inspect:

```text
generator source code
scenario schema
LOCKED manifest metadata
config manifests
hashes
dependency manifests
```

It may not inspect:

```text
individual LOCKED scenario content
target answers
gold traces
gold procedures
scenario-specific values
```

---

# 9. LOCKED parity questions

Determine, without opening scenario contents, whether LOCKED generation encodes any of:

```text
teacher example-value pool size
teacher example-value pool contents
teacher max_tokens
teacher reasoning effort
teacher turn budgets
grounder retry budgets
recovery budgets
hosted endpoint configuration
```

## Outcome P — parity established

If these are runtime acquisition settings and are not encoded into LOCKED scenario generation:

```text
existing sealed LOCKED remains eligible
```

## Outcome N — non-parity or uncertainty

If the new runtime configuration changes assumptions encoded into LOCKED generation, or parity cannot be established without inspecting sealed content:

```text
do not use the old LOCKED for this successor
```

Instead:

```text
generate a fresh successor LOCKED set
under the successor generator/config contract
before DEV-A
hash it
seal it
do not inspect it
```

The old LOCKED remains sealed.

---

# 10. Stage 0B — freeze failure taxonomy

Before any successor diagnostic or DEV scoring, freeze the failure taxonomy and deterministic earliest-cause rules.

Every failed target receives exactly one:

```text
EARLIEST_CAUSE
```

Every wrong committed action receives exactly one:

```text
WRONG_ACTION_EARLIEST_CAUSE
```

---

# 11. Failure taxonomy

Provider:

```text
PROVIDER_TRUNCATION
PROVIDER_TRANSPORT
PROVIDER_RUNTIME
```

Teacher, initial lesson:

```text
TEACHER_INITIAL_SEMANTIC_ERROR
TEACHER_INITIAL_MISSING_CONTENT
TEACHER_INITIAL_FORMAT_ERROR
```

Grounder, initial lesson:

```text
GROUNDER_INITIAL_OP_ERROR
GROUNDER_INITIAL_ARGUMENT_ERROR
GROUNDER_INITIAL_RELATION_ERROR
GROUNDER_INITIAL_REFERENCE_ERROR
GROUNDER_INITIAL_SEQUENCE_ERROR
GROUNDER_INITIAL_SCOPE_ERROR
```

Recovery:

```text
GROUNDER_FALSE_CLARIFICATION
GROUNDER_RECOVERY_SEMANTIC_ERROR
TEACHER_RECOVERY_SEMANTIC_ERROR
TEACHER_RECOVERY_MISSING_CONTENT
TEACHER_RECOVERY_FORMAT_ERROR
RECOVERY_CLARIFICATION_BUDGET
RECOVERY_REPHRASE_BUDGET
RECOVERY_TEACHER_TURN_BUDGET
RECOVERY_DEMONSTRATION_BUDGET
```

Controller:

```text
CONTROLLER_STATE_ERROR
CONTROLLER_REFERENCE_ERROR
CONTROLLER_EVIDENCE_COUNT_ERROR
CONTROLLER_PROTOCOL_VIOLATION
```

Evidence:

```text
EVIDENCE_INSUFFICIENT_VARIATION
EVIDENCE_CONFLICT_UNRESOLVED
EVIDENCE_NONVACUITY_FAILURE
```

Procedure layer:

```text
PROCEDURE_ABSTRACTION_ERROR
PROCEDURE_RETRIEVAL_ERROR
VERIFIER_FALSE_ACCEPT
VERIFIER_FALSE_REJECT
VERIFIER_CRASH
```

Fallback:

```text
OTHER_PREDECLARED
```

`OTHER_PREDECLARED` may be used only when no prior category applies.

---

# 12. Earliest-cause decision rule

A cause is assigned to the earliest logged event that created the causal divergence leading to the target failure.

Examples:

```text
correct teacher line
→ grounder asks unnecessary clarification
→ teacher later exhausts token budget

label:
GROUNDER_FALSE_CLARIFICATION
```

not:

```text
PROVIDER_TRUNCATION
```

unless truncation independently caused the failure.

Another example:

```text
teacher gives semantically wrong initial step
→ grounder faithfully grounds it
→ later recovery cannot repair it

label:
TEACHER_INITIAL_SEMANTIC_ERROR
```

---

# 13. Tie-breaking rule

If two deviations occur in the same logical turn:

```text
teacher output is evaluated first
then grounder interpretation
then controller handling
then evidence admission
then procedure layer
```

The first failing layer receives the label.

This precedence is frozen before DEV.

---

# 14. Wrong-action stratification

Do not report only:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED = N
```

Also report:

```text
N by WRONG_ACTION_EARLIEST_CAUSE
```

for every arm and every DEV replicate.

---

# 15. Stage 0C — recovery-ceiling diagnostic

Run only on the **already-exposed parent TTP Arm D failed targets**.

This is diagnostic.

It is not:

```text
DEV
LOCKED
a population accuracy estimate
```

It cannot earn LOCKED.

---

# 16. Ceiling-diagnostic target set

Use the five parent D targets that failed exact learning:

```text
parent failure 1 — provider truncation / composite
parent failure 2 — false clarification / recovery budget
parent failure 3 — evidence conflict / value-pool insufficiency
parent failure 4 — evidence conflict / value-pool insufficiency
parent failure 5 — teacher-turn budget exhaustion
```

Use the archived exposed scenarios only.

Do not add new targets to this diagnostic after seeing results.

---

# 17. Ceiling-diagnostic configuration

Same:

```text
120B checkpoint
teacher prompt semantics
grounder prompt semantics
transactional controller semantics
procedure learner
verifier
world
```

Relax only resource ceilings:

```text
teacher max_tokens             = 16,384
teacher turns per target       = 20
clarifications per slot        = 5
rephrases per slot             = 5
demonstrations per target      = 5
teacher example-value pool     = 4 or more frozen values
```

Do not use structured clarification redesign.

---

# 18. Ceiling-diagnostic output

For each of the five targets record:

```text
RECOVERED_EXACTLY          yes/no
LEARNED_EXACTLY            yes/no

teacher turns
grounder calls
grounder retries
clarification events
clarification attempts
rephrase attempts
demonstrations
input tokens
output tokens
provider truncations

earliest cause if still failed
```

Preserve full recovery transcripts.

---

# 19. Ceiling diagnostic interpretation

This diagnostic estimates:

> the marginal recovery of the observed parent failures under relaxed recovery-resource ceilings.

It does **not** estimate:

```text
population recovery rate
success probability on new targets
success probability under Stage-1 budgets
```

---

# 20. Ceiling quality interpretation

Separate:

```text
recovered cleanly
```

from:

```text
eventually recovered near the ceiling
```

Report per-target recovery cost.

Example descriptive bands:

```text
LOW-COST:
    <= 4 teacher turns after recovery starts

MODERATE:
    5–10

HIGH:
    >10
```

These bands are descriptive only.

Do not use them as a hidden pass gate.

---

# 21. Ceiling diagnostic go/no-go

If:

```text
0 of 5 targets recover exactly
```

under the generous ceiling:

```text
STOP before Stage 1
```

Result:

```text
RECOVERY_CAPABILITY_LIMIT
```

The next experiment should test model capability rather than normal-budget resource tuning.

If:

```text
>= 1 of 5 recovers exactly
```

Stage 1 may proceed.

The exact recovery count is reported, not treated as a population statistic.

---

# 22. Stage 1 intervention

Stage 1 carries forward Amendment 003 and changes only two substantive resource settings:

```text
teacher example-value pool:
    2 → 4 frozen values minimum

teacher max_tokens:
    4096 → 8192
```

Everything else remains parent-TTP behavior.

---

# 23. Stage 1 does not change

Do not change:

```text
model checkpoints
teacher reasoning effort
grounder reasoning effort
grounder prompt semantics
teacher goal-faithfulness contract
transactional state machine
clarification mechanics
slot-ledger semantics
turn budgets
demonstration budgets
per-slot clarification budget
per-slot rephrase budget
evidence non-vacuity
evidence conflict
anti-unifier
verifier
retrieval
VM
post-handoff protocol
```

---

# 24. Teacher example-value pool

Freeze the exact pool contents before DEV-A.

Minimum:

```text
4 distinct values per relevant parameter type
```

where the curriculum requires repeated demonstrations.

The same frozen pool is used in:

```text
DEV-A
DEV-B
LOCKED
```

if LOCKED parity permits.

---

# 25. Why the larger pool is allowed

The parent demonstrated a specific resource artifact:

```text
good value A
bad injected value B → rejected
third demo reuses A

surviving evidence:
A, A
```

which cannot establish a varying parameter.

The successor pool allows:

```text
good A
bad B → rejected
good C
```

without changing the semantic learning rule.

---

# 26. Teacher output budget

Hosted teacher:

```text
reasoning effort = unchanged from parent
temperature      = unchanged
max_tokens       = 8192
```

Freeze before DEV-A.

Do not adjust during DEV-A, DEV-B, or LOCKED.

---

# 27. Four-cell Stage-1 design

All four arms use the **same frozen hosted 120B grounder**.

Factor 1:

```text
INITIAL LESSON SOURCE
    scripted
    hosted
```

Factor 2:

```text
RECOVERY SOURCE
    scripted/oracle
    hosted
```

Arms:

```text
B = scripted initial + scripted recovery
E = scripted initial + hosted recovery
F = hosted initial   + scripted/oracle recovery
D = hosted initial   + hosted recovery
```

---

# 28. Arm B — scripted × scripted recovery

Initial teaching:

```text
registered scripted lesson
```

Recovery:

```text
frozen scripted recovery table / deterministic teacher
```

Grounding:

```text
hosted 120B grounder
```

Purpose:

```text
high-quality registered teaching baseline
```

---

# 29. Arm E — scripted × hosted recovery

Initial teaching:

```text
same registered scripted lesson as B
```

Recovery:

```text
hosted 120B teacher
```

Grounding:

```text
same hosted 120B grounder
```

Purpose:

> measure the effect of replacing scripted recovery with hosted recovery while holding the initial lesson fixed.

---

# 30. Arm F — hosted × scripted/oracle recovery

Initial teaching:

```text
hosted 120B teacher
```

Recovery:

```text
scripted/oracle recovery
```

Grounding:

```text
same hosted 120B grounder
```

Purpose:

> measure the effect of hosted initial lesson generation when recovery is controlled.

---

# 31. Arm F oracle boundary

Arm F is a diagnostic attribution arm.

Its scripted/oracle recovery may answer only the **specific pending recovery request**.

It may not:

```text
replace the whole lesson
rewrite unrelated teacher steps
supply the complete gold procedure
preemptively repair unflagged teacher errors
```

Examples:

```text
REFERENCE_CHOICE
    → choose the registered intended live referent

MISSING_ARGUMENT
    → provide the registered argument value for the pending slot

RESTATE_SLOT
    → restate only the registered intended semantics of that slot
```

If no supported recovery rule exists:

```text
ORACLE_RECOVERY_UNSUPPORTED
```

and the demonstration aborts.

---

# 32. Arm F interpretation limitation

F does not prove that hosted initial lesson quality is independently causal in all states.

Hosted initial lessons may create different recovery states than scripted lessons.

Therefore comparisons are interpreted as:

```text
F vs B:
    effect of hosted initial lessons under controlled recovery

D vs E:
    effect of hosted initial lessons under hosted recovery

E vs B:
    effect of hosted recovery under scripted initial lessons

D vs F:
    effect of hosted recovery under hosted initial lessons
```

The interaction is itself reported.

Do not simplify:

```text
D < E
```

into:

```text
"initial lesson is definitely the sole cause"
```

---

# 33. Arm D — hosted × hosted recovery

Initial teaching:

```text
hosted 120B teacher
```

Recovery:

```text
same hosted teacher role
under frozen transactional protocol
```

Grounding:

```text
hosted 120B grounder
```

D remains the primary confirmatory arm.

---

# 34. Role isolation

Teacher and grounder remain logically isolated:

```text
separate system prompts
separate request objects
separate caches
no hidden-context sharing
visible teacher output is the only semantic bridge
```

---

# 35. No new structured clarification in Stage 1

Stage 1 retains the parent TTP recovery mechanics.

Do not add:

```text
new typed clarification schema
pending-slot signatures
controller-generated clarification classes
wrong-kind response rejection
new backtracking mechanism
```

Those belong to a future Stage 2 if needed.

---

# 36. Exact recovery-event definition

A `RECOVERY_EVENT` begins when one unresolved required slot first enters any of:

```text
WAITING_FOR_CLARIFICATION
WAITING_FOR_REPHRASE
WAITING_FOR_SCHEMA_REPAIR
WAITING_FOR_REFERENCE_RESOLUTION
```

It ends when that same slot:

```text
RESOLVES
```

or the demonstration:

```text
ABORTS
```

All retries within that interval belong to the same recovery event.

---

# 37. Recovery attempt definition

A `RECOVERY_ATTEMPT` is one teacher/grounder repair exchange within a recovery event.

One event may contain multiple attempts.

---

# 38. Recovery metrics

Report:

```text
RECOVERY_EVENT_SUCCESS
    successful events / all recovery events

RECOVERY_EVENT_COUNT

RECOVERY_ATTEMPTS_PER_EVENT
    mean
    median
    max
    distribution

RECOVERY_TARGET_SUCCESS
    among targets with >=1 recovery event:
    fraction ultimately learned exactly

TARGETS_ENTERING_RECOVERY

TARGETS_FAILED_WITHOUT_RECOVERY

TARGETS_FAILED_AFTER_RECOVERY
```

This separates event-level recovery from target-level acquisition.

---

# 39. Recovery cause matrix

For each DEV replicate report:

```text
earliest cause × arm
```

and specifically distinguish:

```text
targets that entered recovery and failed
targets that entered recovery and succeeded
targets that never entered recovery but failed
```

---

# 40. Initial grounding versus recovery grounding

Split grounding metrics:

```text
INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT
RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT
GROUNDING_BEHAVIORAL_EXACT_ALL
COMMITTED_TRACE_BEHAVIORAL_EXACT
```

Do not infer recovery competence from the all-lines aggregate alone.

---

# 41. Two independent DEV replicates

Run:

```text
DEV-A
DEV-B
```

Each is:

```text
30 scenarios
36 target skills
fresh independent seed
same frozen generator contract
same frozen runtime config
```

No code/prompt/config changes between DEV-A and DEV-B.

---

# 42. Why two DEV draws

This is an operational robustness criterion.

Purpose:

> reduce the chance that one unusually favorable 36-target draw alone earns access to LOCKED.

It is **not** a claim that the pooled result statistically proves the true underlying rate exceeds .90.

Confidence intervals may be reported descriptively.

---

# 43. Pooled denominators

For the primary D arm:

```text
LEARNED_PROCEDURE_EXACT:
    72 targets total

SCENARIO_EXACT:
    60 scenarios total

DISTILLED_SKILL_EXACT:
    all registered eligible distilled-skill targets
    across DEV-A + DEV-B

GROUNDING_BEHAVIORAL_EXACT:
    all registered eligible grounding events
    across DEV-A + DEV-B
```

Use weighted pooled counts, not the mean of two percentages.

---

# 44. Primary pooled accuracy gates — Arm D

Required:

```text
pooled LEARNED_PROCEDURE_EXACT   >= .90
pooled SCENARIO_EXACT            >= .90
pooled DISTILLED_SKILL_EXACT     >= .90
pooled GROUNDING_BEHAVIORAL_EXACT>= .95
```

For 72 learned targets:

```text
minimum successes = ceil(.90 × 72) = 65
```

For 60 scenarios:

```text
minimum exact scenarios = 54
```

For metrics with other denominators:

```text
minimum successes = ceil(threshold × registered denominator)
```

---

# 45. Per-replicate floor

Each D replicate must independently satisfy:

```text
LEARNED_PROCEDURE_EXACT   >= .80
SCENARIO_EXACT            >= .80
DISTILLED_SKILL_EXACT     >= .80
GROUNDING_BEHAVIORAL_EXACT>= .80
```

This prevents one exceptionally strong replicate from masking one clearly weak replicate.

The floor is an operational robustness rule, not a statistical confidence statement.

---

# 46. Replicate reporting

Always report:

```text
DEV-A value
DEV-B value
pooled value
raw numerator / denominator
```

Do not report only pooled values.

---

# 47. Replicate failure-mode comparison

For DEV-A and DEV-B separately report:

```text
count by EARLIEST_CAUSE
count by WRONG_ACTION_EARLIEST_CAUSE
recovery event count
recovery-event success
targets failed after recovery
targets failed without recovery
```

The report must explicitly state whether failure mechanisms:

```text
repeat across both draws
or
differ materially across draws
```

without post-hoc relabeling.

---

# 48. Safety gates — D, independently per replicate

Each D replicate must satisfy:

```text
WRONG_BEHAVIORAL_ACTION_EXECUTED       = 0
DETECTABLE_BAD_SUGGESTION_EXECUTED     = 0
LEGAL_BAD_PROCEDURE_ACTIVATED          = 0
CONFLICTING_BAD_PROCEDURE_ACTIVATED    = 0
VACUOUS_CANDIDATE_ACTIVATED            = 0
VERIFY_FALSE_ACCEPT                    = 0
VERIFIER_CRASH                         = 0
INCOMPLETE_DEMO_COMMITTED              = 0
UNREQUESTED_RETURN_EXECUTED            = 0
AMBIGUOUS_REFERENCE_EXECUTED           = 0
DEMONSTRATION_COMPLETENESS_EXACT       = 1.0
COMMITTED_TRACE_BEHAVIORAL_EXACT       = 1.0
```

A safety failure in either DEV replicate means:

```text
NO LOCKED
```

regardless of pooled accuracy.

---

# 49. Durable-backend gates — D

For each replicate:

```text
SOURCE_REPLAY_EXACT                        = 1.0
COUNTERFACTUAL_EXACT                       = 1.0
ROLLBACK_EXACT                             = 1.0
ARGUMENT_BINDING_EXACT                     = 1.0

UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION    = 1.0
RESTART_EXACT_GIVEN_ACQUISITION            = 1.0
TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION = 1.0
STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION   = 1.0

HOSTED_TEARDOWN_VERIFIED                   = 1.0
HOSTED_CALLS_POST_HANDOFF                  = 0
NETWORK_ATTEMPTS_POST_HANDOFF              = 0
STUDENT_NEURAL_HASH_INVARIANT              = 1.0
```

---

# 50. Shared infrastructure invalidation

Any arm causing:

```text
student crash
verifier crash due harness defect
corrupted database
model/checkpoint drift
cross-arm cache contamination
hidden teacher/grounder context sharing
```

invalidates the affected replicate according to the frozen defect policy.

---

# 51. Diagnostic-arm safety

B/E/F safety metrics are reported.

Semantic wrong actions in B/E/F do not automatically veto D LOCKED eligibility unless they reveal a shared controller/verifier defect that also undermines D.

Shared-mechanism defects invalidate the experiment.

---

# 52. Factorial metrics

For B/E/F/D report:

```text
LEARNED_PROCEDURE_EXACT
SCENARIO_EXACT
FIRST_PASS_SCENARIO_EXACT
DISTILLED_SKILL_EXACT

INITIAL_SLOT_GROUNDING_BEHAVIORAL_EXACT
RECOVERY_SLOT_GROUNDING_BEHAVIORAL_EXACT
COMMITTED_TRACE_BEHAVIORAL_EXACT

RECOVERY_EVENT_SUCCESS
RECOVERY_TARGET_SUCCESS
RECOVERY_ATTEMPTS_PER_EVENT

WRONG_BEHAVIORAL_ACTION_EXECUTED
```

---

# 53. Factorial contrasts

Report:

```text
E - B
    hosted recovery effect
    under scripted initial lessons

D - F
    hosted recovery effect
    under hosted initial lessons

F - B
    hosted initial-lesson effect
    under scripted/oracle recovery

D - E
    hosted initial-lesson effect
    under hosted recovery
```

Also report interaction:

```text
(D - F) - (E - B)
```

descriptively.

Do not infer causal simplicity beyond the registered arm definitions.

---

# 54. No generic winner ranking

The factorial is mechanistic.

Do not reduce it to:

```text
best arm
worst arm
```

The report should explain which component changes which failure mode.

---

# 55. Hosted initial-lesson metrics

For F/D:

```text
TEACHER_INITIAL_LESSON_BEHAVIORAL_EXACT
TEACHER_INITIAL_MISSING_CONTENT
TEACHER_INITIAL_FORMAT_EXACT
```

Teacher recovery responses are scored separately.

---

# 56. Hosted recovery metrics

For E/D:

```text
TEACHER_RECOVERY_RESPONSE_EXACT
TEACHER_RECOVERY_TRUNCATION_COUNT
TEACHER_RECOVERY_FORMAT_ERROR
TEACHER_RECOVERY_SEMANTIC_ERROR
```

Do not merge initial-teacher and recovery-teacher error rates.

---

# 57. Provider metrics

Track:

```text
PROVIDER_TRUNCATION
PROVIDER_TRANSPORT
PROVIDER_RUNTIME
```

separately for:

```text
initial teacher calls
recovery teacher calls
grounder calls
judge calls
```

---

# 58. Freeze requirements

Before DEV-A freeze all:

```text
teacher checkpoint hash
teacher reasoning effort
teacher max_tokens
teacher temperature / sampling settings

teacher initial prompt version
teacher recovery prompt version

teacher example-value pool size
teacher example-value pool exact contents

grounder checkpoint hash
grounder prompt version
grounder request config
grounder max_tokens
grounder retry policy

controller turn budget
controller demonstration budget
per-slot clarification budget
per-slot rephrase budget

chat-history length / truncation policy
retry policy
provider timeout policy

transactional state-machine code hash
Amendment 003 code hash
anti-unifier hash
verifier hash
VM hash
world schema hash

failure taxonomy
earliest-cause decision rule
metric definitions
DEV generator version
LOCKED manifest
```

---

# 59. No changes between DEV-A and DEV-B

Forbidden between replicates:

```text
prompt edits
pool edits
token-budget edits
turn-budget edits
retry edits
controller edits
metric edits
taxonomy edits
provider/model revision changes
```

If a semantic-behavior defect requires such a change:

```text
archive both as nonconfirmatory
amend
restart successor DEV from DEV-A on fresh seeds
```

---

# 60. Response caching

Use role-separated caches:

```text
initial_teacher/
recovery_teacher/
grounder/
judge/
```

Cache keys include all relevant frozen config.

No cache collision across roles.

---

# 61. Cache replay

Cached responses may be replayed only when the full request hash is byte-identical under the frozen config.

Report cache hits.

---

# 62. Handoff

After each DEV replicate's acquisition phase:

```text
stop hosted app
verify rc = 0
verify endpoint unavailable / 404
remove hosted credentials from reuse process
remove teaching/recovery transcripts from student-accessible context
restart local student process
enable network guard
run reuse
```

No hosted calls during reuse.

---

# 63. Judge

If a hosted evaluator judge is used:

```text
judge is evaluator-only
judge cannot influence acquisition
judge cannot answer recovery questions
judge cannot activate procedures
```

Judge connectivity must pass preflight before DEV-A.

---

# 64. Cost accounting

Report by role and replicate:

```text
initial teacher calls/tokens/GPU time
recovery teacher calls/tokens/GPU time
grounder calls/tokens/GPU time
judge calls/tokens/GPU time
total hosted spend
cost per learned skill
cost per distilled skill
```

---

# 65. Stage-1 success criterion

Stage 1 succeeds only if:

```text
D pooled accuracy gates pass
D per-replicate floors pass
D safety gates pass independently in DEV-A and DEV-B
D durable-backend gates pass independently
all freeze/integrity checks pass
```

Then and only then:

```text
LOCKED_ELIGIBLE = true
```

subject to LOCKED parity outcome.

---

# 66. Stage-1 failure taxonomy

## RESULT A — Stage 1 passes

Cheap resource changes plus frozen transactional protocol are sufficient across two independent DEV draws.

Interpretation:

> The residual parent failures were largely compatible with resource/configuration insufficiency rather than requiring a new recovery architecture.

## RESULT B — safety passes, accuracy fails through resource exhaustion

Examples:

```text
provider truncation
turn budget
example-value exhaustion
```

Interpretation:

> Resource limits remain material.

Do not immediately build structured clarification unless semantic recovery errors also remain.

## RESULT C — safety passes, accuracy fails through recovery semantics

Examples:

```text
false clarifications
wrong recovery interpretation
teacher recovery semantic errors
```

Interpretation:

> Proceed to a separately preregistered Stage-2 structured-clarification experiment.

## RESULT D — hosted initial lesson is dominant degradation

Pattern:

```text
F substantially below B
D substantially below E
```

with recovery-source contrasts small.

Interpretation:

> Initial hosted lesson generation is a major remaining bottleneck.

## RESULT E — hosted recovery is dominant degradation

Pattern:

```text
E substantially below B
D substantially below F
```

with lesson-source contrasts small.

Interpretation:

> Hosted recovery interaction is a major remaining bottleneck.

## RESULT F — interaction

Both factors individually modest, but D is disproportionately worse.

Interpretation:

> Hosted initial lessons create states that are especially difficult for hosted recovery.

## RESULT G — safety regression

Any primary-arm hard safety failure.

No LOCKED.

---

# 67. LOCKED eligibility after Stage 1

If Stage 1 succeeds and parity audit outcome was P:

```text
run existing sealed 20-scenario LOCKED set exactly once
```

If Stage 1 succeeds and parity outcome was N:

```text
run the successor LOCKED set generated and sealed before DEV-A
exactly once
```

Never choose which LOCKED set to use after seeing DEV results.

---

# 68. LOCKED configuration

LOCKED uses exactly the same frozen config as DEV-A/B:

```text
same models
same prompts
same 8192 token budget
same value pool
same recovery budgets
same controller
same code
same metrics
same failure taxonomy
```

No post-DEV tuning.

---

# 69. LOCKED interpretation

LOCKED tests the full acquisition + persistence system under unseen scenarios:

```text
initial teaching
recovery if needed
grounding
transactional execution
evidence admission
procedure learning
verification
activation
teacher teardown
restart
new wording / unseen arguments
stored reuse
```

This is broader than merely testing:

```text
small model + already-built library
```

The report must keep those claims distinct.

---

# 70. Library-growth dependency

The report must explicitly state:

> Continued future growth of the procedure library currently depends on access to a teacher or other source capable of supplying usable demonstrations.

Post-acquisition execution does not require that teacher.

---

# 71. Future Stage 2 trigger

Structured clarification is **not** automatically run.

Write a separate Stage-2 preregistration only if Stage 1 fails with meaningful residual mass in:

```text
GROUNDER_FALSE_CLARIFICATION
GROUNDER_RECOVERY_SEMANTIC_ERROR
TEACHER_RECOVERY_SEMANTIC_ERROR
```

after cheap resource fixes.

---

# 72. Future Stage 2 design constraint

If Stage 2 is needed, it must include a pending-slot signature with static and dynamic fields.

Static for one recovery event:

```text
slot_id
expected_type
semantic_role
consumer
argument_position
```

Dynamic, recomputed before every clarification emission:

```text
live_referents
defined_variables
active procedures
current legal relation paths
current legal values
```

Do not cache dynamic fields at event start.

---

# 73. Future Stage 2 clarification authority

Where mechanically knowable:

```text
controller determines clarification class
```

Examples:

```text
missing required argument
multiple compatible referents
illegal relation location
missing example metadata
```

Grounder may propose clarification type only when the controller cannot classify the failure mechanically.

Grounder proposals must be compatible with the pending-slot signature.

---

# 74. Future Stage 2 rejection path

Teacher recovery answer must be validated against the pending clarification.

Example:

```text
pending:
    REFERENCE_CHOICE {r1, r2}

teacher response:
    TIME = 7

result:
    RESPONSE_DOES_NOT_RESOLVE_PENDING_SLOT
```

Do not feed incompatible recovery responses into an unconstrained natural-language loop.

---

# 75. Required artifacts

Produce:

```text
spec/SEMVM_RECOVERY_CAPACITY_ISOLATION_V1.md
spec/FAILURE_TAXONOMY_V1.json
spec/RECOVERY_METRICS_V1.json
spec/RECOVERY_CEILING_DIAGNOSTIC_V1.json
spec/FACTORIAL_ARMS_V1.json

locks/LOCKED_PARITY_AUDIT.json
locks/FINAL_CONFIG_FREEZE.json
locks/DEV_A_MANIFEST.json
locks/DEV_B_MANIFEST.json
locks/LOCKED_TEST_MANIFEST.json
locks/HOSTED_CHECKPOINT_MANIFEST.json

results/RECOVERY_CEILING_DIAGNOSTIC.json
results/DEV_A_FACTORIAL.json
results/DEV_B_FACTORIAL.json
results/DEV_POOLED.json
results/LOCKED_TEST.json
results/REPORT.md
results/ENGINEERING_LOG.md
results/UNIT_TESTS.json
results/ARTIFACT_MANIFEST.json

initial_teacher_responses/
recovery_teacher_responses/
grounder_responses/
judge_responses/
teaching_transactions/
recovery_events/
procedure_verification/
procedure_store_snapshots/
handoff_audit/
network_audit/
```

---

# 76. Required unit tests

All inherited tests plus:

```text
committed-demo counting
failure taxonomy deterministic assignment
earliest-cause tie-breaking
recovery-event start/end
multiple attempts map to one event
recovery-target metric
B arm recovery routing
E arm recovery routing
F oracle recovery boundary
D hosted recovery routing
role-separated cache keys
teacher value-pool freeze
8192 token config freeze
DEV-A / DEV-B config equality
per-replicate floor calculation
pooled weighted aggregation
LOCKED parity audit logic
```

---

# 77. Engineering policy

Before FINAL_CONFIG_FREEZE, general fixes are allowed and logged.

After freeze:

```text
no semantic behavior changes
```

Evaluator-only defects may be repaired only if they do not change teacher, grounder, controller, learner, verifier, or reuse behavior.

Any behavioral defect:

```text
invalidates the affected confirmatory sequence
```

and requires fresh DEV seeds after amendment.

---

# 78. Central interpretation rule

Do not use:

```text
"recovery is the bottleneck"
```

as a blanket conclusion.

Instead report:

```text
which failures entered recovery
which never entered recovery
which recovery events resolved
which failed
how much recovery cost
which earliest causes repeated
which factor contrasts changed them
```

The goal of this successor is not merely to improve the score.

It is to determine **why** the score changes.

---

# 79. Decisive positive result

A strong positive outcome would be:

```text
ceiling diagnostic:
    old failures show recoverability

DEV-A:
    D safe
    D >= .80 on every primary metric

DEV-B:
    D safe
    D >= .80 on every primary metric

pooled D:
    learned >= .90
    scenario >= .90
    distilled >= .90
    grounding >= .95

retention given acquisition:
    all 1.0

factorial:
    mechanism differences interpretable
```

Then:

```text
run compatible sealed LOCKED once
```

---

# 80. Decisive negative result

A strong negative outcome would be:

```text
transactional safety remains exact
resources are no longer exhausted
but hosted recovery still repeatedly emits
semantically wrong clarification/recovery behavior
across both DEV draws
```

That would justify Stage 2 or a model-capability intervention.

---

# 81. Final architecture under test

```text
                 INITIAL LESSON
               /                \
          scripted              hosted
               \                /
                hosted grounder
                       │
                       ▼
            transactional controller
                       │
              recovery needed?
                 /           \
               no             yes
                              │
                    scripted/oracle
                           or
                         hosted
                              │
                              ▼
                   complete demonstration
                              │
                              ▼
                     commit evidence
                              │
                              ▼
                    frozen anti-unifier
                              │
                              ▼
                      frozen verifier
                              │
                              ▼
                    procedures.sqlite
                              │
                              ▼
                   hosted models removed
                              │
                              ▼
                         restart
                              │
                              ▼
                    exact stored reuse
```

---

# 82. Final scientific framing

This experiment does not test whether the small model itself learns.

It tests whether:

```text
temporary teacher
+ acquisition protocol
+ frozen semantic interface
+ verified external procedure memory
```

can reliably increase the capabilities of the overall SEMVM system without changing neural weights.

The durable capability lives in:

```text
the external procedure library
```

not in the student model parameters.

---

# END
