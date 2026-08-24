# Void Melody — VieNeu Enrollment v2 Implementation Plan

> **Approved scope:** nâng cấp Voice Lab/custom voice để tận dụng đúng cơ chế enrollment của VieNeu-TTS v3 Turbo trước khi nghiên cứu multi-engine clone.

## 1. Mục tiêu

Current flow của Void Melody:

```text
upload → analyze → chọn 3–8s → lưu reference_audio_path
→ mỗi lần synthesize lại dùng ref_audio
→ VieNeu lại denoise / speaker encode / ref-code encode
```

Target Enrollment v2:

```text
upload
→ analyze
→ auto-select best 5–8s
→ conditional denoise
→ prepare_reference ONCE
→ persist speaker_emb + ref_codes
→ calibration
→ validation
→ READY
→ mọi TTS sau đó reuse enrollment artifact
```

Goals:

```text
- tăng speaker similarity
- tăng consistency
- giảm thời gian repeated synthesis
- không re-enroll per chunk/job
- reference selection tốt hơn
- conditional denoise
- persist artifact qua restart
- Fidelity / Stability thật theo VieNeu
- calibration preview
- backward compatible với voice v1
```

Không làm trong scope này:

```text
Gwen-TTS
F5-TTS
Viterbox
Fish Speech
CosyVoice
cloud cloning
multi-engine selector
```

---

# 2. Audit hiện tại

## Custom voice DB

`tts_custom_voices` hiện đã lưu:

```text
id
display_name
reference_audio_path
transcript
provider_id
engine_id
status
duration
source/reference duration
selected start/end
quality score
analysis warnings
```

Nhưng chưa có:

```text
enrollment artifact
speaker embedding
reference codes
profile format version
engine version
reference fingerprint
denoise policy
clone mode
calibration result
similarity result
```

## `clone_orchestrator.py`

Hiện profile creation gọi runtime preflight thật, sau đó gọi `create_reference_profile()`.

Nhưng `create_reference_profile()` chỉ tạo profile kiểu:

```text
strategy = reference-backed
format_version = reference-v1
```

Nó không persist engine tensors.

## `clone_preflight.py`

Hiện preflight gọi:

```python
engine.encode_reference(reference_audio)
```

VieNeu trả:

```text
speaker_emb
ref_codes
```

nhưng kết quả bị discard.

Đây là gap quan trọng nhất.

## `vieneu_provider.py`

Custom voice hiện resolve:

```text
reference_audio_path
transcript
```

và synthesize bằng reference audio.

Do đó runtime lại chuẩn bị reference.

## `voice_analysis.py`

Analyzer hiện có:

```text
speech_ratio
noise_level_db
clipping_ratio
quality_score
waveform
best speech-dense window
```

Nhưng noise metric và segment score còn heuristic đơn giản.

---

# 3. Technical truth từ VieNeu v3 Turbo

VieNeu v3 Turbo có flow đúng:

```python
speaker_emb, ref_codes = engine.prepare_reference(
    ref_audio,
    denoise=True,
    use_ref_codes=True,
)
```

Engine docs nói rõ:

```text
compute once and reuse for every chunk
```

Semantics:

```text
speaker_emb
→ speaker identity anchor

ref_codes
→ in-context reference frames
```

Inference:

```text
use_ref_codes=True
→ fidelity / bám sát mẫu

use_ref_codes=False
→ speaker embedding only
→ consistency / ổn định
```

CPU runtime:

```text
ONNX int8 → nhanh hơn, default
ONNX fp32 → max fidelity, chậm hơn

GPU
→ PyTorch
```

Reference:

```text
3–8 seconds
automatic denoise available
VieNeu output 48 kHz
denoiser output 44.1 kHz mono
```

---

# 4. Target Architecture

```text
Upload source
    ↓
Reference Analysis v2
    ↓
Best Segment Selector
    ↓
5–8s reference
    ↓
Cleanup Policy
auto / off / on
    ↓
Canonical Reference
    ↓
VieNeu prepare_reference()
    ↓
speaker_emb + ref_codes
    ↓
atomic enrollment-v2.npz
    ↓
Calibration Synthesis
    ↓
Similarity / output quality
    ↓
Profile READY
```

---

# 5. Artifact design

Không lưu giant JSON arrays trong SQLite.

Recommended:

```text
data/voices/<voice-id>/
├── reference.wav
├── cleaned-reference.wav      # nếu denoise applied
├── enrollment-v2.npz
├── enrollment.json
└── calibration.wav
```

## `enrollment-v2.npz`

Persist exact arrays:

```text
speaker_emb → float32
ref_codes   → int64
```

Load:

```python
np.load(path, allow_pickle=False)
```

Không dùng pickle.

## `enrollment.json`

```json
{
  "formatVersion": "vieneu-enrollment-v2",
  "providerId": "vieneu",
  "engineId": "v3turbo",
  "engineVersion": "...",
  "referenceFingerprint": "...",
  "referenceSampleRate": 44100,
  "referenceDuration": 6.2,
  "denoiseMode": "auto",
  "denoiseApplied": true,
  "defaultCloneMode": "fidelity"
}
```

---

# 6. Alembic migration

Add columns cho `tts_custom_voices`:

```text
profile_format_version
enrollment_artifact_path
cleaned_reference_audio_path
calibration_audio_path

engine_version
reference_fingerprint

denoise_mode
denoise_applied

clone_mode

speaker_similarity_score
calibration_quality_score

enrollment_created_at
```

Recommended defaults:

```text
profile_format_version = reference-v1
denoise_mode = auto
clone_mode = fidelity
```

Existing voices giữ `reference-v1`.

Không auto-upgrade tất cả profiles lúc startup.

---

# 7. Backward compatibility

Resolver:

```text
if valid enrollment-v2 exists
    use enrollment artifact
else
    fallback reference_audio_path
```

Old voice vẫn chạy.

Future action:

```text
Upgrade voice profile
```

có thể enroll lại từ existing reference không cần upload lại.

---

# 8. Reference Analysis v2

Refactor `voice_analysis.py` hoặc tạo `voice_analysis_v2.py`.

Analysis-only representation có thể giữ:

```text
16 kHz
mono
100ms frames
```

Mỗi frame compute:

```text
RMS
peak
silence/activity
clipping
```

Derived:

```text
speech_ratio
silence_ratio
rms_dbfs
peak_dbfs
noise_floor_dbfs
estimated_snr_db
clipping_ratio
dynamic_range_db
level_stability
```

## Better noise estimate

Không derive noise từ overall RMS.

Use low-energy frame percentile:

```text
noise floor ≈ low-energy RMS percentile
speech level ≈ active-speech RMS percentile
SNR ≈ speech level - noise floor
```

---

# 9. Better auto segment selection

Evaluate candidate lengths:

```text
5.0
5.5
6.0
6.5
7.0
7.5
8.0 sec
```

Conceptual score:

```text
speech coverage
+ SNR
+ level stability
+ clean boundaries
- clipping penalty
- silence penalty
- extreme loudness penalty
```

Prefer ~5–7 sec khi score tương đương.

Không chọn đơn giản window loud nhất.

Use rolling sums/prefix sums, tránh O(N²) trên source dài.

---

# 10. Quality Score v2

Response:

```json
{
  "quality_score": 87,
  "metrics": {
    "speech_score": 91,
    "noise_score": 82,
    "clipping_score": 100,
    "stability_score": 84,
    "segment_score": 89
  }
}
```

Suggested bands:

```text
0–59   poor
60–74  usable
75–89  good
90–100 excellent
```

Không block profile chỉ vì quality thấp.

Hard block chỉ khi:

```text
too short
decode failure
almost no speech
severe invalid/clipped input
```

---

# 11. Conditional denoise

Modes:

```text
auto
off
on
```

UI:

```text
Tự động
Giữ nguyên
Làm sạch
```

Default `auto`.

Initial heuristic cần benchmark:

```text
estimated SNR thấp / noise floor cao
→ denoise

sample clean
→ preserve original
```

Starting thresholds có thể test:

```text
SNR < ~25 dB → denoise candidate
SNR > ~30 dB + no clipping → keep original
```

Không coi thresholds này là permanent.

---

# 12. Canonical enrollment reference

Current selected segment được xuất 16 kHz mono WAV.

Enrollment v2 nên tách:

```text
analysis copy
→ 16 kHz

enrollment reference
→ preserve source fidelity
or canonical 44.1 kHz mono WAV
```

Recommended experiment:

```text
44.1 kHz mono WAV
```

vì VieNeu denoiser output là 44.1 kHz.

A/B verify trước khi lock.

Create service:

```text
voice_reference_processor.py
```

Responsibilities:

```text
extract segment
canonicalize
conditional denoise
fingerprint
persist reference artifacts
```

---

# 13. Reference fingerprint

SHA-256 over canonical reference bytes + relevant processing version/settings.

Use cho:

```text
artifact integrity
re-enroll detection
future migration
cache safety
```

---

# 14. True Enrollment Service

Create:

```text
apps/api/app/services/vieneu_enrollment.py
```

Interface:

```python
@dataclass(frozen=True)
class EnrollmentResult:
    speaker_emb: np.ndarray
    ref_codes: np.ndarray | None
    artifact_path: Path
    engine_version: str | None
    reference_fingerprint: str
```

Enrollment:

```text
reuse shared ModelManager
↓
reuse existing inference semaphore
↓
prepare_reference ONCE
↓
convert arrays to exact dtype
↓
atomic NPZ persist
```

Không load model thứ hai.

---

# 15. Preflight cleanup

Current preflight đang enroll thật rồi discard.

Change semantics:

```text
preflight
→ capability/artifact/runtime validation

enrollment service
→ expensive actual enrollment exactly once
```

Không duplicate `encode_reference`.

---

# 16. Atomic artifact writes

Flow:

```text
enrollment-v2.npz.tmp
↓
write
↓
load + validate
↓
atomic replace
↓
enrollment-v2.npz
```

Validate:

```text
format version
speaker_emb present
finite values
ref_codes integer
artifact readable
```

Nếu artifact corrupt:

```text
log
→ fallback v1 if reference exists
```

Không crash queue.

---

# 17. Update `vieneu_core.voice_profiles`

Giữ v1.

Add v2 domain type:

```python
@dataclass(frozen=True)
class EnrolledVoiceProfileResult:
    profile_id: str
    reference_audio_path: Path
    enrollment_artifact_path: Path
    strategy: str = "enrolled"
    engine_id: str = "v3turbo"
    format_version: str = "vieneu-enrollment-v2"
```

---

# 18. Clone orchestrator v2

Lifecycle:

```text
validating
analyzing
preparing_reference
enrolling
calibrating
validating_clone
saving
ready
```

DB status vẫn có thể chỉ:

```text
creating
ready
failed
```

Không mark `ready` trước khi artifact đã persisted.

Failure:

```text
mark failed
cleanup partial artifacts
```

---

# 19. Provider integration

Create resolver type:

```python
@dataclass(frozen=True)
class ResolvedCustomVoice:
    voice_id: str
    profile_format_version: str
    speaker_emb: np.ndarray | None
    ref_codes: np.ndarray | None
    reference_audio_path: str | None
    clone_mode: str
```

For v2:

```python
engine.infer(
    text=text,
    voice={
        "speaker_emb": speaker_emb,
        "codes": ref_codes,
    },
    use_ref_codes=...,
)
```

Do NOT pass `ref_audio` if v2 artifact is valid.

For v1:

```text
fallback current ref_audio flow
```

---

# 20. Critical performance assertion

For any valid v2 profile:

```text
prepare_reference
encode_reference
```

must NOT run during normal TTS synthesis.

Allowed only during:

```text
enrollment
re-enrollment
manual upgrade
```

Add temporary instrumentation/test to prove this.

---

# 21. Enrollment cache

Provider may cache:

```text
voice_id → ResolvedEnrollment
```

Invalidation:

```text
delete
upgrade
re-enroll
```

Do not load NPZ once per chunk.

Better:

```text
resolve once per TTS job
→ put resolved voice into JobSnapshot
→ all chunks reuse it
```

---

# 22. Fidelity / Stability modes

Use real VieNeu behavior:

```text
Fidelity
→ use_ref_codes=True

Stability
→ use_ref_codes=False
```

UI:

```text
Bám sát mẫu
Ổn định
```

Do not expose technical `use_ref_codes`.

## Balanced

Không tạo fake mode.

Chỉ add `Balanced` sau A/B benchmark nếu có policy thực sự khác.

---

# 23. Calibration synthesis

Sau enrollment:

```text
new profile
↓
generate short fixed Vietnamese sentence
↓
save calibration.wav
```

Sentence nên:

```text
3–6 sec
neutral
phonetic variety
no emotion tag
```

User nghe ngay kết quả.

---

# 24. Speaker similarity

Compare:

```text
reference speaker embedding
vs
calibration speaker embedding
```

Use cosine similarity.

Phase đầu:

```text
store raw cosine
```

Không đơn giản `cosine * 100` rồi gọi là accuracy.

Calibrate thresholds từ fixture/A-B set trước khi hiển thị percentage mạnh.

Initial UI có thể:

```text
Tốt
Khá
Cần mẫu tốt hơn
```

---

# 25. Calibration quality

Analyze calibration output:

```text
clipping
silence
duration
RMS stability
valid audio
```

Persist:

```text
calibration_quality_score
```

---

# 26. Runtime Max Quality

Current shared `ModelManager` hardcodes:

```python
precision="int8"
```

VieNeu CPU ONNX supports:

```text
int8
fp32
```

Add config:

```text
VIENEU_PRECISION=int8|fp32
```

Default:

```text
int8
```

UI later:

```text
Nhanh
Chất lượng tối đa
```

Important:

```text
precision is runtime-level
not per voice
```

Void Melody has one shared model instance.

MVP precision change:

```text
require engine/app restart
```

Do not load int8 + fp32 simultaneously.

Implement this **after core Enrollment v2 works**.

---

# 27. API changes

Keep existing route where practical:

```text
POST /api/v1/tts/voices/analyze
POST /api/v1/tts/voices/clone
```

Clone new form fields:

```text
denoise_mode
clone_mode
```

Server recomputes trusted analysis.

Do not trust client score.

Analysis response add:

```text
estimated_snr_db
noise_floor_dbfs
silence_ratio
level_stability
recommended segment
denoise recommendation
quality subscores
```

Maintain old fields during transition.

Custom voice response add:

```text
profile_format_version
engine_version
clone_mode
denoise_mode
denoise_applied
speaker_similarity_score
calibration_quality_score
calibration_available
```

Never return filesystem paths.

---

# 28. Voice Lab UI v2

Use shadcn/ui primitives where possible:

```text
Card
Button
Badge
Slider
RadioGroup
Tooltip
Alert
Progress
Separator
Skeleton
```

## Step 1 — Upload

Keep current.

Recommend copy:

```text
Best: WAV source
Accepted: MP3 / M4A
```

FLAC can be added if backend/constants support is updated.

## Step 2 — Analyze

Target:

```text
Phân tích & Tối ưu mẫu

Đoạn đề xuất 1.1–7.4s

[Waveform]

[▶ Nghe đoạn]
[✨ Dùng đoạn tốt nhất]

Giọng nói         91%
SNR               31 dB
Clipping          0%
Ổn định           88%
Chất lượng        89/100
```

## Noise processing

```text
● Tự động
○ Giữ nguyên
○ Làm sạch
```

If cleanup used:

```text
[▶ Bản gốc]
[▶ Bản làm sạch]
```

## Step 3 — Clone mode

```text
● Bám sát mẫu
  Ưu tiên đặc điểm từ reference.

○ Ổn định
  Ưu tiên đọc dài ổn định.
```

## Progress

```text
Đang kiểm tra mẫu
Đang chuẩn hóa
Đang tạo hồ sơ giọng
Đang hiệu chỉnh
Đang kiểm tra kết quả
Đang lưu
```

## Result

```text
Hồ sơ giọng đã sẵn sàng

Chất lượng mẫu   89/100
Độ tương đồng    Tốt
Chế độ           Bám sát mẫu

[▶ Nghe thử]
[Thư viện giọng]
```

---

# 29. Cleanup / delete

Current cleanup recognizes top-level UUID audio files.

V2 introduces profile directories:

```text
voices/<voice-id>/
```

Update delete:

```text
check no active job
↓
delete DB profile
↓
delete entire owned profile directory safely
```

Startup cleanup:

```text
remove stale incomplete profile dirs
preserve all DB-referenced ready profiles
```

---

# 30. Crash recovery

On startup:

```text
find stale status=creating
```

Then:

```text
mark failed
cleanup incomplete temp artifacts
```

Do not delete ready artifacts.

---

# 31. Transcript

Keep transcript field.

For v3 Turbo core enrollment:

```text
audio → speaker_emb + ref_codes
```

Transcript should not be mandatory.

Keep for:

```text
metadata
future engines
future analysis
compatibility
```

---

# 32. Security / privacy

Requirements:

```text
voice data local only
no artifact paths in frontend
no embeddings in API response
NPZ allow_pickle=False
no raw voice vectors in logs
consent remains required
```

---

# 33. File map

## Modify

```text
apps/api/app/models/custom_voice.py
apps/api/app/schemas/custom_voice.py
apps/api/app/api/v1/voices.py
apps/api/app/providers/vieneu_provider.py
apps/api/app/services/clone_orchestrator.py
apps/api/app/services/clone_preflight.py
apps/api/app/services/voice_analysis.py
apps/api/app/services/voice_artifact_cleanup.py
apps/api/app/services/voice_resolver.py

packages/vieneu-core/src/vieneu_core/voice_profiles.py
packages/vieneu-core/src/vieneu_core/engine.py

apps/web/src/components/vieneu/vieneu-page.tsx
apps/web/src/hooks/use-voice-lab.ts
apps/web/src/hooks/use-custom-voice.ts
apps/web/src/locales/vi.ts
apps/web/src/locales/en.ts
apps/web/src/locales/types.ts
```

## Create

```text
apps/api/app/services/vieneu_enrollment.py
apps/api/app/services/voice_reference_processor.py
apps/api/app/services/voice_profile_artifacts.py
apps/api/app/services/voice_similarity.py

apps/api/alembic/versions/<revision>_add_voice_enrollment_v2.py
```

Recommended optional frontend split:

```text
apps/web/src/features/voice-lab/
├── sample-upload-card.tsx
├── reference-analysis-card.tsx
├── denoise-control.tsx
├── clone-mode-control.tsx
├── enrollment-progress.tsx
└── voice-profile-result.tsx
```

---

# 34. Implementation Phases

## Phase 0 — Baseline

Fixtures:

```text
clean male WAV
clean female WAV
clean MP3
mild noise
heavy noise
echo
quiet
loud
clipped
>8s
```

Capture:

```text
current quality
profile creation time
first synthesis
repeated synthesis
long synthesis
```

No large new test suite yet.

---

## Phase 1 — Schema + Artifact foundation

Implement:

```text
Alembic columns
profile format version
voice directory layout
atomic NPZ
artifact loader
legacy fallback
cleanup support
```

Done:

```text
v1 still works
v2 NPZ round-trip works
```

---

## Phase 2 — Analysis v2

Implement:

```text
SNR estimate
noise floor
silence ratio
level stability
candidate lengths
better score
auto-selection
```

Use efficient rolling/prefix algorithms.

---

## Phase 3 — Reference processor

Implement:

```text
selection
canonical reference
auto/off/on denoise
fingerprint
preview artifacts
```

A/B 44.1 kHz canonical vs preservation.

---

## Phase 4 — True Enrollment

Implement:

```text
prepare_reference exactly once
speaker_emb
ref_codes
atomic persistence
metadata
```

Remove duplicate expensive preflight enrollment.

---

## Phase 5 — Provider reuse

Implement:

```text
load v2 artifact
cache enrollment
resolve once per job
infer with enrolled voice dict
fallback v1
```

Must prove:

```text
no prepare_reference during valid v2 TTS
```

---

## Phase 6 — Fidelity / Stability

```text
Fidelity → ref_codes
Stability → speaker_emb only
```

Persist profile default.

---

## Phase 7 — Calibration & Similarity

```text
calibration.wav
speaker embedding compare
raw cosine
output quality
persist result
```

---

## Phase 8 — UI v2

Add:

```text
best segment
quality breakdown
denoise control
clone mode
progress
calibration/result
original vs cleaned
```

Use shadcn.

---

## Phase 9 — CPU Max Quality

Add:

```text
VIENEU_PRECISION
int8 / fp32
```

Singleton engine constraint remains.

Prefer restart-to-apply MVP.

---

## Phase 10 — Legacy upgrade

Optional:

```text
Upgrade profile
```

No forced auto migration.

---

# 35. Benchmark

Compare:

```text
v1
v2 Fidelity
v2 Stability
```

Optional:

```text
INT8
FP32
```

Measure:

```text
enrollment time
first synthesis
second synthesis
long synthesis
speaker similarity
naturalness
stability
artifacts
pronunciation
```

Manual blind score 1–5 where practical.

---

# 36. Defaults

Initial recommendation:

```text
Reference window: auto ~5–7s
Denoise: auto
Clone mode: Fidelity
Precision: int8
Calibration: enabled
```

Change only after benchmark.

---

# 37. Do Not

```text
- store NumPy with pickle
- store giant vector JSON in DB
- re-enroll per chunk
- load second VieNeu model
- denoise every reference blindly
- force 16k enrollment reference without A/B
- expose uncalibrated similarity as accuracy %
- invent fake Balanced mode
- delete reference-v1 support immediately
- mix Gwen/F5 into this implementation
```

---

# 38. Commit sequence

```text
feat(voice-lab): add enrollment v2 schema
refactor(voice-lab): add versioned artifact storage
feat(voice-lab): improve reference analysis
feat(voice-lab): add automatic reference selection
feat(voice-lab): add conditional cleanup
feat(vieneu): persist enrollment artifacts
perf(vieneu): reuse enrolled voices during synthesis
feat(vieneu): add fidelity and stability modes
feat(voice-lab): add calibration and similarity
refactor(voice-lab): upgrade UI with shadcn
feat(vieneu): add optional fp32 max-quality runtime
chore(voice-lab): add legacy upgrade path
```

---

# 39. Validation

Priority:

```text
DB migration
API startup
existing v1 voice
new v2 voice
clean WAV
MP3
noisy sample
>8s sample
auto selection
denoise auto/off/on
Fidelity
Stability
calibration
restart
v2 synthesis after restart
long v2 TTS
delete profile
artifact cleanup
existing backend tests
web build
Tauri sidecar where available
```

Targeted tests worth adding:

```text
artifact serialization
allow_pickle=False
migration
legacy fallback
fingerprint determinism
v2 provider avoids re-enrollment
cleanup safety
```

---

# 40. Definition of Done

```text
✓ Best reference selection is improved.
✓ Denoise is conditional.
✓ Canonical reference avoids unnecessary fidelity loss.
✓ prepare_reference executes once at enrollment.
✓ speaker_emb is persisted.
✓ ref_codes is persisted.
✓ artifact survives restart.
✓ valid v2 TTS never re-enrolls reference.
✓ Fidelity uses ref_codes.
✓ Stability uses embedding-only.
✓ calibration exists.
✓ similarity/internal validation exists.
✓ Voice Lab exposes understandable quality feedback.
✓ v1 voices still work.
✓ deletion safely removes all owned artifacts.
✓ one shared VieNeu model remains.
✓ voice data remains local.
```

---

# 41. Coding Agent Prompt

```text
Read `VOID_MELODY_VIENEU_ENROLLMENT_V2_PLAN.md` completely before editing code.

Implement VieNeu Enrollment v2 end-to-end.

PRIMARY OBJECTIVE

Change custom voices from:

reference-backed profile
→ repeated reference preparation on synthesis

to:

reference
→ analyze
→ best segment
→ conditional denoise
→ prepare_reference ONCE
→ persist speaker_emb + ref_codes
→ calibration
→ reuse enrollment artifact for all future synthesis.

RULES

1. Current repository main is source of truth.
2. Preserve all existing v1 custom voices.
3. Keep reference-v1 fallback.
4. Do not add any other voice clone engine.
5. Never load a second VieNeu model.
6. Reuse shared ModelManager/provider runtime.
7. NPZ must use allow_pickle=False.
8. Do not store huge array JSON in SQLite.
9. Do not expose embeddings or local paths to frontend.
10. Do not always denoise.
11. Implement only truthful Fidelity/Stability behavior.
12. Fidelity => use_ref_codes=True.
13. Stability => use_ref_codes=False.
14. Do not invent Balanced.
15. Preserve TTS queue, CapCut, Emotional Script, Tauri and auth.
16. Use Alembic.
17. Use shadcn primitives for new UI controls.
18. Do not create a large test suite before implementation.
19. Add targeted artifact/migration/fallback/no-re-enrollment tests.
20. Continue through all phases unless genuinely blocked.

AUDIT FIRST

Inspect:
- apps/api/app/models/custom_voice.py
- apps/api/app/schemas/custom_voice.py
- apps/api/app/api/v1/voices.py
- apps/api/app/providers/vieneu_provider.py
- apps/api/app/services/clone_orchestrator.py
- apps/api/app/services/clone_preflight.py
- apps/api/app/services/voice_analysis.py
- apps/api/app/services/voice_artifact_cleanup.py
- apps/api/app/services/voice_resolver.py
- packages/vieneu-core/src/vieneu_core/voice_profiles.py
- packages/vieneu-core/src/vieneu_core/engine.py
- apps/web/src/components/vieneu/vieneu-page.tsx
- apps/web/src/hooks/use-voice-lab.ts

Confirm current behavior:
- DB stores reference path
- preflight runs real encode_reference
- enrollment output is discarded
- provider later uses ref_audio
- custom TTS therefore prepares reference again

PHASE ORDER

0. Baseline
1. Schema + artifact foundation
2. Analysis v2
3. Reference processor
4. True enrollment
5. Provider artifact reuse
6. Fidelity / Stability
7. Calibration + similarity
8. UI v2
9. Optional CPU fp32 max quality
10. Legacy upgrade path

CRITICAL ASSERTION

For a valid enrollment-v2 voice:

prepare_reference / encode_reference MUST NOT execute in normal TTS synthesis.

They may execute only during enrollment, re-enrollment or explicit profile upgrade.

ARTIFACT

data/voices/<voice-id>/
  reference.wav
  cleaned-reference.wav
  enrollment-v2.npz
  enrollment.json
  calibration.wav

speaker_emb => float32
ref_codes => int64

Use atomic writes.

BACKWARD COMPATIBILITY

If v2 artifact is missing/invalid:
- fallback to reference-v1 if reference exists
- log fallback
- do not crash worker

FINAL REPORT

Return:
## Completed phases
## DB migration
## Artifact format
## Analysis changes
## Denoise behavior
## Enrollment behavior
## Provider changes
## Fidelity/Stability
## Calibration/similarity
## UI changes
## Legacy compatibility
## Performance results
## Validation PASS/FAIL/NOT RUN
## Remaining technical debt

Explicitly confirm whether normal v2 synthesis calls prepare_reference.
```
