"""RCI lesson-source x recovery-source routing (spec §27-§33; spec/FACTORIAL_ARMS_V1.json).
The transactional controller asks ONE teacher object; this router sends each request by its kind:
  LESSON-SOURCE kinds  : LESSON, NEW_DEMO, FORMAT, REMAINING, MISSING_EXAMPLE      (the teaching stream itself)
  RECOVERY kinds       : RESTATE_SLOT, RESTATE_OBSCURED, CLARIFY_REFERENCE         (answers to a recovery event of one pending slot, spec §36)
Arms: B = scripted/scripted, E = scripted/hosted, F = hosted/oracle, D = hosted/hosted. Both hosted roles are the same frozen checkpoint with
separate cache namespaces (initial_teacher/, recovery_teacher/); the hosted recovery teacher sees exactly the visible dialogue (the lesson it
receives in the transcript may be a scripted one in Arm E).

ORACLE recovery (Arm F only; spec §31): answers ONLY the pending request from the registered target semantics, never replaces the lesson, never
repairs unflagged steps. It requires that the demonstration's executed trace so far is a structural prefix of the registered reference for the
demonstration's EXAMPLE values; otherwise ORACLE_RECOVERY_UNSUPPORTED (the controller aborts the demonstration).
  CLARIFY_REFERENCE -> the live result the next reference step reads (mapped by bind order)
  RESTATE_SLOT / RESTATE_OBSCURED -> registered band-A wording (DEV template bank) of the next n reference steps, n = max(1, reference steps left
                                     - teacher slots still pending after this one)  [registered heuristic; F is a diagnostic attribution arm]"""
import os, sys, re, json, copy, random
HERE = os.path.dirname(os.path.realpath(__file__)); ROOT = os.path.dirname(HERE)
RECOVERY_KINDS = {"RESTATE_SLOT", "RESTATE_OBSCURED", "CLARIFY_REFERENCE"}
UNSUPPORTED = "ORACLE_RECOVERY_UNSUPPORTED"


class Routed:
    def __init__(self, lesson, recovery, lesson_source, recovery_source):
        self.lesson, self.recovery, self.lesson_source, self.recovery_source = lesson, recovery, lesson_source, recovery_source; self.routed = []

    def respond(self, messages, kind, payload):
        who = self.recovery if kind in RECOVERY_KINDS else self.lesson
        self.routed.append({"kind": kind, "to": self.recovery_source if kind in RECOVERY_KINDS else self.lesson_source})
        text, prov = who.respond(messages, kind, payload); prov = dict(prov or {}, route=self.routed[-1]["to"], recovery=kind in RECOVERY_KINDS); return text, prov


def _nv(steps):
    s = json.dumps(steps, sort_keys=True); s = re.sub(r'"(var|as|bind)": "[^"]+"', r'"\1": "_"', s); return s


class OracleRecovery:
    def __init__(self, item, family_steps, gen):
        self.it, self.fs, self.g = item, family_steps, gen; self.log = []

    def respond(self, messages, kind, payload):
        st = payload.get("state") or {}; ex = st.get("example") or {}; P = {"provider": "oracle"}
        try: ref = self.fs(self.it["family"], {p: ex[p] for p in self.it["sig"]}) if all(p in ex for p in self.it["sig"]) else None
        except Exception: ref = None
        if ref is None: return self._u("no reference for the example values", payload)
        steps = [s for _, s in ref]; pats = [p for p, _ in ref]; exe = st.get("executed") or []; k = len(exe)
        if k > len(steps) or _nv(exe) != _nv(steps[:k]): return self._u("executed trace is not a prefix of the registered reference", payload)
        if k >= len(steps): return self._u("reference already complete", payload)
        if kind == "CLARIFY_REFERENCE":
            gold_binds = [s.get("bind") for s in steps[:k] if s.get("bind")]; stu_binds = [s.get("bind") for s in exe if s.get("bind")]
            want = [v for v in re.findall(r'"var": "(r\d+)"', json.dumps(steps[k])) if v in gold_binds]
            if not want: return self._u("next reference step reads no earlier result", payload)
            ch = stu_binds[gold_binds.index(want[0])] if gold_binds.index(want[0]) < len(stu_binds) else None
            if ch not in (payload.get("offered") or []): return self._u("intended referent not among the offered ones", payload)
            self.log.append({"kind": kind, "answer": ch}); return f"REFERENT: {ch}", P
        if kind in ("RESTATE_SLOT", "RESTATE_OBSCURED"):
            n = max(1, (len(steps) - k) - int(st.get("pending_teacher_slots_after", 0)))
            lines = []
            for p in pats[k:k + n]:
                try: txt, _ = self.g.clause(p, "A", ex)
                except Exception: return self._u(f"no registered wording for pattern {p}", payload)
                lines.append("STEP: " + txt[0].upper() + txt[1:] + ".")
            self.log.append({"kind": kind, "steps": n}); return "\n".join(lines), P
        return self._u(f"no oracle rule for {kind}", payload)

    def _u(self, why, payload):
        self.log.append({"kind": "UNSUPPORTED", "why": why}); return UNSUPPORTED, {"provider": "oracle", "unsupported": why}


def oracle_gen():
    sys.path.insert(0, os.path.join(ROOT, "scenarios")); import pdx_generate as PG
    TPL = json.load(open(os.path.join(ROOT, "scenarios", "templates_dev.json")))
    for k, v in PG.EXTRA_CLAUSES["dev"].items(): TPL["clauses"].setdefault(k, v)
    for k, v in PG.EXTRA_CLAUSES["returns"].items(): TPL["returns"].setdefault(k, v)
    return PG, PG.PGen(random.Random("RCI-ORACLE-WORDING"), "dev", TPL)
