"""Independent reference semantics (test oracle). Deliberately does NOT import any runtime module (ir / resolver / vm / store): it re-implements
the registered V1 semantics from the spec + Amendment 001 in a few plain dict operations, so GOLD_IR exactness is a real check of the runtime.
Rules: per-type 6-digit counters; events created per assertion (outer, then inner), new persons in canonical value order (type, surface);
persons by exact alias (lowercase): 0 new / 1 reuse / >=2 AMBIGUOUS; scalar ids <type>:<normalized>; LAST_<T> = highest-seq active event of T;
UPDATE = per assignment retract active (ref, rel, *) then assert; any relation illegal for the frozen matrix -> VM_EXEC_ERROR, no change."""
import re, copy, json
OUTER = ["REMINDER", "PLAN", "REQUEST", "NOTE"]; INNER = ["CALL", "EMAIL", "VISIT", "MESSAGE"]
VALID = {"WHEN": set(OUTER + INNER), "WHO": {"REMINDER", "PLAN", "REQUEST", "CALL", "EMAIL", "VISIT", "MESSAGE"}, "RECIPIENT": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "MESSAGE"},
         "TOPIC": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "MESSAGE"}, "WHERE": {"REMINDER", "REQUEST", "NOTE", "CALL", "EMAIL", "VISIT", "MESSAGE"}}
VT = {"WHO": "PERSON", "RECIPIENT": "PERSON", "WHEN": "TIME", "WHERE": "PLACE", "TOPIC": "TOPIC"}


def tnorm(s):
    if s in ("noon", "midnight", "dawn", "dusk"): return s.upper()
    h, _, m = s.partition(":"); return f"{int(h):02d}:{m or '00'}"


def sid(vt, s): return f"{vt.lower()}:{tnorm(s) if vt == 'TIME' else s.lower()}"


class Oracle:
    def __init__(self): self.obj = {}; self.rels = []; self.alias = {}; self.cnt = {}; self.seq = 0; self.surface = {}

    def _new(self, t):
        n = self.cnt.get(t, 0) + 1; self.cnt[t] = n; self.seq += 1; oid = f"{t.lower()}:{n:06d}"; self.obj[oid] = [t, "active", self.seq]; return oid

    def persons(self, a): return sorted(o for o, al in self.alias.items() if self.obj[o][1] == "active" and a.lower() in [x.lower() for x in al])

    def state(self):
        return {"objects": sorted([[o, v[0]] for o, v in self.obj.items() if v[1] == "active"]), "relations": sorted([list(r) for r in self.rels]),
                "aliases": sorted([[o, a] for o, al in self.alias.items() if self.obj[o][1] == "active" for a in al])}

    def assertion(self, facts):
        """facts: {"outer": T, "inner": T, "mods": [(rel, value, 'outer'|'inner')]} -> status"""
        for r, v, _ in facts["mods"]:
            if VT[r] == "PERSON" and len(self.persons(v)) >= 2: return "RESOLUTION_AMBIGUOUS"
        e0 = self._new(facts["outer"]); e1 = self._new(facts["inner"]); ev = {"outer": e0, "inner": e1}; new = []
        pers = {}
        for r, v, _ in sorted(facts["mods"], key=lambda m: ({"PERSON": "PERSON", "TIME": "TIME", "PLACE": "PLACE", "TOPIC": "TOPIC_VALUE"}[VT[m[0]]], m[1])):
            if VT[r] == "PERSON":
                hit = self.persons(v)
                if hit: pers[v] = hit[0]
                elif v not in pers: pers[v] = self._new("PERSON"); self.alias[pers[v]] = [v]
        self.rels.append((e0, "TODO", e1))
        for r, v, a in facts["mods"]:
            o = pers[v] if VT[r] == "PERSON" else sid(VT[r], v); self.rels.append((ev[a], r, o)); self.surface[o] = v
        return "OK"

    def last(self, t):
        c = [(v[2], o) for o, v in self.obj.items() if v[0] == t and v[1] == "active"]; return max(c)[1] if c else None

    def command(self, text):
        """-> (status, result list | None)"""
        t = text.split(); op = t[0]
        if op == "NEW": oid = self._new("PERSON"); self.alias[oid] = [t[2]]; return "OK", None
        if op == "QUERY":
            rel, tgt = t[1], t[3]; cons = [(c.split("=")[0].split(".")[0] if "." in c.split("=")[0] else "SELF", c.split("=")[0].split(".")[-1], c.split("=")[1]) for c in t[5:]]
            if tgt.startswith("LAST_"):
                x = self.last(tgt[5:])
                if x is None: return "RESOLVE_REFERENCE", None
                cands = [x]
            else: cands = sorted(o for o, v in self.obj.items() if v[0] == tgt and v[1] == "active")
            def val_id(r, v):
                if VT[r] != "PERSON": return sid(VT[r], v)
                h = self.persons(v); return h[0] if h else None
            for _, r, v in cons:
                if VT[r] == "PERSON" and len(self.persons(v)) >= 2: return "RESOLUTION_AMBIGUOUS", None
            out = set()
            for x in cands:
                ok = True
                for sc, r, v in cons:
                    nodes = [x] if sc == "SELF" else [s for s, p, o in self.rels if p == "TODO" and o == x] if sc == "PARENT" else [o for s, p, o in self.rels if p == "TODO" and s == x]
                    if not any((n, r, val_id(r, v)) in self.rels for n in nodes): ok = False; break
                if ok: out |= {o for s, p, o in self.rels if s == x and p == rel}
            return "OK", sorted(self.render(o) for o in out)
        x = self.last(t[1][5:])
        if x is None: return "RESOLVE_REFERENCE", None
        if op == "DELETE": self.obj[x][1] = "deleted"; self.rels = [r for r in self.rels if x not in (r[0], r[2])]; return "OK", None
        if op == "RETRACT": self.rels = [r for r in self.rels if not (r[0] == x and r[1] == t[2])]; return "OK", None
        if op == "UPDATE":
            snap = copy.deepcopy((self.obj, self.rels, self.alias, self.cnt, self.seq, self.surface))
            for a in t[2:]:
                r, v = a.split("=")
                if VT[r] == "PERSON" and len(self.persons(v)) >= 2: self.obj, self.rels, self.alias, self.cnt, self.seq, self.surface = snap; return "RESOLUTION_AMBIGUOUS", None
                self.rels = [q for q in self.rels if not (q[0] == x and q[1] == r)]
                if VT[r] == "PERSON":
                    h = self.persons(v); o = h[0] if h else self._new("PERSON")
                    if not h: self.alias[o] = [v]
                else: o = sid(VT[r], v); self.surface[o] = v
                self.rels.append((x, r, o))
                if self.obj[x][0] not in VALID[r]: self.obj, self.rels, self.alias, self.cnt, self.seq, self.surface = snap; return "VM_EXEC_ERROR", None
            return "OK", None
        raise ValueError(text)

    def render(self, o):
        if o.startswith("person:"): return self.alias[o][0]
        return self.surface[o]
