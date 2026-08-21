# VOID MELODY — OMNIVOICE PROVIDER + MULTILINGUAL + VOICE DESIGN + SRT DUBBING
## Execution Plan — Backend-First / Low-Conflict Integration

**Project:** `voidstation-dev/void-melody`  
**Plan date:** 2026-08-21  
**Baseline branch:** `main`  
**Baseline commit:** `e1d2694079e0eca9bcaf2ae96d157d0800a71c00`  
**Baseline merge:** PR #17 — `fix: harden post-PR16 Voice Lab runtime and batch flows`  
**Target:** free/non-commercial GitHub release, local/offline-first desktop app  
**New provider ID:** `omnivoice`  
**Existing provider IDs preserved:** `capcut`, `vieneu`

---

# 0. Executive decision

OmniVoice **will be added as an optional provider**, not as a replacement for VieNeu.

Final engine roles:

```text
Void Melody
│
├── CapCut
│   └── preserve existing behavior
│
├── VieNeu
│   ├── default Vietnamese engine
│   ├── VI / EN
│   ├── CPU / ONNX
│   ├── lightweight
│   ├── streaming
│   └── Vietnamese voice cloning
│
└── OmniVoice
    ├── optional downloadable runtime
    ├── 600+ languages
    ├── zero-shot voice cloning
    ├── reusable VoiceClonePrompt
    ├── voice design / instruction
    ├── target-duration generation
    └── primary SRT multilingual dubbing engine
```

The integration must preserve the current Void Melody architecture.

**Do not create:**

- another FastAPI application;
- another localhost HTTP port;
- another SQLite database;
- another TTS queue;
- another global job system;
- a replacement for the existing VieNeu `ModelManager`;
- a second export/conversion stack;
- a new custom voice library unrelated to `tts_custom_voices`.

---

# 1. Why OmniVoice must be runtime-isolated

The current Melody API dependency set intentionally stays relatively small and already embeds VieNeu.

Current API:

```text
FastAPI
SQLAlchemy
CapCut
vieneu-core
VieNeu
PyInstaller
```

OmniVoice 0.2.x requires a much heavier stack:

```text
torch >= 2.4
torchaudio >= 2.4
transformers >= 5.3.0
accelerate
librosa
soundfile
pydub
...
```

The upstream OmniVoice project explicitly recommends using a fresh virtual environment to avoid dependency conflicts.

Therefore production integration MUST NOT simply add:

```toml
"omnivoice"
```

to the base `apps/api/pyproject.toml` and hope dependency resolution remains stable.

That approach would:

1. inflate the base installer;
2. make VieNeu CPU-only installs pull PyTorch unnecessarily;
3. increase startup time and RAM;
4. increase PyInstaller complexity;
5. create future `transformers` / `torch` version conflicts;
6. make low-spec VieNeu mode worse;
7. make uninstall/update of OmniVoice difficult.

## Approved runtime architecture

```text
Tauri
  │
  ▼
Melody API sidecar
  │
  │ normal TTS job queue
  │
  ├─────────────── VieNeuProvider
  │                   │
  │                   └── existing VieNeu ModelManager
  │
  └─────────────── OmniVoiceProvider
                      │
                      ▼
               OmniVoiceRuntimeClient
                      │
             stdin/stdout JSONL IPC
                      │
                      ▼
        optional omnivoice-worker process
                      │
                 isolated runtime
                      │
        ~/.void-melody/runtimes/omnivoice/
                      │
                OmniVoice model
```

There is still only **one HTTP API** and **one TTS queue**.

The OmniVoice worker is a local model subprocess, not another server.

**No HTTP port. No public socket.**

---

# 2. Runtime/package layout

Recommended application data layout:

```text
~/.void-melody/
├── db/
├── audio/
├── voices/
│   ├── vieneu/
│   └── omnivoice/
│       ├── references/
│       └── prompts/
├── models/
│   ├── vieneu/
│   └── omnivoice/
│       └── k2-fsa-OmniVoice/
├── runtimes/
│   └── omnivoice/
│       ├── runtime-manifest.json
│       ├── bin/
│       ├── python/
│       └── packages/
└── temp/
    └── omnivoice/
```

For release builds:

```text
Void Melody base installer
    ↓
does NOT include OmniVoice weights
    ↓
Models page
    ↓
Install OmniVoice
    ↓
download/install optional runtime
    ↓
download official model
    ↓
verify hashes
    ↓
runtime becomes Ready
```

---

# 3. OmniVoice version policy

Do not run against unpinned `master` in production.

Initial target:

```text
omnivoice package = 0.2.1
```

Before release, resolve and record:

```text
package_version
source_commit
model_repo
model_revision
model_file_sha256
runtime_platform
torch_version
torchaudio_version
transformers_version
```

Store in:

```text
runtime-manifest.json
```

Example contract:

```json
{
  "provider_id": "omnivoice",
  "runtime_version": 1,
  "omnivoice_version": "0.2.1",
  "model_repo": "k2-fsa/OmniVoice",
  "model_revision": "<PINNED_HF_REVISION>",
  "device_backend": "cpu",
  "status": "ready"
}
```

Do not fill `<PINNED_HF_REVISION>` by guessing.

Resolve it during implementation Phase O0.

---

# 4. Provider capability model

Existing provider registry already supports stable provider IDs.

Extend it additively.

Provider capability contract should become provider-neutral enough to represent:

```text
preset voices
voice cloning
streaming
batch
styles
emotion tags
multilingual
voice design
target duration
text normalization
cross-lingual cloning
```

Recommended capability shape:

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    supports_preset_voices: bool
    supports_voice_cloning: bool
    supports_streaming: bool
    supports_styles: bool
    supports_batch: bool
    supports_emotion_tags: bool

    supports_multilingual: bool = False
    supports_voice_design: bool = False
    supports_target_duration: bool = False
    supports_text_normalization: bool = False
    supports_cross_lingual_clone: bool = False

    max_text_chars: int | None = None
    sample_rate: int | None = None
    languages: tuple[str, ...] | None = None
```

Do not hard-code OmniVoice capability in the frontend.

Backend is the source of truth.

---

# 5. Provider registry target

Current:

```text
capcut
vieneu
```

Target:

```text
capcut
vieneu
omnivoice
```

Stable ID:

```python
OMNIVOICE = "omnivoice"
```

Registry descriptor only describes the provider.

It MUST NOT load the 0.6B model.

Application startup must remain fast even if OmniVoice is installed.

---

# 6. Two registry concepts must remain separate

Current code has two related concepts:

1. provider descriptor registry;
2. queue manager live provider instance mapping.

Keep them separate.

Target:

```text
ProviderRegistry
    ↓
metadata/capabilities

QueueManager.provider_registry
    ↓
live adapters
```

Do not turn descriptor registration into model initialization.

---

# 7. OmniVoice runtime state machine

Use an explicit runtime state.

```text
NOT_INSTALLED
    ↓
DOWNLOADING_RUNTIME
    ↓
INSTALLING_RUNTIME
    ↓
DOWNLOADING_MODEL
    ↓
VERIFYING
    ↓
READY
```

Failure paths:

```text
DOWNLOAD_FAILED
INSTALL_FAILED
MODEL_CORRUPT
RUNTIME_INCOMPATIBLE
MODEL_MISSING
BROKEN
```

Do not expose a boolean only:

```text
installed = true
```

because installed files do not prove inference works.

Capability is Ready only after smoke verification.

---

# 8. OmniVoice runtime smoke verification

After installation:

```text
spawn worker
    ↓
ping
    ↓
report package versions
    ↓
report device
    ↓
load model
    ↓
run minimal inference
    ↓
validate WAV
    ↓
shutdown
```

Only then:

```text
runtime.status = READY
```

Recommended smoke sentence:

```text
"Hello."
```

Do not use voice cloning for the base runtime smoke.

Clone is verified separately.

---

# 9. IPC protocol

Use newline-delimited JSON over stdin/stdout.

No HTTP.

Example request:

```json
{
  "id": "req-123",
  "method": "synthesize",
  "params": {
    "text": "Hello world",
    "language": "en",
    "voice_prompt_path": null,
    "instruct": null,
    "duration": null,
    "speed": 1.0,
    "normalize_text": false,
    "output_path": "/tmp/output.wav"
  }
}
```

Response:

```json
{
  "id": "req-123",
  "ok": true,
  "result": {
    "path": "/tmp/output.wav",
    "sample_rate": 24000,
    "duration_seconds": 1.82
  }
}
```

Error:

```json
{
  "id": "req-123",
  "ok": false,
  "error": {
    "code": "OMNI_INFERENCE_FAILED",
    "message": "..."
  }
}
```

Worker logs go to stderr.

Never mix logging into stdout JSON protocol.

---

# 10. Worker methods

Minimum worker RPC methods:

```text
ping
runtime_info
load_model
unload_model
synthesize
create_voice_prompt
validate_voice_prompt
shutdown
```

Later optional:

```text
synthesize_batch
```

Do not implement training/fine-tuning in initial integration.

---

# 11. OmniVoice runtime lifecycle

`OmniVoiceRuntimeClient` owns process lifecycle.

Requirements:

- lazy spawn;
- one worker per application session;
- serialized model load;
- detect dead child;
- request timeout;
- clean shutdown;
- restart after crash;
- no zombie process;
- maximum one model instance by default.

Pseudo-flow:

```text
job arrives
    ↓
OmniVoiceProvider
    ↓
runtime_client.ensure_started()
    ↓
worker exists?
    ├── yes → reuse
    └── no  → spawn
                 ↓
             handshake
                 ↓
             load model
```

Idle unload can be deferred until real memory measurements exist.

---

# 12. Concurrency rule

Do NOT assume OmniVoice can safely run at Void Melody's generic chunk concurrency.

Initial production rule:

```text
OmniVoice inference concurrency = 1
```

Use provider-level semaphore:

```python
asyncio.Semaphore(1)
```

Later benchmarking may increase this for CUDA.

The global TTS queue may have concurrency >1.

That does not mean OmniVoice inference should.

---

# 13. Resource arbitration between VieNeu and OmniVoice

Potential conflict:

```text
VieNeu GPU model
+
OmniVoice GPU model
=
VRAM pressure
```

Initial rule:

```text
do not keep both heavy GPU runtimes loaded simultaneously
```

Introduce optional `ModelResourceCoordinator`.

Minimal responsibilities:

```text
provider requests heavy model
    ↓
check currently active heavy provider
    ↓
if different:
    unload previous if policy requires
    ↓
grant
```

Do not build a complex GPU scheduler.

V1 can use:

```text
single_heavy_model = true
```

for GPU mode.

CPU VieNeu ONNX can remain resident if memory budget allows.

---

# 14. Base provider API must be extended carefully

Current provider call:

```python
provider.synthesize(
    text=...,
    voice_type=...,
    resource_id=...,
    rate=...,
    style=...,
)
```

OmniVoice additionally needs:

```text
language
instruct
duration
normalize_text
voice prompt
```

Avoid adding a growing list of provider-specific top-level parameters.

Recommended additive contract:

```python
@dataclass(frozen=True)
class SynthesisOptions:
    language: str | None = None
    instruction: str | None = None
    target_duration_seconds: float | None = None
    normalize_text: bool = False
```

Provider:

```python
async def synthesize(
    *,
    text: str,
    voice_type: str,
    resource_id: str | None,
    rate: float,
    style: str | None = None,
    options: SynthesisOptions | None = None,
) -> ProviderResult:
    ...
```

Update:

```text
CapCutProvider
VieNeuProvider
OmniVoiceProvider
TTSProvider Protocol
tests
```

CapCut/VieNeu ignore unsupported options or reject invalid requests at a higher validation layer.

Do NOT allow silent semantic mismatches.

---

# 15. Job persistence changes

Generation settings must survive:

```text
queue delay
app restart
job retry
```

Therefore they cannot exist only in HTTP memory.

Add additive job columns.

Recommended:

```text
language_code
voice_instruction
target_duration_seconds
normalize_text
generation_mode
```

Possible modes:

```text
standard
voice_clone
voice_design
srt_cue
```

Prefer explicit columns for release-critical semantics.

Do not hide `target_duration_seconds` only inside arbitrary JSON because:

- it affects worker execution;
- it affects retry determinism;
- it affects SRT correctness;
- it needs validation/index-independent debugging.

Provider-specific advanced knobs may later use JSON.

---

# 16. Rate vs target duration invariant

This is a release-critical backend rule.

Current worker can apply playback speed with FFmpeg `atempo`.

OmniVoice target-duration generation already controls pacing.

These must not fight.

Invariant:

```text
target_duration_seconds != None
    =>
provider receives duration
    AND
post-generation FFmpeg rate adjustment = disabled
```

Reject:

```text
duration = 3.5
rate = 1.3
```

unless product semantics explicitly define precedence.

For V1:

```text
duration overrides rate
```

matching OmniVoice semantics.

Store effective rate as:

```text
1.0
```

for strict-duration SRT jobs.

---

# 17. Generic chunking vs fixed-duration invariant

Current worker:

```text
text
  ↓
split_text_into_chunks
  ↓
provider.synthesize each chunk
  ↓
combine
```

This is unsafe for a cue with:

```text
target duration = 3.5 seconds
```

because applying 3.5 seconds to every chunk is wrong.

For:

```text
generation_mode = srt_cue
```

use:

```text
ONE cue
=
ONE provider synthesis request
=
ONE target duration
```

Do not generic-chunk a cue in V1.

Enforce cue text maximum.

If a cue is too long:

```text
SRT_CUE_TEXT_TOO_LONG
```

and let the Dubbing planner resolve it.

---

# 18. Custom voice schema strategy

Do not replace `tts_custom_voices`.

Current model already has:

```text
provider_id
engine_id
status
reference_audio_path
transcript
quality metadata
```

This is already provider-aware.

For OmniVoice V1, keep custom voices **provider-scoped**.

Example:

```text
voice A
provider=vieneu

voice B
provider=omnivoice
```

Do not prematurely build a provider-agnostic parent voice graph.

---

# 19. Custom voice additive fields

Add only what OmniVoice actually needs.

Recommended fields:

```text
language_code
clone_artifact_path
clone_artifact_format
clone_artifact_version
```

Where OmniVoice can store:

```text
VoiceClonePrompt .pt
```

Example:

```text
provider_id = omnivoice
engine_id = omnivoice-0.2.1
reference_audio_path = ...
clone_artifact_path = .../prompts/<uuid>.pt
clone_artifact_format = omnivoice-voice-clone-prompt
clone_artifact_version = 1
```

VieNeu can leave clone artifact fields null.

---

# 20. Why save OmniVoice VoiceClonePrompt

OmniVoice supports:

```text
create_voice_clone_prompt()
VoiceClonePrompt.save()
VoiceClonePrompt.load()
```

This avoids re-encoding the same reference every generation.

Create Voice flow:

```text
reference audio
    ↓
audio validation
    ↓
OmniVoice worker
    ↓
create_voice_clone_prompt
    ↓
save prompt artifact
    ↓
validate prompt load
    ↓
DB ready
```

Generation:

```text
custom voice ID
    ↓
resolve DB
    ↓
prompt path
    ↓
worker VoiceClonePrompt.load()
    ↓
generate
```

This is preferable to reprocessing reference WAV on every call.

Keep reference audio anyway for:

- future migration;
- recreation if artifact format changes;
- preview;
- audit/recovery.

---

# 21. OmniVoice custom voice lifecycle

Use explicit states:

```text
creating
ready
failed
deleting
```

Create:

```text
upload/reference exists
    ↓
DB row status=creating
    ↓
create prompt to temporary .pt
    ↓
validate prompt
    ↓
atomic rename to final path
    ↓
DB status=ready
```

Failure:

```text
cleanup temporary artifact
DB failed or row removed
reference retained/removed according to transaction policy
```

Never mark `ready` before the prompt can be loaded.

---

# 22. Voice name uniqueness

Current duplicate-name behavior must be reviewed for multi-provider semantics.

Recommended uniqueness for V1:

```text
(display_name, provider_id)
```

This permits:

```text
"My Voice" / VieNeu
"My Voice" / OmniVoice
```

If current DB has global display-name uniqueness in application logic, modify it carefully.

Do not change legacy records unexpectedly.

---

# 23. VoiceResolver changes

Current resolver hard-codes custom voice language:

```text
vi-VN
```

This must be removed before OmniVoice custom voices.

Target:

```python
ResolvedVoice(
    voice_type=custom.id,
    display_name=custom.display_name,
    language_code=custom.language_code,
    resource_id=None,
    provider_id=custom.provider_id,
    source="custom",
    status=custom.status,
)
```

Fallback for old rows:

```text
provider=vieneu
language_code missing
    →
vi-VN
```

Migration should backfill existing VieNeu custom profiles.

---

# 24. Voice resolution must remain shared

Do not regress PR #17.

The same `resolve_voice()` must continue to serve:

```text
single job
preview
batch
SRT cue creation
```

OmniVoice must not add a separate voice lookup path.

---

# 25. OmniVoiceProvider responsibilities

`apps/api/app/providers/omnivoice_provider.py`

Responsibilities:

```text
validate provider options
resolve custom prompt path
talk to runtime client
convert/return audio path
map worker errors
expose provider capabilities
```

It must NOT:

```text
create database sessions for arbitrary job logic
manage TTS queue
download models
run migrations
parse SRT
own UI state
```

Voice resolution happens before provider invocation.

---

# 26. Model installer responsibilities

Create a focused service:

```text
OmniVoiceRuntimeInstaller
```

Responsibilities:

```text
detect platform
download correct runtime pack
verify checksum
atomic install
download model from official source
track progress
verify model files
write manifest
run smoke
rollback failed install
uninstall
```

Do not put installation logic into `OmniVoiceProvider`.

---

# 27. Optional runtime distribution

Preferred GitHub release layout:

```text
VoidMelody-x.y.z-setup.exe
VoidMelody-x.y.z.dmg

optional assets:
omnivoice-runtime-windows-x64-<version>.zip
omnivoice-runtime-macos-arm64-<version>.tar.zst
omnivoice-runtime-macos-x64-<version>.tar.zst
```

Runtime packs contain:

```text
Python runtime
OmniVoice code
Torch stack
dependencies
worker entrypoint
manifest
```

Runtime packs do NOT need to contain pretrained model weights.

Model Manager downloads model separately from official source.

---

# 28. Model download security/reliability

Requirements:

- HTTPS only;
- allowlisted official source;
- temp `.partial` path;
- resume if supported;
- expected size;
- SHA-256;
- atomic rename;
- disk-space preflight;
- cancellation;
- cleanup partial on fatal failure;
- never execute content from model directory.

Paths must be generated by backend, not supplied unchecked by UI.

---

# 29. Models API

Add a general model/runtime API rather than OmniVoice-specific frontend filesystem logic.

Suggested:

```text
GET    /api/v1/models
GET    /api/v1/models/omnivoice
POST   /api/v1/models/omnivoice/install
POST   /api/v1/models/omnivoice/repair
DELETE /api/v1/models/omnivoice
POST   /api/v1/models/omnivoice/smoke
```

If installation is long-running, use an existing local task/job mechanism or a small install-state service backed by manifest.

Do NOT reuse TTS jobs for model download unless doing so materially simplifies recovery.

Only one install operation at a time.

---

# 30. Provider capabilities API

Move toward:

```text
GET /api/v1/tts/providers
GET /api/v1/tts/providers/{provider_id}/capabilities
```

Do not remove existing:

```text
GET /api/v1/tts/voices/capabilities
```

Keep backward compatibility for VieNeu Voice Lab.

Frontend can transition gradually.

---

# 31. Auto provider router

Do not auto-route silently in the backend on day one.

Phase 1 behavior:

```text
provider chosen explicitly by voice/provider
```

After providers are stable, add:

```text
provider_id = auto
```

Routing policy should be deterministic and explainable.

Suggested V1 auto rules:

```text
custom voice selected
    → use voice.provider_id

Vietnamese preset / low-spec
    → VieNeu

VI/EN streaming
    → VieNeu

unsupported VieNeu language
    → OmniVoice if installed

voice design request
    → OmniVoice

SRT strict-duration request
    → OmniVoice

OmniVoice unavailable
    → do not silently switch if semantics change
```

Return routing decision in response/job metadata.

---

# 32. Multilingual contract

Add canonical language code.

Use BCP-47 where possible:

```text
vi-VN
en-US
ja-JP
ko-KR
fr-FR
...
```

Provider adapter maps BCP-47 to OmniVoice accepted language code/name.

Central service:

```text
LanguageRegistry
```

Responsibilities:

```text
canonical language
display name
provider mapping
provider support
```

Do not put a hard-coded list of 600 languages inside React components.

---

# 33. Language validation

At job creation:

```text
requested language
    ↓
provider capability
    ↓
supported?
```

Error:

```text
LANGUAGE_NOT_SUPPORTED_BY_PROVIDER
```

Do not allow a job to queue if the provider cannot fulfill it.

---

# 34. Cross-lingual cloning behavior

OmniVoice supports using cloned identity across languages.

However accent can follow the reference audio.

UI and API must not promise perfect native accent preservation.

Store:

```text
reference_language_code
```

Optionally target:

```text
language_code
```

Allow:

```text
reference_language != target_language
```

if provider capability:

```text
supports_cross_lingual_clone = true
```

---

# 35. Expression layer design

Do not expose OmniVoice's raw `instruct` as the only UI.

Create a provider-neutral expression request:

```text
style
emotion
intensity
instruction
```

Initially map:

```text
VieNeu:
style → existing style

OmniVoice:
instruction → instruct
```

Advanced free-form instruction can remain under:

```text
Advanced
```

Do not fake unsupported numeric emotion controls.

Capability-driven UI only.

---

# 36. Voice Design mode

OmniVoice supports generating a designed voice without reference audio.

Treat this separately from persisted voice clone.

Modes:

```text
preset
clone
design
auto
```

Initial design generation can be ephemeral.

Later user can save output audio as a new reference and clone from it.

Do not invent a stable "voice embedding" for Voice Design if OmniVoice does not expose one.

---

# 37. OmniVoice generation request

Internal request:

```python
@dataclass
class OmniSynthesisRequest:
    text: str
    language: str | None
    clone_prompt_path: str | None
    instruction: str | None
    target_duration_seconds: float | None
    speed: float | None
    normalize_text: bool
```

Rules:

```text
clone_prompt + instruction
    allowed
    but instruction may lose against reference characteristics

target_duration
    overrides speed

clone_prompt
    overrides raw ref audio during normal generation
```

---

# 38. Audio output normalization

OmniVoice commonly produces WAV around 24 kHz.

Void Melody's existing job pipeline expects final MP3 artifacts.

Provider may:

```text
worker writes WAV
    ↓
OmniVoiceProvider / common audio layer
    ↓
FFmpeg converts to MP3
    ↓
ProviderResult.local_paths
```

Reuse existing FFmpeg config.

Do not introduce another encoder.

---

# 39. Important worker compatibility

Current TTS worker expects provider local paths to become:

```text
*.mp3
```

Therefore OmniVoiceProvider should return an MP3 local path to the existing generic worker for standard TTS jobs.

Alternative WAV-native worker support can be considered later.

Keep initial blast radius low.

---

# 40. SRT module ownership

SRT parsing is NOT a provider concern.

Create:

```text
apps/api/app/services/dubbing/
├── srt_parser.py
├── timeline.py
├── duration_fit.py
├── renderer.py
└── schemas.py
```

Provider only synthesizes a cue.

---

# 41. SRT parser contract

Parse:

```text
cue_id
start_ms
end_ms
duration_ms
text
```

Validate:

- monotonic timestamps;
- start < end;
- non-empty text;
- safe maximum cue count;
- safe total duration;
- UTF-8 / BOM;
- CRLF/LF;
- malformed timestamps;
- overlapping cues.

Do not silently repair malformed SRT without reporting warnings.

---

# 42. Dubbing persistence

Create dedicated dubbing tables if feature must survive restart.

Recommended:

```text
tts_dubbing_projects
tts_dubbing_cues
```

Project:

```text
id
name
source_file_name
language_code
voice_type
provider_id
status
created_at
updated_at
```

Cue:

```text
id
project_id
position
start_ms
end_ms
text
provider_id
voice_type
status
audio_path
generated_duration_ms
fit_ratio
error_code
error_message
```

Do NOT overload one `tts_jobs` row to represent an entire SRT.

---

# 43. Relationship between SRT cues and TTS jobs

Each cue generation should reuse the existing job queue where practical.

Recommended:

```text
DubbingCue
    │
    └── creates TTSJob
          generation_mode=srt_cue
          target_duration_seconds=cue duration
```

Store:

```text
dubbing_project_id
dubbing_cue_id
```

on job if necessary.

Then existing queue/retry/cancellation remains useful.

---

# 44. SRT cue generation strategy

For each cue:

```text
text
target_duration
language
voice
provider
    ↓
validate
    ↓
create cue TTS job
    ↓
queue
    ↓
provider
    ↓
generated audio
    ↓
measure duration
    ↓
fit evaluation
```

Do not render final timeline until required cue jobs finish.

---

# 45. Duration fit policy

OmniVoice native `duration` is primary.

After output:

```text
actual_duration
vs
target_duration
```

Tolerance:

```text
absolute error <= 80 ms
OR
relative error <= 3%
```

Exact numbers should be benchmarked and may be adjusted.

If outside tolerance:

```text
small difference
    → FFmpeg micro-fit

large difference
    → retry with adjusted target / mark warning
```

Never blindly stretch by extreme factors.

Suggested hard limits:

```text
0.85x <= post-fit speed <= 1.18x
```

Beyond this:

```text
CUE_DURATION_UNFIT
```

with UI warning.

---

# 46. Very short SRT cues

OmniVoice upstream notes very short generation (around 1–2 seconds) can be less reliable without reference audio.

Policy:

```text
duration < short_cue_threshold
```

Options:

1. prefer cloned/reference voice;
2. allow generated audio + controlled fit;
3. flag cue if output is unstable.

Do not globally fail all 1–2 second cues.

Add tests and benchmark.

---

# 47. SRT overlap policy

SRT may contain overlapping cues.

Initial render strategy:

```text
mix cues at timestamp
```

not concatenate sequentially.

Use FFmpeg filter graph or an equivalent deterministic timeline compositor.

Do not shift later cues automatically unless user selects a reflow policy.

---

# 48. SRT final render

Render:

```text
silence base timeline
    +
cue audio positioned at start_ms
    ↓
mix
    ↓
final WAV
    ↓
export MP3/M4A/WAV
```

Reuse existing FFmpeg binary.

Preserve maximum end timestamp.

---

# 49. Speaker-per-cue future compatibility

Schema should allow:

```text
cue.voice_type
cue.provider_id
```

even if V1 applies one voice globally.

This enables future:

```text
multi-speaker dubbing
```

without schema rewrite.

Do not implement diarization in this phase.

---

# 50. Frontend navigation

Approved target:

```text
Generate
Voice Lab
SRT Dubbing
Voice Library
Models
```

Do not add a standalone `OmniVoice` route as the primary product UX.

Provider is an engine, not a product page.

---

# 51. Generate UI

Engine control:

```text
Auto
VieNeu
OmniVoice
```

Only show OmniVoice if:

```text
runtime status known
```

If not installed:

```text
OmniVoice
Not installed
[Install]
```

Do not crash or disable VieNeu when OmniVoice is absent.

---

# 52. Capability-driven controls

VieNeu selected:

```text
Style
Speed
Streaming
VI/EN
```

OmniVoice selected:

```text
Language
Voice Clone
Voice Design
Instruction
Speed
Target Duration (advanced / SRT)
Text normalization
```

Do not display disabled controls without explaining why unless that improves discoverability.

---

# 53. Voice Lab integration

Current Voice Lab must continue working for VieNeu.

Add provider selection to Create Voice:

```text
Clone with
○ VieNeu
○ OmniVoice
```

Do not make `Auto` the initial create-profile default.

Reason:

```text
a custom voice profile is provider-scoped
```

and ambiguity would make persistence confusing.

---

# 54. Voice Lab provider behavior

VieNeu:

```text
existing reference analysis
3–8 sec contract
real VieNeu preflight
ready
```

OmniVoice:

```text
reference analysis
recommended 3–10 sec
transcript required/recommended
create VoiceClonePrompt
save .pt
validate load
ready
```

The shared upload/analyze UX may be reused.

Provider-specific validation occurs after selection.

---

# 55. Reference transcript

OmniVoice can use `ref_text`.

For V1:

```text
require transcript for explicit clone creation
```

This avoids introducing an ASR model and more runtime dependencies immediately.

Later:

```text
Auto Transcribe
```

can be optional.

Do not silently download a large ASR model during clone creation.

---

# 56. Voice Library

Existing table can show:

```text
Name
Provider badge
Language
Clone status
Reference duration
Quality
Preview
Use
Delete
```

Examples:

```text
My Vietnamese Voice   VieNeu
Global Clone          OmniVoice
```

Search remains shared.

---

# 57. Delete semantics

For OmniVoice custom voice delete:

```text
check active/queued jobs
    ↓
if in use:
    reject or defer
    ↓
delete prompt artifact
    ↓
delete reference audio if owned uniquely
    ↓
delete DB row
```

Do not delete shared reference files without ownership tracking.

Initial implementation should keep each custom profile's files unique.

---

# 58. Provider error taxonomy

Add stable error codes.

Runtime:

```text
OMNI_RUNTIME_NOT_INSTALLED
OMNI_RUNTIME_START_FAILED
OMNI_RUNTIME_HANDSHAKE_FAILED
OMNI_RUNTIME_CRASHED
OMNI_RUNTIME_TIMEOUT
OMNI_MODEL_NOT_INSTALLED
OMNI_MODEL_CORRUPT
OMNI_MODEL_LOAD_FAILED
```

Generation:

```text
OMNI_LANGUAGE_UNSUPPORTED
OMNI_INFERENCE_FAILED
OMNI_OUTPUT_INVALID
OMNI_DURATION_UNFIT
OMNI_PROMPT_INVALID
```

Clone:

```text
OMNI_CLONE_REFERENCE_INVALID
OMNI_CLONE_PROMPT_CREATE_FAILED
OMNI_CLONE_PROMPT_LOAD_FAILED
```

Do not return raw stack traces to UI.

---

# 59. Retry semantics

Retry only failures that may recover.

Retryable:

```text
worker crashed once
temporary IO failure
runtime startup race
```

Non-retryable:

```text
invalid language
invalid prompt
unsupported option
corrupt reference
duration impossible
model missing
```

Provider error mapping must integrate with current `retry_policy`.

---

# 60. Crash recovery

On app startup:

```text
detect orphan OmniVoice worker
cleanup known temp files
validate runtime manifest
do not auto-load model
recover interrupted TTS jobs using existing mechanism
```

Prompt artifacts:

```text
*.tmp
```

older than threshold may be swept.

Never delete final `.pt` files solely based on age.

---

# 61. Shutdown

On Melody API shutdown:

```text
stop accepting jobs
existing queue grace period
    ↓
send worker shutdown
    ↓
wait bounded time
    ↓
terminate
    ↓
kill only if necessary
```

No zombie child.

---

# 62. Security boundary

Worker accepts only commands from parent process stdin.

Do not expose:

```text
eval
arbitrary Python
arbitrary shell
arbitrary file read
```

Output paths must be validated under approved directories.

Reference paths must be validated under app-owned voice/temp directories.

---

# 63. License / attribution UX

Models page must show:

```text
OmniVoice
Code: Apache-2.0
Pretrained model: CC-BY-NC
Non-commercial use
Source: k2-fsa/OmniVoice
```

Before model download:

```text
[ ] I understand the pretrained model is licensed for non-commercial use.
```

This is product clarity, not a substitute for legal advice.

---

# 64. Consent UX

Voice cloning keeps existing consent.

```text
I confirm I have permission to use this voice sample.
```

Store consent metadata as currently done.

Provider does not change consent requirements.

---

# 65. Metrics/logging

Log structured events:

```text
provider_id
runtime
device
job_id
generation_mode
language
text_length
duration_target
duration_actual
latency_ms
model_load_ms
peak memory if measurable
```

Do not log:

```text
full user text by default
raw reference audio
voice prompt tensor
```

---

# 66. Performance metrics

Benchmark:

```text
cold runtime start
cold model load
warm first audio
generation wall time
RTF
RAM
VRAM
prompt creation time
prompt reuse time
SRT 100-cue throughput
```

Compare:

```text
VieNeu
OmniVoice CPU
OmniVoice MPS
OmniVoice CUDA
```

Do not claim "works smoothly on low-end PCs" without measurements.

---

# 67. Backend conflict audit

## Conflict A — dependency environment

Risk: **HIGH**

Mitigation:

```text
isolated optional runtime
```

## Conflict B — provider registry

Risk: **LOW**

Current architecture already uses stable provider IDs.

Add `omnivoice` without changing CapCut/VieNeu IDs.

## Conflict C — live provider instances

Risk: **LOW/MEDIUM**

Add one adapter to queue registry.

Do not instantiate model during queue manager construction.

## Conflict D — custom voice language hard-code

Risk: **HIGH functional bug**

Current custom voice resolver assumes `vi-VN`.

Must migrate to stored `language_code`.

## Conflict E — provider synthesize signature

Risk: **MEDIUM**

Use `SynthesisOptions`.

Update all provider implementations together.

Regression tests mandatory.

## Conflict F — generic worker chunking

Risk: **HIGH for SRT**

`target_duration` and generic chunking cannot be combined naively.

SRT cue mode bypasses generic text chunking.

## Conflict G — FFmpeg rate

Risk: **HIGH for SRT**

Native OmniVoice duration must disable post-rate `atempo`.

## Conflict H — GPU memory

Risk: **MEDIUM/HIGH**

Do not assume simultaneous loaded heavy GPU engines.

Start with one-heavy-model policy.

## Conflict I — installer size

Risk: **HIGH UX**

Do not bundle OmniVoice model/runtime in base installer.

Use Models installer.

## Conflict J — release portability

Risk: **HIGH**

Build/test optional runtime packs per supported OS/arch.

---

# 68. Execution phases

## PHASE O0 — Re-baseline and freeze contracts

**Priority:** BLOCKER  
**Goal:** confirm repository state and pin OmniVoice technical target.

Tasks:

- pull latest `main`;
- verify HEAD is at least `e1d2694`;
- run existing API/web/vieneu-core tests;
- inspect PR #17 status tracker;
- record current DB migration head;
- inspect Tauri/PyInstaller packaging;
- pin OmniVoice package version;
- resolve official model revision;
- generate dependency compatibility report;
- verify runtime target matrix.

Deliverables:

```text
OMNIVOICE_BASELINE_REPORT.md
OMNIVOICE_RUNTIME_MATRIX.md
```

Acceptance:

- no implementation begins on stale branch;
- exact package/model versions recorded;
- baseline regressions known.

---

## PHASE O1 — Provider-neutral capability contract

**Priority:** BLOCKER

Implement:

- add `OMNIVOICE = "omnivoice"`;
- extend capability type;
- preserve existing fields;
- register OmniVoice descriptor;
- descriptor must report unavailable without loading model;
- provider capability endpoints.

Tests:

- CapCut unchanged;
- VieNeu unchanged;
- OmniVoice absent;
- OmniVoice installed but broken;
- OmniVoice ready.

Acceptance:

```text
app starts normally without OmniVoice installed
```

---

## PHASE O2 — Optional OmniVoice runtime worker

**Priority:** BLOCKER

Create package/module:

```text
packages/omnivoice-runtime/
or
apps/omnivoice-worker/
```

Worker:

```text
JSONL IPC
ping
runtime_info
load_model
synthesize
create_voice_prompt
shutdown
```

Client:

```text
apps/api/app/services/omnivoice_runtime.py
```

Tests:

- handshake;
- malformed JSON;
- timeout;
- worker crash;
- restart;
- stderr isolation;
- graceful shutdown.

No UI yet.

Acceptance:

```text
API can launch a mock OmniVoice worker and survive crash/restart.
```

---

## PHASE O3 — Runtime installer + Model Manager

**Priority:** BLOCKER

Implement:

```text
Models API
runtime manifest
download state
checksum
atomic install
repair
uninstall
smoke
```

Do not download model on application startup.

Tests:

- no disk space;
- cancelled download;
- checksum mismatch;
- partial archive;
- reinstall;
- upgrade;
- uninstall while runtime active.

Acceptance:

```text
OmniVoice can be installed/uninstalled without changing VieNeu.
```

---

## PHASE O4 — OmniVoiceProvider basic TTS

**Priority:** HIGH

Implement `omnivoice_provider.py`.

Start with:

```text
text
language
speed
auto voice
```

No cloning yet.

Reuse existing queue.

Convert WAV → MP3.

Tests:

- standard generation;
- provider unavailable;
- language mapping;
- output invalid;
- cancellation;
- queue retry behavior.

Acceptance:

```text
POST /tts/jobs using OmniVoice completes through existing TTS queue.
```

Regression:

```text
CapCut tests pass
VieNeu tests pass
```

---

## PHASE O5 — Job options and multilingual

**Priority:** HIGH

Migration:

```text
language_code
voice_instruction
target_duration_seconds
normalize_text
generation_mode
```

Add:

```text
SynthesisOptions
LanguageRegistry
```

Update:

```text
API schema
tts_service
JobSnapshot
worker
providers
serializer
retry
```

Tests:

- persistence through retry;
- restart;
- unsupported language;
- old jobs;
- CapCut/VieNeu options compatibility.

Acceptance:

```text
OmniVoice multilingual job survives queue/retry without losing language/options.
```

---

## PHASE O6 — OmniVoice voice cloning

**Priority:** HIGH

Extend custom voice model:

```text
language_code
clone_artifact_path
clone_artifact_format
clone_artifact_version
```

Create provider-aware clone path.

OmniVoice:

```text
reference + transcript
    ↓
worker create_voice_prompt
    ↓
save .pt temp
    ↓
validate load
    ↓
atomic final
    ↓
status ready
```

Tests:

- missing transcript;
- invalid ref;
- worker crash during prompt creation;
- corrupt prompt;
- DB commit fail;
- prompt cleanup;
- restart + reuse.

Acceptance:

```text
create clone
restart app
generate using clone
```

---

## PHASE O7 — VoiceResolver + Voice Library multi-provider correctness

**Priority:** HIGH

Remove custom voice language hard-code.

Add DB-backed language.

Ensure shared resolver supports:

```text
VieNeu custom
OmniVoice custom
preset
```

Voice Library:

```text
provider badge
language
preview
use
delete
search
```

Tests:

- same display name on different providers if policy allows;
- provider missing;
- profile not ready;
- prompt missing;
- reference missing.

Acceptance:

```text
Voice Library can safely mix VieNeu and OmniVoice profiles.
```

---

## PHASE O8 — Voice Design / Expression

**Priority:** MEDIUM

Add:

```text
generation_mode=voice_design
voice_instruction
language
```

UI:

```text
style
emotion preset
instruction advanced
```

Backend validates provider capability.

Do not fake support on VieNeu.

Tests:

- OmniVoice design;
- invalid empty instruction if required;
- clone + compatible instruction;
- provider mismatch.

Acceptance:

```text
Voice Design works without contaminating Voice Clone persistence.
```

---

## PHASE O9 — SRT parser + project persistence

**Priority:** HIGH

Implement:

```text
srt_parser
dubbing projects
dubbing cues
```

API:

```text
POST /tts/dubbing/projects
POST /tts/dubbing/projects/{id}/srt
GET  /tts/dubbing/projects/{id}
```

No generation yet.

Tests:

- UTF-8;
- BOM;
- CRLF;
- overlap;
- malformed;
- cue-count limits;
- invalid timestamps.

Acceptance:

```text
SRT imports deterministically into persisted cue timeline.
```

---

## PHASE O10 — SRT cue synthesis with target duration

**Priority:** BLOCKER FOR DUBBING

Add:

```text
generation_mode=srt_cue
target_duration_seconds
```

Critical:

```text
no generic chunk split
no FFmpeg rate after native target-duration generation
```

Tests:

- 3.5s cue;
- duration overrides speed;
- retry retains duration;
- cue too long;
- provider without duration support;
- very short cue;
- cancellation.

Acceptance:

```text
individual cue generation respects target timing.
```

---

## PHASE O11 — Duration fit + final timeline renderer

**Priority:** HIGH

Implement:

```text
duration validation
micro-fit
timeline positioning
overlap mixing
final render
```

Outputs:

```text
WAV
MP3
M4A
```

Reuse existing FFmpeg.

Tests:

- silence gaps;
- overlaps;
- first cue not at 0;
- long timeline;
- failed cue;
- exact end duration;
- export formats.

Acceptance:

```text
SRT → final dubbing audio maintains subtitle timeline.
```

---

## PHASE O12 — Frontend integration

**Priority:** after O4/O6/O10 backend stable

Pages:

```text
Generate
Voice Lab
SRT Dubbing
Voice Library
Models
```

Models:

```text
VieNeu Installed
OmniVoice Install/Ready/Broken
```

Generate:

```text
Auto
VieNeu
OmniVoice
```

Voice Lab:

```text
clone provider
```

Dubbing:

```text
upload SRT
cue table
provider/voice
generate
preview
export
```

No low-level runtime controls in normal UX.

Acceptance:

- backend truth drives states;
- missing OmniVoice does not break existing UI;
- all errors actionable.

---

## PHASE O13 — Reliability hardening

**Priority:** RELEASE BLOCKER

Test:

```text
worker dies mid-generation
app closes
download interrupted
model corrupt
prompt corrupt
DB locked
disk full
delete voice while queued
uninstall OmniVoice with pending job
runtime repair
stale temp
```

Add:

```text
orphan sweeper
runtime health
model repair
bounded shutdown
```

Acceptance:

```text
no known path leaves database claiming ready when required artifact is absent.
```

---

## PHASE O14 — Performance / resource policy

**Priority:** RELEASE BLOCKER

Benchmarks:

```text
Windows x64 CPU
Windows NVIDIA CUDA
macOS arm64 MPS
optional macOS Intel CPU
```

Collect:

```text
install size
runtime size
model size
cold load
warm generation
RAM
VRAM
RTF
100-cue SRT
clone prompt build/reuse
```

Define Auto routing only after data exists.

Acceptance:

```text
routing policy documented from measurements, not assumptions.
```

---

## PHASE O15 — Packaging / GitHub Release

**Priority:** RELEASE BLOCKER

Base release:

```text
Void Melody app
VieNeu existing behavior
OmniVoice integration code
NO OmniVoice weights
```

Optional runtime asset:

```text
per platform
checksummed
versioned
```

Models page downloads official model.

Add:

```text
THIRD_PARTY_NOTICES.md
license display
runtime manifest
```

Smoke:

```text
fresh machine
install Void Melody
launch
VieNeu works
install OmniVoice
restart
OmniVoice works
clone
multilingual
SRT
export
```

---

# 69. Milestones

## M0 — Integration foundation

Requires `O0 + O1 + O2`.

Result:

```text
provider registered
isolated worker architecture works
no production model dependency in base API
```

## M1 — Optional OmniVoice TTS

Requires `O3 + O4 + O5`.

Result:

```text
install model
generate multilingual TTS
existing queue
existing export
```

## M2 — Multi-provider Voice Lab

Requires `O6 + O7 + O8`.

Result:

```text
VieNeu clone preserved
OmniVoice clone
VoiceClonePrompt reuse
Voice Design
Voice Library mixed providers
```

## M3 — SRT Dubbing

Requires `O9 + O10 + O11`.

Result:

```text
SRT import
timed cue generation
timeline render
export
```

## M4 — Public GitHub Release

Requires `O12 + O13 + O14 + O15`.

---

# 70. Branch strategy

Do not implement everything in one branch.

Suggested:

```text
feat/omnivoice-runtime-foundation
feat/omnivoice-provider
feat/omnivoice-voice-cloning
feat/omnivoice-expression
feat/srt-dubbing-core
feat/srt-dubbing-ui
chore/omnivoice-packaging
```

Keep PRs reviewable.

---

# 71. Suggested commit sequence

```text
feat(tts): add provider-neutral synthesis options
feat(omnivoice): add optional runtime protocol
feat(models): add omnivoice runtime installer
feat(omnivoice): add provider adapter
feat(tts): persist language and target-duration options
feat(voices): support omnivoice clone prompt artifacts
fix(voices): make custom voice language provider-aware
feat(expression): add omnivoice voice design controls
feat(dubbing): add srt project and cue parser
feat(dubbing): generate fixed-duration cue jobs
feat(dubbing): render subtitle-aligned audio timeline
feat(web): add provider-aware generate and models ui
feat(web): add srt dubbing workspace
test(omnivoice): add crash and packaged runtime coverage
chore(release): package optional omnivoice runtime
```

---

# 72. Files expected to change

Backend:

```text
apps/api/app/providers/base.py
apps/api/app/providers/registry.py
apps/api/app/providers/omnivoice_provider.py
apps/api/app/workers/queue_manager.py
apps/api/app/workers/tts_worker.py
apps/api/app/services/voice_resolver.py
apps/api/app/services/tts_service.py
apps/api/app/services/omnivoice_runtime.py
apps/api/app/services/model_installer.py
apps/api/app/services/language_registry.py
apps/api/app/models/tts_job.py
apps/api/app/models/custom_voice.py
apps/api/app/schemas/tts.py
apps/api/app/config.py
apps/api/app/api/v1/models.py
apps/api/app/api/v1/voices.py
apps/api/app/api/v1/tts_jobs.py
apps/api/app/api/v1/tts_batches.py
```

Dubbing:

```text
apps/api/app/services/dubbing/srt_parser.py
apps/api/app/services/dubbing/timeline.py
apps/api/app/services/dubbing/duration_fit.py
apps/api/app/services/dubbing/renderer.py
apps/api/app/models/dubbing_project.py
apps/api/app/models/dubbing_cue.py
apps/api/app/api/v1/dubbing.py
```

Runtime:

```text
apps/omnivoice-worker/
or
packages/omnivoice-runtime/
```

Frontend:

```text
apps/web/src/app/...
apps/web/src/components/...
apps/web/src/hooks/...
```

Migrations:

```text
apps/api/alembic/versions/...
```

---

# 73. Must-not-touch unnecessarily

Avoid broad refactors in:

```text
CapCutProvider internals
VieNeu ModelManager internals
existing queue priority semantics
existing retry machinery
existing audio storage
Tauri boot protocol
existing export APIs
```

Modify only the narrow contract needed.

---

# 74. Backend test matrix

Provider contracts:

```text
CapCut standard
VieNeu standard
VieNeu custom
OmniVoice standard
OmniVoice custom
OmniVoice design
```

Queue:

```text
provider lookup
retry
cancel
shutdown
restart
batch
```

Runtime:

```text
not installed
installed
broken
timeout
crash
repair
uninstall
```

Voice clone:

```text
create
artifact save
artifact load
restart
corruption
delete
```

Language:

```text
VI
EN
JA
KO
FR
invalid code
unsupported provider
```

SRT:

```text
parse
cue duration
fixed generation
overlap
gaps
render
export
```

---

# 75. Frontend test matrix

```text
OmniVoice not installed
installing
ready
broken
repair

Generate Auto
Generate VieNeu
Generate OmniVoice

Voice Lab VieNeu
Voice Lab OmniVoice

Voice Library mixed providers

SRT import
cue edit
generate
retry cue
preview
export
```

---

# 76. Packaged smoke matrix

Minimum:

```text
macOS arm64
Windows x64 CPU
Windows x64 NVIDIA
```

Test from clean install.

Flow:

```text
install
launch
VieNeu generation
open Models
install OmniVoice runtime
download model
runtime smoke
OmniVoice English
OmniVoice Japanese
clone reference
restart
reuse cloned voice
import SRT
generate cues
render
export
uninstall OmniVoice
confirm VieNeu still works
```

---

# 77. Release blockers

Do not label OmniVoice integration production-ready if any remain:

```text
runtime dependency conflict with base app
worker zombie process
model install not atomic
model corruption not detectable
custom voice language hard-coded
prompt artifact can be missing while DB says ready
SRT target duration goes through generic chunking
FFmpeg atempo modifies fixed-duration cue
OmniVoice absence breaks VieNeu
GPU OOM can crash API process
packaged runtime unverified
license attribution missing
```

---

# 78. Feature flags

Add:

```text
OMNIVOICE_ENABLED=true/false
SRT_DUBBING_ENABLED=true/false
```

Runtime absence remains distinct from feature flag.

Example:

```text
feature enabled + model absent
    → Install available

feature disabled
    → provider hidden/disabled
```

---

# 79. Rollback plan

Because OmniVoice is optional:

```text
OMNIVOICE_ENABLED=false
```

must restore:

```text
CapCut
VieNeu
Voice Lab VieNeu
batch
queue
exports
```

without DB rollback.

New nullable columns remain harmless.

SRT feature can also be disabled independently.

---

# 80. Recommended implementation order

Strict order:

```text
1. O0 baseline
2. O1 provider contract
3. O2 runtime IPC
4. O3 runtime/model installation
5. O4 standard OmniVoice provider
6. O5 job options + multilingual
7. O6 clone prompt persistence
8. O7 VoiceResolver/Library
9. O8 expression
10. O9 SRT persistence/parser
11. O10 fixed-duration cue generation
12. O11 renderer
13. O12 UI
14. O13 reliability
15. O14 benchmarks
16. O15 release
```

Do NOT start with SRT UI.

Do NOT start by adding OmniVoice directly to `apps/api/pyproject.toml`.

Do NOT start by changing VieNeu.

---

# 81. First implementation PR

Recommended first branch:

```text
feat/omnivoice-runtime-foundation
```

Scope ONLY:

```text
O0
O1
O2
```

Expected outcome:

```text
Provider descriptor exists
OmniVoice absent is safe
mock/runtime worker protocol exists
runtime client can handshake
runtime crash is recoverable
no real model yet
all existing tests pass
```

This PR gives a safe architectural foundation before downloading multi-GB models.

---

# 82. Second implementation PR

```text
feat/omnivoice-provider
```

Scope:

```text
O3
O4
O5
```

Outcome:

```text
install optional runtime
download model
standard multilingual TTS
existing queue/export
```

No voice cloning until this is stable.

---

# 83. Third implementation PR

```text
feat/omnivoice-voice-cloning
```

Scope:

```text
O6
O7
O8
```

Outcome:

```text
VoiceClonePrompt
multi-provider Voice Library
Voice Design
```

---

# 84. Fourth/Fifth PRs

```text
feat/srt-dubbing-core
feat/srt-dubbing-ui
```

Keep backend and UI reviewable separately.

---

# 85. Definition of Done — OmniVoice provider

```text
Void Melody starts without OmniVoice
    ↓
VieNeu still works
    ↓
Models → OmniVoice Install
    ↓
runtime installs
    ↓
model downloads
    ↓
smoke passes
    ↓
OmniVoice becomes Ready
    ↓
select Japanese
    ↓
generate
    ↓
existing queue
    ↓
existing output
    ↓
export
```

---

# 86. Definition of Done — OmniVoice clone

```text
Voice Lab
    ↓
select OmniVoice
    ↓
upload reference
    ↓
analyze
    ↓
transcript
    ↓
consent
    ↓
create
    ↓
VoiceClonePrompt saved
    ↓
DB ready
    ↓
preview
    ↓
restart app
    ↓
reuse profile
```

---

# 87. Definition of Done — SRT

```text
SRT Dubbing
    ↓
import .srt
    ↓
parse cues
    ↓
choose language
    ↓
choose voice
    ↓
generate
    ↓
one target duration per cue
    ↓
duration validation
    ↓
timeline mix
    ↓
preview
    ↓
export WAV / MP3 / M4A
```

---

# 88. Final architecture

```text
                         VOID MELODY
                              │
                         FastAPI API
                              │
                    Existing TTS Job Queue
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
       CapCut               VieNeu             OmniVoice
          │                   │                    │
 existing remote        local provider       local adapter
          │                   │                    │
          │              ModelManager               │
          │                   │                    ▼
          │               ONNX/Torch       Runtime Client
          │                                        │
          │                                  JSONL IPC
          │                                        │
          │                                        ▼
          │                               OmniVoice Worker
          │                                        │
          │                                  isolated env
          │                                        │
          └───────────────────┬────────────────────┘
                              │
                       Common Audio Layer
                              │
                            FFmpeg
                              │
                        Existing Storage
                              │
                  MP3 / WAV / M4A / Preview
```

Dubbing sits above providers:

```text
SRT
 ↓
DubbingProject
 ↓
DubbingCue
 ↓
VoiceResolver
 ↓
TTS Job
 ↓
provider
 ↓
duration validation
 ↓
timeline renderer
 ↓
export
```

---

# 89. Key engineering principle

The goal is not:

```text
"make OmniVoice run somehow"
```

The goal is:

```text
"make OmniVoice an optional, failure-isolated provider
that cannot destabilize VieNeu or the existing Void Melody release."
```

Backend correctness takes priority over UI completeness.

---

# 90. Agent execution instruction

For coding agents:

1. Read this document completely.
2. Pull current `main`.
3. Compare HEAD against baseline `e1d2694`.
4. If newer commits exist, re-audit affected files.
5. Never assume this document overrides newer proven architecture.
6. Work one phase at a time.
7. Run tests after each backend phase.
8. Update phase status in this file.
9. Do not mark DONE from code presence alone.
10. Stop release progression on any release blocker.

Status values:

```text
⬜ NOT_STARTED
🟦 PLANNED
🟨 IN_PROGRESS
🟧 IN_REVIEW
🟥 BLOCKED
🟩 DONE
⏸️ DEFERRED
```

Initial tracker:

| Phase | Status |
|---|---|
| O0 Re-baseline | 🟩 DONE |
| O1 Capability contract | 🟩 DONE |
| O2 Runtime IPC | 🟩 DONE |
| O3 Runtime installer | 🟦 PLANNED |
| O4 Basic provider | ⬜ NOT_STARTED |
| O5 Multilingual job options | ⬜ NOT_STARTED |
| O6 Voice cloning | ⬜ NOT_STARTED |
| O7 VoiceResolver / Library | ⬜ NOT_STARTED |
| O8 Voice Design | ⬜ NOT_STARTED |
| O9 SRT parser/persistence | ⬜ NOT_STARTED |
| O10 SRT fixed-duration | ⬜ NOT_STARTED |
| O11 Timeline renderer | ⬜ NOT_STARTED |
| O12 Frontend | ⬜ NOT_STARTED |
| O13 Reliability | ⬜ NOT_STARTED |
| O14 Performance | ⬜ NOT_STARTED |
| O15 Packaging/release | ⬜ NOT_STARTED |

---

# 91. Research notes used for this plan

OmniVoice current public capabilities include:

```text
massively multilingual TTS
zero-shot voice cloning
voice design
language parameter
reusable VoiceClonePrompt
fixed duration generation
speed control
text normalization option
```

Important implementation facts:

```text
OmniVoice package 0.2.1
torch/torchaudio required
transformers >= 5.3.0
upstream recommends fresh environment
model size ≈ 0.6B parameters
model repository ≈ 3.27 GB
main model safetensors ≈ 2.45 GB
pretrained model license = CC-BY-NC
code license = Apache-2.0
```

The exact pinned model revision must be resolved during O0.

---

# END
