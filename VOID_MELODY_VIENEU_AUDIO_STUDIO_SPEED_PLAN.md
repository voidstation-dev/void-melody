# Void Melody — VieNeu Audio Studio Speed Optimization Plan

> **Scope locked:** tối ưu **phần Tạo Audio bằng VieNeu** trong Audio Studio.
>
> **Không thay đổi thuật toán tạo Voice Clone / Enrollment v2.**
>
> Voice Clone chỉ bị ảnh hưởng ở mức **consumer path**: Audio Studio phải reuse đúng `speaker_emb + ref_codes` đã được Enrollment v2 tạo ra, thay vì vô tình quay lại `reference.wav` và re-enroll.

---

# 1. Scope

Plan này chỉ tối ưu đường:

```text
Audio Studio
→ Generate Audio
→ VieNeu
→ TTS execution
→ cache
→ media composition
→ output
```

Không thay đổi đường:

```text
Voice Lab
→ upload reference
→ analyze
→ auto-select
→ denoise policy
→ prepare_reference()
→ speaker_emb + ref_codes
→ enrollment-v2.npz
→ calibration
→ profile READY
```

---

# 2. Hard Boundary

Regression rule bắt buộc:

```text
Create Voice Clone:
prepare_reference() = 1 lần trong enrollment ✅

Generate Audio bằng clone đó:
prepare_reference() = 0 lần ✅
```

Không được thay đổi:

```text
Voice reference analysis
Best segment selection
Denoise policy
Enrollment artifact generation
Calibration algorithm
Speaker similarity algorithm
Clone quality scoring
Profile creation UX
Consent flow
```

Có thể modify shared files như:

```text
voice_resolver.py
vieneu_provider.py
```

nhưng chỉ để **đọc/reuse profile đã hoàn thành** nhanh hơn.

---

# 3. Current Main Baseline

Plan được viết dựa trên latest `main` hiện tại:

```text
commit:
c2880d4f6ce54b5ab273e6b49ad43bbb00e2df40
```

Current stack đã có:

```text
FastAPI
Async SQLAlchemy
SQLite WAL
provider-aware scheduler
VieNeu v3 Turbo
Enrollment v2 artifacts
generic segment cache
central media pipeline
bounded FFmpeg concurrency
```

Các phần tốt hiện tại cần giữ:

```text
one VieNeu model per process
VieNeu inference semaphore = 1
CPU ONNX int8 default
GPU PyTorch auto detection
TTS retry/recovery
cancellation registry
generic cache
```

---

# 4. Current Bottlenecks

## 4.1 Enrollment v2 có thể bị bypass trong Audio Studio

`voice_resolver.py` đã có thể load:

```text
speaker_emb
ref_codes
clone_mode
```

nhưng current TTS job snapshot vẫn chủ yếu truyền:

```text
reference_audio_path
prompt_text
```

sang VieNeu provider.

Nếu `ref_audio` được truyền vào provider, VieNeu có thể quay lại:

```text
reference audio
→ prepare_reference()
→ encode speaker
→ encode ref codes
→ infer
```

thay vì dùng artifact v2 đã có.

Đây là bottleneck P0.

---

## 4.2 VieNeu jobs chưa luôn route đúng provider lane

Job creation cần bảo đảm:

```python
provider_id=job.provider_id
```

được truyền vào queue scheduler.

Nếu không:

```text
VieNeu job
→ default CapCut lane
```

làm sai execution policy và gây head-of-line blocking trên mixed workload.

---

## 4.3 Generic 450-char chunking không tối ưu cho VieNeu

Current application-level splitter:

```text
~450 chars
```

trong khi VieNeu v3 Turbo tự có internal native chunking:

```text
~256 chars
```

Kết quả:

```text
Void Melody outer chunk
↓
VieNeu inner chunk
```

Nested chunking tạo quá nhiều:

```text
provider calls
cache lookups
cache writes
temp files
FFmpeg processes
```

---

## 4.4 Mỗi VieNeu outer chunk đang encode MP3 riêng

Current pattern:

```text
VieNeu infer
↓
save WAV
↓
FFmpeg WAV → MP3
↓
return part.mp3
```

cho từng chunk.

Sau đó:

```text
part0.mp3
part1.mp3
part2.mp3
...
↓
FFmpeg concat
↓
final.mp3
```

Nếu output là WAV thì còn có nguy cơ:

```text
PCM/WAV
→ MP3
→ WAV
```

vừa chậm, vừa không còn lossless thật.

---

## 4.5 Cache hit vẫn copy file

Current cache hit path có thể:

```text
cache.mp3
→ copy job_part.mp3
→ concat
→ delete copied file
```

Copy này không cần thiết.

---

## 4.6 Cache hit vẫn commit DB mỗi segment

`last_used_at` update có thể:

```text
cache hit
→ UPDATE
→ COMMIT
```

cho từng segment.

Long render với nhiều cache hit tạo write amplification.

---

## 4.7 Cache miss cũng commit từng segment

Mỗi cache store hiện có thể mở session và commit riêng.

Có thể batch metadata commit cuối render.

---

## 4.8 GPU batching chưa được Audio Studio tận dụng

Vendored VieNeu hỗ trợ:

```python
infer_batch(...)
```

và static batching trên:

```text
PyTorch + CUDA
```

Current Melody vẫn chủ yếu:

```text
chunk 1 → infer
chunk 2 → infer
chunk 3 → infer
```

---

## 4.9 First-generation latency còn model lazy-load

VieNeu engine load khi `get_engine()` được gọi lần đầu.

Nếu user bấm Generate ngay:

```text
click
→ load model
→ initialize runtime
→ infer
```

nên lần đầu cảm thấy chậm.

---

# 5. Target Architecture

```text
Audio Studio
     ↓
Audio Render Planner
     ↓
VieNeu-specific Macro Planner
     ↓
Prepared Voice ONCE
     ↓
Segment Cache
   ↙            ↘
cache hit       cache miss
   ↓                ↓
direct reuse     VieNeu engine
                     │
                CPU  │ GPU
                seq  │ infer_batch
                     ↓
              lossless internal audio
                     ↓
                Media Pipeline
                 /          \
               WAV          MP3
                ↓            ↓
             direct     one final encode
```

---

# 6. Safety Principles

## Keep

```text
one shared VieNeu model per process
one FastAPI process
bounded FFmpeg
cache
retry/recovery
cancellation
SQLite
hardware-aware runtime policy
```

## Adaptive CPU policy

VieNeu chạy local nên được phép dùng concurrency > 1 khi hardware thực tế chứng minh có lợi.

Không hardcode:

```text
concurrency = os.cpu_count()
```

Thay vào đó autotune cặp:

```text
inference_concurrency × threads_per_inference
```

Safe bootstrap:

```text
concurrency = 1
threads = engine default
```

Safe autotune range đầu tiên:

```text
CPU inference concurrency = 1–4
```

Ví dụ candidates:

```text
4-core:
1×4
2×2

8-core:
1×8
2×4
3×2

12-core:
1×8
2×6
3×4

16+ core:
1×8
2×8
3×4
4×4
```

Không assume candidate nào nhanh nhất trước benchmark.

## GPU policy

Trên CUDA ưu tiên:

```text
infer_batch()
```

thay vì nhiều concurrent `infer()` độc lập.

Autotune batch candidates:

```text
1
2
4
8
16
```

Không default 32.

OOM fallback bắt buộc:

```text
16 → 8 → 4 → 2 → 1
```

## Do NOT

```text
set CPU concurrency directly from logical CPU count
load multiple VieNeu models
use multiple Uvicorn workers
default GPU batch size to 32
force all CPU cores permanently
send giant 50k text directly into one infer()
change VieNeu sampling parameters for speed
lower audio quality
change Enrollment v2 creation algorithm
```

---

# 7. Phase 0 — Performance Instrumentation

## Goal

Biết thời gian thật đang nằm ở đâu.

Add timings:

```text
queue_wait_ms
voice_resolve_ms
cache_lookup_ms
vieneu_infer_ms
wav_save_ms
ffmpeg_encode_ms
cache_store_ms
concat_ms
duration_probe_ms
total_ms
```

Also log:

```text
provider
runtime backend
device
char_count
outer_block_count
cache_hits
cache_misses
voice_profile_format
clone_mode
output_format
```

Do not add heavy telemetry stack.

Structured logging is enough.

---

# 8. Phase 1 — Fix Provider Lane Routing

## Modify

```text
apps/api/app/api/v1/tts_jobs.py
apps/api/app/api/v1/tts_batches.py
```

Wherever enqueue occurs, pass:

```python
await queue_manager.enqueue(
    job.id,
    batch_position=job.batch_position or 0,
    provider_id=job.provider_id,
)
```

Also verify:

```text
retry
recovery
batch
single job
```

all preserve `provider_id`.

Definition of done:

```text
VieNeu job always enters VieNeu lane
CapCut job always enters CapCut lane
```

---

# 9. Phase 2 — PreparedVoice for Audio Generation

## Goal

Resolve completed cloned voice once.

Create a runtime-only prepared voice type.

Example:

```python
@dataclass(frozen=True)
class PreparedVoice:
    voice_type: str
    provider_id: str
    source: str

    voice_revision: str

    speaker_emb: np.ndarray | None = None
    ref_codes: np.ndarray | None = None
    clone_mode: str = "fidelity"

    reference_audio_path: str | None = None
    prompt_text: str | None = None
```

## Resolution behavior

Preset VieNeu:

```text
preset name
→ VieNeu native preset
```

Clone v2:

```text
speaker_emb
ref_codes
clone_mode
```

Clone v1:

```text
reference_audio_path
prompt_text
```

## Extend JobSnapshot

Update:

```text
apps/api/app/services/chunk_executor.py
```

Add:

```text
speaker_emb
ref_codes
clone_mode
profile_format_version
```

Do not serialize these into DB.

Runtime memory only.

## Provider behavior

For v2 voice:

```python
voice_spec = {
    "speaker_emb": prepared.speaker_emb,
    "codes": prepared.ref_codes,
}

engine.infer(
    text=text,
    voice=voice_spec,
    use_ref_codes=(prepared.clone_mode == "fidelity"),
)
```

Do not pass `ref_audio` for valid v2.

V1 fallback keeps current reference-backed behavior.

## Critical assertion

```text
v2 profile
+ 10 chunks
→ prepare_reference count == 0
```

during normal generation.

---

# 10. Phase 3 — VieNeu-Specific Text Planner

## Goal

Reduce application-level provider calls.

Create:

```text
apps/api/app/services/vieneu_text_planner.py
```

Do not use generic `450-char` splitter for VieNeu.

Initial safe values:

```text
target_chars = 1024
hard_max_chars = 1280
```

Preserve:

```text
paragraph boundaries
sentence boundaries
native cue boundaries
```

Target:

```text
Void Melody macro block ~1024
↓
VieNeu native internal chunking ~256
↓
one returned waveform
```

Benchmark:

```text
450
768
1024
1280
```

Measure:

```text
total time
RAM
cancel responsiveness
quality
pronunciation continuity
```

---

# 11. Phase 4 — Cache Fast Path

## Cache hit no-copy

Instead of:

```text
cached.mp3
→ copy
→ job-part.mp3
```

return cached path directly.

Extend result metadata:

```python
owned_by_job: bool = True
```

Cache path:

```text
owned_by_job=False
```

Cleanup must never delete it.

## Batch last_used_at

Instead of:

```text
N hits
→ N UPDATE + COMMIT
```

collect fingerprints and update once at job end.

## Batch cache stores

For misses:

```text
generate blocks
↓
persist cache files
↓
bulk metadata upsert
↓
ONE transaction
```

Cache failure must not fail final audio.

---

# 12. Phase 5 — VieNeu Provider Becomes Inference-Only

Current:

```text
infer
save WAV
FFmpeg MP3
return MP3
```

Target:

```text
infer
return WAV/PCM artifact
```

Use central:

```text
apps/api/app/media/pipeline.py
```

for:

```text
concat
transcode
final encode
output format
duration probe
```

Remove direct FFmpeg responsibility from `vieneu_provider.py` after validation.

---

# 13. Phase 6 — Lossless Internal Pipeline

## MP3

```text
WAV block 1
WAV block 2
WAV block 3
↓
compose
↓
ONE final MP3 encode
```

## WAV

```text
VieNeu PCM/WAV
↓
compose WAV
↓
final WAV
```

No MP3 intermediary.

Important:

```text
WAV (Lossless Studio)
```

must mean actual lossless path.

Do not keep huge render in RAM.

Use disk-backed WAV/PCM intermediate artifacts.

---

# 14. Phase 7 — Final Composition Optimization

For multiple lossless blocks:

```text
concat/compose
↓
rate processing if needed
↓
final output format
```

Use central FFmpeg semaphore.

Keep laptop-safe concurrency.

---

# 15. Phase 8 — Adaptive VieNeu Runtime

## Goal

Tận dụng tối đa hardware local nhưng không oversubscribe CPU/GPU.

Create:

```text
apps/api/app/services/vieneu_runtime_policy.py
apps/api/app/services/vieneu_auto_tuner.py
apps/api/app/services/vieneu_resource_governor.py
```

Suggested runtime profile:

```python
@dataclass(frozen=True)
class VieNeuRuntimeProfile:
    device: str
    backend: str
    precision: str

    inference_concurrency: int
    threads_per_inference: int

    gpu_batch_size: int

    performance_mode: str

    hardware_key: str
    score: float | None
```

## CPU autotune

Tune the pair:

```text
inference_concurrency
×
threads_per_inference
```

Safe bootstrap:

```text
1 × engine-default
```

Safe candidate concurrency range:

```text
1–4
```

Do not use more than 4 concurrent CPU inference workers in the first implementation.

Autotune candidate generation should consider:

```text
physical cores
logical cores
available RAM
current backend
precision
```

Prefer leaving roughly:

```text
15–25% CPU headroom
```

in Auto mode for:

```text
Tauri UI
FastAPI
SQLite
FFmpeg
OS
```

## GPU autotune

Only when:

```text
backend = pytorch
device = cuda
```

Use:

```python
engine.infer_batch(...)
```

Candidate batch sizes:

```text
1
2
4
8
16
```

Safe initial probe:

```text
4
```

If stable and VRAM allows:

```text
4 → 8 → 16
```

If CUDA OOM or instability:

```text
16 → 8 → 4 → 2 → 1
```

Never load another model to increase throughput.

## Short benchmark

Autotune should be lightweight.

Use a fixed Vietnamese benchmark sample around:

```text
150–250 chars
```

Warm engine once first.

For each candidate measure:

```text
throughput
real-time factor
wall-clock duration
memory
CPU utilization
GPU VRAM
errors
```

Autotune should generally finish in:

```text
~5–15 seconds
```

depending on hardware.

Run only when:

```text
first VieNeu setup
hardware profile changed
VieNeu engine/version changed
precision changed
user presses Re-optimize
```

Do not benchmark every startup.

## Hardware key

Persist a hardware/runtime signature:

```text
CPU model
physical cores
logical cores
RAM class
GPU model
VRAM
backend
VieNeu engine version
precision
```

If key changes:

```text
invalidate old tune
→ safe bootstrap
→ retune
```

## Runtime modes

Expose product modes:

```text
Auto
Eco
Performance
```

Suggested policy:

```text
Auto
→ use tuned profile with ~15–25% headroom

Eco
→ reduce concurrency / threads / GPU batch

Performance
→ use aggressive validated profile
```

Do not expose raw thread counts to normal users by default.

Advanced settings may show them later.

## Resource Governor

`VieNeuResourceGovernor` owns:

```text
CPU inference concurrency
ONNX threads per inference
GPU batch size
FFmpeg concurrency coordination
```

It must prevent a local optimization from starving the rest of the desktop app.

## Guardrails

Reject or downgrade a candidate if it causes:

```text
OOM
runtime errors
audio corruption
sustained UI starvation
excessive RAM
worse throughput
severe thermal throttling where detectable
```

Fastest raw candidate is not automatically the winner.

Conceptual score:

```text
throughput
- memory penalty
- latency penalty
- stability penalty
```

## Cross-job GPU micro-batching

Optional after per-job batching is stable.

GPU lane may collect compatible blocks from multiple jobs:

```text
A1
A2
B1
C1
↓
micro-batch
```

Use a very short collector window:

```text
10–30ms
```

Requirements:

```text
same compatible engine/runtime
correct result ownership
cancel safety
priority safety
```

Do not implement cross-job micro-batching before single-job `infer_batch()` is validated.

---

# 16. Phase 9 — Lazy Background Warmup

When selected voice provider becomes VieNeu:

```text
background get_engine()
```

Do not block UI.

Do not warm VieNeu when user only uses CapCut.

For clone v2, preload enrollment artifact into resolver cache if useful.

Do not perform dummy synthesis by default.

---

# 17. Phase 10 — Streaming Preview

Use existing `infer_stream()` first for:

```text
Preview / Nghe thử
```

Flow:

```text
click Preview
↓
first PCM frames
↓
FFmpeg pipe
↓
play early
```

Do not replace production render with streaming until cache/retry/recovery are proven safe.

---

# 18. Phase 11 — Persisted Hardware Runtime Profile

Persist the selected runtime profile in local settings or SQLite.

Example:

```json
{
  "hardwareKey": "...",
  "device": "cpu",
  "backend": "onnx",
  "precision": "int8",
  "inferenceConcurrency": 2,
  "threadsPerInference": 4,
  "gpuBatchSize": 1,
  "performanceMode": "auto",
  "score": 1.74,
  "testedAt": "..."
}
```

Rules:

```text
startup reads persisted profile
hardwareKey match
→ reuse immediately

hardwareKey mismatch
→ safe defaults
→ schedule retune
```

Expose action:

```text
Re-optimize VieNeu for this machine
```

Do not force users to understand threads/concurrency.

---

# 19. Phase 12 — Cleanup

After stable migration remove:

```text
direct VieNeu ffmpeg encode
duplicate combine path
legacy per-chunk MP3 temporary flow
redundant copied cache paths
```

Keep v1 clone fallback.

---

# 20. File Map

## Modify

```text
apps/api/app/api/v1/tts_jobs.py
apps/api/app/api/v1/tts_batches.py

apps/api/app/workers/tts_worker.py
apps/api/app/workers/queue_manager.py

apps/api/app/services/chunk_executor.py
apps/api/app/services/voice_resolver.py
apps/api/app/services/tts_service.py

apps/api/app/providers/vieneu_provider.py

apps/api/app/media/cache.py
apps/api/app/media/pipeline.py

apps/api/app/config.py

packages/vieneu-core/src/vieneu_core/engine.py
```

## Create

```text
apps/api/app/services/vieneu_text_planner.py
apps/api/app/services/prepared_voice.py
apps/api/app/services/vieneu_runtime_policy.py
apps/api/app/services/vieneu_auto_tuner.py
apps/api/app/services/vieneu_resource_governor.py
```

Optional:

```text
apps/api/app/media/artifacts.py
apps/api/app/services/vieneu_runtime_warmup.py
```

---

# 21. Files That Must Not Change Semantically

Preserve behavior of:

```text
apps/api/app/services/vieneu_enrollment.py
apps/api/app/services/voice_reference_processor.py
apps/api/app/services/voice_analysis.py
apps/api/app/services/voice_similarity.py
apps/api/app/services/clone_orchestrator.py
apps/api/app/services/clone_preflight.py
```

If imports/types require edits, keep enrollment behavior identical.

---

# 22. Benchmark Matrix

Voices:

```text
Preset VieNeu
Clone v2 VieNeu
Clone v1 fallback
```

Text:

```text
500 chars
2k chars
10k chars
50k chars
```

Formats:

```text
MP3
WAV
```

Hardware:

```text
CPU ONNX
CUDA GPU if available
```

Metrics:

```text
first-run total
warm-run total
inference total
FFmpeg total
cache-hit run
memory peak
CPU peak
GPU memory
outer block count
FFmpeg process count
cache DB commit count

selected CPU inference concurrency
selected ONNX threads
selected GPU batch size
autotune score
autotune duration
```

---

# 23. Expected Directional Wins

## Enrollment v2 consumption fix

```text
before:
reference processing may repeat

after:
0 re-enrollment during Audio Studio synthesis
```

## Macro planner

Example 10k chars:

```text
450 chars
→ ~23 outer calls

1024 chars
→ ~10 outer calls
```

## One final encode

Example 20 blocks:

```text
before:
20 MP3 encodes + concat

after:
1 final encode
```

## Cache no-copy

```text
before:
copy cache artifact

after:
direct reuse
```

## Adaptive CPU

On machines where benchmark proves it helps:

```text
1 inference × many threads
```

may become:

```text
2–4 inference workers × fewer threads each
```

while preserving resource headroom.

The selected policy is hardware-specific.

## GPU batch

```text
sequential
→ static batching
```

on CUDA only.

Batch size is tuned to the installed GPU and persisted locally.

---

# 24. Validation

## Voice Clone regression

Must PASS:

```text
create new clone
analysis unchanged
denoise unchanged
enrollment artifact unchanged
calibration unchanged
profile READY
preview still works
```

## Audio Studio

Must PASS:

```text
VieNeu preset
VieNeu clone v2
VieNeu clone v1
MP3
WAV
rate 1.0
rate != 1.0
cancel
retry
restart recovery
cache hit
cache miss
batch
long text
```

## Scheduler

Must PASS:

```text
VieNeu → VieNeu lane
CapCut → CapCut lane
mixed queue
```

## Adaptive runtime

Must PASS:

```text
safe bootstrap policy
CPU autotune candidates bounded to 1–4 concurrency
hardware profile persisted
hardware profile reused after restart
hardware key invalidates stale tune
Auto mode keeps resource headroom
Eco mode lowers resource usage
Performance mode only uses benchmark-validated settings
CUDA OOM fallback works when GPU available
```

## Critical enrollment assertion

```text
normal v2 generation
→ zero prepare_reference calls
```

---

# 25. Rollout Strategy

Recommended PR order:

```text
PR 1
provider lane
PreparedVoice
zero v2 re-enrollment

PR 2
VieNeu macro planner

PR 3
cache fast path

PR 4
lossless internal artifacts

PR 5
one final encode + true WAV

PR 6
Adaptive VieNeu Runtime:
CPU concurrency × threads autotune
GPU infer_batch autotune
runtime profile persistence

PR 7
background warmup

PR 8
streaming preview

PR 9
cross-job GPU micro-batching (optional)

PR 10
cleanup
```

---

# 26. Feature Flags

Recommended during rollout:

```text
VIENEU_MACRO_PLANNER_ENABLED=true
VIENEU_MACRO_TARGET_CHARS=1024

VIENEU_LOSSLESS_INTERNAL_ENABLED=false
VIENEU_ADAPTIVE_RUNTIME_ENABLED=false
VIENEU_GPU_BATCH_ENABLED=false
VIENEU_BACKGROUND_WARMUP_ENABLED=true

VIENEU_RUNTIME_MODE=auto
VIENEU_MAX_CPU_CONCURRENCY=4
```

P0 correctness fixes do not need a feature flag.

---

# 27. Commit Sequence

```text
fix(tts): route jobs through provider-specific execution lanes
```

```text
perf(vieneu): reuse enrolled custom voice during audio generation
```

```text
perf(vieneu): add provider-aware macro text planner
```

```text
perf(cache): reuse cached audio without job-local copies
```

```text
perf(cache): batch cache touch and metadata writes
```

```text
refactor(vieneu): return lossless provider artifacts
```

```text
refactor(media): centralize final VieNeu audio composition
```

```text
perf(media): encode VieNeu output only once
```

```text
fix(audio): generate true lossless WAV from VieNeu output
```

```text
perf(vieneu): add adaptive local runtime autotuning
```

```text
perf(vieneu): add safe CUDA batch inference
```

```text
feat(vieneu): persist hardware-specific runtime profiles
```

```text
perf(vieneu): warm selected VieNeu runtime in background
```

```text
feat(audio): add low-latency VieNeu streaming preview
```

```text
chore(audio): remove legacy per-chunk media paths
```

---

# 28. Definition of Done

```text
✓ Voice Clone creation algorithm unchanged.
✓ v2 clone generation does not call prepare_reference.
✓ VieNeu jobs route through VieNeu lane.
✓ VieNeu no longer relies on generic 450-char outer chunking.
✓ provider calls reduced on long text.
✓ cache hits require no redundant file copy.
✓ cache metadata writes batched/debounced.
✓ VieNeu provider no longer owns final MP3 encoding.
✓ MP3 output uses one final encode where practical.
✓ WAV output never goes through MP3.
✓ CPU concurrency is hardware-adaptive instead of hardcoded.
✓ CPU autotune jointly selects inference concurrency and ONNX thread count.
✓ Auto mode preserves desktop resource headroom.
✓ GPU batching is hardware-adaptive, conservative and OOM-safe.
✓ tuned runtime profile persists across restarts and invalidates on hardware/runtime changes.
✓ first VieNeu generation latency reduced by background warmup.
✓ retry/cancel/recovery remain intact.
✓ CapCut behavior unchanged.
✓ Voice Clone behavior unchanged.
```

---

# 29. Coding Agent Prompt

```text
Read `VOID_MELODY_VIENEU_AUDIO_STUDIO_SPEED_PLAN.md` completely before changing code.

Your task is to optimize VieNeu generation speed in Audio Studio ONLY.

HARD SCOPE BOUNDARY

Do NOT change the Voice Clone / Enrollment v2 creation algorithm.

The following flow must remain behaviorally unchanged:

Voice Lab
→ reference analysis
→ best segment selection
→ denoise decision
→ prepare_reference
→ speaker_emb + ref_codes
→ enrollment-v2 artifact
→ calibration
→ similarity
→ READY profile.

You may modify shared voice resolver/provider code only to make Audio Studio consume a completed voice profile faster.

CRITICAL ASSERTION

Create Voice Clone:
prepare_reference is expected during enrollment.

Generate Audio using a valid enrollment-v2 profile:
prepare_reference / encode_reference = ZERO calls.

If normal Audio Studio synthesis re-enrolls a v2 reference, the implementation is incorrect.

SOURCE OF TRUTH

Use the current repository main branch.

Audit first:

- apps/api/app/api/v1/tts_jobs.py
- apps/api/app/api/v1/tts_batches.py
- apps/api/app/workers/queue_manager.py
- apps/api/app/workers/tts_worker.py
- apps/api/app/services/chunk_executor.py
- apps/api/app/services/voice_resolver.py
- apps/api/app/providers/vieneu_provider.py
- apps/api/app/media/cache.py
- apps/api/app/media/pipeline.py
- apps/api/app/utils/text_utils.py
- packages/vieneu-core/src/vieneu_core/engine.py
- vendored VieNeu v3 Turbo infer / infer_batch / infer_stream behavior

IMPLEMENT IN PHASES

Phase 0
Add stage-level performance measurements.

Phase 1
Fix provider lane routing.
All enqueue/retry/recovery paths must preserve provider_id.

Phase 2
Add PreparedVoice runtime snapshot:
- preset
- clone v2 speaker_emb/ref_codes/clone_mode
- clone v1 reference fallback
Resolve once per job.
For clone v2 DO NOT pass ref_audio.

Phase 3
Add VieNeu-specific macro text planner.
Start with target 1024 chars and hard max 1280.
Preserve sentence/paragraph boundaries.
Do not apply to CapCut.

Phase 4
Optimize cache:
- no copy on cache hit
- artifact ownership metadata
- never delete cache-owned files
- batch/debounce last_used_at writes
- batch cache metadata writes where safe

Phase 5
Refactor VieneuProvider to return lossless WAV/PCM-like artifacts.
Provider performs inference only.
Encoding/format decisions belong to MediaPipeline.

Phase 6
Lossless composition:
- MP3 => one final encode
- WAV => direct lossless output
Never PCM/WAV -> MP3 -> WAV.

Phase 7
Implement Adaptive VieNeu Runtime.

CPU:
- bootstrap safely at concurrency 1
- autotune inference_concurrency × threads_per_inference
- candidate concurrency must stay within 1–4 initially
- do NOT map logical CPU count directly to concurrency
- preserve 15–25% resource headroom in Auto mode where practical
- persist the winning hardware profile

CUDA:
- use infer_batch
- benchmark batch candidates 1/2/4/8/16
- start probing around batch 4
- OOM fallback 16 -> 8 -> 4 -> 2 -> 1
- one model instance only
- persist safe batch size

Add runtime modes:
Auto / Eco / Performance.

Phase 8
Background warmup when selected provider is VieNeu.
Do not warm when user uses CapCut.

Phase 9
Use infer_stream for low-latency Preview first.
Do not replace production rendering with streaming until cache/retry/recovery are proven.

Phase 10
Optional after single-job GPU batching is stable:
cross-job GPU micro-batching with a 10–30ms collector window.

SAFETY RULES

CPU concurrency is allowed to exceed 1 ONLY through the adaptive runtime tuner.

Do NOT:
- set CPU inference concurrency directly from os.cpu_count()
- exceed initial CPU autotune range 1–4 without new benchmark evidence
- combine high concurrency with unrestricted ONNX thread counts
- add multiple VieNeu model instances
- add multiple Uvicorn workers
- default CUDA batch size to 32
- ignore CUDA OOM fallback
- change model sampling parameters for speed
- reduce synthesis quality
- modify Enrollment v2 quality logic
- modify denoise policy
- modify clone calibration logic
- change CapCut behavior
- remove v1 clone fallback

ROLLBACK

Where useful use feature flags for:
- macro planner
- lossless internal media
- adaptive runtime
- GPU batching
- background warmup

If adaptive tuning fails:
- immediately fall back to concurrency 1
- use engine-default threads
- disable GPU batching or batch size 1
- generation must continue safely

VALIDATION

Must verify Voice Clone regression:
- new clone creation
- enrollment
- calibration
- profile ready
- preview
all unchanged.

Must verify Audio Studio:
- preset VieNeu
- clone v2
- clone v1 fallback
- MP3
- WAV
- rate 1.0
- non-1.0 rate
- cache hit
- cache miss
- cancel
- retry
- recovery
- long text
- mixed CapCut/VieNeu queue

PERFORMANCE REPORT

Compare before/after:
- total generation time
- VieNeu inference time
- FFmpeg time
- outer provider call count
- FFmpeg process count
- cache DB commit count
- first-run latency
- warm-run latency
- cache-hit latency
- selected CPU inference concurrency
- selected threads per inference
- selected GPU batch size
- autotune time
- autotune score
- memory peak
- CPU/GPU utilization

FINAL REPORT

Return:

## Completed phases
## Files changed
## Provider lane fix
## PreparedVoice implementation
## Confirmation of zero v2 re-enrollment
## VieNeu text planner
## Cache optimizations
## Media pipeline changes
## MP3/WAV behavior
## Adaptive runtime behavior
## CPU concurrency/thread policy
## GPU batching behavior
## Hardware profile persistence
## Warmup behavior
## Voice Clone regression result
## Performance before/after
## Validation PASS/FAIL/NOT RUN
## Remaining technical debt

Do not stop after the first phase unless a genuine blocker prevents safe continuation.
```
