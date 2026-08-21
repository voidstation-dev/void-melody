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
- **Model Parameters:** ~0.6B
- **Model Revision:** `main` (commit SHA pinned in `runtime-manifest.json` during packaging)
- **Weights License:** Creative Commons Attribution-NonCommercial (CC-BY-NC 4.0)
- **Code License:** Apache-2.0
- **Supported Audio Sample Rate:** 24,000 Hz (24 kHz)
- **Multilingual Support:** 600+ languages

---

## 3. Dependency Isolation Strategy

OmniVoice will **NOT** be included in `apps/api/pyproject.toml`. It will run in an isolated subprocess (`apps/omnivoice-worker`) managed via a JSONL IPC protocol (`OmniVoiceRuntimeClient`).
This ensures:
1. Zero bloat in the base installer.
2. No dependency or version conflicts with FastAPI/VieNeu/PyInstaller.
3. Clean crash recovery and resource arbitration.
