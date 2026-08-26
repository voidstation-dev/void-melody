# Void Melody — Voice Design via OmniVoice Provider Plan

> **Goal:** add an ElevenLabs-style **Voice Design** workflow to Void Melody using **OmniVoice / G-OmniVoice as a separate provider**, without changing or coupling the existing VieNeu cloning/enrollment pipeline.
>
> **Core rule:** Voice Design must not be implemented inside the existing VieNeu Voice Lab stack. VieNeu and OmniVoice remain isolated providers with independent runtime, data, scheduling, artifacts, and lifecycle.

---

## 1. Product decision

Target user-facing flow:

```text
Create voice
├── Voice Design
│   └── OmniVoice / G-OmniVoice
│
├── Instant Voice Clone
│   └── VieNeu (existing flow)
│
├── Professional Voice Clone
│   └── Coming later
│
└── Voice Remixing
    └── Coming later
```

The UI should expose product capabilities, not model names.

Recommended UX labels:

```text
Voice Design
Create an entirely new voice from a description.

Instant Voice Clone
Clone a voice from a short recording.
```

Internally:

```text
Voice Design        → provider_id=omnivoice
Instant Voice Clone → provider_id=vieneu
```

---

## 2. Current Void Melody architecture

The repository already has useful OmniVoice foundations:

```text
apps/omnivoice-worker/
├── worker.py
├── backend.py
├── real_backend.py
├── mock_backend.py
└── errors.py
```

Core-side runtime IPC already exists:

```text
apps/api/app/services/omnivoice_runtime.py
```

The current OmniVoice runtime uses:

```text
FastAPI Core
    ↓
OmniVoiceRuntimeClient
    ↓
stdin/stdout JSONL IPC
    ↓
omnivoice-worker
    ↓
torch / transformers / omnivoice
```

This is the correct isolation boundary and should be preserved.

The provider registry already defines:

```text
capcut
vieneu
omnivoice
```

and OmniVoice capabilities already include:

```text
supports_voice_cloning = true
supports_voice_design = true
supports_multilingual = true
sample_rate = 24000
```

However, the current scheduler/runtime installation stack is not yet fully wired for OmniVoice.

---

## 3. Non-conflict rule with VieNeu

The following existing VieNeu components should be treated as protected boundaries:

```text
apps/api/app/services/clone_orchestrator.py
apps/api/app/services/vieneu_enrollment.py
apps/api/app/providers/vieneu_provider.py
apps/api/app/services/voice_reference_processor.py
apps/api/app/models/custom_voice.py
```

Do not add OmniVoice-specific branches to VieNeu clone orchestration.

Avoid patterns such as:

```python
if provider_id == "omnivoice":
    # OmniVoice design logic
```

inside:

```text
CloneOrchestrator
VieneuEnrollmentService
VieneuProvider
```

The existing VieNeu clone workflow remains:

```text
reference audio
    ↓
analysis / selection
    ↓
reference processing
    ↓
VieNeu enrollment
    ↓
speaker_emb + ref_codes
    ↓
calibration
    ↓
tts_custom_voices
```

The new OmniVoice workflow must be independent:

```text
design description
    ↓
OmniVoice generation
    ↓
candidate previews
    ↓
selected preview
    ↓
OmniVoice VoiceClonePrompt
    ↓
tts_omnivoice_voices
```

---

## 4. Why not reuse `tts_custom_voices`

The current `tts_custom_voices` schema is clearly optimized for VieNeu reference enrollment:

```text
reference_audio_path
transcript
consent_given
denoise_mode
denoise_applied
clone_mode
enrollment_artifact_path
speaker_similarity_score
calibration_quality_score
reference_fingerprint
```

A designed voice has no original user reference recording and should not pretend to be a VieNeu clone.

Therefore:

```text
DO NOT
tts_custom_voices
    + design_prompt
    + omnivoice_prompt_path
    + voice_kind
    + many nullable provider-specific fields
```

Instead create a provider-specific table.

---

# Phase A — OmniVoice Runtime Pack

## 5. Add OmniVoice as an optional runtime

The Runtime Manager currently knows about:

```text
vieneu
speech
```

Extend it to:

```text
vieneu
speech
omnivoice
```

Update:

```text
apps/api/app/services/runtime_manager/models.py
apps/api/app/services/runtime_manager/manifests.py
apps/api/app/services/runtime_manager/service.py
```

Target:

```python
KNOWN_RUNTIME_IDS = (
    "vieneu",
    "speech",
    "omnivoice",
)
```

Runtime storage:

```text
MELODY_DATA_DIR/
├── runtimes/
│   ├── vieneu/
│   ├── speech/
│   └── omnivoice/
│       └── <runtime-version>/
│
└── models/
    ├── vieneu/
    ├── whisper/
    └── omnivoice/
        └── g-omnivoice/
            └── <pinned-revision>/
```

---

## 6. Do not bundle OmniVoice into Melody Core

Default installer remains lean:

```text
Void Melody Core
├── Tauri app
├── melody-api-core
├── FFmpeg
└── lightweight resources
```

Do not embed:

```text
torch
transformers
omnivoice
G-OmniVoice model weights
CUDA
cuDNN
```

OmniVoice runtime should be an optional downloadable pack:

```text
melody-omnivoice-runtime-<version>-windows-x64.zip
melody-omnivoice-runtime-<version>-linux-x64.zip
melody-omnivoice-runtime-<version>-macos-arm64.zip
```

Runtime and model must remain separate.

---

## 7. OmniVoice runtime responsibilities

The worker owns:

```text
ML imports
torch
transformers
omnivoice
model loading
model unloading
inference
VoiceClonePrompt creation
hardware-specific runtime behavior
```

Core owns:

```text
DB
API
jobs
provider routing
runtime install state
model install state
preview sessions
voice metadata
voice library
UI orchestration
```

---

# Phase B — Dedicated OmniVoice Provider

## 8. Create `OmniVoiceProvider`

Add:

```text
apps/api/app/providers/omnivoice_provider.py
```

Concept:

```python
class OmniVoiceProvider:
    provider_id = "omnivoice"

    async def synthesize(...):
        voice = await resolve_omnivoice_voice(voice_type)

        return await runtime.synthesize(
            OmniSynthesisRequest(
                text=text,
                voice_prompt_path=voice.prompt_artifact_path,
                language=...,
                speed=rate,
            )
        )
```

Provider must call:

```text
OmniVoiceRuntimeClient
```

and never import:

```text
torch
omnivoice
transformers
```

inside the core API process.

---

## 9. Keep existing runtime IPC

Current architecture:

```text
OmniVoiceProvider
       ↓
OmniVoiceRuntimeClient
       ↓
JSONL
       ↓
omnivoice-worker
       ↓
RealOmniBackend
```

Keep it.

Do not replace it with:

```text
FastAPI core
↓
direct model import
```

and do not introduce a new local HTTP port unless there is a measured reason later.

---

# Phase C — Dedicated Scheduler Lane

## 10. Add OmniVoice execution policy

Current scheduling isolates providers.

Add:

```text
omnivoice_job_concurrency = 1
omnivoice_chunk_concurrency = 1
omnivoice_inference_timeout_seconds = 180
```

Update:

```text
apps/api/app/scheduler/policies.py
apps/api/app/workers/queue_manager.py
```

Target:

```text
TTS Scheduler
├── CapCut lane
├── VieNeu lane
└── OmniVoice lane
```

Initial OmniVoice defaults:

```text
job concurrency   = 1
chunk concurrency = 1
```

Do not use:

```text
vieneu_governor
vieneu_job_concurrency
vieneu_chunk_concurrency
```

for OmniVoice.

---

## 11. Provider routing invariant

A job must always preserve:

```text
tts_jobs.provider_id
```

Mapping:

```text
provider_id=capcut    → CapCut lane
provider_id=vieneu    → VieNeu lane
provider_id=omnivoice → OmniVoice lane
```

Retries and job recovery must preserve provider affinity.

Never silently fall back an OmniVoice job to CapCut or VieNeu.

---

# Phase D — OmniVoice Voice Data Model

## 12. Create a separate table

Add:

```text
tts_omnivoice_voices
```

Suggested model:

```text
OmniVoiceModel

id
display_name

provider_id
engine_id
voice_kind

status

design_prompt
compiled_instruction
design_attributes_json

preview_text
selected_preview_audio_path

prompt_artifact_path
prompt_format_version

model_id
model_revision
engine_version

sample_rate
voice_revision

created_at
updated_at
```

Recommended constants:

```text
provider_id = omnivoice
engine_id   = g-omnivoice
```

Voice kind:

```text
design
clone
remix
```

V1 only needs:

```text
design
```

but designing the enum now avoids a migration later.

---

## 13. Do not persist VieNeu fields

The OmniVoice table should not contain:

```text
speaker_emb
ref_codes
denoise_mode
denoise_applied
clone_mode=fidelity
vieneu enrollment version
VieNeu calibration fields
```

Provider-specific artifacts stay provider-specific.

---

## 14. Artifact layout

Recommended:

```text
MELODY_DATA_DIR/
└── voices/
    ├── vieneu/
    │   └── ...
    │
    └── omnivoice/
        └── <voice-id>/
            ├── source-preview.wav
            ├── voice-prompt.bin
            └── metadata.json
```

Do not store OmniVoice artifacts inside VieNeu voice profile directories.

---

# Phase E — Voice Design Orchestration

## 15. Critical product decision: freeze the designed voice

Do not implement designed voices as:

```text
save design prompt
    ↓
each future TTS call
    ↓
run instruct again
```

This may regenerate slightly different voice identity every time.

Instead:

```text
design description
      ↓
G-OmniVoice Voice Design
      ↓
generate candidates
      ↓
user selects candidate
      ↓
selected candidate audio
      +
exact preview transcript
      ↓
create_voice_clone_prompt()
      ↓
persistent VoiceClonePrompt
      ↓
saved reusable voice
```

This gives the user a stable acoustic identity.

---

## 16. Why the current worker supports this well

The current OmniVoice runtime already exposes:

```text
create_voice_prompt(
    audio_path,
    transcript,
    output_path
)
```

and the real backend already supports:

```text
model.create_voice_clone_prompt(
    ref_audio=...,
    ref_text=...
)
```

Therefore Voice Design can be a two-stage workflow:

```text
Stage 1 — Explore identity
instruct → preview voices

Stage 2 — Freeze identity
selected preview → VoiceClonePrompt
```

After saving, normal TTS should use the frozen prompt.

---

## 17. Create Voice Design services

Add:

```text
apps/api/app/services/voice_design/
├── __init__.py
├── models.py
├── prompt_builder.py
├── orchestrator.py
├── preview_store.py
└── cleanup.py
```

Responsibilities:

### `prompt_builder.py`

Convert UI attributes into a stable OmniVoice instruction.

Example input:

```json
{
  "gender": "female",
  "age": "young-adult",
  "accent": "southern-vietnamese",
  "pitch": "medium-low",
  "tone": "warm",
  "style": "storytelling",
  "emotion": "calm"
}
```

Compiled result:

```text
Young adult Vietnamese female speaker with a Southern Vietnamese accent,
medium-low pitch, warm and intimate tone, calm storytelling delivery,
clear articulation and natural pacing.
```

The compiled instruction is the backend source of truth.

---

### `preview_store.py`

Own temporary preview sessions:

```text
MELODY_DATA_DIR/
└── temp/
    └── voice-design/
        └── <session-id>/
            ├── candidate-a.wav
            ├── candidate-b.wav
            ├── candidate-c.wav
            └── session.json
```

Preview sessions should expire.

Suggested initial TTL:

```text
30–60 minutes
```

Cleanup on:

```text
commit
expiry
app maintenance
failed session
```

---

### `orchestrator.py`

Responsible for:

```text
validate request
check runtime
check model
compile instruction
generate candidates
persist temporary session
commit selected candidate
create VoiceClonePrompt
persist OmniVoiceModel
cleanup unused candidates
```

---

# Phase F — Voice Design API

## 18. API: generate preview candidates

Add:

```http
POST /api/v1/tts/voice-design/previews
```

Request:

```json
{
  "prompt": "A warm young Vietnamese female storyteller",
  "language": "vi",
  "previewText": "Xin chào, đây là giọng nói mẫu của tôi.",
  "count": 3,
  "attributes": {
    "gender": "female",
    "age": "young-adult",
    "accent": "southern-vietnamese",
    "pitch": "medium-low",
    "style": "storytelling",
    "tone": "warm"
  }
}
```

Rules:

```text
count: 1–3 initially
previewText: required or use stable app default
prompt: bounded length
runtime must be ready
model must be installed
```

Response:

```json
{
  "sessionId": "uuid",
  "compiledInstruction": "...",
  "candidates": [
    {
      "id": "a",
      "audioUrl": "/api/v1/tts/voice-design/sessions/.../candidates/a/audio"
    },
    {
      "id": "b",
      "audioUrl": "/api/v1/tts/voice-design/sessions/.../candidates/b/audio"
    },
    {
      "id": "c",
      "audioUrl": "/api/v1/tts/voice-design/sessions/.../candidates/c/audio"
    }
  ]
}
```

---

## 19. API: preview audio

Add:

```http
GET /api/v1/tts/voice-design/sessions/{session_id}/candidates/{candidate_id}/audio
```

Return:

```text
audio/wav
```

Do not return local filesystem paths.

---

## 20. API: commit selected voice

Add:

```http
POST /api/v1/tts/voice-design/sessions/{session_id}/commit
```

Request:

```json
{
  "candidateId": "b",
  "displayName": "Luna"
}
```

Backend:

```text
selected candidate
    ↓
selected WAV
    +
preview text
    ↓
OmniVoiceRuntime.create_voice_prompt()
    ↓
voice-prompt.bin
    ↓
tts_omnivoice_voices
    ↓
status=ready
```

Return:

```json
{
  "id": "...",
  "display_name": "Luna",
  "provider_id": "omnivoice",
  "engine_id": "g-omnivoice",
  "voice_kind": "design",
  "status": "ready",
  "preview_available": true
}
```

---

## 21. API: cancel / expire preview session

Optional explicit endpoint:

```http
DELETE /api/v1/tts/voice-design/sessions/{session_id}
```

Used when user closes the modal or starts over.

Server-side TTL cleanup remains mandatory.

---

# Phase G — OmniVoice Voice Resolver

## 22. Add dedicated resolver

Create:

```text
apps/api/app/services/omnivoice_voice_resolver.py
```

Example result:

```python
@dataclass(frozen=True)
class ResolvedOmniVoice:
    id: str
    display_name: str
    provider_id: str
    voice_kind: str
    prompt_artifact_path: str
    model_revision: str
    voice_revision: str
```

Do not reuse VieNeu's:

```text
PreparedVoice
speaker_emb
ref_codes
clone_mode
reference_audio_path
```

for OmniVoice.

---

# Phase H — Voice Library API and Types

## 23. Avoid bloating existing `CustomVoice`

Current frontend `CustomVoice` is VieNeu-specific.

Do not turn it into:

```ts
type CustomVoice = {
  // VieNeu fields
  transcript?: string
  denoise_mode?: string
  speaker_similarity_score?: number

  // OmniVoice fields
  design_prompt?: string
  prompt_artifact_path?: string

  // future provider fields...
}
```

Instead add a provider-specific type.

Example:

```ts
export type OmniVoice = {
  id: string
  display_name: string
  provider_id: "omnivoice"
  engine_id: string
  voice_kind: "design" | "clone" | "remix"
  status: string
  design_prompt?: string | null
  preview_available: boolean
  created_at: string
  updated_at?: string | null
}
```

Library union:

```ts
type LibraryCustomVoice =
  | {
      provider: "vieneu"
      kind: "clone"
      voice: CustomVoice
    }
  | {
      provider: "omnivoice"
      kind: "design" | "clone" | "remix"
      voice: OmniVoice
    }
```

---

## 24. Voice Library card behavior

Example:

```text
Luna

Designed Voice
OmniVoice

Female · Warm · Storytelling

▶ Preview

[ Use ] [...]
```

VieNeu remains:

```text
Phong Clone

Cloned Voice
VieNeu

Vietnamese · Fidelity

▶ Preview

[ Use ] [...]
```

Filtering continues to use:

```text
provider_id
kind
language
search
```

---

# Phase I — Create Voice Modal

## 25. Replace direct `/vieneu` New Voice link

Current Voice Library header sends:

```text
New Voice
→ /vieneu
```

Change to:

```text
New Voice
→ CreateVoiceDialog
```

Initial dialog:

```text
┌──────────────────────────────────────────┐
│ Create voice                         ×   │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ✦ Voice Design                       │ │
│ │ Design a new voice from a prompt.    │ │
│ │                       < 1 minute      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ⚡ Instant Voice Clone               │ │
│ │ Clone from a short recording.        │ │
│ │                       ~2 minutes      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ◌ Professional Voice Clone           │ │
│ │                         Coming soon   │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ✦ Voice Remixing                     │ │
│ │                         Coming soon   │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

Routing:

```text
Voice Design
→ VoiceDesignDialog / route

Instant Voice Clone
→ existing /vieneu Voice Lab
```

---

# Phase J — Voice Design UI

## 26. Step 1 — Describe voice

Suggested UI:

```text
Create a voice

Describe your voice

┌─────────────────────────────────────┐
│ A warm Vietnamese female voice,     │
│ around 25 years old, calm and       │
│ intimate storytelling tone...       │
└─────────────────────────────────────┘

Gender
[ Female ▼ ]

Age
[ Young Adult ▼ ]

Accent
[ Southern Vietnamese ▼ ]

Pitch
[ Medium-low ▼ ]

Style
[ Storytelling ▼ ]

Tone
[ Warm ▼ ]

                      [ Generate ]
```

Use shadcn/ui components.

The freeform description should be primary.

Structured controls should help users who do not know how to prompt.

---

## 27. Step 2 — Preview candidates

```text
Choose your favorite

Candidate A
▶ ━━━━━━━━━━━━━━━━━━━━━
Warm · Soft · Young

Candidate B                  ✓
▶ ━━━━━━━━━━━━━━━━━━━━━
Warm · Intimate · Natural

Candidate C
▶ ━━━━━━━━━━━━━━━━━━━━━
Deeper · Storytelling

[ Regenerate 3 voices ]
```

Allow:

```text
play
pause
seek
select
regenerate
```

Do not save a permanent voice yet.

---

## 28. Step 3 — Save voice

```text
Voice name
[ Luna                         ]

Selected voice

▶ ━━━━━━━━━━━━━━━━━━━━━

Created with Voice Design

                         [ Save voice ]
```

`Save voice` triggers the commit endpoint.

Only after commit does the selected preview become a persistent OmniVoice prompt artifact.

---

# Phase K — Audio Studio Integration

## 29. TTS job identity

For a designed voice:

```text
voice_type  = <omnivoice-voice-id>
provider_id = omnivoice
engine_id   = g-omnivoice
```

Flow:

```text
Audio Studio
     ↓
tts_jobs
provider_id=omnivoice
     ↓
OmniVoice scheduler lane
     ↓
OmniVoiceProvider
     ↓
OmniVoiceVoiceResolver
     ↓
voice-prompt.bin
     ↓
OmniVoiceRuntimeClient
     ↓
omnivoice-worker
     ↓
G-OmniVoice
```

VieNeu remains:

```text
Audio Studio
     ↓
provider_id=vieneu
     ↓
VieNeu lane
     ↓
VieneuProvider
     ↓
PreparedVoice
     ↓
speaker_emb + ref_codes
```

---

# Phase L — Generic TTS Worker Cleanup

## 30. Remove provider-specific media assumptions gradually

Current worker logic treats VieNeu specially for local WAV output.

Avoid accumulating:

```python
if is_vieneu:
    ...
elif is_omnivoice:
    ...
elif is_future_provider:
    ...
```

Move toward provider-result metadata:

```python
@dataclass(frozen=True)
class ProviderResult:
    raw_response: dict
    audio_urls: list[str]
    local_paths: list[str] | None = None
    mime_type: str | None = None
    sample_rate: int | None = None
```

Example:

```text
VieNeu
mime_type=audio/wav
sample_rate=48000

OmniVoice
mime_type=audio/wav
sample_rate=24000

CapCut
mime_type=audio/mpeg
```

The worker should handle media generically.

---

# Phase M — OmniVoice Model Lifecycle

## 31. Add model service

Create:

```text
apps/api/app/services/omnivoice_model_service.py
```

Responsibilities:

```text
is_installed
install
verify pinned revision
resolve model path
load
unload
warmup
disk usage
model status
```

Keep:

```text
runtime version
model revision
prompt format version
```

independent.

---

## 32. Pin model revision

Do not use mutable:

```text
main
latest
```

Persist:

```text
provider_id
model_id
model_revision
runtime_version
engine_version
prompt_format_version
```

Each saved voice should remember the model revision used to create its prompt.

This allows compatibility checks when OmniVoice is upgraded later.

---

# Phase N — Missing Runtime UX

## 33. Voice Design first-use flow

```text
User clicks Voice Design
        ↓
OmniVoice runtime ready?
    ┌───────┴────────┐
    │                │
   NO               YES
    │                │
    ▼                ▼
Install dialog      Editor
```

Install dialog:

```text
Voice Design requires the OmniVoice AI engine.

OmniVoice Runtime
Not installed

G-OmniVoice Model
Not installed

Installed separately from Void Melody.

[ Install ] [ Cancel ]
```

Do not download multi-GB assets silently.

---

## 34. Installation sequence

```text
download runtime
↓
verify SHA-256
↓
safe extract staging
↓
worker probe
↓
activate runtime
↓
download pinned model
↓
verify model snapshot
↓
load test
↓
ready
```

Failure must not affect VieNeu.

---

# Phase O — Error Model

## 35. Stable error codes

Suggested:

```text
OMNI_RUNTIME_NOT_INSTALLED
OMNI_RUNTIME_BROKEN
OMNI_RUNTIME_TIMEOUT
OMNI_RUNTIME_CRASHED

OMNI_MODEL_NOT_INSTALLED
OMNI_MODEL_LOAD_FAILED
OMNI_MODEL_NOT_LOADED

VOICE_DESIGN_INVALID_PROMPT
VOICE_DESIGN_PREVIEW_FAILED
VOICE_DESIGN_SESSION_NOT_FOUND
VOICE_DESIGN_SESSION_EXPIRED
VOICE_DESIGN_CANDIDATE_NOT_FOUND
VOICE_DESIGN_COMMIT_FAILED

OMNI_PROMPT_CREATE_FAILED
OMNI_PROMPT_INVALID
```

Frontend should branch on stable codes, not raw exception text.

---

# Phase P — Security and Filesystem

## 36. Filesystem constraints

All OmniVoice worker paths must remain under approved app-data roots.

Do not accept arbitrary paths from frontend.

Validate:

```text
model path
output path
voice prompt path
preview candidate path
```

Worker IPC passes filesystem paths, but core owns those paths.

---

## 37. Runtime ZIP safety

Keep the Runtime Manager protections:

```text
reject ../
reject absolute paths
reject path traversal
validate entrypoint
verify SHA-256
extract to staging
atomic activation
```

OmniVoice must follow the same mechanism as other optional runtime packs.

---

# Phase Q — Testing

## 38. Provider isolation tests

Mandatory:

```text
OmniVoice Voice Design
→ never calls CloneOrchestrator

OmniVoice Voice Design
→ never calls VieneuEnrollmentService

OmniVoice Audio Studio job
→ never calls VieneuProvider

VieNeu clone
→ never calls OmniVoiceRuntimeClient
```

---

## 39. Runtime isolation tests

```text
Core API starts without torch
Core API starts without omnivoice package
Core API starts without OmniVoice model

VieNeu remains available when OmniVoice is missing

Uninstall OmniVoice
→ VieNeu remains operational

OmniVoice worker crash
→ VieNeu worker unaffected

OmniVoice timeout
→ OmniVoice request fails cleanly
→ VieNeu jobs continue
```

---

## 40. Voice Design lifecycle tests

```text
prompt
→ candidates generated

candidate selection
→ commit succeeds

commit
→ VoiceClonePrompt created

app restart
→ saved voice still resolvable

saved voice
→ Audio Studio synthesis succeeds

expired session
→ commit rejected

delete saved OmniVoice
→ artifacts cleaned
```

---

## 41. Scheduler tests

```text
provider_id=omnivoice
→ omnivoice lane

provider_id=vieneu
→ vieneu lane

retry OmniVoice
→ stays omnivoice

recover interrupted OmniVoice job
→ stays omnivoice
```

---

## 42. VieNeu regression suite

All existing VieNeu behavior must stay intact:

```text
VieNeu V3 clone
VieNeu Enrollment v2
zero re-enrollment Audio Studio path
reference analysis
conditional denoise
calibration
speaker similarity
custom voice playback
batch synthesis
provider lane routing
```

Acceptance requirement:

```text
No existing VieNeu API contract changes are required
for Voice Design implementation.
```

---

# Phase R — Suggested File Changes

## 43. Existing files to extend

```text
apps/api/app/providers/registry.py

apps/api/app/providers/base.py

apps/api/app/scheduler/policies.py
apps/api/app/workers/queue_manager.py
apps/api/app/workers/tts_worker.py

apps/api/app/services/omnivoice_runtime.py

apps/api/app/services/runtime_manager/models.py
apps/api/app/services/runtime_manager/manifests.py
apps/api/app/services/runtime_manager/service.py

apps/omnivoice-worker/real_backend.py

apps/web/src/routes/voices.tsx
apps/web/src/components/voices/voice-library-header.tsx
apps/web/src/types/voice.ts
```

---

## 44. New backend files

```text
apps/api/app/providers/omnivoice_provider.py

apps/api/app/models/omnivoice_voice.py
apps/api/app/schemas/omnivoice_voice.py

apps/api/app/services/voice_design/
├── __init__.py
├── models.py
├── prompt_builder.py
├── orchestrator.py
├── preview_store.py
└── cleanup.py

apps/api/app/services/omnivoice_voice_resolver.py
apps/api/app/services/omnivoice_model_service.py

apps/api/app/api/v1/voice_design.py
```

Migration:

```text
apps/api/alembic/versions/
└── <revision>_add_omnivoice_voices.py
```

---

## 45. New frontend files

```text
apps/web/src/components/voices/create-voice-dialog.tsx

apps/web/src/components/voices/voice-design/
├── voice-design-dialog.tsx
├── voice-design-form.tsx
├── voice-design-preview-list.tsx
├── voice-design-candidate.tsx
├── voice-design-save-step.tsx
└── voice-design-runtime-gate.tsx

apps/web/src/api/voice-design.ts
apps/web/src/queries/voice-design.queries.ts
```

---

# Phase S — Implementation Order

## 46. Recommended order

### Phase 1 — Provider boundary

```text
confirm provider registry
add OmniVoice execution policy
add OmniVoice queue lane
```

Acceptance:

```text
A provider_id=omnivoice job is never dispatched through VieNeu.
```

---

### Phase 2 — Runtime installation

```text
add omnivoice runtime id
add runtime manifest support
add Runtime Manager support
wire worker entrypoint
wire runtime status
```

Acceptance:

```text
Core can report:
missing
installing
ready
broken
```

without importing OmniVoice ML packages.

---

### Phase 3 — Model lifecycle

```text
OmniVoiceModelService
pinned G-OmniVoice revision
install/verify/load/unload
```

Acceptance:

```text
runtime ready + model ready
→ Voice Design capability available
```

---

### Phase 4 — OmniVoiceProvider

```text
provider adapter
voice resolver
scheduler integration
generic local WAV handling
```

Acceptance:

```text
saved OmniVoice prompt
→ synthesize text
→ WAV output
```

---

### Phase 5 — OmniVoice DB model

```text
tts_omnivoice_voices
schema
migration
CRUD
resolver
artifact cleanup
```

Acceptance:

```text
provider-specific voice storage
with zero VieNeu schema changes
```

---

### Phase 6 — Voice Design preview backend

```text
prompt builder
preview session
candidate generation
temporary storage
preview audio API
```

Acceptance:

```text
prompt
→ 3 playable candidate voices
```

---

### Phase 7 — Freeze selected identity

```text
select candidate
→ create VoiceClonePrompt
→ save prompt artifact
→ persist OmniVoice voice
```

Acceptance:

```text
selected acoustic identity
survives app restart
```

---

### Phase 8 — Create Voice modal

```text
Voice Design
Instant Voice Clone
Professional Voice Clone — disabled
Voice Remixing — disabled
```

Acceptance:

```text
New Voice no longer routes directly to /vieneu.
```

---

### Phase 9 — Voice Design wizard

```text
Describe
→ Preview
→ Save
```

Acceptance:

```text
complete ElevenLabs-style design flow
```

---

### Phase 10 — Voice Library integration

```text
designed voice cards
preview
provider filtering
use in Audio Studio
delete
```

---

### Phase 11 — Audio Studio integration

```text
provider_id=omnivoice
voice_type=<voice id>
OmniVoice lane
OmniVoiceProvider
VoiceClonePrompt
```

---

### Phase 12 — Regression and hardening

```text
provider isolation tests
runtime isolation
filesystem safety
worker crash recovery
VieNeu regression
desktop installer test
```

---

# Phase T — V1 Scope

## 47. Ship in V1

```text
Create Voice modal
Voice Design
OmniVoice optional runtime
G-OmniVoice optional model
3 preview candidates
select candidate
freeze as VoiceClonePrompt
save designed voice
Voice Library integration
Audio Studio synthesis
runtime missing/install UX
provider isolation tests
```

---

## 48. Do not ship yet

```text
Professional Voice Clone
Voice Remixing
OmniVoice Instant Clone UI
multi-model OmniVoice selector
automatic GPU pack switching
advanced seed controls
voice breeding/interpolation
cloud sync
shared voice marketplace
```

Keep the architecture ready, but avoid expanding scope before Voice Design is stable.

---

# Phase U — Final Architecture

```text
                            Void Melody Core
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              Provider Layer              Runtime Manager
                    │                           │
       ┌────────────┼────────────┐              │
       │            │            │              │
       ▼            ▼            ▼              │
    CapCut       VieNeu      OmniVoice           │
       │            │            │              │
       │            │            └──────────────┼────────────┐
       │            │                           │            │
       │            ▼                           ▼            ▼
       │       VieNeu runtime              Omni runtime   G-OmniVoice
       │            │                           │          model
       │            │                           │
       │            ▼                           ▼
       │      VieNeu Provider            OmniVoice Worker
       │            │                           │
       │            ▼                           ▼
       │      speaker_emb/ref_codes        Voice Design
       │                                        │
       │                                        ▼
       │                                 candidate previews
       │                                        │
       │                                   user selects
       │                                        │
       │                                        ▼
       │                                VoiceClonePrompt
       │                                        │
       └──────────────────┬─────────────────────┘
                          ▼
                     Audio Studio
```

---

# Phase V — Architectural Invariants

## 49. Must remain true

```text
1. VieNeu clone orchestration never knows about Voice Design.

2. OmniVoice runtime dependencies never become core API dependencies.

3. OmniVoice has its own scheduler lane.

4. OmniVoice voices do not store VieNeu enrollment fields.

5. VieNeu voices do not store OmniVoice prompt artifacts.

6. A designed voice is frozen from the selected preview before being reused.

7. Runtime and model installation stay optional and separate.

8. Missing OmniVoice never breaks VieNeu.

9. Missing VieNeu never prevents OmniVoice Voice Design when OmniVoice is ready.

10. Provider identity is preserved across queue, retry and recovery.
```

---

# Acceptance Checklist

## Backend

- [ ] `omnivoice` registered as a first-class provider.
- [ ] Dedicated OmniVoice scheduler lane exists.
- [ ] Runtime Manager supports OmniVoice runtime packs.
- [ ] G-OmniVoice model lifecycle is separate from runtime lifecycle.
- [ ] Core API starts without OmniVoice ML dependencies.
- [ ] `OmniVoiceProvider` routes only through `OmniVoiceRuntimeClient`.
- [ ] `tts_omnivoice_voices` exists.
- [ ] Voice Design preview session API works.
- [ ] Up to three preview candidates can be generated.
- [ ] Candidate audio can be played through a safe API route.
- [ ] Selected candidate is materialized as `VoiceClonePrompt`.
- [ ] Saved OmniVoice voice survives restart.
- [ ] Audio Studio can synthesize using saved OmniVoice voice.
- [ ] Deleting OmniVoice voice cleans its artifacts.
- [ ] OmniVoice failures never mutate VieNeu profile state.

## Frontend

- [ ] `New Voice` opens a Create Voice modal.
- [ ] Modal includes Voice Design and Instant Voice Clone.
- [ ] Instant Voice Clone still opens the existing VieNeu Voice Lab.
- [ ] Voice Design has Describe → Preview → Save steps.
- [ ] Missing OmniVoice runtime has explicit install UX.
- [ ] User can audition and select preview candidates.
- [ ] Saved designed voices appear in Voice Library.
- [ ] Designed voices can be selected in Audio Studio.
- [ ] Provider filter recognizes OmniVoice.
- [ ] UI does not require users to understand provider/model internals.

## Regression

- [ ] VieNeu clone API unchanged.
- [ ] VieNeu Enrollment v2 unchanged.
- [ ] VieNeu zero re-enrollment path unchanged.
- [ ] VieNeu batch generation remains operational.
- [ ] VieNeu custom voice cards remain correct.
- [ ] CapCut behavior unchanged.
- [ ] Existing provider-routing tests remain green.
- [ ] New OmniVoice isolation tests pass.

---

# Final Recommendation

Implement Voice Design as:

```text
OmniVoice provider
+
optional OmniVoice runtime pack
+
separate OmniVoice voice storage
+
design preview workflow
+
selected-preview → VoiceClonePrompt freeze
```

Do **not** turn the existing VieNeu Voice Lab into a generic multi-provider orchestrator.

The clean separation should be:

```text
VieNeu
→ fast/local Vietnamese TTS
→ existing clone/enrollment workflow

OmniVoice
→ high-quality Voice Design
→ future high-quality clone/remix
→ isolated Torch/GPU runtime
```

This gives Void Melody an ElevenLabs-style voice creation experience while preserving the stability of the existing VieNeu implementation.
