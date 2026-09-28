"""POST-HANDOFF network guard (spec §25, §68): loaded into every reuse-phase process via PYTHONPATH. Any socket connection to a
non-loopback address is BLOCKED and logged to $NETGUARD_LOG (one JSON line per attempt). Loopback (the local student LLM service) is allowed."""
import os, socket, json, time
_LOG = os.environ.get("NETGUARD_LOG"); _orig_connect = socket.socket.connect; _orig_cc = socket.create_connection
def _ok(addr):
    try: host = addr[0] if isinstance(addr, tuple) else str(addr)
    except Exception: return False
    return host in ("127.0.0.1", "localhost", "::1") or str(host).startswith("127.")
def _log(addr):
    if _LOG:
        with open(_LOG, "a") as f: f.write(json.dumps({"t": time.time(), "pid": os.getpid(), "addr": str(addr)}) + "\n")
def connect(self, addr):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _ok(addr): _log(addr); raise ConnectionRefusedError(f"netguard: blocked {addr}")
    return _orig_connect(self, addr)
def create_connection(addr, *a, **k):
    if not _ok(addr): _log(addr); raise ConnectionRefusedError(f"netguard: blocked {addr}")
    return _orig_cc(addr, *a, **k)
socket.socket.connect = connect; socket.create_connection = create_connection
os.environ["PDX_NETGUARD_ACTIVE"] = "1"
