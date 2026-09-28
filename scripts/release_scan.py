"""Release secret scan (two independent passes). Prints counts and file paths only, never matched secret values.

python scripts/release_scan.py [--known FILE ...]

Pass 1 (known values): every --known FILE holds a secret the author knows was used (an API key, a hosted endpoint URL, ...).
  The file's stripped content, and its host name if it is a URL, are searched for verbatim in every file of the tree.
Pass 2 (patterns): generic credential / endpoint / personal-path patterns, case-insensitive where appropriate.
Exit status 0 only if pass 1 finds nothing and every pass-2 hit is in the allow-list below (documented false positives)."""
import os, re, sys, argparse, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__"}
PATTERNS = {
    "openai_style_key": r"\bsk-[A-Za-z0-9_\-]{20,}",
    "groq_key": r"\bgsk_[A-Za-z0-9]{20,}",
    "hf_token": r"\bhf_[A-Za-z0-9]{30,}",
    "github_token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}",
    "aws_key": r"\bAKIA[0-9A-Z]{16}\b",
    "slack_token": r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",
    "modal_token": r"\b(ak|as)-[A-Za-z0-9]{20,}\b",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "bearer_literal": r"Bearer\s+[A-Za-z0-9_\-\.]{20,}",
    "modal_endpoint": r"https?://[A-Za-z0-9\-\.]+\.modal\.run",
    "modal_dashboard": r"modal\.com/(apps|logs|settings|storage)/",
    "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "home_path": r"/home/[a-z][a-z0-9_\-]*/",
    "media_path": r"/media/[a-z][a-z0-9_\-]*/",
    "tmp_claude_path": r"/tmp/claude-\d+",
}
# documented false positives: (pattern, substring of the matched text)
ALLOW = [("email", "noreply@anthropic.com"), ("email", "users.noreply.github.com"), ("email", "@users.noreply"),
         ("email", "example.com"), ("email", "git@github.com")]


def files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns: yield os.path.join(dp, fn)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--known", nargs="*", default=[]); a = ap.parse_args()
    needles = []
    for k in a.known:
        v = open(k).read().strip()
        if not v: continue
        needles.append((os.path.basename(k), v.encode()))
        if v.startswith("http"):
            host = urllib.parse.urlparse(v).hostname
            if host: needles.append((os.path.basename(k) + ":host", host.encode()))
    comp = {n: re.compile(p.encode()) for n, p in PATTERNS.items()}
    p1 = {n: [] for n, _ in needles}; p2 = {n: [] for n in PATTERNS}; allowed = {n: 0 for n in PATTERNS}; nf = 0; nb = 0
    self_path = os.path.abspath(__file__)
    for f in files():
        try: raw = open(f, "rb").read()
        except OSError: continue
        nf += 1; nb += len(raw); rel = os.path.relpath(f, ROOT)
        for n, v in needles:
            if v in raw: p1[n].append(rel)
        if os.path.abspath(f) == self_path: continue   # this file contains the patterns themselves
        for n, rx in comp.items():
            for m in rx.finditer(raw):
                s = m.group(0).decode("utf-8", "replace")
                if any(n == an and sub in s for an, sub in ALLOW): allowed[n] += 1; continue
                p2[n].append(rel)
    print(f"scanned {nf} files, {nb / 1e6:.1f} MB")
    print("PASS 1 (known values):")
    for n, hits in p1.items(): print(f"  {n:28s} files matched: {len(set(hits))}" + (f"  {sorted(set(hits))[:10]}" if hits else ""))
    print("PASS 2 (patterns):")
    for n, hits in p2.items(): print(f"  {n:18s} hits: {len(hits):4d} allowed: {allowed[n]:4d}" + (f"  files: {sorted(set(hits))[:10]}" if hits else ""))
    ok = not any(p1.values()) and not any(p2.values())
    print("SCAN_CLEAN" if ok else "SCAN_FINDINGS"); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
