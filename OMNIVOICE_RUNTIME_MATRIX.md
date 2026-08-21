# OMNIVOICE RUNTIME MATRIX

**Target Version:** OmniVoice 0.2.1  
**Architecture:** Process-isolated worker communicating via JSONL IPC.

---

## 1. Supported Platform & Acceleration Matrix

| Platform | Arch | Acceleration | Engine Backend | Status | Notes |
|---|---|---|---|---|---|
| Windows | x86_64 | CUDA (NVIDIA) | `torch` + `cuda` | Supported | Recommended for high throughput dubbing |
| Windows | x86_64 | CPU | `torch` (CPU) | Supported | Default fallback for generic PCs |
| macOS | arm64 | MPS (Apple Silicon) | `torch` + `mps` | Supported | Metal Performance Shaders |
| macOS | x86_64 | CPU | `torch` (CPU) | Supported | Intel Mac fallback |
| Linux | x86_64 | CUDA / CPU | `torch` | Supported | Headless / container environments |

---

## 2. Capability Matrix by Provider

| Feature | CapCut | VieNeu | OmniVoice |
|---|---|---|---|
| Preset Voices | ✅ Yes | ✅ Yes (Vietnamese/English) | ❌ No (Zero-shot / Design) |
| Voice Cloning | ❌ No | ✅ Yes (VieNeu ONNX speaker encoder) | ✅ Yes (VoiceClonePrompt `.pt`) |
| Streaming | ❌ No | ✅ Yes (v3 Turbo ONNX) | ❌ No (Batch cue / wav generation) |
| Multilingual (600+) | ❌ No | ❌ No (VI, EN) | ✅ Yes |
| Voice Design (Prompt) | ❌ No | ❌ No | ✅ Yes |
| Target Duration (SRT) | ❌ No | ❌ No | ✅ Yes (Native pacing) |
| Text Normalization | ❌ No | ❌ No | ✅ Yes |
| Cross-lingual Clone | ❌ No | ❌ No | ✅ Yes |
| Isolation Model | Remote API | In-process ModelManager | Out-of-process Worker (IPC) |
