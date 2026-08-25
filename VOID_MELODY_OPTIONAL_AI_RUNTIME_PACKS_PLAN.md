# Void Melody — Optional Local AI Runtime Packs Plan

> **Goal:** keep the default Melody installer small and stable while making VieNeu and Whisper installable as versioned local runtime packs after installation.
>
> **Core rule:** do **not** bundle VieNeu / Whisper model stacks into the default Tauri bundle. Keep an optional Full Offline installer as a separate release artifact.

## 1. Product decision

Default release:

```text
Melody Core Installer
        ↓
small / stable desktop app
        ↓
optional Local AI components
```

Optional components:

```text
VieNeu Runtime Pack
Speech Runtime Pack
├── Silero VAD
└── Faster-Whisper
```

Models remain separate from runtimes:

```text
VieNeu models
Whisper models
```

Do not embed the runtime ZIPs or model weights into `MelodySetup.exe` by default.

## 2. Why this fits the current repo

Current Tauri bundle already ships sidecars such as:

```text
melody-api
ffmpeg
```

Current VieNeu model artifacts are already downloaded separately into persistent local storage. The main remaining architectural problem is that the PyInstaller `melody-api` build still collects heavy ML runtime dependencies such as VieNeu and ONNX/PyTorch-related packages.

Target:

```text
melody-api-core
→ lean orchestration/API sidecar

melody-vieneu-worker
→ downloadable runtime pack

melody-speech-worker
→ downloadable runtime pack
```

## 3. Target architecture

```text
                 Melody Core
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   Runtime Manager          Core API
          │                       │
  ┌───────┴────────┐              │
  │                │              │
  ▼                ▼              │
VieNeu Pack     Speech Pack        │
  │                │              │
  ▼                ▼              │
VieNeu Worker   Speech Worker      │
  │                │              │
  ▼                ├── Silero VAD │
VieNeu Models      └── Whisper ASR│
          │                       │
          └───────────┬───────────┘
                      ▼
                 Melody features
```

Core owns:

```text
Tauri UI
FastAPI orchestration
SQLite
jobs/queues
cache metadata
Voice Lab workflow
Audio Studio workflow
runtime install/update/remove
```

Workers own:

```text
ML imports
native ML dependencies
model loading
inference
hardware-specific ML runtime behavior
```

## 4. Default installer

Ship only:

```text
Melody Core
├── Tauri app
├── melody-api-core
├── FFmpeg
└── small static resources
```

Do not embed:

```text
VieNeu runtime ZIP
Whisper runtime ZIP
VieNeu models
Whisper models
CUDA
cuDNN
```

## 5. First-use UX

Voice Lab:

```text
Open Voice Lab
→ VieNeu installed?
   ├── yes → ready
   └── no  → Install VieNeu
              ↓
           download
              ↓
           SHA-256 verify
              ↓
           install/probe
              ↓
           model download
              ↓
           ready
```

Whisper:

```text
User clicks "Tự nhận diện lời thoại"
→ Whisper installed?
   ├── yes → transcribe selected segment
   └── no  → [Cài Whisper] [Nhập thủ công]
```

Whisper must never be required for V3 voice cloning.

## 6. Runtime pack vs model pack

Keep runtime and model independent.

VieNeu runtime:

```text
melody-vieneu-worker
VieNeu Python/native packages
ONNX/PyTorch runtime pieces
```

VieNeu models:

```text
V3 Turbo model files
speaker encoder
denoiser
MOSS codec
```

Speech runtime:

```text
melody-speech-worker
faster-whisper
CTranslate2
PyAV
Silero VAD runtime
```

Whisper model:

```text
CTranslate2 base/small model snapshot
```

Benefits:

```text
runtime update without model redownload
model update without app rebuild
future VieNeu V4 support
runtime rollback
smaller Melody updates
```

## 7. Runtime storage

Use persistent app-data storage, not the Tauri installation directory:

```text
MELODY_DATA_DIR/
├── runtimes/
│   ├── vieneu/
│   │   └── 1.2.0/
│   └── speech/
│       └── 1.0.0/
├── models/
│   ├── vieneu/
│   └── whisper/
├── voices/
├── cache/
└── app.db
```

App updates must not remove runtimes/models/voices.

## 8. Runtime release assets

Example:

```text
melody-vieneu-runtime-1.2.0-windows-x64.zip
melody-vieneu-runtime-1.2.0-linux-x64.zip
melody-vieneu-runtime-1.2.0-macos-arm64.zip

melody-speech-runtime-1.0.0-windows-x64.zip
melody-speech-runtime-1.0.0-linux-x64.zip
melody-speech-runtime-1.0.0-macos-arm64.zip
```

Optional GPU packs can come later:

```text
melody-speech-runtime-cuda12-1.1.0-windows-x64.zip
```

## 9. Runtime manifest

Example:

```json
{
  "schemaVersion": 1,
  "id": "speech-runtime",
  "version": "1.0.0",
  "protocolVersion": 1,
  "platform": "windows",
  "arch": "x86_64",
  "downloadUrl": "...",
  "sha256": "...",
  "sizeBytes": 182391231,
  "entrypoint": "melody-speech-worker.exe",
  "minimumAppVersion": "0.6.0"
}
```

Recommended fields:

```text
schemaVersion
id
version
protocolVersion
platform
arch
downloadUrl
sha256
sizeBytes
entrypoint
minimumAppVersion
maximumAppVersion optional
```

## 10. Atomic installation

Runtime installation flow:

```text
download to temp
→ verify SHA-256
→ safe extract to staging
→ validate manifest
→ run worker probe
→ atomic rename to final version
→ switch active runtime pointer
```

On failure:

```text
previous runtime remains active
```

Never overwrite the active runtime in place.

ZIP extraction must reject:

```text
../
absolute paths
path traversal
unexpected executable layout
```

## 11. Runtime Manager

Suggested backend package:

```text
apps/api/app/services/runtime_manager/
├── models.py
├── manifests.py
├── downloader.py
├── installer.py
├── registry.py
├── verifier.py
└── service.py
```

Responsibilities:

```text
probe
download
checksum
extract
activate
rollback
remove
repair
version compatibility
disk usage
```

## 12. Runtime registry

Persist installed state instead of relying only on filesystem scanning.

Example:

```json
{
  "vieneu": {
    "activeVersion": "1.2.0",
    "installedVersions": ["1.1.0", "1.2.0"]
  },
  "speech": {
    "activeVersion": "1.0.0",
    "installedVersions": ["1.0.0"]
  }
}
```

SQLite is also acceptable.

## 13. Runtime API

Add:

```http
GET /api/v1/runtimes
POST /api/v1/runtimes/{id}/install
POST /api/v1/runtimes/{id}/update
POST /api/v1/runtimes/{id}/repair
DELETE /api/v1/runtimes/{id}
GET /api/v1/runtimes/{id}/status
```

Status values:

```text
missing
downloading
verifying
installing
ready
update_available
repair_required
failed
```

Polling is enough initially; WebSocket is unnecessary.

## 14. Worker IPC

Use initially:

```text
subprocess
+ stdin/stdout
+ JSON Lines
```

Do not open additional local HTTP ports unless later required.

Request:

```json
{"id":"1","method":"probe","params":{}}
```

Response:

```json
{"id":"1","ok":true,"result":{"version":"1.0.0"}}
```

Pass audio as local filesystem paths, not binary JSON.

## 15. Worker protocol

Common request:

```json
{
  "id": "request-id",
  "method": "method-name",
  "params": {}
}
```

Error:

```json
{
  "id": "request-id",
  "ok": false,
  "error": {
    "code": "MODEL_NOT_READY",
    "message": "..."
  }
}
```

Version the protocol independently from app/runtime version.

## 16. Runtime probe

Every worker must implement:

```text
probe
```

Example result:

```json
{
  "runtimeVersion": "1.0.0",
  "protocolVersion": 1,
  "device": "cpu",
  "backend": "onnx",
  "modelReady": true
}
```

Installation is successful only after probe passes.

## 17. VieNeu worker

Create later:

```text
apps/vieneu-worker/
```

Methods:

```text
probe
load
unload
prepare_reference
infer
infer_many
runtime_info
```

Core continues owning:

```text
DB
queue
job state
cache
Voice Lab state
Audio Studio orchestration
```

Worker owns:

```text
VieNeu imports
ModelManager
model loading
prepare_reference
infer/infer_many
CPU/GPU tuning
```

## 18. Keep VieNeu model downloads separate

Retain the current pinned model-download principle:

```text
pinned Hugging Face revision
→ local cache
→ deterministic model paths
```

Do not move model weights into the app bundle.

Target:

```text
Runtime Manager
→ VieNeu runtime ready

Model Manager
→ VieNeu pinned model ready
```

## 19. Startup behavior

Change startup behavior toward:

```text
app startup
→ probe installed runtimes/models only
```

Do not silently download multi-GB AI assets during every startup.

Large downloads occur only after:

```text
explicit Install action
```

or first-use confirmation.

## 20. Speech worker

Create:

```text
apps/speech-worker/
```

Initial functionality:

```text
Silero VAD
Faster-Whisper
```

Methods:

```text
probe
detect_speech
transcribe
transcribe_segment
unload
```

## 21. VAD first

Use VAD as speech detection, not Whisper.

Pipeline:

```text
upload
↓
existing audio metrics
+
Silero VAD
↓
speech timeline
↓
best reference selector
↓
3–8 second reference
```

VAD supplies:

```text
speech regions
silence regions
continuous speech score
```

If VAD is unavailable:

```text
fallback to current selector
```

## 22. Reference Selector v2

Score candidate windows using:

```text
speech continuity
+ speech ratio
+ SNR
+ level stability
- silence
- clipping
- noise
- boundary cut penalty
```

Prefer continuous 3–8 second speech.

Do not select windows dominated by silence/music/noise.

## 23. Whisper integration

Whisper runs only after the reference window has been selected.

```text
selected 3–8 sec
↓
Whisper
↓
draft transcript
↓
user review/edit
```

Whisper output is a draft, never hidden ground truth.

## 24. Whisper choice

Initial recommendation:

```text
faster-whisper
```

CPU baseline:

```text
device=cpu
compute_type=int8
```

GPU support is optional.

Do not make CUDA/cuDNN a core dependency.

## 25. Whisper model choice

Benchmark:

```text
base
small
```

Evaluate:

```text
Vietnamese transcript accuracy
3–8 sec latency
RAM
download size
```

Do not default to `large-v3` without measurement.

Ship one simple default first.

## 26. Whisper model lifecycle

Whisper model is separate from runtime:

```text
models/whisper/<model>/
```

Pin model revisions.

Avoid unpinned:

```text
main
latest
```

## 27. Failure behavior

Critical:

```text
Whisper failure
≠
Voice Clone failure
```

If Whisper is missing/broken:

```text
manual transcript
→ clone normally
```

If VAD fails:

```text
current audio-analysis selector
→ fallback
```

## 28. Voice Clone target pipeline

```text
Upload reference
        ↓
Audio Metrics + Silero VAD
        ↓
Speech Timeline
        ↓
Best Segment Selector
        ↓
selected 3–8 sec
        ↓
Whisper installed?
    ┌───────┴────────┐
    │                │
   YES               NO
    │                │
    ▼                ▼
Auto transcript   Manual transcript
    │                │
    └───────┬────────┘
            ▼
      User review/edit
            ↓
      VieNeu Enrollment
            ↓
 speaker_emb + ref_codes
            ↓
       Calibration
```

## 29. V3 quality boundary

Do not change current VieNeu V3 enrollment semantics in this task.

Keep:

```text
prepare_reference(audio)
→ speaker_emb
→ ref_codes
```

VAD changes only:

```text
which sample segment is selected
```

Whisper changes only:

```text
transcript convenience / future readiness
```

## 30. Settings > Local AI

Add:

```text
Settings
└── Local AI
```

Example:

```text
VieNeu Voice Engine
Installed · 1.2.0
Model ready
[Update] [Repair] [Remove]

Speech Detection
Ready

Automatic Transcript
Whisper
Not installed
[Install]

Disk usage
2.7 GB
```

## 31. Voice Lab missing-runtime UX

VieNeu missing:

```text
Tạo giọng cần VieNeu Local Engine.
[Cài VieNeu]
```

Whisper missing:

```text
Tự nhận diện lời thoại cần Whisper.
[Cài Whisper] [Nhập thủ công]
```

Do not block unrelated features.

## 32. Build strategy

Prefer runtime worker builds as:

```text
PyInstaller --onedir
→ ZIP the directory
```

Benefits:

```text
faster process startup
native libs visible
simpler debugging
no repeated onefile extraction
```

Core `melody-api` can remain onefile if desired.

## 33. Dependency separation

Eventually:

```text
apps/api/pyproject.toml
→ core dependencies only

apps/vieneu-worker/pyproject.toml
→ VieNeu dependencies

apps/speech-worker/pyproject.toml
→ faster-whisper/CTranslate2/PyAV/VAD
```

This isolates dependency conflicts.

## 34. Core PyInstaller cleanup

Only after VieNeu worker is validated, remove heavy VieNeu collection from the core build, including equivalent entries such as:

```text
--hidden-import=vieneu
--collect-all=vieneu
--collect-all=vieneu_utils
--collect-all=onnxruntime
```

Remove only dependencies no longer needed by core.

Measure bundle size before/after.

## 35. GPU strategy

Phase 1:

```text
CPU-first
```

Later:

```text
optional GPU runtime pack
```

Do not bundle CUDA/cuDNN into Melody Core.

GPU runtime failure should fall back to CPU where possible.

## 36. Runtime lifecycle

Start workers lazily when their features are used.

Do not load:

```text
VieNeu
Whisper
```

at app startup by default.

Workers shut down on app exit and may later use idle timeout unloading.

## 37. Runtime security

Install only trusted manifests.

Require:

```text
HTTPS
SHA-256
known runtime ID
known platform/arch
protocol compatibility
```

Do not support arbitrary URL runtime installation.

## 38. Update strategy

Use independent lifecycles:

```text
Melody Core
→ Tauri updater

Runtime
→ Runtime Manager

Model
→ Model Manager
```

This prevents app UI updates from forcing large model/runtime redownloads.

## 39. Optional Full Offline installer

Later release both:

```text
MelodySetup.exe
```

and optional:

```text
Melody-Full-Offline.exe
```

Offline installer may include runtime/model packs but should not be the default public artifact.

## 40. Recommended implementation phases

### Phase 0 — Runtime Manager foundation

Implement:

```text
manifest
registry
download
SHA-256
safe ZIP extraction
staging
worker probe
atomic activation
rollback
remove
repair
status API
```

No major ML migration yet.

### Phase 1 — Silero VAD

Implement:

```text
speech timeline
continuous speech scoring
fallback
```

Use it in best-segment selection.

### Phase 2 — Reference Selector v2

Combine VAD and existing audio metrics.

Benchmark old vs new segment selection.

### Phase 3 — Speech Worker

Create standalone runtime pack with:

```text
Silero VAD
faster-whisper
worker protocol
```

### Phase 4 — Auto Transcript

```text
selected segment
→ transcribe_segment
→ prefill transcript
→ user edit
```

### Phase 5 — Local AI Settings

Add install/update/repair/remove/progress/disk-usage UI.

### Phase 6 — VieNeu Worker

Extract VieNeu inference from core while keeping DB/jobs/cache/orchestration in core.

### Phase 7 — Core bundle slimming

Remove heavy VieNeu/native ML dependencies from `melody-api-core` after worker validation.

### Phase 8 — Optional GPU packs

Add only after CPU path is production-stable.

### Phase 9 — Full Offline Installer

Optional release artifact only.

## 41. Recommended commit sequence

```text
feat(runtime): add local AI runtime manifest and registry
feat(runtime): add verified runtime installer and rollback
feat(voice-lab): add Silero VAD speech timeline
feat(voice-lab): improve reference selection with speech continuity
feat(speech): add standalone speech worker
feat(speech): add optional faster-whisper transcription
feat(voice-lab): auto-fill selected segment transcript
feat(settings): add Local AI runtime management
refactor(vieneu): move inference into standalone worker
build(api): remove VieNeu runtime dependencies from core sidecar
feat(runtime): add optional GPU runtime support
```

## 42. Validation

Core must PASS:

```text
Melody opens without VieNeu runtime
Melody opens without Whisper runtime
CapCut path works
DB works
settings work
updater works
```

VieNeu:

```text
missing state
install
checksum/probe
model download
clone
Audio Studio generation
restart reuse
repair
remove
```

VAD:

```text
silence
clean speech
speech + silence
noise
music + speech
long pause
fallback
```

Whisper:

```text
missing runtime
install
short Vietnamese sample
CPU INT8
transcript
manual edit
failure fallback
restart reuse
```

Privacy:

```text
audio remains local
transcript remains local
no transcript content in logs
no cloud ASR
```

## 43. Benchmark

Measure:

```text
Core installer size
Core API sidecar size
VieNeu runtime pack size
Speech runtime pack size
model sizes
first install time
warm startup time
worker startup time
VAD latency
Whisper 3–8 sec latency
RAM
CPU
```

Do not fabricate numbers.

## 44. Feature flags / rollback

Use during migration:

```text
RUNTIME_PACK_MANAGER_ENABLED
SPEECH_VAD_ENABLED
SPEECH_WHISPER_ENABLED
VIENEU_WORKER_ENABLED
```

During transition:

```text
VIENEU_WORKER_ENABLED=false
→ current in-process VieNeu path
```

Remove the old path only after worker validation.

## 45. Definition of Done

```text
✓ Default installer does not include VieNeu model files.
✓ Default installer does not include Whisper runtime/model.
✓ Heavy VieNeu runtime is separable from Core Melody.
✓ Heavy Whisper runtime is separable from Core Melody.
✓ Runtime packs are versioned and checksummed.
✓ Installation is atomic and rollback-safe.
✓ Runtime/model data lives in persistent app data.
✓ Core works without optional runtimes.
✓ VAD improves speech-aware reference selection.
✓ Whisper can auto-fill selected-segment transcript.
✓ Manual transcript always remains available.
✓ Whisper failure never blocks V3 voice cloning.
✓ VieNeu model downloads remain pinned/reproducible.
✓ Core/runtime/model updates have independent lifecycles.
✓ Full Offline installer remains possible later.
```

---

# Coding Agent Prompt

```text
Read `VOID_MELODY_OPTIONAL_AI_RUNTIME_PACKS_PLAN.md` completely before changing code.

Work against the latest main and report the base commit SHA first.

PRIMARY GOAL

Move Void Melody toward a small Core installer with optional downloadable local AI runtimes.

Heavy VieNeu/Whisper ML stacks must not become permanent dependencies of the default Tauri bundle.

TARGET

Core Melody:
- Tauri UI
- melody-api core
- SQLite
- FFmpeg
- orchestration
- runtime manager

Optional runtime packs:
- VieNeu worker
- Speech worker

Models:
- separately downloaded, pinned model files

AUDIT FIRST

Inspect:
- apps/web/src-tauri/tauri.conf.json
- apps/api/build.py
- apps/api/pyproject.toml
- package.json build scripts
- apps/api/app/main.py
- apps/api/app/services/vieneu_bootstrap.py
- packages/vieneu-core/src/vieneu_core/downloader.py
- packages/vieneu-core/src/vieneu_core/engine.py
- current Voice Lab audio analysis/reference selector
- current runtime/model storage paths
- release workflow

HARD RULES

Do NOT:
- bundle Whisper model into default installer
- bundle Whisper runtime into default installer
- move VieNeu models into default installer
- silently download large AI assets every startup
- require Whisper for V3 cloning
- require CUDA
- break CapCut
- move DB/job business state into workers
- rewrite the whole queue architecture
- combine VieNeu and Whisper worker extraction into one unsafe mega-change

PHASE 0 — RUNTIME MANAGER

Implement:
- runtime manifest
- registry
- verified download
- SHA-256
- safe ZIP extraction
- staging
- worker probe
- atomic activation
- rollback
- repair
- uninstall
- status API

Use persistent app-data storage, not Tauri resources/Program Files.

PHASE 1 — VAD

Add Silero VAD to Voice Lab analysis.

VAD is the primary speech detector.
Whisper is NOT the primary speech detector.

Improve the reference selector using:
- continuous speech
- speech ratio
- SNR
- noise
- clipping
- level stability
- silence
- boundary-cut penalty

Keep a fallback to the existing selector.

PHASE 2 — SPEECH WORKER

Create `apps/speech-worker`.

Use JSON Lines over stdin/stdout.

Methods:
- probe
- detect_speech
- transcribe
- transcribe_segment
- unload

Pass audio using local paths.

PHASE 3 — FASTER-WHISPER

Integrate faster-whisper as optional ASR.

Start with CPU INT8.
Benchmark a practical Vietnamese base/small model.
Do not default to large-v3 without evidence.

Whisper runtime and Whisper model must be independently installable.

PHASE 4 — VOICE LAB AUTO TRANSCRIPT

selected 3–8 sec
→ optional transcribe_segment
→ prefill transcript
→ user review/edit

Whisper failure or missing runtime:
→ manual transcript remains available
→ V3 cloning still works

Do not change VieNeu V3 enrollment semantics.

PHASE 5 — SETTINGS > LOCAL AI

Add:
- install
- update
- repair
- remove
- status
- progress
- disk usage

PHASE 6 — VIENEU WORKER

Only after Runtime Manager/Speech Worker are stable, move VieNeu inference into a standalone worker pack.

Core keeps:
- DB
- jobs
- scheduler
- cache
- Voice Lab workflow
- Audio Studio orchestration

Worker owns:
- VieNeu imports
- ModelManager
- model loading
- prepare_reference
- infer
- infer_many
- runtime tuning

PHASE 7 — CORE BUNDLE SLIMMING

Only after VieNeu worker validation, remove heavy VieNeu/native ML collection from the Core PyInstaller build.

Measure bundle size before and after.

STARTUP

Replace automatic large-asset downloading with:
- runtime/model probe on startup
- explicit Install action
- first-use confirmation

Do not redownload installed models every startup.

BUILD

Prefer worker runtime packs built as:
PyInstaller --onedir
→ ZIP

Runtime and app versions are independent.

SECURITY

Require:
- HTTPS
- SHA-256
- platform/arch match
- protocolVersion compatibility
- safe extraction

Reject arbitrary runtime URLs and ZIP path traversal.

GPU

CPU first.
GPU runtime support is optional later.
Do not bundle CUDA/cuDNN into Melody Core.

VALIDATION

Core must run with neither VieNeu nor Whisper installed.

Validate:
- runtime install/update/repair/remove
- restart reuse
- VieNeu clone/generation
- VAD speech selection
- Whisper short Vietnamese transcription
- manual transcript fallback
- CapCut unchanged
- privacy/local-only behavior

FINAL REPORT

Return:

## Base commit
## Current bundle audit
## Runtime Manager
## Runtime manifest/registry
## Runtime storage
## VAD integration
## Reference Selector v2
## Speech Worker
## Whisper integration
## Voice Lab auto transcript
## Local AI settings
## VieNeu worker migration
## Core bundle size before/after
## Startup/download behavior
## Runtime update/rollback
## Validation PASS/FAIL/NOT RUN
## Remaining technical debt

Do not fabricate size or benchmark numbers.

If a later phase is too risky to combine safely, stop at a clean architectural boundary and document the exact next phase rather than forcing a mega-refactor.
```
