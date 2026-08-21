# Voice Lab runtime matrix

This is the release record for the pinned VieNeu v3 Turbo integration. It deliberately distinguishes verified behavior from environments that still need a packaged desktop run.

| Runtime | Capability result | Verification |
|---|---|---|
| macOS arm64, CPU, ONNX | Preset voices are available when ONNX Runtime is present. Cloning is enabled only when `torch`, `torchaudio`, speaker encoder, denoiser, and codec-encode artifacts are present and enrollment preflight succeeds. | Capability and clone-gate tests pass locally; this host reports clone unavailable because `torch`/`torchaudio` and model artifacts are absent. Packaged smoke not run. |
| macOS Intel, CPU, ONNX | Same explicit preset/clone distinction as macOS arm64. | Not verified on a packaged Intel runner. |
| Windows, CPU, ONNX | Preset voices should use the CPU ONNX path; cloning remains disabled until the frontend/artifact/preflight gate passes. | Not verified on a packaged Windows CPU runner. |
| Windows, CUDA, PyTorch | Preset and clone support depend on the packaged CUDA/PyTorch runtime and a successful enrollment preflight. | Not verified on a CUDA-equipped Windows runner. |
| Tauri packaged sidecar | Not marked supported until the sidecar, bundled FFmpeg, and selected hardware matrix each pass smoke verification. | Local `cargo check` and web production build pass; full packaged smoke requires generated sidecar assets and target runners. |

The API exposes `GET /api/v1/tts/voices/capabilities` so the UI gates cloning from the actual runtime instead of assuming that every packaged machine has the same backend. The clone endpoint repeats the gate and runs a real shared-provider enrollment preflight. Set `VOICE_LAB_ENABLED=false` to roll back the Voice Lab surface without changing existing preset/custom TTS routes.
