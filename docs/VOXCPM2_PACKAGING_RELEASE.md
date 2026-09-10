# VoxCPM2 — Packaging & Release Notes (Phase 11)

Status: Phase 11 (descriptive / docs phase). The integration ships with a
**bootstrap-only** packaging contract: no model weights and no heavy Python
wheels are ever bundled into an installer.

## What ships in the installer

- The VoxCPM2 worker source (`apps/voxcpm-worker/worker.py` + backends) —
  plain Python, no dependencies.
- The lifecycle/bootstrap code (`app/services/voxcpm_env.py`,
  `app/services/voxcpm_lifecycle.py`) that lazily creates the dedicated
  worker environment on demand.
- Nothing else. `torch`, `torchaudio`, `voxcpm`, and the 4.6 GB HF
  checkpoint are **never** in the installer.

## What is bootstrapped at runtime (user-initiated)

1. **Worker env** — created under the app data dir (`data/envs/voxcpm`)
   with `uv` (preferred) or `python -m venv`, requiring Python
   `>=3.10,<3.13`. `VOID_VOXCPM_PYTHON` overrides the interpreter.
2. **Runtime deps** — `pip install .[runtime]` from `apps/voxcpm-worker/`
   **inside the dedicated env only** (voxcpm>=2.0,<3.0, torch>=2.5, torchaudio,
   numpy, soundfile). Idempotent via the `voxcpm-runtime.installed` marker.
3. **Model weights** — `openbmb/VoxCPM2` (~4.6 GB) is pulled by HF
   `from_pretrained` into the shared HF cache on first `load_model`, with
   coarse progress exposed via `GET /api/v1/voxcpm/installation/download-progress`.

All three steps are user-triggered from **Settings → Local AI → VoxCPM2
Studio** (Install runtime / Verify) or happen transparently on the first
VoxCPM2 synthesis. They can be undone with Remove runtime (env) and Delete
model (HF cache) in the same card.

## Platform support matrix (target)

| Platform | Accelerator | Status |
|---|---|---|
| Windows x64 | CUDA | Supported — worker resolves `device="auto"` |
| Windows x64 | CPU | Supported (reference behavior; slowest) |
| macOS ARM64 | MPS | Planned — verify `from_pretrained` device handling |
| macOS ARM64 | CPU | Supported |

The worker defaults to `device="auto"`; explicit device selection from the
Settings/Runtime UI is a follow-up. Device compatibility questions are
answered by `GET /api/v1/voxcpm/runtime-state` + the worker's `runtime_info`
RPC, never by spawning a worker from a status probe.

## Release invariants (must hold on every packaged build)

1. No VoxCPM2 model weights or `torch` wheels inside the installer or its
   caches.
2. The FastAPI main environment must never import `torch`/`voxcpm`; the
   Phase 10 verify action proves importability **inside the dedicated env**.
3. No silent provider fallback: VoxCPM2 jobs succeed via the VoxCPM2 runtime
   or fail explicitly (`PROVIDER_REJECTED` / `PROVIDER_TIMEOUT` /
   `VOXCPM_RUNTIME_BUSY`).
4. Unload-before-load via `SpeechRuntimeCoordinator` — at most one heavy
   speech runtime resident.
5. VoxCPM2 identity assets (`tts_voxcpm_voices`, `data/voices/voxcpm2/`)
   remain isolated from VieNeu's `tts_custom_voices`.

## Versioning

The worker package (`melody-voxcpm-worker`) is versioned independently at
`0.1.0`. Bump it whenever `worker.py`/backends change protocol or behavior;
the JSONL RPC protocol version is carried by the worker's `ping`/handshake.