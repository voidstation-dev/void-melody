# OMNIVOICE PHASE O0 — BASELINE REPORT

**Project:** `voidstation-dev/void-melody`  
**Date:** 2026-08-21  
**Baseline commit:** `6ae329a` (on `main`)  
**Base release version:** `0.2.7`  
**Scope:** Re-baseline and contract freeze before OmniVoice integration.

---

## 1. Repository State & Test Gates

All unit tests pass at baseline:
- `apps/api`: 116 / 116 tests PASS (`test:api`)
- `packages/vieneu-core`: 36 / 36 tests PASS (`pytest`)

Active providers in baseline:
1. `capcut` (remote / legacy)
2. `vieneu` (local VieNeu v3 Turbo ONNX/PyTorch engine)

---

## 2. Pinned OmniVoice Target Specifications

- **OmniVoice Package Version:** `0.2.1` (pinned)
- **Model Repository:** `k2-fsa/OmniVoice` (Hugging Face)
- **Model Parameters:** ~0.6B (612,577,288 params in float32 / safetensors)
- **Model Revision SHA:** `c5fdb5ccb189668d56333f77ba2629f4cd7535f4` (resolved and pinned 2026-08-21)
- **Weights License:** Creative Commons Attribution-NonCommercial (CC-BY-NC 4.0)
- **Code License:** Apache-2.0
- **Supported Audio Sample Rate:** 24,000 Hz (24 kHz)
- **Multilingual Support:** 600+ languages
- **Audio Tokenizer Subdirectory:** `audio_tokenizer/`

---

## 3. Dependency Isolation Strategy

OmniVoice introduces no additional OmniVoice/Transformers/model dependencies into the base API environment.
OmniVoice will **NOT** be included in `apps/api/pyproject.toml`. It will run in an isolated subprocess (`apps/omnivoice-worker`) managed via a JSONL IPC protocol (`OmniVoiceRuntimeClient`).

This ensures:
1. No OmniVoice or Transformers dependencies are bundled into the base API distribution.
2. Independent lifecycle, crash recovery, and resource arbitration.
3. No dependency or version conflicts with FastAPI, VieNeu, or PyInstaller.
