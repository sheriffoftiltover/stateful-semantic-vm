"""Persistent procedure library (spec §9-§10, §25, §27, §34, §53-§55): procedures.sqlite. Versions are never overwritten
(proc:<name>:v<k>); lifecycle CANDIDATE -> TESTING -> VERIFIED -> ACTIVE | REJECTED_*; exactly one ACTIVE version per name (the active pointer);
previous ACTIVE versions become RETIRED (kept for audit / rollback). Activation REQUIRES status VERIFIED (stop condition S8) and an explicit
acceptance. Disabled procedures stay stored but cannot be called. Everything is logged."""
import sqlite3, json, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import lang as L
SCHEMA = """
CREATE TABLE IF NOT EXISTS procedures(procedure_id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL, program_json TEXT NOT NULL,
  parameters_json TEXT NOT NULL, preconditions_json TEXT NOT NULL, postconditions_json TEXT NOT NULL, created_at TEXT NOT NULL, source_hash TEXT NOT NULL,
  program_hash TEXT NOT NULL, effect TEXT, returns TEXT, parent_version TEXT, change_reason TEXT, proposer TEXT);
CREATE TABLE IF NOT EXISTS procedure_examples(procedure_id TEXT NOT NULL, interaction_id TEXT NOT NULL, role TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS procedure_tests(procedure_id TEXT NOT NULL, test_id TEXT NOT NULL, passed INTEGER NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS procedure_aliases(procedure_id TEXT NOT NULL, alias TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS active_pointer(name TEXT PRIMARY KEY, procedure_id TEXT NOT NULL, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS provenance(procedure_id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lib_log(n INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, json TEXT NOT NULL);
"""


class Library:
    def __init__(self, path): self.path = path; self.db = sqlite3.connect(path); self.db.executescript(SCHEMA); self.db.commit()

    def close(self): self.db.close()

    def log(self, event, obj): self.db.execute("INSERT INTO lib_log(event, json) VALUES(?,?)", (event, json.dumps(obj, sort_keys=True, default=str))); self.db.commit()

    def add_candidate(self, proc, provenance, examples, ts, source_hash, parent=None, reason=None):
        v = (self.db.execute("SELECT MAX(version) FROM procedures WHERE name=?", (proc["name"],)).fetchone()[0] or 0) + 1; pid = f"proc:{proc['name']}:v{v}"
        body = {"name": proc["name"], "parameters": proc["parameters"], "body": proc["body"]}
        self.db.execute("INSERT INTO procedures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid, proc["name"], v, "CANDIDATE", L.canonical_json(body), json.dumps(proc["parameters"]),
                        json.dumps([s for s in proc["body"] if s["op"] == "PRECONDITION"]), "[]", ts, source_hash, L.program_hash(body), None, None, parent, reason, provenance.get("proposer")))
        for iid, role in examples: self.db.execute("INSERT INTO procedure_examples VALUES(?,?,?)", (pid, iid, role))
        self.db.execute("INSERT INTO provenance VALUES(?,?)", (pid, json.dumps(provenance, sort_keys=True, default=str))); self.db.commit(); self.log("CANDIDATE", {"id": pid}); return pid

    def set_status(self, pid, status, effect=None, returns=None):
        self.db.execute("UPDATE procedures SET status=?, effect=COALESCE(?, effect), returns=COALESCE(?, returns) WHERE procedure_id=?", (status, effect, returns, pid)); self.db.commit(); self.log(status, {"id": pid})

    def record_tests(self, pid, tests):
        for tid, passed, res in tests: self.db.execute("INSERT INTO procedure_tests VALUES(?,?,?,?)", (pid, tid, int(passed), json.dumps(res, sort_keys=True, default=str)))
        self.db.commit()

    def status(self, pid):
        r = self.db.execute("SELECT status FROM procedures WHERE procedure_id=?", (pid,)).fetchone(); return r[0] if r else None

    def activate(self, pid):
        """explicit acceptance of a VERIFIED version; the previous ACTIVE version (if any) is RETIRED, never deleted"""
        st = self.status(pid)
        if st != "VERIFIED": raise PermissionError(f"STOP-S8 guard: cannot activate {pid} in status {st}")
        name = self.db.execute("SELECT name FROM procedures WHERE procedure_id=?", (pid,)).fetchone()[0]
        old = self.db.execute("SELECT procedure_id FROM active_pointer WHERE name=?", (name,)).fetchone()
        if old: self.db.execute("UPDATE procedures SET status='RETIRED' WHERE procedure_id=?", (old[0],))
        self.db.execute("UPDATE procedures SET status='ACTIVE' WHERE procedure_id=?", (pid,)); self.db.execute("INSERT OR REPLACE INTO active_pointer VALUES(?,?,1)", (name, pid))
        self.db.commit(); self.log("ACTIVATE", {"id": pid, "retired": old[0] if old else None})

    def get(self, pid):
        r = self.db.execute("SELECT program_json, effect, returns FROM procedures WHERE procedure_id=?", (pid,)).fetchone()
        if not r: return None
        p = json.loads(r[0]); p["_id"] = pid; p["_effect"] = r[1]; p["_returns"] = r[2]; return p

    def active(self, name):
        r = self.db.execute("SELECT procedure_id, enabled FROM active_pointer WHERE name=?", (name,)).fetchone()
        if not r or not r[1]: return None
        p = self.get(r[0]); return {k: v for k, v in p.items() if not k.startswith("_")} if p else None

    def active_id(self, name):
        r = self.db.execute("SELECT procedure_id, enabled FROM active_pointer WHERE name=?", (name,)).fetchone(); return r[0] if r and r[1] else None

    def list_active(self):
        out = []
        for name, pid in self.db.execute("SELECT name, procedure_id FROM active_pointer WHERE enabled=1 ORDER BY name").fetchall():
            p = self.get(pid); out.append({"name": name, "id": pid, "parameters": p["parameters"], "effect": p["_effect"], "returns": p["_returns"], "aliases": self.aliases(pid)})
        return out

    def set_enabled(self, name, on):
        if not self.db.execute("SELECT 1 FROM active_pointer WHERE name=?", (name,)).fetchone(): raise KeyError(name)
        self.db.execute("UPDATE active_pointer SET enabled=? WHERE name=?", (int(on), name)); self.db.commit(); self.log("ENABLE" if on else "DISABLE", {"name": name})

    def delete(self, name):
        self.db.execute("UPDATE procedures SET status='DELETED' WHERE name=? AND status='ACTIVE'", (name,)); self.db.execute("DELETE FROM active_pointer WHERE name=?", (name,)); self.db.commit(); self.log("DELETE", {"name": name})

    def add_alias(self, name_or_pid, alias):
        pid = name_or_pid if name_or_pid.startswith("proc:") else self.active_id(name_or_pid)
        if pid is None: raise KeyError(name_or_pid)
        self.db.execute("INSERT INTO procedure_aliases VALUES(?,?)", (pid, alias.lower())); self.db.commit(); self.log("ALIAS", {"id": pid, "alias": alias.lower()})

    def aliases(self, pid): return sorted({a for (a,) in self.db.execute("SELECT alias FROM procedure_aliases WHERE procedure_id=?", (pid,))})

    def versions(self, name):
        return [dict(zip(("id", "version", "status", "program_hash", "parent", "reason", "proposer"), r)) for r in self.db.execute(
            "SELECT procedure_id, version, status, program_hash, parent_version, change_reason, proposer FROM procedures WHERE name=? ORDER BY version", (name,))]

    def explain(self, name):
        vs = self.versions(name)
        if not vs: return None
        pid = self.active_id(name) or vs[-1]["id"]; p = self.get(pid); prov = json.loads(self.db.execute("SELECT json FROM provenance WHERE procedure_id=?", (pid,)).fetchone()[0])
        tests = [dict(zip(("test", "passed"), r)) for r in self.db.execute("SELECT test_id, passed FROM procedure_tests WHERE procedure_id=?", (pid,))]
        deps = sorted({s["procedure"] for s in _walk(p["body"]) if s["op"] == "CALL"})
        return {"signature": f"{name}(" + ", ".join(f"{x['name']}:{x['type']}" for x in p["parameters"]) + f") -> {p['_returns']}  [{p['_effect']}]", "id": pid,
                "status": self.status(pid), "enabled": bool(self.active_id(name)), "dependencies": deps, "source_interactions": prov.get("source_interactions"), "provenance": prov,
                "verification": tests, "program": L.fmt_procedure(p), "aliases": self.aliases(pid), "version_history": vs}

    def library_bytes(self): return os.path.getsize(self.path)

    def canonical(self):
        rows = self.db.execute("SELECT procedure_id, status, program_hash FROM procedures ORDER BY procedure_id").fetchall()
        return {"procedures": [list(r) for r in rows], "active": [list(r) for r in self.db.execute("SELECT name, procedure_id, enabled FROM active_pointer ORDER BY name")],
                "aliases": sorted([list(r) for r in self.db.execute("SELECT procedure_id, alias FROM procedure_aliases")])}

    def hash(self): return hashlib.sha256(json.dumps(self.canonical(), sort_keys=True).encode()).hexdigest()


def _walk(ss):
    for s in ss:
        yield s
        for k in ("body", "then", "else"):
            if k in s: yield from _walk(s[k])
