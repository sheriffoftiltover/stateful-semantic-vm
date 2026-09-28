# Environment notes

## What the bundle needs
- Linux x86-64, Python 3.10 (tested: 3.10.12), with `venv` and `ensurepip`.
- NVIDIA driver supporting CUDA 12.1 wheels (tested: driver 580.119.02). A system CUDA toolkit is **not** needed: the PyTorch wheel ships its CUDA/cuDNN runtime as pip packages (`nvidia-*-cu12`).
- Network access to https://pypi.org and https://download.pytorch.org/whl/cu121 at install time only.

## Files
| File | Purpose |
|---|---|
| `requirements.txt` | Minimal specification: the three direct dependencies (torch, numpy, scipy), with the PyTorch CUDA 12.1 wheel index. |
| `requirements-lock.txt` | Every package resolved in a clean venv built from `requirements.txt` on the source machine. **Use this one for reproduction.** |
| `pip_freeze_source.txt` | Provenance only: the original source environment. It is not portable (torch came from a `.pth` link into a ComfyUI venv) and must not be recreated. |
| `python_info.txt`, `torch_cuda_info.txt` | Interpreter, torch, CUDA, cuDNN and GPU of the clean source-side resolve environment. |

## Direct dependencies actually used at run time
The runtime traces found only these third-party modules loaded by project code: `torch`, `numpy`, `scipy`. torch in turn loads typing_extensions, sympy, filelock, jinja2, networkx, fsspec and the nvidia-* runtime libraries. `sklearn` is used only by predecessor dataset gates, which are not executed here, so it is not a dependency. Everything else is the Python standard library.

## Numerical settings
These are the values the registered runs used. The launchers print them, and they must not be changed.

| Setting | Value | Set by |
|---|---|---|
| `torch.use_deterministic_algorithms` | `True` | the locked code |
| `torch.backends.cudnn.benchmark` | `False` | the locked training code |
| `CUBLAS_WORKSPACE_CONFIG` | `:4096:8` | the locked code (`setdefault`) and the launchers (explicitly) |
| `torch.backends.cuda.matmul.allow_tf32` | `False` | PyTorch 2.5 default; not changed |
| `torch.backends.cudnn.allow_tf32` | `True` | PyTorch 2.5 default; not changed. The model uses no convolutions, so cuDNN TF32 has no effect. |
| AMP / mixed precision | not used (float32 training) | |
| dropout | 0.0 | no RNG is consumed during training |

## Expected nondeterminism across hardware
For this experiment the reference local GPU is the RTX 3060 (sm_86); scientific runs may execute on Modal GPUs (see the benchmark report and results/MODAL_BUDGET_STATE.json). Cross-architecture bit-equality is NOT claimed.

- **Same GPU class, same versions:** training, evaluation and analysis reproduce bit-exactly. This is tested by `run_validation.py` (trainer, scientific) and by `run_analysis.py` / `run_evaluation.py`.
- **Different GPU architecture:**
  - Floating-point reduction order in cuBLAS and in scatter/segment kernels can differ.
  - Deterministic mode guarantees run-to-run determinism on one device, not bit equality across architectures.
  - Expect small numeric drift that can compound over training. In practice this can move early-stop epochs and, with them, headline metrics.
  - Cross-hardware results must be compared with the registered tolerances in `README_RUN.md`, not bit-for-bit.
- **Different library versions** (torch, CUDA, cuDNN): same caveat as a different architecture. Use `requirements-lock.txt`.
