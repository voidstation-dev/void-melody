# Voice Lab runtime matrix

This is the release record for the pinned VieNeu v3 Turbo integration. It deliberately distinguishes verified behavior from environments that still need a packaged desktop run.

| Runtime | Capability result | Verification |
|---|---|---|
| macOS arm64, CPU, ONNX | Preset voices, reference cloning, and denoise are available when the ONNX runtime probe succeeds | Local `probe_runtime()` contract tests and API capability test |
| CUDA/PyTorch | Supported by the capability contract when the CUDA runtime probe succeeds; not exercised on this host | Requires a CUDA-equipped verification runner |
| Tauri packaged sidecar | Not verified in this environment | Requires the desktop toolchain, bundled FFmpeg, and generated sidecar assets |

The API exposes `GET /api/v1/tts/voices/capabilities` so the UI gates cloning from the actual runtime instead of assuming that every packaged machine has the same backend. Set `VOICE_LAB_ENABLED=false` to roll back the Voice Lab surface without changing existing preset/custom TTS routes.
