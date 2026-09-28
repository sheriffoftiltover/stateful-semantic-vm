# Release security audit

- **Date:** 2026-09-28.
- **Scope:** every file in this repository at the release commit: 14,177 files, 488.5 MB scanned (508 MB on disk). Git metadata was excluded.
- **Tool:** `scripts/release_scan.py`. It prints only counts and paths, never matched values.
- **Verdict:** **SCAN_CLEAN.** Both passes found nothing.

## What must never be published, and how it was checked

| Class | Check | Result |
|---|---|---|
| Hosted teacher API key used by PDX / HTG / TTP / RCI | Pass 1: exact byte match of the key, loaded from the author's local secret file | 0 files |
| Hosted endpoint URLs (four Modal apps) | Pass 1: exact match of each URL **and** of each URL's host name | 0 files |
| Third-party provider key (GROQ, used in earlier planning) | Pass 1: exact match of the value from the author's environment | 0 files |
| Generic credential formats: OpenAI-style `sk-`, `gsk_`, `hf_`, GitHub (`ghp_` …, `github_pat_`), AWS `AKIA`, Slack `xox*`, Modal `ak-`/`as-`, PEM private keys, literal `Bearer` tokens | Pass 2: regex over raw bytes of every file, including SQLite and binary files | 0 hits |
| Hosted endpoint patterns (`*.modal.run`) and Modal dashboard links (workspace names) | Pass 2 | 0 hits |
| E-mail addresses | Pass 2 | 0 hits |
| Personal filesystem paths (`/home/<user>/`, `/media/<user>/`, `/tmp/claude-N`) | Pass 2 | 0 hits |
| Username / work-e-mail remnants | Separate `grep` over text files, and `grep -a` over SQLite / PDF / PNG / PT files | Only the intended `github.com/sheriffoftiltover/stateful-semantic-vm` |

The final scan output is below. The same scan also ran, clean, before the docs and paper were finalized.

```
PASS 1 (known values):   teacher_key 0 | teacher_url 0 (+host 0) | htg_url 0 (+host 0) | rci_url 0 (+host 0) | ttp_url 0 (+host 0) | groq 0
PASS 2 (patterns):       all 15 patterns: 0 hits, 0 allow-listed
SCAN_CLEAN
```

## Sanitization policy (see `scripts/build_release.py`)

- **Built from scratch.** The repository was assembled by the builder as a new tree. The author's internal git history is **not** included.
- **Path replacement.** Absolute machine paths in text files were replaced by placeholders: `$SEMVM_INTERNAL_ROOT`, `$ML_ROOT`, `$HOME`, `$JOB_TMP`, `$JOB_DIR`.
  - 1,170 files were changed.
  - Each changed file's original and released sha256, and its substitution count, are in `PROVENANCE_SANITIZATION.json`. Freeze-manifest hashes can therefore still be checked against the original values.
- **One code edit for portability.** The evaluators' hard-coded interpreter path became `SEMVM_LLM_PYTHON`, and it is recorded in the same file.
- **Not published:**
  - transient work directories, world snapshots, student-service logs, pid files and `__pycache__`;
  - the contents of sealed LOCKED sets that were never run (NL_TEACH, PDX, HTG/TTP). Their hash manifests are published.
- **By design, credentials never reach artifacts.** Teacher credentials were passed only through environment variables. They were scrubbed before every reuse process, and the network guard logged any egress attempt; all post-handoff attempt counts are 0.
- **Response caches were scanned like everything else.** They record provenance (request hash, token counts, finish reason, latency), not headers or keys.
- **No model weights are published** except the small frozen binder checkpoint of END_TO_END_POC_V1 (2.95 MB). It is present, byte-identical, in each of the seven as-run trees, and git stores it once. No file exceeds 20 MB.

## Residual risks and notes

- **The hosted apps are stopped.** Even so, a published endpoint URL would only reveal a dead Modal app name, and the scan confirms none is present.
- **Two sealed sets are no longer blind.**
  - HTG and TTP share a sealed LOCKED set that was never run. It was generated from the same template file as the RCI LOCKED set, which *is* published because it was run.
  - Treat that HTG/TTP set as no longer blind; its scenario contents are still withheld.
- **Re-run before publishing.** Anyone preparing a derived release should run `python scripts/release_scan.py --known <secret files>` first.
