"""Persistent world model (spec §7-§8, §35): SQLite, explicit transactions, deterministic persistent IDs (<type>:<6-digit per-type counter>),
scalar values with natural keys (<type>:<normalized>), logical timestamps (scenario reference time + turn), canonical state + STATE_SHA256."""
import sqlite3, json, hashlib
SCHEMA = """
CREATE TABLE IF NOT EXISTS objects(object_id TEXT PRIMARY KEY, object_type TEXT NOT NULL, created_at TEXT NOT NULL, created_by_utterance TEXT, status TEXT NOT NULL, seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS relations(relation_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, predicate TEXT NOT NULL, object_id TEXT NOT NULL, created_at TEXT NOT NULL, created_by_utterance TEXT, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS aliases(alias_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, alias_text TEXT NOT NULL, normalized_alias TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scalar_values(value_id TEXT PRIMARY KEY, value_type TEXT NOT NULL, normalized_value TEXT, surface_value TEXT);
CREATE TABLE IF NOT EXISTS utterances(utterance_id TEXT PRIMARY KEY, raw_text TEXT NOT NULL, timestamp TEXT NOT NULL, parse_status TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(transaction_id TEXT PRIMARY KEY, utterance_id TEXT NOT NULL, committed INTEGER NOT NULL, state_diff_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY, next INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS audit(utterance_id TEXT PRIMARY KEY, record_json TEXT NOT NULL);
"""


class Store:
    def __init__(self, path):
        self.path = path; self.db = sqlite3.connect(path, isolation_level=None); self.db.executescript(SCHEMA); self.in_tx = False

    def close(self): self.db.close()

    # ---- transactions ----
    def begin(self): self.db.execute("BEGIN"); self.in_tx = True
    def commit(self): self.db.execute("COMMIT"); self.in_tx = False
    def rollback(self): self.db.execute("ROLLBACK"); self.in_tx = False

    def _next(self, name):
        r = self.db.execute("SELECT next FROM counters WHERE name=?", (name,)).fetchone(); n = r[0] if r else 1
        self.db.execute("INSERT OR REPLACE INTO counters(name, next) VALUES(?,?)", (name, n + 1)); return n

    # ---- mutations (only called by the VM executor inside a transaction) ----
    def create_object(self, typ, ts, utt):
        n = self._next(f"obj:{typ}"); seq = self._next("seq"); oid = f"{typ.lower()}:{n:06d}"
        self.db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?)", (oid, typ, ts, utt, "active", seq)); return oid

    def add_alias(self, oid, alias, ts):
        n = self._next("alias"); self.db.execute("INSERT INTO aliases VALUES(?,?,?,?,?)", (f"alias:{n:06d}", oid, alias, alias.lower(), ts))

    def ensure_value(self, vid, vtype, norm, surface):
        self.db.execute("INSERT OR IGNORE INTO scalar_values VALUES(?,?,?,?)", (vid, vtype, norm, surface))

    def assert_rel(self, s, p, o, ts, utt):
        n = self._next("rel"); self.db.execute("INSERT INTO relations VALUES(?,?,?,?,?,?,1)", (f"rel:{n:06d}", s, p, o, ts, utt))

    def retract_rel(self, s, p, o):
        return self.db.execute("UPDATE relations SET active=0 WHERE subject_id=? AND predicate=? AND object_id=? AND active=1", (s, p, o)).rowcount

    def delete_object(self, oid):
        self.db.execute("UPDATE objects SET status='deleted' WHERE object_id=?", (oid,))
        return self.db.execute("UPDATE relations SET active=0 WHERE (subject_id=? OR object_id=?) AND active=1", (oid, oid)).rowcount

    def log_utterance(self, uid, raw, ts, status, kind):
        self.db.execute("INSERT OR REPLACE INTO utterances VALUES(?,?,?,?,?)", (uid, raw, ts, status, kind))

    def log_transaction(self, uid, committed, diff):
        self.db.execute("INSERT OR REPLACE INTO transactions VALUES(?,?,?,?)", (f"tx:{uid}", uid, int(committed), json.dumps(diff)))

    def log_audit(self, uid, rec): self.db.execute("INSERT OR REPLACE INTO audit VALUES(?,?)", (uid, json.dumps(rec, sort_keys=True, default=str)))

    # ---- reads ----
    def object(self, oid):
        r = self.db.execute("SELECT object_type, status FROM objects WHERE object_id=?", (oid,)).fetchone(); return {"type": r[0], "status": r[1]} if r else None

    def active_objects(self, typ=None):
        q = "SELECT object_id, object_type FROM objects WHERE status='active'" + (" AND object_type=?" if typ else "") + " ORDER BY seq"
        return self.db.execute(q, (typ,) if typ else ()).fetchall()

    def last_active(self, typ):
        r = self.db.execute("SELECT object_id FROM objects WHERE status='active' AND object_type=? ORDER BY seq DESC LIMIT 1", (typ,)).fetchone(); return r[0] if r else None

    def persons_with_alias(self, alias):
        return [r[0] for r in self.db.execute("SELECT DISTINCT a.object_id FROM aliases a JOIN objects o ON o.object_id=a.object_id WHERE a.normalized_alias=? AND o.status='active' ORDER BY a.object_id", (alias.lower(),))]

    def alias_of(self, oid):
        r = self.db.execute("SELECT alias_text FROM aliases WHERE object_id=? ORDER BY alias_id LIMIT 1", (oid,)).fetchone(); return r[0] if r else None

    def value(self, vid):
        r = self.db.execute("SELECT value_type, normalized_value, surface_value FROM scalar_values WHERE value_id=?", (vid,)).fetchone(); return r

    def rels(self, s=None, p=None, o=None):
        q = "SELECT subject_id, predicate, object_id FROM relations WHERE active=1"; a = []
        for col, v in (("subject_id", s), ("predicate", p), ("object_id", o)):
            if v is not None: q += f" AND {col}=?"; a.append(v)
        return self.db.execute(q + " ORDER BY relation_id", a).fetchall()

    def canonical_state(self):
        return {"objects": sorted([list(r) for r in self.active_objects()]), "relations": sorted([list(r) for r in self.rels()]),
                "aliases": sorted([list(r) for r in self.db.execute("SELECT a.object_id, a.alias_text FROM aliases a JOIN objects o ON o.object_id=a.object_id WHERE o.status='active'")])}

    def state_hash(self): return hashlib.sha256(json.dumps(self.canonical_state(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
