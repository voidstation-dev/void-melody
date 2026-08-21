# OMNIVOICE RUNTIME MATRIX

**Target Version:** OmniVoice 0.2.1  
**Architecture:** Process-isolated worker communicating via JSONL IPC.

---

## 1. Platform & Verification Status Matrix

| Platform | Arch | Target | Contract Tested (Mock) | Real Runtime Tested | Packaged Tested | Notes |
|---|---|---|---|---|---|---|
| Windows | x86_64 CPU | Yes | PASS | Pending O3+ | Pending O15 | Default fallback for PC |
| Windows | x86_64 CUDA | Yes | PASS | Pending O3+ | Pending O15 | Recommended for GPU acceleration |
| macOS | arm64 (MPS) | Yes | PASS | Pending O3+ | Pending O15 | Apple Silicon MPS |
| macOS | x86_64 CPU | Optional | PASS | Pending O3+ | Pending O15 | Intel Mac fallback |
| Linux | x86_64 CPU/CUDA | Yes | PASS | Pending O3+ | Pending O15 | CI / Server environments |

*Note: Platform entries are only labeled "Verified / Production Ready" once real-runtime tests (O3+) and packaging smoke tests (O15) pass on target hardware.*

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
