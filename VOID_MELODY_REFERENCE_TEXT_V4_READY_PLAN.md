# Void Melody — Reference Text / VieNeu V4-Ready Voice Clone Plan

> **Scope:** bổ sung `reference transcript` vào Voice Lab của Void Melody theo hướng **engine-aware** và **V4-ready**, nhưng **không thay đổi hành vi Enrollment v2 của VieNeu V3 Turbo hiện tại**.
>
> Current `main` audited for this plan:
>
> ```text
> 68ee67efbff318b5f0c3b1c665f65fe54d2dc563
> ```
>
> Current Void Melody already stores `transcript` in `tts_custom_voices`, and the clone API already accepts a `transcript` form field. The main missing piece is the frontend and a capability-aware contract that decides whether reference text is ignored, optional, or required per engine.

---

# 1. Executive Summary

Current Void Melody Voice Lab:

```text
upload audio
→ analyze
→ select best 3–8s
→ optional denoise
→ VieNeu V3 prepare_reference()
→ speaker_emb + ref_codes
→ calibration
→ profile ready
```

Current frontend sends:

```text
transcript = ""
```

even though backend already accepts and stores the field.

Target:

```text
upload audio
→ analyze
→ select best reference segment
→ user enters exact words spoken in selected segment
→ validate/reference-text UX
→ save transcript with profile

V3 Turbo:
→ transcript stored as metadata
→ DO NOT feed transcript into prepare_reference()

Future transcript-conditioned engine / V4:
→ transcript can become required
→ provider consumes exact reference text
```

This design gives Void Melody a correct UX today and avoids pretending that reference text changes V3 Turbo quality when the current V3 clone pipeline does not use it.

---

# 2. Goals

Implement:

```text
1. Add a visible "Reference Transcript" field to Voice Lab.
2. Ensure the text corresponds to the currently selected audio segment.
3. Persist transcript in the existing DB field.
4. Pass transcript through the existing clone API.
5. Add engine capability metadata:
   ignored / optional / required.
6. Keep V3 Turbo Enrollment v2 behavior unchanged.
7. Prepare API/UI contracts for a future transcript-conditioned VieNeu engine.
8. Avoid a DB migration unless current schema inspection proves one is required.
9. Preserve all existing custom voices.
10. Preserve Audio Studio generation behavior.
```

---

# 3. Non-Goals

Do NOT implement as part of this plan:

```text
VieNeu V4 runtime/model integration
new voice-clone engine
ASR dependency
cloud transcription
OpenAI/Whisper API
automatic translation
forced alignment
speaker diarization
multi-speaker references
changes to V3 sampling
changes to V3 Enrollment v2 tensor generation
```

Automatic local transcription can be a separate future plan.

---

# 4. Current Void Melody Audit

## 4.1 Database already has transcript

Current model:

```text
tts_custom_voices.transcript
```

is already persisted.

Therefore initial implementation should not introduce a new transcript column.

## 4.2 Clone API already accepts transcript

Current endpoint:

```text
POST /api/v1/tts/voices/clone
```

already accepts:

```python
transcript: str = Form(default="")
```

So the API surface is already mostly ready.

## 4.3 Frontend currently discards this capability

Current frontend clone request effectively does:

```ts
form.append("transcript", "")
```

Target:

```ts
form.append("transcript", referenceTranscript.trim())
```

## 4.4 Current V3 Enrollment v2 must stay unchanged

Current V3 enrollment is:

```text
reference audio
→ prepare_reference(...)
→ speaker_emb
→ ref_codes
```

Reference text must not be injected into this pipeline unless the installed VieNeu V3 API actually begins consuming it in a future version.

For current V3:

```text
transcript = metadata / future compatibility
```

not:

```text
transcript = model conditioning
```

---

# 5. Reference Text Capability Model

Introduce an engine capability contract.

Recommended enum:

```ts
type ReferenceTextPolicy =
  | "ignored"
  | "optional"
  | "required"
```

Semantics:

```text
ignored
→ engine does not consume reference text
→ UI may hide field

optional
→ profile can store it
→ engine may not consume it today
→ useful for future migration

required
→ profile cannot be enrolled without valid reference text
```

For current VieNeu V3 Turbo:

```text
referenceTextPolicy = optional
```

This is intentionally a product-level compatibility choice.

The current V3 inference/enrollment implementation does not use the transcript for its audio-conditioning path.

---

# 6. Capability Response

Extend:

```text
GET /api/v1/tts/voices/capabilities
```

with fields such as:

```json
{
  "provider_id": "vieneu",
  "engine_id": "v3turbo",
  "reference_text_policy": "optional",
  "reference_text_used_for_enrollment": false,
  "reference_min_seconds": 3,
  "reference_max_seconds": 8
}
```

Recommended backend schema:

```python
reference_text_policy: Literal["ignored", "optional", "required"] = "optional"
reference_text_used_for_enrollment: bool = False
reference_min_seconds: float = 3.0
reference_max_seconds: float = 8.0
```

Do not hardcode these values in multiple frontend components.

Frontend should read runtime capability truth.

---

# 7. Engine-Specific Reference Duration

Current V3 behavior:

```text
3–8 seconds
```

Keep it unchanged.

Do not globally change Voice Lab to a 10-second sample just because a future/newer engine recommends a different duration.

Target architecture:

```text
V3 Turbo
→ min 3s
→ max 8s

future engine
→ capability-driven min/max
```

All segment sliders and validation should eventually read:

```text
reference_min_seconds
reference_max_seconds
```

from capability metadata.

---

# 8. Voice Lab UI

Add the field in Step 2, near the selected reference segment.

Recommended layout:

```text
2. Phân tích & Tối ưu mẫu

[ waveform ]

Đoạn tham chiếu
1.2s ━━━━━━━━━━━━━━━━━ 7.2s

[ Nghe đoạn ]
[ Dùng đoạn tốt nhất ]

Lời thoại trong đoạn tham chiếu
┌──────────────────────────────────────────────┐
│ Hôm nay tôi muốn kể cho bạn nghe một câu... │
└──────────────────────────────────────────────┘

Nhập chính xác những gì được nói trong đoạn 1.2–7.2s.
```

---

# 9. V3-Specific UX Copy

For V3:

```text
Lời thoại mẫu
Tùy chọn
```

Helper text:

```text
VieNeu V3 Turbo tạo hồ sơ giọng trực tiếp từ âm thanh.
Lời thoại này được lưu cùng hồ sơ để giúp quản lý và
tương thích với các engine nâng cao trong tương lai.
```

Avoid copy that claims:

```text
"Nhập transcript sẽ tăng độ giống giọng trên V3"
```

because that is not true for the current V3 enrollment path.

---

# 10. Future Required-Transcript UX

If capability returns:

```text
reference_text_policy = required
```

UI becomes:

```text
Lời thoại trong mẫu *
Bắt buộc
```

Create button disabled when:

```text
transcript.trim() == ""
```

Validation message:

```text
Nhập chính xác lời thoại trong đoạn tham chiếu đã chọn.
```

For `optional`:

```text
empty transcript
→ allowed
```

For `ignored`:

```text
field can be hidden
```

or displayed only under advanced metadata.

---

# 11. Selected Segment Consistency

Reference text must correspond to the currently selected segment.

If user changes:

```text
selected_start_seconds
selected_end_seconds
```

after typing transcript, show a non-blocking notice:

```text
Bạn đã thay đổi đoạn tham chiếu.
Hãy kiểm tra lại lời thoại để đảm bảo nội dung khớp đoạn mới.
```

Recommended state:

```ts
const [referenceTranscript, setReferenceTranscript] = useState("")
const [transcriptSegmentKey, setTranscriptSegmentKey] = useState<string | null>(null)
```

When transcript editing begins:

```text
segmentKey = `${start.toFixed(2)}:${end.toFixed(2)}`
```

If selection changes:

```text
currentSegmentKey !== transcriptSegmentKey
→ transcriptNeedsReview = true
```

Do not automatically clear the transcript.

---

# 12. Transcript Quality Guidance

Simple local UX rules only.

Warn if transcript:

```text
very short compared with sample
obviously empty
contains only punctuation
```

Do not try to estimate exact WER without ASR.

Recommended warnings:

```text
"Đoạn mẫu có vẻ dài nhưng lời thoại rất ngắn."
"Kiểm tra lại transcript nếu đoạn âm thanh vừa được thay đổi."
```

Warnings should not block V3 optional flow.

---

# 13. Backend Clone Request

Current request fields should become:

```text
audio_file
transcript
display_name
consent_given
selected_start_seconds
selected_end_seconds
denoise_mode
clone_mode
```

No new endpoint required.

Frontend:

```ts
cloneVoiceProfile({
  file,
  displayName,
  transcript: referenceTranscript,
  ...
})
```

---

# 14. Frontend API Contract

Update:

```text
apps/web/src/lib/voice-lab-api.ts
```

From:

```ts
form.append("transcript", "")
```

To:

```ts
form.append("transcript", transcript.trim())
```

Function type:

```ts
{
  file: File
  displayName: string
  transcript?: string
  consentGiven: boolean
  ...
}
```

Default:

```ts
transcript = ""
```

for compatibility.

---

# 15. Clone Orchestrator

Current `CloneOrchestrator.create()` already receives:

```text
transcript
```

Keep:

```python
transcript=transcript.strip() or "[reference audio]"
```

if compatibility requires it.

Preferred future cleanup:

```text
DB transcript may be empty
```

but only change this if existing code/tests do not depend on the placeholder.

For this first implementation, avoid unnecessary semantic migration.

---

# 16. Enrollment Metadata

Current `enrollment.json` / artifact metadata may optionally include a transcript hash.

Do not store the full transcript redundantly in NPZ.

Optional metadata:

```json
{
  "referenceTranscriptPresent": true,
  "referenceTranscriptSha256": "..."
}
```

This is useful later for:

```text
artifact provenance
migration
future engine re-enrollment
```

But this is not required for MVP because the DB already stores transcript.

---

# 17. Reference Fingerprint

Current V3 enrollment fingerprint should NOT suddenly include transcript if the transcript is not used by V3 synthesis/enrollment.

Why:

```text
same audio
+ changed metadata transcript
```

should not invalidate V3 speaker_emb/ref_codes.

For current V3:

```text
reference fingerprint
→ audio + preprocessing
```

not transcript.

For a future transcript-conditioned engine:

```text
fingerprint
→ audio
+ transcript
+ preprocessing
+ engine version
```

Make fingerprint strategy engine-specific.

---

# 18. Voice Resolver

Current resolver already exposes:

```text
prompt_text = custom.transcript
```

Keep this.

However, rename or document semantics carefully.

For V3:

```text
prompt_text
→ stored metadata / legacy compatibility
```

not model-conditioning in Enrollment v2 generation.

Future provider can consume it if required.

---

# 19. Provider Contract

Recommended provider capability interface:

```python
@dataclass(frozen=True)
class VoiceCloneCapabilities:
    reference_text_policy: str
    reference_text_used_for_enrollment: bool
    reference_min_seconds: float
    reference_max_seconds: float
```

Future:

```text
V3TurboCloneProvider
→ optional
→ used_for_enrollment = false

Future transcript-conditioned provider
→ required
→ used_for_enrollment = true
```

---

# 20. Do Not Inject Transcript Into V3

Explicit regression guard:

```text
VieneuEnrollmentService.enroll()
```

must continue to call:

```python
engine.prepare_reference(
    reference_audio,
    denoise=False,
    use_ref_codes=True,
)
```

without pretending to pass transcript conditioning.

If a future installed VieNeu package introduces an official text-conditioned V3 API, treat that as a separate compatibility review.

---

# 21. Existing Voice Compatibility

Existing custom voices may contain:

```text
transcript = ""
```

or:

```text
"[reference audio]"
```

They must remain valid.

Do not:

```text
force transcript migration
mark old voices invalid
re-enroll automatically
```

Future V4 upgrade may offer:

```text
Add reference transcript
→ Upgrade profile
```

as an explicit action.

---

# 22. Voice Library

Optional display:

```text
Reference transcript
Available / Missing
```

Do not show long transcript in the main card.

Profile details may show:

```text
Lời thoại mẫu
"Hôm nay tôi..."
```

with edit support only if re-enrollment semantics are defined.

For current V3, editing transcript metadata should not trigger re-enrollment.

---

# 23. Editing Transcript

If profile is V3 and transcript is only metadata:

```text
edit transcript
→ DB metadata update only
```

Do not recompute:

```text
speaker_emb
ref_codes
calibration
```

If a future engine uses transcript for conditioning:

```text
edit transcript
→ profile becomes stale
→ explicit re-enrollment required
```

Capability model should support that distinction.

---

# 24. Local Privacy

Transcript should remain local together with the voice profile.

Requirements:

```text
do not upload transcript
do not send transcript to external providers
do not add telemetry containing transcript
do not log full transcript
```

Structured logs may safely record:

```text
reference_transcript_present=true
reference_transcript_chars=42
```

not the content.

---

# 25. Optional Future Local ASR

Out of scope now, but architecture should allow:

```text
[ Tự nhận diện lời thoại ]
```

Future flow:

```text
selected audio segment
→ local ASR
→ draft transcript
→ user reviews/corrects
```

Important:

```text
user must be able to edit ASR output
```

because a transcript-conditioned clone should use the exact spoken text.

Do not make future ASR automatic and invisible.

---

# 26. File-by-File Implementation Map

## Backend

Modify:

```text
apps/api/app/schemas/custom_voice.py
apps/api/app/api/v1/voices.py
apps/api/app/services/clone_orchestrator.py
apps/api/app/services/voice_resolver.py
```

Potential shared capability files:

```text
packages/vieneu-core/src/vieneu_core/capabilities.py
```

or whichever capability module exists in latest main.

Avoid changing:

```text
apps/api/app/services/vieneu_enrollment.py
```

except comments/type wiring.

## Frontend

Modify:

```text
apps/web/src/components/vieneu/vieneu-page.tsx
apps/web/src/lib/voice-lab-api.ts
apps/web/src/hooks/use-voice-lab.ts
apps/web/src/types/voice.ts
```

or the current equivalent type location.

Locales:

```text
apps/web/src/locales/vi.ts
apps/web/src/locales/en.ts
apps/web/src/locales/types.ts
```

---

# 27. Recommended Frontend Component

If Voice Lab is being modularized, create:

```text
reference-transcript-field.tsx
```

Props:

```ts
type ReferenceTranscriptFieldProps = {
  value: string
  onChange: (value: string) => void

  policy: "ignored" | "optional" | "required"

  segmentStart: number
  segmentEnd: number

  needsReview?: boolean
  disabled?: boolean
}
```

Use shadcn primitives where available:

```text
Textarea
Label
Badge
Alert
Tooltip
```

---

# 28. API Validation

Backend validation:

```text
policy == required
+ transcript empty
→ 422 REFERENCE_TEXT_REQUIRED
```

For current V3:

```text
policy == optional
+ transcript empty
→ accepted
```

Normalize:

```python
transcript = transcript.strip()
```

Set a reasonable max length.

Suggested:

```text
2,000 characters
```

for a 3–10 second sample this is already extremely generous.

Reject pathological payloads.

---

# 29. Error Codes

Add stable codes:

```text
REFERENCE_TEXT_REQUIRED
REFERENCE_TEXT_TOO_LONG
REFERENCE_TEXT_NEEDS_REVIEW
```

`NEEDS_REVIEW` should generally be frontend warning, not backend hard error.

---

# 30. Capability-Driven UI

Avoid:

```ts
if (engineId === "v3turbo") ...
```

everywhere.

Prefer:

```ts
const policy = capabilities.reference_text_policy
```

Then:

```text
ignored
→ hide/advanced

optional
→ show optional

required
→ show required
```

This is the core V4-ready design.

---

# 31. Future Engine Upgrade Path

When a transcript-conditioned engine becomes available:

```text
Custom Voice Profile
V3
├── reference.wav
├── transcript
├── enrollment-v2.npz
└── calibration.wav
```

can be upgraded:

```text
reference.wav
+
transcript
↓
new engine enrollment
↓
new artifact
```

without asking the user to re-upload audio if the original reference still exists.

---

# 32. Future Engine-Specific Profile Metadata

Add later if needed:

```text
reference_text_policy
reference_text_hash
reference_text_verified_at
source_engine_id
```

Do not add these DB columns now unless actual V4 integration requires them.

Keep current change minimal.

---

# 33. UI Example — Current V3

```text
Lời thoại trong đoạn tham chiếu
[Tùy chọn]

┌────────────────────────────────────────────┐
│ Tôi xin chào mọi người, hôm nay chúng ta...│
└────────────────────────────────────────────┘

Nhập chính xác nội dung được nói trong đoạn 1.3–7.1s.

VieNeu V3 Turbo tạo hồ sơ giọng trực tiếp từ âm thanh.
Lời thoại được lưu cùng hồ sơ để hỗ trợ quản lý và
tương thích với engine nâng cao.
```

---

# 34. UI Example — Future Required Engine

```text
Lời thoại trong đoạn tham chiếu
[Bắt buộc]

┌────────────────────────────────────────────┐
│ Tôi xin chào mọi người, hôm nay chúng ta...│
└────────────────────────────────────────────┘

Engine này sử dụng cả âm thanh và lời thoại để tạo hồ sơ giọng.
Transcript phải khớp chính xác đoạn 1.3–9.8s.
```

---

# 35. Validation

## V3 regression

Must PASS:

```text
clone with transcript
clone without transcript
speaker artifact created
calibration created
same Enrollment v2 code path
same denoise behavior
same clone_mode behavior
preview works
Audio Studio works
```

Critical:

```text
adding transcript must NOT change V3 prepare_reference arguments
```

## UI

Must PASS:

```text
field visible for optional policy
required badge for required policy
selected segment appears in helper text
segment change triggers review warning
transcript persists to backend
existing profile without transcript still displays
```

## API

Must PASS:

```text
optional empty transcript
optional non-empty transcript
required empty transcript → 422
max length validation
no filesystem paths in response
```

---

# 36. Tests

Do not build a giant test suite.

Add targeted tests for:

```text
capability policy
frontend FormData transcript
required validation
V3 transcript does not alter enrollment call
existing profile compatibility
segment-change review state if practical
```

Run existing backend/web tests.

Run:

```text
web build
API startup
manual Voice Lab flow
Tauri smoke if available
```

---

# 37. Commit Sequence

```text
feat(voice-lab): expose reference text capability
```

```text
feat(voice-lab): add reference transcript input
```

```text
feat(voice-lab): persist sample transcript
```

```text
feat(voice-lab): add segment transcript review warning
```

```text
refactor(voice-lab): use capability-driven reference text policy
```

```text
test(voice-lab): protect v3 enrollment behavior
```

---

# 38. Definition of Done

```text
✓ Voice Lab has a reference transcript field.
✓ Transcript is tied visually to selected audio segment.
✓ Transcript is sent to the existing clone endpoint.
✓ Transcript is stored in the existing profile.
✓ Current V3 accepts empty transcript.
✓ Current V3 enrollment behavior is unchanged.
✓ Current V3 does not falsely consume transcript.
✓ Capability response declares reference text policy.
✓ UI uses capability instead of hardcoding engine behavior.
✓ Existing custom voices remain valid.
✓ Future required-transcript engines can reuse the same UI/API contract.
✓ Voice data and transcript remain local.
```

---

# 39. Coding Agent Prompt

```text
Read `VOID_MELODY_REFERENCE_TEXT_V4_READY_PLAN.md` completely before changing code.

Work against the latest `main`.

PRIMARY OBJECTIVE

Add reference transcript support to Void Melody Voice Lab in an engine-aware way.

Current V3 Turbo behavior MUST remain unchanged.

The transcript should be captured and persisted today so the profile is ready for future transcript-conditioned clone engines.

AUDIT FIRST

Inspect:
- apps/api/app/models/custom_voice.py
- apps/api/app/schemas/custom_voice.py
- apps/api/app/api/v1/voices.py
- apps/api/app/services/clone_orchestrator.py
- apps/api/app/services/vieneu_enrollment.py
- apps/api/app/services/voice_resolver.py
- current capabilities code
- apps/web/src/components/vieneu/vieneu-page.tsx
- apps/web/src/lib/voice-lab-api.ts
- apps/web/src/hooks/use-voice-lab.ts
- voice frontend types
- locale files

CONFIRM CURRENT FACTS

Before implementation verify:
- DB already has transcript
- clone endpoint accepts transcript
- frontend currently sends empty transcript
- V3 enrollment uses prepare_reference(audio)
- V3 enrollment does not consume reference text

IMPLEMENT

1. Add reference text capability:
   ignored / optional / required.

2. Current V3 Turbo:
   reference_text_policy = optional
   reference_text_used_for_enrollment = false

3. Add capability-driven min/max reference duration if cleanly possible:
   current V3 = 3–8s.

4. Add Voice Lab reference transcript UI near the selected reference segment.

5. Explain clearly for V3:
   transcript is optional and stored with the profile;
   it is not used by current V3 enrollment.

6. Pass actual transcript through voice-lab-api instead of always sending "".

7. Persist through existing clone endpoint/model.

8. If selected audio segment changes after transcript entry:
   keep the text but mark it as needing user review.

9. Add backend required validation only for engines whose policy is required.

10. Do NOT add a new transcript DB column if the existing one is sufficient.

V3 HARD REGRESSION RULE

Do not alter the V3 enrollment call to pretend it uses transcript.

Current behavior must stay equivalent to:

prepare_reference(
    reference_audio,
    denoise=False,
    use_ref_codes=True
)

The transcript must NOT be added to the V3 reference fingerprint unless the V3 engine actually conditions on it.

DO NOT

- implement VieNeu V4 runtime
- add Whisper/ASR
- add cloud transcription
- change V3 reference analysis
- change best-segment scoring
- change denoise policy
- change speaker embedding generation
- change calibration
- change speaker similarity
- change Audio Studio speed runtime
- force old profiles to add transcript
- auto re-enroll existing voices

PRIVACY

Transcript must remain local.
Do not log full transcript text.
Do not send it to remote telemetry.

VALIDATION

Verify:
- V3 clone with transcript
- V3 clone without transcript
- same enrollment path
- calibration still works
- Audio Studio works
- transcript persists
- existing profiles with empty transcript work
- optional/required capability UI
- segment-change review warning

FINAL REPORT

Return:

## Base commit

## Files changed

## Capability changes

## Voice Lab UI

## API changes

## Transcript persistence

## Segment consistency behavior

## V3 enrollment regression

Explicitly answer:
Did V3 prepare_reference behavior change?

Expected:
NO.

## Existing profile compatibility

## Validation PASS / FAIL / NOT RUN

## Future V4-ready pieces

Do not implement V4 itself in this task.
```
