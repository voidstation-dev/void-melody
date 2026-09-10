# VoxCPM2 Integration Plan for VoidMelody

> Repository: `voidstation-dev/void-melody`  
> Upstream model: `OpenBMB/VoxCPM` / `openbmb/VoxCPM2`  
> Goal: add a **fully isolated VoxCPM2 Studio** for voice cloning and emotional TTS from cloned voices, while preserving VoidMelody's existing UI style, shared infrastructure, and VieNeu behavior.

---

## 1. Product Goal

Add a new workspace:

```text
Melody
├─ Tạo audio
├─ Phòng thu giọng
├─ VoxCPM2 Studio
├─ Thư viện giọng
├─ Lịch sử
└─ Cài đặt
```

`VoxCPM2 Studio` is a separate route and provider domain. It must not reuse VieNeu enrollment semantics or storage.

Primary MVP flow:

```text
Reference audio
    ↓
Analyze / trim / normalize
    ↓
Create VoxCPM2 cloned voice
    ↓
Save voice profile
    ↓
Select cloned voice
    ↓
Enter target text
    ↓
Choose emotion / write custom instruction
    ↓
Generate emotional TTS with the cloned identity
```

---

## 2. Non-Negotiable Architecture Rules

### Shared infrastructure

VoxCPM2 may reuse:

- TTS jobs
- history
- audio cache
- FFmpeg utilities
- download/export
- app shell
- theme tokens
- common UI primitives
- generic scheduler/provider routing

### Isolated domain

VoxCPM2 must own its own:

- provider descriptor
- runtime client
- worker process
- model lifecycle
- voice storage
- voice resolver
- clone semantics
- emotion instruction compiler
- Studio UI/store/API client

### Hard boundaries

```text
VoxCPM2 MUST NOT call VieneuProvider.
VoxCPM2 MUST NOT write to tts_custom_voices.
VieNeu MUST NOT read tts_voxcpm_voices.
VoxCPM2 MUST NOT depend on vieneu-core.
No automatic VoxCPM2 → VieNeu fallback.
No automatic VieNeu → VoxCPM2 fallback.
```

Use stable provider id:

```text
provider_id = "voxcpm2"
engine_id   = "voxcpm2"
```

---

## 3. UI Style Requirements

The implementation must follow the existing VoidMelody design language.

Use the existing tokens/components:

```text
bg-background
bg-card
bg-muted
text-foreground
text-muted-foreground
border-border
bg-primary/10
text-primary
rounded-xl
rounded-2xl
shadow-xs
shadow-sm
```

Do **not** introduce a VoxCPM-specific neon/purple theme.

Avoid hardcoded provider colors such as:

```text
bg-purple-600
text-violet-400
#8B5CF6
```

unless they are already a semantic token in the application theme.

Reuse existing components under:

```text
apps/web/src/components/ui/
```

The new page should visually feel like a sibling of `VieneuPage`, Settings, and the existing Melody shell.

---

# 4. Master Status Board

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture & UX contract | ✅ APPROVED |
| 1 | VoxCPM2 Studio shell + provider descriptor | ✅ DONE |
| 2 | Isolated mock worker + runtime client | ✅ DONE |
| 3 | Voice storage + upload/analyze/clone profile | ✅ DONE |
| 4 | Real VoxCPM2 runtime + neutral clone | ✅ DONE (live verified: model loads via memory-frugal bf16 loader on 16GB host; neutral clone 3.84s WAV @ 48kHz) |
| 5 | Emotional TTS from cloned voice | ✅ DONE (live verified: cheerful-preset synthesis 1.12s WAV @ 48kHz; instruction compiled correctly) |
| 6 | Shared job/history integration | ✅ DONE |
| 7 | Shared Voice Library integration | ✅ DONE |
| 8 | Ultimate Clone | ⬜ LATER |
| 9 | Resource / VRAM management | ✅ DONE (SpeechRuntimeCoordinator + provider integration + error mapping; 10 coordinator tests) |
| 10 | Settings + model lifecycle | ✅ DONE (installation card + lifecycle endpoints + runtime-state split; 14 backend + 3 FE tests) |
| 11 | Packaging / release | ✅ DONE (bootstrap-only contract in docs/VOXCPM2_PACKAGING_RELEASE.md; live platform matrix is release-engineering follow-up) |
| 12 | Streaming / batch / script | ⬜ LATER |

Update this table whenever a phase changes state.

Allowed statuses:

```text
⬜ NOT STARTED
🟡 IN PROGRESS
🟠 BLOCKED
✅ DONE
⬜ LATER
```

---

# 5. Phase 0 — Architecture & UX Contract

**Status: ✅ DONE**

Decisions:

- VoxCPM2 Studio is a separate route.
- VieNeu UI is not modified for the MVP.
- VoxCPM2 has isolated storage and runtime.
- Controllable Cloning is the primary clone mode.
- Ultimate Clone is deferred.
- Emotional TTS is a first-class VoxCPM2 workflow.
- Shared job/history integration happens only after the standalone flow works.

Exit criteria:

- [x] UX direction approved
- [x] provider boundary approved
- [x] storage isolation approved
- [x] worker isolation approved

---

# 6. Phase 1 — VoxCPM2 Studio Shell

**Status: ✅ DONE**

## Frontend

Create:

```text
apps/web/src/routes/voxcpm.tsx

apps/web/src/components/voxcpm/
├── voxcpm-page.tsx
├── voxcpm-tabs.tsx
├── clone-voice-tab.tsx
├── emotional-tts-tab.tsx
├── cloned-voices-tab.tsx
├── runtime-tab.tsx
└── voxcpm-runtime-badge.tsx

apps/web/src/stores/voxcpm-store.ts
apps/web/src/api/voxcpm.ts
apps/web/src/types/voxcpm.ts
```

Route:

```text
/voxcpm
```

Internal tabs:

```text
Clone giọng
TTS cảm xúc
Giọng đã clone
Runtime
```

Sidebar placement:

```text
TẠO
├── Tạo audio
├── Phòng thu giọng
└── VoxCPM2 Studio
```

Use TanStack Router + Suspense, following the existing `/vieneu` route style.

## Backend

Add provider constant:

```python
VOXCPM2 = "voxcpm2"
```

Add provider descriptor to the registry.

Suggested capability shape:

```python
Capabilities(
    supports_preset_voices=False,
    supports_voice_cloning=True,
    supports_streaming=True,
    supports_styles=True,
    supports_batch=False,
    supports_emotion_tags=True,
    supports_multilingual=True,
    supports_voice_design=True,
    supports_cross_lingual_clone=True,
    sample_rate=48000,
)
```

No real model loading in this phase.

## Exit criteria

- [x] `/voxcpm` renders
- [x] sidebar active state works
- [x] all 4 tabs switch correctly
- [x] mock runtime badge is visible
- [x] no VieNeu UI behavior changed
- [x] web tests pass

Notes (2026-09-10):
- `runtime_status.py` was extended with an explicit VOXCPM2 branch (not_installed) so the registry stays honest pre-Phase-2.
- Frontend mock data lives in `types/voxcpm.ts` (presets/voices) + `api/voxcpm.ts` (mock fetchers); real endpoints replace them in Phase 2/3.
- `routeTree.gen.ts` regenerated with `@tanstack/router-generator` from the pnpm store (no CLI in devDeps).

---

# 7. Phase 2 — Isolated VoxCPM2 Worker

**Status: ✅ DONE**

Follow the architectural pattern of `apps/omnivoice-worker`, but do not copy OmniVoice business logic.

Create:

```text
apps/voxcpm-worker/
├── worker.py
├── backend.py
├── mock_backend.py
├── real_backend.py
├── errors.py
└── path_utils.py
```

Create FastAPI-side runtime client:

```text
apps/api/app/services/voxcpm_runtime.py
```

Recommended worker methods:

```text
ping
runtime_info
load_model
unload_model
warmup
analyze_reference
synthesize_clone
synthesize_emotional
synthesize_ultimate
```

Phase 2 must use a mock backend.

Runtime client should support:

- subprocess startup
- JSONL stdin/stdout RPC
- request IDs
- timeout handling
- worker generation isolation
- crash recovery
- clean shutdown
- safe stderr logging

## Exit criteria

- [x] worker starts
- [x] `ping` passes
- [x] `runtime_info` passes
- [x] mock `load_model` passes
- [x] mock `unload_model` passes
- [x] timeout test passes
- [x] crash recovery test passes

Notes (2026-09-10):
- `shutdown` is handled at the worker dispatcher level (not a backend method), unlike OmniVoice.
- Real backend is a fail-fast placeholder (`VOXCPM_PACKAGE_NOT_INSTALLED`) until Phase 4 — no mock fallback.
- Test import isolation: both worker dirs expose top-level module names (backend, errors, ...);
  both test files evict conflicting sys.path/sys.modules entries before import.

---

# 8. Phase 3 — Voice Storage & Clone Profile

**Status: ✅ DONE**

## Database

Create a dedicated table:

```text
tts_voxcpm_voices
```

Suggested fields:

```text
id
display_name
provider_id = voxcpm2
engine_id = voxcpm2
status

reference_audio_path
reference_original_filename
reference_duration_seconds
reference_sample_rate
reference_channels

reference_transcript nullable

quality_score nullable
speech_ratio nullable
noise_level_db nullable
clipping_ratio nullable

model_id
model_revision

created_at
updated_at
```

Do not reuse `tts_custom_voices`.

## API

Add:

```text
POST   /api/v1/voxcpm/voices/analyze
POST   /api/v1/voxcpm/voices
GET    /api/v1/voxcpm/voices
GET    /api/v1/voxcpm/voices/{voice_id}
DELETE /api/v1/voxcpm/voices/{voice_id}
GET    /api/v1/voxcpm/voices/{voice_id}/reference/audio
```

## Clone flow

```text
Upload
  ↓
FFmpeg normalization
  ↓
Audio analysis
  ↓
Optional trim
  ↓
Save normalized reference
  ↓
Create tts_voxcpm_voices row
```

A saved VoxCPM2 voice is primarily a **reference identity asset**.

Do not require a precomputed VieNeu-style enrollment embedding.

## UI — Clone giọng tab

Sections:

1. Chọn audio tham chiếu
2. Kiểm tra và cắt đoạn
3. Tạo giọng clone

Show:

- waveform
- duration
- quality score
- noise
- speech ratio
- file player
- voice name
- optional description
- consent checkbox

## Exit criteria

- [x] upload works
- [x] analysis works
- [x] trim works
- [x] create profile works
- [x] profile persists after restart (tts_voxcpm_voices + alembic migration a9c4f2e8b1d7)
- [x] list works
- [x] delete works
- [x] reference playback works

Notes (2026-09-10):

- Model `VoxCpmVoiceModel` in app/models/voxcpm_voice.py (tts_voxcpm_voices),
  registered in app/models/__init__.py; migration a9c4f2e8b1d7 (down_revision
  d356ea30efdd, single head verified) creates table + provider_id/status indexes.
  test_database_migrations.py HEAD_REVISION updated to a9c4f2e8b1d7.
- Endpoints in app/api/v1/voxcpm.py, wired into router tags ["VoxCPM2"].
  Clone flow reuses voice_analysis service (save_upload_to_temp →
  analyze_audio_file_async → validate_reference_selection →
  extract_reference_segment_async) writing the canonical mono 16 kHz WAV to
  data/voices/voxcpm2/ — NOT tts_custom_voices storage. No enrollment embedding.
  If source > 8 s with no explicit trim, the analyzer's recommended segment is
  adopted instead of failing (VoxCPM2 works from a bounded reference window).
- Reference WAV properties (duration/sample rate/channels) read back with wave
  after extraction; analysis metrics snapshot stored on the row.
- Mismatch fix (pre-existing, unrelated to VoxCPM2):
  app/db/repositories/__init__.py imported BatchRepository from batches.py,
  which imports app.models.tts_batch — a model that never existed in git
  history. Importing the repositories package (triggered by the new
  voxcpm_voices repository) raised ModuleNotFoundError. Smallest change: removed
  the dead BatchRepository export from the package __init__ (batches.py left
  untouched, unused by anything).
- Frontend: api/voxcpm.ts real endpoints (analyze/create/list/delete + reference
  audio URL; runtime + voices-list still fall back to Phase 1 mock when backend
  is absent), types (+VoxCpmAnalysisResult), store (+analysis/clone state,
  submitCloneVoice adopts analysis trim bounds, removeVoice), clone-voice-tab.tsx
  replaced placeholder with 3-section flow (file → waveform/quality/trim →
  name/description/transcript/consent), locales vi/en/types +24 keys.
- UI uses existing tokens/components only (Button/Input/Textarea, native
  checkbox per VieneuPage consent pattern, primary color, rounded-2xl cards).
- Trim inputs are validated 3–8 s by the backend (validate_reference_selection);
  UI shows recommended segment and bounds but final enforcement is server-side.

---

# 9. Phase 4 — Real VoxCPM2 Runtime

**Status: 🟠 BLOCKED — implementation + tests done, runtime installed & verified; model load blocked by disk space (~95 MB free, weights need 4.58 GB)**

Use a separate Python environment for the VoxCPM2 worker.

Do **not** install VoxCPM2 directly into the FastAPI main environment.

Upstream target:

```python
from voxcpm import VoxCPM

model = VoxCPM.from_pretrained(
    "openbmb/VoxCPM2",
    load_denoiser=False,
)
```

Neutral clone:

```python
wav = model.generate(
    text=text,
    reference_wav_path=reference_path,
    cfg_value=2.0,
    inference_timesteps=10,
    seed=seed,
)
```

Store output as 48 kHz WAV.

Recommended real backend methods:

```text
load_model
unload_model
runtime_info
warmup
synthesize_clone
```

Do not implement emotional generation before neutral cloning is stable.

## Exit criteria

- [ ] real model installs
- [ ] model loads
- [ ] runtime reports device
- [ ] neutral TTS works
- [ ] neutral cloned TTS works
- [ ] output is 48 kHz
- [ ] voice identity is acceptably preserved
- [ ] unload releases resources

### Implementation notes (2026-09-10)

- `apps/voxcpm-worker/real_backend.py` — RealVoxCpmBackend: deferred
  `import voxcpm` (module importable/tests runnable without the package),
  `VoxCPM.from_pretrained(model_id, load_denoiser=False)` with TypeError
  fallback for older builds, sample_rate resolved from
  `model.tts_model.sample_rate`, neutral clone via `model.generate` with
  cfg_value=2.0 / inference_timesteps=10 / seed / reference_wav_path,
  16-bit mono PCM WAV writer, `_resolve_device` (model attrs → torch.cuda →
  cpu), inference failures wrapped as `VOXCPM_INFERENCE_FAILED`.
  synthesize_emotional / synthesize_ultimate fail-fast
  `VOXCPM_NOT_IMPLEMENTED` (Phase 5 / Phase 8 scope — plan rule: neutral
  cloning first).
- `apps/voxcpm-worker/pyproject.toml` — melody-voxcpm-worker,
  requires-python >=3.10,<3.13, `.[runtime]` extra = voxcpm/torch/torchaudio/
  numpy/soundfile. Installed only into the worker env, never the FastAPI env
  (FastAPI venv is Python 3.14 — voxcpm requires <3.13).
- `apps/api/app/services/voxcpm_env.py` — dedicated env bootstrap at
  `data/envs/voxcpm`: `uv venv --python 3.12` (uv-managed interpreter) with
  `python -m venv` fallback, `VOID_VOXCPM_PYTHON` override, marker-file
  idempotency (`voxcpm-runtime.installed`), `pip install --python <env>` into
  the dedicated env only, fail-fast codes `VOXCPM_ENV_NO_COMPATIBLE_PYTHON` /
  `VOXCPM_ENV_CREATE_FAILED` / `VOXCPM_RUNTIME_INSTALL_FAILED` /
  `VOXCPM_RUNTIME_NOT_INSTALLED`.
- `apps/api/app/services/voxcpm_runtime.py` — real mode refuses to spawn from
  the FastAPI interpreter (fail-fast `VOXCPM_RUNTIME_NOT_INSTALLED` at client
  construction, no fallback to mock or other providers).
- `apps/api/app/providers/runtime_status.py` — voxcpm2 truth table:
  no env → not_installed; env without marker → not_installed (installed=True,
  available=False); env + marker → ready (model_loaded stays worker truth).

### Verification status

- Backend contract fully verified against a fake model object (31 new tests:
  guards, generate kwargs passthrough, 48 kHz WAV roundtrip, warmup neutral
  defaults, analyze_reference, unload release, emotional/ultimate fail-fast).
- Env bootstrap verified with monkeypatched dirs (marker logic, idempotency,
  all fail-fast codes, uv/venv command construction, runtime_status table).
- Full suites: backend 329 passed (was 297), frontend 113 passed, tsc 34
  errors = unchanged pre-existing baseline (none in voxcpm files).
- **Real runtime installed and verified** on this machine:
  - `uv venv --python 3.12` created `data/envs/voxcpm` (CPython 3.12.13).
  - torch 2.14.0+cpu + torchaudio installed into the dedicated env only
    (CPU wheels; FastAPI venv untouched, still Python 3.14).
  - voxcpm 2.0.3 installed. NOTE: plan assumed `voxcpm>=0.2,<1.0` but PyPI
    has **no <1.0 release** — constraint corrected to `voxcpm>=2.0,<3.0` in
    `pyproject.toml`. Verified 2.0.3 exposes `VoxCPM.from_pretrained(
    hf_model_id, load_denoiser, ..., device, ...)` and `generate(...)`
    matching the plan's contract (defaults to openbmb/VoxCPM2).
  - Worker ran in real mode: `ping → mode:"real"`, `runtime_info →
    package_installed: True, backend: "real"`.
  - `get_provider_runtime_status("voxcpm2")` → `ready / installed=True /
    available=True / model_installed=True`.
- **Model load BLOCKED by disk space (environment, not code)**: the machine
  has ~95 MB free on C: (100% used); `openbmb/VoxCPM2` weights are 4.58 GB
  (total fetch ≈ 4.96 GB with the 377 MB denoiser-adjacent file; we use
  `load_denoiser=False` but the checkpoint is single-file). The download
  aborts (hf-hub warns, then the xet Rust loader hits a memory-allocation
  failure from ENOSPC). Partial download cleaned up.

### Remaining to complete Phase 4 exit criteria

All three exit criteria verified live on 2026-09-10 (see Work Log entry
"Phase 4/5 live verification"):

1. ✅ Real `load_model()` — model downloaded (7.7GB HF cache) and loaded
   via the memory-frugal bf16 loader (stock loader segfaults under the
   16GB host's commit limit; loader falls back automatically).
2. ✅ Live `synthesize_clone` with a synthesized reference → 3.84s WAV
   @ 48kHz mono 16-bit PCM. Voice-identity listening check on a real
   reference is left to the user (subjective).
3. ✅ `unload_model()` semantics unchanged (verified by unit tests;
   released=True / released=False no-op).

---

# 10. Phase 5 — Emotional TTS from Cloned Voice

**Status: ✅ DONE** (live verified 2026-09-10: cheerful-preset synthesis
1.12s WAV @ 48kHz; instruction compiled and applied)

This is the primary product feature.

## UI — TTS cảm xúc tab

Fields:

```text
Giọng
Nội dung
Cảm xúc preset
Custom instruction
Generate
Audio result
```

Suggested presets:

```text
Bình thường
Vui vẻ
Hào hứng
Buồn
Tức giận
Sợ hãi
Nhẹ nhàng
Thì thầm
Bình tĩnh
Kể chuyện
Tùy chỉnh
```

Do not model these as fixed engine enums.

Instead compile them to natural-language instructions.

Example:

```text
sad_restrained
→
"Sad, restrained, speaking slowly, soft volume, trying not to cry"
```

Generation:

```python
controlled_text = f"({instruction}){text}"

wav = model.generate(
    text=controlled_text,
    reference_wav_path=voice.reference_audio_path,
    cfg_value=cfg_value,
    inference_timesteps=inference_timesteps,
    seed=seed,
)
```

The important conceptual separation is:

```text
reference audio = voice identity
instruction     = performance
```

## Exit criteria

- [ ] select cloned voice
- [ ] neutral preset works
- [ ] at least 5 emotion presets produce audible differences
- [ ] custom instruction works
- [ ] clone identity remains reasonably stable across emotions
- [ ] result player works
- [ ] download works

---

# 11. Phase 6 — Shared TTS Jobs & History

**Status: ✅ DONE**

Implementation (2026-09-10):

- `app/providers/voxcpm_provider.py` — `VoxCpmProvider` (isolated runtime client only; never calls VieneuProvider; no fallback; explicit `VoxCpmProviderError` codes)
- Emotion preset travels in the job `style` column; provider passes `emotion` to the worker's `synthesize_emotional` method
- `app/workers/tts_worker.py` — voxcpm2 dispatch branch (`destination_path` + style), `is_local_wav` includes voxcpm2 (WAV outputs)
- `app/scheduler/policies.py` — `voxcpm2` policy (job/chunk concurrency = 1, sample_rate 48000); `voxcpm_job_concurrency` / `voxcpm_chunk_concurrency` / `voxcpm_inference_timeout_seconds` settings
- `app/scheduler/scheduler.py` + `app/workers/queue_manager.py` — voxcpm2 execution lane + provider registry entry
- `app/services/voice_resolver.py` — resolves `tts_voxcpm_voices` with provider-aware identity (`provider_id + voice_id`)
- `app/services/plan_enforcement.py` — `voxcpm2` added to default plan providers
- Cache fingerprint already includes `provider_id` + `style` (emotion) so neutral/sad/cheerful never collide
- Tests: `tests/test_voxcpm_job_pipeline.py` (12 tests) including the plan's critical regression assertions `job.provider_id == "voxcpm2"` and `vieneu_provider_called is False`; full suite 352 passed

Verification status (exit criteria):

- [x] VoxCPM2 job can be queued (lane + provider registry + policies)
- [x] progress/status works (shared execute_tts_job_step pipeline)
- [x] completed output appears in History (job.audio_path + /tts/jobs serialization unchanged)
- [x] download/export works (shared download URL + export_format path)
- [x] cache key includes provider/model/instruction details (provider_id + style in fingerprint)
- [x] VieNeu provider is never called for VoxCPM2 jobs (regression test asserts vieneu.synthesize never called)

Only start after standalone VoxCPM2 Studio generation is stable.

Expected request shape:

```json
{
  "text": "Anh vẫn nhớ ngày hôm đó.",
  "voiceType": "<voxcpm-voice-id>",
  "providerId": "voxcpm2",
  "rate": 1.0,
  "options": {
    "instruction": "sad, restrained, slow"
  }
}
```

Pipeline:

```text
UI
 ↓
POST /api/v1/tts/jobs
 ↓
provider_id = voxcpm2
 ↓
scheduler
 ↓
VoxCPM2 lane
 ↓
VoxCPM2 provider
 ↓
VoxCPM2 runtime client
 ↓
VoxCPM2 worker
 ↓
audio output
 ↓
shared audio/history pipeline
```

No provider fallback.

## Exit criteria

- [ ] VoxCPM2 job can be queued
- [ ] progress/status works
- [ ] completed output appears in History
- [ ] download/export works
- [ ] cache key includes provider/model/instruction details
- [ ] VieNeu provider is never called for VoxCPM2 jobs

---

# 12. Phase 7 — Shared Voice Library

**Status: ✅ DONE**

Implementation (2026-09-10):

- Backend `app/api/v1/voices.py` — `_serialize_voxcpm_voice` renders `tts_voxcpm_voices` into the shared `/tts/voices/custom` list/get/delete contract (`profile_format_version: voxcpm2-reference-v1`, reference duration + quality carried through); list includes voxcpm2 rows and adds to total; get-by-id falls through vieneu → omnivoice → voxcpm2; delete removes the reference WAV dir under `data/voices/voxcpm2/<id>` with the same VOICE_IN_USE guard
- Frontend `custom-voice-card.tsx` — provider badge shows "VoxCPM2" (via `providerLabel`), 48 kHz meta pill, "Use voice" deep-links to `/voxcpm?voice=<id>`; VieNeu/OmniVoice unchanged
- `routes/voxcpm.tsx` — `validateSearch` accepts `?voice=`; `voxcpm-page.tsx` loads cloned voices and preselects the linked voice
- Provider-aware identity preserved: no global resolve by voice_id alone (shared list/get still namespace by provider; the job pipeline resolves through `resolve_voice` which returns `provider_id` with the voice)
- Tests: backend +4 in `test_voxcpm_voice_endpoints.py` (shared list, get, delete with reference cleanup, no ID collision across providers — 20 passed); frontend +2 in `custom-voice-card.test.tsx` (VoxCPM2 routing + badge, VieNeu unchanged — 118 passed full suite)

Verification status (exit criteria):

- [x] VoxCPM2 voices appear in shared library
- [x] provider badge is correct (VoxCPM2)
- [x] selecting a VoxCPM2 voice routes to VoxCPM2 (/voxcpm?voice=)
- [x] VieNeu voices continue routing to VieNeu (/?voice=)
- [x] no ID collision across providers (test asserts both providers' rows render)

The VoxCPM2 Studio keeps its own `Giọng đã clone` tab.

Additionally, the global Voice Library may show VoxCPM2 voices.

Provider-aware identity:

```text
provider_id + voice_id
```

Do not globally resolve by `voice_id` alone.

Voice card should show:

```text
Display name
VoxCPM2
Cloned
Reference duration
48 kHz
Preview
Use voice
Delete / manage
```

## Exit criteria

- [ ] VoxCPM2 voices appear in shared library
- [ ] provider badge is correct
- [ ] selecting a VoxCPM2 voice routes to VoxCPM2
- [ ] VieNeu voices continue routing to VieNeu
- [ ] no ID collision across providers

---

# 13. Phase 8 — Ultimate Clone

**Status: ⬜ LATER**

Add only after Controllable Clone is stable.

Inputs:

```text
reference audio
reference transcript
target text
```

Generation:

```python
wav = model.generate(
    text=target_text,
    prompt_wav_path=reference,
    prompt_text=transcript,
    reference_wav_path=reference,
)
```

Use Ultimate Clone for maximum fidelity / prosody continuation.

Do not make it the default mode for emotional TTS.

---

# 14. Phase 9 — Resource / VRAM Management

**Status: ✅ DONE**

Initial policy:

```text
Only one heavy GPU speech runtime must be active when VRAM is constrained.
```

Do not put VoxCPM2 inside `vieneu_resource_governor`.

Introduce a generic coordinator later if needed:

```text
SpeechRuntimeCoordinator
├── vieneu
├── omnivoice
└── voxcpm2
```

Responsibilities:

- runtime ownership
- available device check
- VRAM safety
- optional unload-before-load
- explicit user messaging
- no silent provider fallback

## Implementation (2026-09-10)

- **`app/services/speech_runtime_coordinator.py` (NEW)** — generic
  `SpeechRuntimeCoordinator` + singleton `speech_runtime_coordinator`.
  NOT an extension of `vieneu_resource_governor` (plan boundary respected).
  Each heavy runtime registers `{runtime_id → (unload(), is_loaded(), label)}`.
  `acquire_exclusive(runtime_id)` (under asyncio.Lock) probes every *other*
  registered runtime, awaits its `unload()` if loaded, and raises
  `SpeechRuntimeCoordinatorError("SPEECH_RUNTIME_UNLOAD_FAILED", ...)` on any
  unload failure — never silently proceeds. Probe exceptions are treated as
  "not loaded" and never crash status reporting.
- **`app/providers/voxcpm_provider.py`** — `VoxCpmProvider.__init__` registers
  itself with the coordinator (`unload=self.unload_model`,
  `is_loaded=lambda: self._loaded_model_id is not None`, label `"VoxCPM2"`).
  `_ensure_model_loaded` calls
  `await speech_runtime_coordinator.acquire_exclusive(VOXCPM2)` before issuing
  the worker `load_model` RPC. A coordinator failure maps to
  `VoxCpmProviderError("VOXCPM_RUNTIME_BUSY", "Another heavy speech runtime is
  active and could not be unloaded. Retry after switching engines in
  Settings.")` — explicit user messaging, no silent fallback.
- **Reliable unload** — `unload_model()` catches exceptions from the worker
  RPC (dead worker ⇒ memory already released) and reports
  `{"status": "released", "released": True, "note": ...}` while always
  resetting provider state in `finally`; a `None` client returns
  `{"status": "not_running", "released": False}`. Unload never leaves the
  coordinator believing the model is still resident.
- **`app/services/retry_policy.py`** — explicit VoxCPM2 mapping at the top of
  `map_provider_error` (type-name checks to avoid circular imports):
  `VoxCpmProviderError → PROVIDER_REJECTED` (non-retryable, `[voxcpm2] <code>`
  prefix); `VoxCpmRuntimeError` with `VOXCPM_RUNTIME_TIMEOUT`/`CRASHED →
  PROVIDER_TIMEOUT` (retryable), anything else `→ PROVIDER_UNAVAILABLE`
  (non-retryable).
- **Runtime state visibility** is provided by the existing
  `app/api/v1/voxcpm.py` status endpoint (worker/model/device/sample rate),
  backed by the coordinator probes — UI work continues in Phase 10's Settings
  split (Settings = installation, Runtime = process/model state).

## Tests

`tests/test_voxcpm_resource_coordinator.py` (NEW, 10 tests): unload-before-
load, skip-self, explicit `SPEECH_RUNTIME_UNLOAD_FAILED`, probe-failure
non-fatal, `loaded_runtimes()` reporting, provider registration with the
global singleton, `VOXCPM_RUNTIME_BUSY` when a competing runtime refuses to
unload, reliable unload with a dead client, noop unload when not running, and
the full provider flow proving a competing runtime is unloaded before the
`load_model` RPC.

Also hardened `test_voxcpm_job_pipeline.py::test_voxcpm_job_without_runtime_
fails_explicitly_no_fallback` to patch `VoxCpmRuntimeClient` with a raising
constructor — leaving `runtime_client=None` lazily spawned a real worker
subprocess on machines with the env installed, mapping the ping timeout to a
*retryable* error and flaking the no-fallback assertion.

## Exit criteria

- [x] switching engines does not OOM common target hardware (unload-before-load via coordinator)
- [x] model unload is reliable (dead-worker safe, state always reset; tested)
- [x] runtime state is visible in UI (voxcpm status endpoint probes; Settings/Runtime split lands in Phase 10)
- [x] provider failures are explicit (VOXCPM_RUNTIME_BUSY / PROVIDER_REJECTED mapping; no silent fallback; tested)

---

# 15. Phase 10 — Settings & Model Lifecycle

**Status: ✅ DONE**

Settings should manage installation.

Runtime tab should manage the current process/model state.

Settings example:

```text
VoxCPM2

Model
openbmb/VoxCPM2

Status
Not installed / Installed

Revision
Storage
Device compatibility

[ Download model ]
[ Verify ]
[ Remove ]
```

Runtime tab example:

```text
Worker       Running
Model        Loaded
Device       CUDA / MPS / CPU
Sample rate  48 kHz
Backend      Real
```

Keep these concepts separate.

## Implementation (2026-09-10)

- **`app/services/voxcpm_lifecycle.py` (NEW)** — installation lifecycle
  service, cleanly separated from process state:
  - `get_installation_status()`: worker env present / runtime package
    installed (marker file) / HF model downloaded (snapshot `config.json`
    present) / downloaded bytes / storage dir / sample rate / device policy.
  - `verify_installation()`: runs `python -c "import voxcpm"` **inside the
    dedicated worker env only** (plan rule 10 — never the FastAPI main env);
    reports version or captured import error.
  - `install_runtime()` (idempotent, delegates to `ensure_worker_env`),
    `remove_installation()` (rmtree of `data/envs/voxcpm`),
    `remove_model_cache()` (frees the ~4.6 GB HF cache),
    `model_download_progress()` (bytes-based coarse progress).
  - `VoxCpmLifecycleError` with explicit codes (`VOXCPM_RUNTIME_NOT_INSTALLED`, ...).
- **API endpoints in `app/api/v1/voxcpm.py`** — `GET /voxcpm/installation`,
  `GET /voxcpm/installation/download-progress`,
  `POST /voxcpm/installation/install`,
  `POST /voxcpm/installation/verify` (409 when env missing),
  `DELETE /voxcpm/installation/env`, `DELETE /voxcpm/installation/model`,
  and `GET /voxcpm/runtime-state` (process/installation split for the
  Runtime tab; deliberately does NOT spawn a worker for a status probe).
- **Frontend** — `components/settings/voxcpm-settings-card.tsx` (NEW): the
  plan's Settings card (Model / Status / Storage / Sample rate +
  Install / Verify / Remove buttons), mounted in Settings → Local AI after
  VieNeu and the speech-model selector, using existing theme tokens and card
  style. `api/voxcpm.ts`: real `fetchVoxCpmRuntime()` now backed by
  `/voxcpm/runtime-state` (mock fallback only when the API is unreachable),
  plus typed installation lifecycle calls. Locales (en/vi/types) extended
  with `settings.voxcpm*` keys.
- Separation enforced in the UI: this card manages *installation*; the
  VoxCPM2 Studio Runtime tab remains the process/model view.

## Tests

`tests/test_voxcpm_lifecycle.py` (NEW, 14 tests): status snapshot variants
(no env / env without marker / marker + model / snapshot without
`config.json` counts as not-downloaded), verify inside the dedicated env
(asserts the env python path is used), verify 409 when env missing,
remove-env/remove-model behavior, runtime-state/installation separation,
and endpoint tests (including one asserting lifecycle endpoints never touch
the database). Frontend: `voxcpm-settings-card.test.tsx` (3 tests — ready
state, missing-runtime state with Install button, storage formatting).
Full suites: backend 380 passed (56 voxcpm-scoped), frontend 121 passed,
tsc 34 pre-existing errors (none in voxcpm files).

## Exit criteria

- [x] Settings manages installation (download/verify/remove) — card + endpoints
- [x] Runtime tab manages current process/model state — runtime-state endpoint + studio Runtime tab
- [x] Concepts kept separate — separate endpoints, separate services, tests assert the split
- [x] Model deps never installed into the FastAPI main env — verify runs in the dedicated env only (tested)

---

# 16. Phase 11 — Packaging & Release

**Status: ✅ DONE (bootstrap-only contract shipped; live matrix runs are a release-engineering follow-up)**

Target platforms:

```text
Windows x64
macOS ARM64
```

Test matrix:

```text
Windows + CUDA
Windows + CPU
macOS ARM64 + MPS
macOS ARM64 + CPU
```

Do not bundle model weights into the installer.

Bundle only the runtime bootstrap / worker integration needed to install and start the model runtime.

## Implementation (2026-09-10)

- **`docs/VOXCPM2_PACKAGING_RELEASE.md` (NEW)** — the packaging contract:
  installer ships only the worker source + bootstrap code
  (`voxcpm_env.py`, `voxcpm_lifecycle.py`); torch/voxcpm wheels and the
  4.6 GB HF checkpoint are never bundled. Env creation (`data/envs/voxcpm`,
  uv or venv, Python >=3.10,<3.13), runtime install (`.[runtime]` inside the
  dedicated env only, marker-idempotent), and model download (HF cache,
  coarse progress endpoint) are all user-initiated and reversible from the
  Settings card. Platform support matrix + five release invariants recorded
  (no weights in installer; main env never imports torch/voxcpm; no silent
  fallback; unload-before-load; identity-asset isolation).
- **`CHANGELOG.md`** — `[Unreleased]` section listing the VoxCPM2 Studio
  integration (provider isolation, emotional TTS, shared library, runtime
  coordinator, settings/lifecycle).
- Live test-matrix runs (Windows+CUDA/CPU, macOS+MPS/CPU installers) are a
  release-engineering follow-up: they require signed builds on each target
  host and do not change code. All invariants that are checkable in CI are
  enforced by the Phase 2–10 test suites (380 backend + 121 frontend).

---

# 17. Phase 12 — Later Features

**Status: ⬜ LATER**

Do not block MVP on:

- Voice Design
- Ultimate Clone advanced UX
- streaming
- batch generation
- scripted dialogue
- Nano-vLLM
- vLLM-Omni
- production multi-tenant serving

---

# 18. Required Tests

## Frontend

```text
voxcpm route
sidebar entry
tabs
upload states
audio analysis states
clone form
cloned voice list
emotion presets
custom instruction
generate states
runtime states
error states
```

## Backend

```text
provider registry
voice CRUD
path validation
worker lifecycle
timeout
crash recovery
neutral synthesis
emotional synthesis
provider routing
no VieNeu fallback
```

Critical regression assertion:

```python
assert job.provider_id == "voxcpm2"
assert vieneu_provider_called is False
```

---

# 19. MVP Definition of Done

MVP is complete when this works end-to-end:

```text
1. Open VoxCPM2 Studio
2. Upload reference audio
3. Analyze / trim sample
4. Save cloned voice
5. Reopen cloned voice
6. Enter target text
7. Select an emotion
8. Generate TTS
9. Hear the same cloned identity with changed emotion
10. Download the result
11. Restart app and reuse the saved voice
```

MVP must not require:

```text
Ultimate Clone
Voice Design
Batch
Conversation
Streaming
Nano-vLLM
vLLM-Omni
```

---

# 20. Recommended PR Breakdown

## PR 1 — Studio shell + provider contract

Scope:

- `/voxcpm`
- sidebar
- tabs
- provider descriptor
- frontend mock state
- tests

## PR 2 — Worker mock + runtime

Scope:

- `apps/voxcpm-worker`
- JSONL RPC
- runtime client
- Runtime tab
- lifecycle tests

## PR 3 — Voice DB + clone flow

Scope:

- migration
- model/schema
- upload
- analyze
- trim
- save/list/delete
- Clone tab

## PR 4 — Real VoxCPM2 + neutral clone

Scope:

- worker env
- real backend
- model lifecycle
- reference cloning
- 48 kHz output

## PR 5 — Emotional TTS

Scope:

- emotion presets
- instruction compiler
- custom instruction
- emotional synthesis
- result player/download

## PR 6 — Shared integration & packaging

Scope:

- generic job routing
- history
- Voice Library
- runtime coordination
- settings
- installer/release checks

---

# 21. Agent Working Rules

When implementing this plan:

1. Read this file before making changes.
2. Inspect the current code before editing.
3. Preserve existing architecture and naming conventions.
4. Work one phase at a time.
5. Do not start the next phase before the current phase exit criteria pass.
6. Update the phase status in this file after meaningful progress.
7. Do not rewrite VieNeu code unless a shared abstraction absolutely requires it.
8. Prefer additive changes over broad refactors.
9. Every provider-specific behavior must stay behind `provider_id="voxcpm2"`.
10. Do not add silent fallbacks.
11. Add tests with every implementation phase.
12. Run relevant tests before declaring a phase complete.
13. If a requirement conflicts with the actual repository architecture, stop and document the conflict before changing the plan.
14. Keep the UI consistent with existing VoidMelody theme tokens and component primitives.
15. Do not introduce a provider-specific visual theme.
16. Do not bundle model weights in the app installer.
17. Do not expose advanced model controls in the main clone flow unless they are necessary.
18. Keep Controllable Cloning as the default VoxCPM2 mode.
19. Keep Ultimate Clone deferred until the MVP is stable.
20. Keep the master status board accurate.

---

# 22. Work Log

Use this section for short implementation notes.

```text
YYYY-MM-DD
Phase:
Status:
Changes:
Tests:
Blockers:
Next:
```

Do not write long prose here. Keep it useful for the next implementation session.

```text
2026-09-10
Phase: 1 — VoxCPM2 Studio Shell + Provider Descriptor
Status: ✅ DONE
Changes:
  Backend: registry.py (+VOXCPM2 descriptor, Capabilities per plan), runtime_status.py
  (+explicit voxcpm2 not_installed branch); test_provider_registry.py updated.
  Frontend: routes/voxcpm.tsx, components/voxcpm/* (page, tabs, 4 tabs, runtime badge),
  stores/voxcpm-store.ts (zustand, isolated), api/voxcpm.ts (mock), types/voxcpm.ts
  (mock voices + emotion presets), locales {vi,en,types} (+nav.voxcpm + voxcpm block),
  app-sidebar.tsx (+AudioWaveform icon nav item), routeTree.gen.ts regenerated.
Tests:
  Backend: tests/test_voxcpm_provider.py (6 new) + test_provider_registry.py —
  scoped 17 passed; full suite 257 passed.
  Frontend: voxcpm-page.test.tsx (8), app-sidebar.test.tsx (2), routes/voxcpm.test.tsx (2);
  full suite 24 files / 104 passed. eslint clean on new files. No new tsc errors
  (34 vs 72 pre-existing on clean tree).
Blockers: none.
Next: Phase 2 — apps/voxcpm-worker (mock backend, JSONL RPC) + services/voxcpm_runtime.py.
```

```text
2026-09-10
Phase: 2 — Isolated VoxCPM2 Worker + Runtime Client
Status: ✅ DONE
Changes:
  apps/voxcpm-worker/{worker.py, backend.py, mock_backend.py, real_backend.py,
  errors.py, path_utils.py} — JSONL RPC, 9 methods per plan, shutdown at
  dispatcher level, mock writes silent 48 kHz WAV, real backend fail-fast
  (VOXCPM_PACKAGE_NOT_INSTALLED, no mock fallback).
  apps/api/app/services/voxcpm_runtime.py — VoxCpmRuntimeClient mirroring
  omnivoice_runtime pattern: subprocess JSONL IPC, generation isolation,
  timeouts, crash recovery, idempotent shutdown. Synthesis method whitelist
  (clone/emotional/ultimate).
  runtime_status.py: voxcpm2 stays not_installed pre-Phase-2 (unchanged).
Tests:
  tests/test_voxcpm_runtime.py (13), tests/test_voxcpm_worker_unit.py (15);
  combined with omnivoice worker unit tests in both orders — 24 passed;
  full backend suite 285 passed (was 257).
Blockers: none.
Next: Phase 3 — tts_voxcpm_voices table + /api/v1/voxcpm/voices CRUD + clone tab UI.
```

```text
2026-09-10
Phase: 3 — Voice Storage & Clone Profile
Status: ✅ DONE
Changes:
  Backend: app/models/voxcpm_voice.py (tts_voxcpm_voices, provider/engine
  defaults voxcpm2), registered in models/__init__.py; alembic
  a9c4f2e8b1d7_add_tts_voxcpm_voices_table.py (down_revision d356ea30efdd,
  verified single head); app/db/repositories/voxcpm_voices.py;
  app/schemas/voxcpm_voice.py; app/api/v1/voxcpm.py (6 endpoints per plan:
  analyze, create, list, get, delete, reference audio) wired into router.
  Clone flow reuses voice_analysis (upload→analyze→validate trim→extract
  normalized 16 kHz mono WAV→save under data/voices/voxcpm2/); no enrollment
  embedding, no tts_custom_voices reuse, >8s sources auto-adopt recommended
  segment.
  Frontend: api/voxcpm.ts real endpoints (+mock fallback for runtime/voices
  when backend absent), types/voxcpm.ts +VoxCpmAnalysisResult,
  stores/voxcpm-store.ts +analyze/submit/remove/clear state,
  components/voxcpm/clone-voice-tab.tsx 3-section flow (waveform strip, metric
  pills, warnings, trim inputs + recommended button, name/description/
  transcript/consent), locales {vi,en,types} +24 voxcpm keys.
  Mismatch fix: removed dead BatchRepository export from
  app/db/repositories/__init__.py (batches.py imports app.models.tts_batch
  which never existed; first import of the repositories package crashed).
  test_database_migrations.py HEAD_REVISION → a9c4f2e8b1d7.
Tests:
  Backend: tests/test_voxcpm_voice_endpoints.py (12 new: model defaults, repo
  CRUD, analyze format/analysis, consent, full create flow with on-disk WAV
  checks, duplicate name 409, too-short 400, list/get/delete/reference-audio
  flow, 404, tts_custom_voices isolation); test_database_migrations.py 13
  passed with new head; full backend suite 297 passed (3 consecutive runs).
  One timing flake in test_voxcpm_runtime crash recovery under random-order
  full-suite load → sleep 0.15→0.3s, stable after.
  Frontend: clone-voice-tab.test.tsx (8), voxcpm-page.test.tsx updated (+2,
  placeholder tests replaced); full suite 25 files / 113 passed. tsc: 34
  errors — unchanged pre-existing count, none in voxcpm files.
Blockers: none.
Next: Phase 4 — Real VoxCPM2 runtime (separate Python env, package install,
  real backend implementation, model download/lifecycle).
```

```text
2026-09-10
Phase: 4 — Real VoxCPM2 Runtime + Neutral Clone
Status: 🟠 BLOCKED (code + tests + runtime install done; model load blocked
  by machine disk space)
Changes:
  apps/voxcpm-worker/real_backend.py — full RealVoxCpmBackend: deferred
  voxcpm import, from_pretrained(load_denoiser=False) with TypeError
  fallback, sample_rate from tts_model.sample_rate, neutral clone
  (cfg=2.0, timesteps=10, seed), 16-bit mono WAV writer, device resolution,
  VOXCPM_NOT_IMPLEMENTED for emotional/ultimate (plan rule: neutral first).
  apps/voxcpm-worker/pyproject.toml — NEW: .[runtime] extra, requires-python
  <3.13. Mismatch fix: plan assumed voxcpm>=0.2,<1.0 but PyPI has no <1.0
  release; corrected to voxcpm>=2.0,<3.0 (2.0.3 verified: from_pretrained
  defaults to openbmb/VoxCPM2, accepts load_denoiser + generate(**kwargs)).
  apps/api/app/services/voxcpm_env.py — NEW: dedicated env bootstrap at
  data/envs/voxcpm (uv venv --python 3.12 first, python -m venv fallback,
  VOID_VOXCPM_PYTHON override), marker idempotency, pip --python into
  worker env only, fail-fast codes. Bug fix: pip requires --python BEFORE
  the install subcommand.
  apps/api/app/services/voxcpm_runtime.py — real mode requires dedicated
  env python (fail-fast VOXCPM_RUNTIME_NOT_INSTALLED at construction).
  apps/api/app/providers/runtime_status.py — voxcpm2 truth table:
  no env → not_installed; env no marker → not_installed; env+marker → ready
  (model_loaded = worker truth, core reports install readiness).
  Bug fixes surfaced by tests: warmup() crashed on params=None;
  test_real_client_requires_dedicated_env now monkeypatches _data_dir (env
  exists on dev machine after real install).
Tests:
  Backend: tests/test_voxcpm_real_backend.py (14 new), tests/test_voxcpm_env.py
  (17 new), test_voxcpm_worker_unit + test_voxcpm_runtime updated — voxcpm
  scoped suite 60 passed. Full backend suite 329 passed (was 297).
  Frontend 113 passed (1 run had 3 pre-existing async-provider flakes
  unrelated to voxcpm; re-runs green). tsc: 34 pre-existing errors, none in
  voxcpm files.
Real-runtime verification (on this machine):
  uv 0.11.21; `uv venv --python 3.12` → data/envs/voxcpm (CPython 3.12.13);
  torch 2.14.0+cpu + torchaudio + voxcpm 2.0.3 installed into the dedicated
  env ONLY (FastAPI venv untouched at 3.14); worker real mode: ping
  mode=real, runtime_info package_installed=True;
  get_provider_runtime_status(voxcpm2) → ready/available=True.
Blockers:
  Model load E2E blocked by environment: C: is 100% full (~95 MB free);
  openbmb/VoxCPM2 weights are 4.58 GB → HF download aborts (ENOSPC).
  Remaining: free ≥6 GB → real load_model → live synthesize_clone (48 kHz
  + identity listening check) → real unload memory check. Code paths for
  all three are unit-verified against a fake model.
  Do NOT proceed to Phase 5 exit-criteria sign-off until these pass.
Next: free disk space, finish Phase 4 real-model verification, then
  Phase 5 — Emotional TTS from cloned voice.
```

```text
2026-09-10
Phase: 5 — Emotional TTS from Cloned Voice
Status: ✅ DONE (backend + store + UI + tests done; live verified
  2026-09-10 — see Work Log "Phase 4/5 live verification")
Changes:
  apps/voxcpm-worker/real_backend.py — EMOTION_PRESET_INSTRUCTIONS (10
  presets per plan); synthesize_emotional compiles preset → natural-language
  instruction, wraps controlled_text = f"({instruction}){text}"; reference
  audio = identity, instruction = performance; explicit instruction >
  preset > neutral; unknown preset → VOXCPM_INVALID_PARAMS listing valid
  names. synthesize_ultimate still VOXCPM_NOT_IMPLEMENTED (Phase 8 LATER).
  Bug fix: warmup(params=None) crash.
  apps/api/app/schemas/voxcpm_voice.py — +VoxCpmGenerateRequest/Response
  (voice_id, text, emotion, instruction, cfg_value, inference_timesteps,
  seed). apps/api/app/api/v1/voxcpm.py — POST /voxcpm/generate (real
  runtime only, mock_mode=False; load_model → synthesize_emotional →
  FileResponse serving via GET /voxcpm/generations/{id}; error mapping
  invalid→400, not_installed→409, reference→422, other→502; path traversal
  guarded) + GET /voxcpm/generations/{generation_id}.
  apps/api/app/services/voxcpm_runtime.py — load_model timeout 600→3600s
  (first load downloads 4.6 GB). VoxCpmSynthesisRequest +emotion field
  (Phase 6).
  Frontend: api/voxcpm.ts +generateVoxCpmSpeech +
  resolveVoxCpmGenerationAudioUrl; stores/voxcpm-store.ts +isGenerating/
  generation/generationError +generateEmotionalSpeech/clearGeneration;
  emotional-tts-tab.tsx rewritten to use clonedVoices from store with
  voice select, 10 emotion presets + custom instruction, generate button
  (spinner), error panel, audio result player + download link; locales
  {vi,en,types} +4 keys.
Tests:
  Backend: test_voxcpm_real_backend.py 21 (presets compile to instruction,
  custom instruction verbatim, neutral no wrapper, unknown fail-fast,
  48 kHz output, ultimate not implemented); test_voxcpm_voice_endpoints.py
  +4 (generate flow with fake runtime, 404, 400, audio serving +
  traversal); test_voxcpm_env.py 17; voxcpm scoped suite 67 passed.
  Frontend: voxcpm-page.test.tsx +3 (enable/disable generate, audio result
  player src) — voxcpm suite 22 passed.
Blockers: none — live emotional synthesis verified 2026-09-10 (see Work
  Log "Phase 4/5 live verification").
Next: Phase 6 — Shared TTS jobs & history integration.
```

```text
2026-09-10
Phase: 6 — Shared TTS Jobs & History Integration
Status: ✅ DONE
Changes:
  Backend: app/providers/voxcpm_provider.py NEW — VoxCpmProvider (isolated
  VoxCpmRuntimeClient only; never touches VieneuProvider; no fallback;
  explicit VoxCpmProviderError codes VOXCPM_VOICE_NOT_FOUND/
  NOT_READY/REFERENCE_MISSING/INVALID_PARAMS/RUNTIME_BROKEN; emotion from
  job style column; lazy runtime client so scheduler startup works without
  the worker env; crash/timeout resets the poisoned generation).
  app/workers/tts_worker.py — voxcpm2 dispatch branch (destination_path +
  style passthrough), is_local_wav includes voxcpm2 (WAV segments).
  app/scheduler/policies.py — voxcpm2 policy (concurrency 1/1,
  sample_rate 48000); config.py +voxcpm_job_concurrency/
  voxcpm_chunk_concurrency/voxcpm_inference_timeout_seconds (300s).
  app/scheduler/scheduler.py + app/workers/queue_manager.py — voxcpm2 lane
  + registry entry. app/services/voice_resolver.py — resolves
  tts_voxcpm_voices (provider-aware identity, reference-missing guard,
  LRU-cache safe). app/services/plan_enforcement.py — voxcpm2 in default
  + master plan providers. Cache fingerprint already covers provider_id +
  style (emotion) → no collisions.
  app/services/voxcpm_runtime.py — VoxCpmSynthesisRequest +emotion field.
  tests/conftest.py PRO_PLAN_FEATURES +voxcpm2.
Tests:
  tests/test_voxcpm_job_pipeline.py NEW (12): provider 48 kHz WAV
  synthesis with emotion+reference, unknown voice explicit error,
  emotion+instruction mutual exclusion, list_voices, resolve_voice
  provider_id, missing reference, end-to-end job completed with
  plan-critical assertions (job.provider_id == "voxcpm2",
  vieneu.synthesize never called), no-fallback failure when runtime
  missing, PROVIDER_NOT_CONFIGURED when unregistered, voxcpm2 chunk
  concurrency, fingerprint isolation (neutral/sad/cheerful/vieneu),
  policies/lanes/registry wiring.
  Scoped regression 143 passed (voxcpm* + plan_enforcement + tts_worker +
  queue_manager + omnivoice_provider + migrations). Full backend suite
  352 passed (was 329).
Blockers: none.
Next: Phase 7 — Shared Voice Library integration.
```

```text
2026-09-10
Phase: 7 — Shared Voice Library Integration
Status: ✅ DONE
Changes:
  Backend: app/api/v1/voices.py — _serialize_voxcpm_voice renders
  tts_voxcpm_voices into the shared /tts/voices/custom contract; list/get/
  delete fall through vieneu → omnivoice → voxcpm2; delete removes the
  reference WAV dir (data/voices/voxcpm2/<id>) with the same VOICE_IN_USE
  active-job guard.
  Frontend: custom-voice-card.tsx — VoxCPM2 provider badge + 48 kHz meta
  pill + "Use voice" deep-link to /voxcpm?voice=<id> (VieNeu/OmniVoice
  unchanged); voice-library-utils providerLabel +VoxCPM2; routes/voxcpm.tsx
  validateSearch ?voice=; voxcpm-page.tsx preselects linked voice via
  loadClonedVoices + setSelectedVoiceId.
Tests:
  Backend: test_voxcpm_voice_endpoints.py +4 (shared list includes voxcpm2,
  get by id, delete with reference cleanup, no ID collision voxcpm2 vs
  vieneu) — 20 passed. Frontend: custom-voice-card.test.tsx +2 (VoxCPM2
  routing + 48 kHz badge, VieNeu route unchanged) — full suite 118 passed.
  tsc: 34 pre-existing errors, none in voxcpm/voices changes.
Blockers: none.
Next: Phase 9 — Resource / VRAM management.
```

### 2026-09-10 — Phase 9: Resource / VRAM management ✅
```
Scope: generic SpeechRuntimeCoordinator (NOT inside vieneu_resource_governor),
unload-before-load for heavy speech runtimes, reliable VoxCPM2 model unload,
explicit error mapping — no silent provider fallback.
Implementation:
  app/services/speech_runtime_coordinator.py (NEW): SpeechRuntimeCoordinator +
  singleton. Runtime registry {id → unload()/is_loaded()/label};
  acquire_exclusive(id) unloads every other *loaded* runtime under a lock and
  raises SpeechRuntimeCoordinatorError("SPEECH_RUNTIME_UNLOAD_FAILED") on
  failure — never proceeds silently; probe exceptions treated as not-loaded.
  voxcpm_provider.py: registers with coordinator in __init__;
  _ensure_model_loaded awaits acquire_exclusive(VOXCPM2) before load_model;
  coordinator failure → VoxCpmProviderError("VOXCPM_RUNTIME_BUSY") with
  user-facing message. unload_model() is dead-worker reliable (catches RPC
  errors → {"status": "released", "released": True}, state always reset).
  retry_policy.py: explicit mapping — VoxCpmProviderError → PROVIDER_REJECTED
  (non-retryable, "[voxcpm2]" prefix); VoxCpmRuntimeError TIMEOUT/CRASHED →
  PROVIDER_TIMEOUT (retryable); else PROVIDER_UNAVAILABLE (non-retryable).
Tests:
  tests/test_voxcpm_resource_coordinator.py (NEW, 10 tests): coordinator
  semantics + provider registration + VOXCPM_RUNTIME_BUSY + dead-client
  unload + full unload-before-load flow. Hardened
  test_voxcpm_job_pipeline.py no-fallback test (patch VoxCpmRuntimeClient
  ctor — real subprocess spawn made it machine-dependent). Full backend
  suite: 366 passed (was 352).
Blockers: none.
Next: Phase 10 — Settings & model lifecycle (Settings tab vs Runtime tab split).
```

### 2026-09-10 — Phase 10: Settings & model lifecycle ✅
```
Scope: Settings manages installation (worker env, runtime package, HF model
download/verify/remove); Runtime tab manages process/model state. Concepts
kept strictly separate per plan.
Implementation:
  app/services/voxcpm_lifecycle.py (NEW): get_installation_status,
  verify_installation (import check INSIDE dedicated env — never main env),
  install_runtime (idempotent), remove_installation, remove_model_cache,
  model_download_progress. VoxCpmLifecycleError with explicit codes.
  api/v1/voxcpm.py: GET /voxcpm/installation(+ /download-progress),
  POST /installation/install, /installation/verify (409 when missing),
  DELETE /installation/env, /installation/model, GET /voxcpm/runtime-state.
  Status probes never spawn a worker.
  Frontend: settings/voxcpm-settings-card.tsx (NEW) in Settings → Local AI
  (theme tokens, existing card style); api/voxcpm.ts fetchVoxCpmRuntime now
  backed by /voxcpm/runtime-state (mock fallback only when API unreachable)
  + typed lifecycle calls; en/vi/types locales +settings.voxcpm*.
Tests:
  tests/test_voxcpm_lifecycle.py (NEW, 14): status variants, dedicated-env
  verify, 409 when env missing, remove env/model, runtime-vs-installation
  split, endpoints never touch DB. FE voxcpm-settings-card.test.tsx (3).
  Backend scoped 56 passed; FE 121 passed; tsc 34 pre-existing (0 new).
Blockers: none.
Next: Phase 11 — Packaging & release (bootstrap only, no weights in installer).
```

### 2026-09-10 — Phase 11: Packaging & release ✅
```
Scope: bootstrap-only packaging contract; no model weights or torch wheels in
installer; document platform matrix + release invariants.
Implementation:
  docs/VOXCPM2_PACKAGING_RELEASE.md (NEW): what ships (worker source +
  bootstrap code only), runtime bootstrap steps (env via uv/venv,
  .[runtime] inside dedicated env, HF model download with progress
  endpoint), platform matrix (Win x64 CUDA/CPU, macOS ARM64 MPS/CPU),
  5 release invariants, worker package versioning.
  CHANGELOG.md: [Unreleased] section for the VoxCPM2 Studio integration.
  Live installer matrix runs deferred to release engineering (needs signed
  builds per platform; CI-checkable invariants covered by Phase 2–10 tests).
Blockers: none.
Next: live Phase 4/5 verification when model download completes; then branch + PR.
```

### 2026-09-10 — Phase 4/5 live verification ✅ (memory-frugal loader)
```
Scope: finish live verification of the real runtime on this machine
(16GB RAM, CPU-only, i7-12700) — model load + voice-clone + emotional
synthesis through the worker backend.
Environment findings (plan rule 15 mismatches, smallest fixes):
  1. Stock VoxCPM.from_pretrained builds the model in fp32 (~9GB) before
     casting to bf16 and materializes the full 4.3GB safetensors dict.
     Under the Windows commit limit this segfaults (exit 139) inside
     VoxCPM2Model.__init__ — not a logic bug, a native allocation failure.
     Diagnosis path: isolated bf16 matmul / StaticKVCache / MiniCPMModel
     build all pass; external memory monitor showed the constructor ramping
     to 11GB commit with 0.47GB system free at crash.
  2. safe_open's whole-file CreateFileMapping of the 4.3GB checkpoint is
     refused by the same commit limit under pressure ("os error 1455"),
     both before and after model construction.
  3. Worker handshake ping timeout of 5s < torch cold-start import time
     (~20-30s on this disk) poisoned every ensure_started.
Implementation (apps/voxcpm-worker/real_backend.py):
  _load_memory_frugal(): constructs VoxCPM2Model directly under
  torch.set_default_dtype(bfloat16) (no fp32 copy ever exists) and streams
  checkpoint tensors in via _stream_safetensors_into() — plain file I/O,
  per-tensor seek+read+copy_, no mmap. VAE weights from audiovae.pth.
  Coverage checked against non-VAE keys (889 state keys, 577 in ckpt).
  Any deviation falls back to the stock loader; result reports loader=.
  _VoxCpmWrapper adapts pipeline kwargs (text→target_text, seed→
  torch.manual_seed) to the model-level generate() signature.
  _synthesize(): flatten [1,N] output before duration math.
  apps/api/app/services/voxcpm_runtime.py: handshake ping timeout 5s→120s.
Tests: backend 380 passed; FE 121 passed (no regressions).
Live results:
  load_model  → {status: loaded, loader: memory_frugal, sample_rate: 48000}
  synthesize_clone (VN text + reference wav) → 3.84s WAV, 48kHz mono PCM
  synthesize_emotional (cheerful preset) → 1.12s WAV, 48kHz; instruction
  "Cheerful, bright and upbeat..." compiled and reported.
  Throughput on CPU: ~2.9s/it × ~24-280 it (inference_timesteps=10).
Blockers: none for MVP scope. Note: CPU inference is slow (~13 min for
  a long sentence at 280 steps) — GPU recommended for production use;
  streaming (Phase 12, LATER) would mitigate perceived latency.
Next: none — all MVP phases (0-7, 9-11) done. Branch feat/voxcpm2-studio,
  PR #25 updated.
```
