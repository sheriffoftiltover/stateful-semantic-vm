"""JobSpec: the backend-independent description of one job (SEMVM execution backend v1).
Scientific inputs (job_type, args) are separated from infrastructure hints (profile, timeout). A backend may read ONLY the infrastructure part to
decide where / how to run; the job itself is always executed as `python <experiment_root>/run_job.py --spec-json '<spec>' --output <dir>`, i.e. the
same scientific entry point on every backend. Output location is logical: results/<job_id>/ (backends map it to a physical location and collect it
back into that layout)."""
import json, hashlib, time
from dataclasses import dataclass, field, asdict

SCIENTIFIC_FIELDS = ("job_type", "args")
INFRA_FIELDS = ("profile", "timeout_s", "local_device")


@dataclass
class JobSpec:
    job_id: str                      # unique, immutable (attempt-qualified), e.g. "d1/C30/STRUCTURAL_s17/attempt_001"
    job_type: str                    # e.g. "corpus-candidate", "fit-pilot", "train", "smoke"
    args: dict = field(default_factory=dict)      # SCIENTIFIC arguments only (candidate, arm, seed, epoch cap, ...)
    profile: str = "cpu-small"      # resource profile name (profiles.json)
    timeout_s: int = 4 * 3600
    local_device: str = None         # local backend only: CUDA_VISIBLE_DEVICES value (infrastructure)

    def scientific_hash(self):
        return hashlib.sha256(json.dumps({k: getattr(self, k) for k in SCIENTIFIC_FIELDS}, sort_keys=True).encode()).hexdigest()

    def to_json(self): return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_json(s): return JobSpec(**json.loads(s))


def stamp(): return time.strftime("%F %T %z")
