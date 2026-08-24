# Void Melody Backend Optimization Plan

> Mục tiêu: tối ưu backend của Void Melody để nhanh hơn, giảm contention, giảm startup time, tận dụng concurrency đúng cách, dễ maintain và có đường scale rõ ràng mà không rewrite backend hiện tại.

## Target Stack

```text
FastAPI
+ Async SQLAlchemy
+ SQLite
+ Alembic
+ Tauri sidecar
+ CapCut TTS
+ VieNeu
+ FFmpeg
```

Không migrate sang microservices, Redis, Celery hay PostgreSQL ở giai đoạn desktop hiện tại.

---

# 1. Optimization Goals

```text
1. Reduce DB contention
2. Reduce write amplification
3. Improve queue throughput
4. Prevent VieNeu from blocking CapCut
5. Reduce repeated TTS work
6. Reduce FFmpeg process spawning
7. Reduce application startup time
8. Make backend boundaries easier to scale later
9. Keep desktop architecture simple
```

Ưu tiên:

```text
measure
→ optimize hot paths
→ simplify architecture
→ isolate provider execution
→ cache repeated work
→ prepare scale boundaries
```

---

# 2. Non-Goals

Không làm trong plan này:

```text
Redis
Celery
RabbitMQ
Kafka
PostgreSQL
multiple Uvicorn workers
microservices
Kubernetes
remote distributed workers
```

Không rewrite Tauri runtime, authentication, TTS provider contracts hoặc existing API nếu không cần.

Không thay Alembic bằng raw SQL migration framework.

---

# 3. Current Backend Strengths

Backend hiện tại đã có nền tảng tốt:

```text
FastAPI
Async SQLAlchemy
SQLite WAL
Alembic
durable job state
job recovery
bounded concurrency
provider circuit breaker
HTTP connection reuse
progress commit throttling
audio validation
```

Giữ SQLite baseline:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
```

---

# 4. Target Architecture

```text
                 ┌──────────────────────┐
                 │      FastAPI API     │
                 │    Control Plane     │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Repository Layer   │
                 │ SQLite / SQLAlchemy  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │     Job Scheduler    │
                 └───────┬───────┬──────┘
                         │       │
                ┌────────▼─┐  ┌──▼──────────┐
                │ CapCut   │  │   VieNeu    │
                │ I/O lane │  │ CPU/GPU lane│
                └─────┬────┘  └────┬────────┘
                      │            │
                      └─────┬──────┘
                            ▼
                 ┌──────────────────────┐
                 │    Media Pipeline    │
                 │ cache/ffmpeg/export  │
                 └──────────┬───────────┘
                            ▼
                       Audio Storage
```

Desktop vẫn có thể chạy tất cả trong một FastAPI process.

---

# 5. Target Folder Structure

```text
apps/api/app/
│
├── api/
│   └── v1/
│
├── core/
│   ├── config.py
│   ├── lifespan.py
│   ├── logging.py
│   └── security.py
│
├── db/
│   ├── engine.py
│   ├── maintenance.py
│   └── repositories/
│       ├── jobs.py
│       ├── batches.py
│       ├── scripts.py
│       └── voices.py
│
├── domain/
│   ├── tts/
│   │   ├── service.py
│   │   ├── fingerprint.py
│   │   └── types.py
│   ├── scripts/
│   └── voices/
│
├── providers/
│   ├── capcut_provider.py
│   ├── vieneu_provider.py
│   ├── registry.py
│   └── policies.py
│
├── scheduler/
│   ├── scheduler.py
│   ├── lanes.py
│   ├── cancellation.py
│   └── recovery.py
│
├── media/
│   ├── storage.py
│   ├── cache.py
│   ├── concat.py
│   ├── transcode.py
│   ├── probe.py
│   └── validation.py
│
└── models/
```

Không cần move toàn bộ code ngay ở phase đầu.

---

# Phase 0 — Measure Before Optimizing

## Goal

Biết thời gian đang nằm ở đâu trước khi tune.

## Add structured timings

Đo:

```text
queue_wait_ms
claim_ms
voice_resolution_ms
provider_ms
download_ms
cache_lookup_ms
compose_ms
transcode_ms
db_write_ms
total_ms
```

Example:

```json
{
  "jobId": "job-id",
  "provider": "vieneu",
  "queueWaitMs": 22,
  "claimMs": 4,
  "voiceResolutionMs": 3,
  "providerMs": 6250,
  "composeMs": 180,
  "transcodeMs": 410,
  "dbWriteMs": 8,
  "totalMs": 6921,
  "cacheHit": false
}
```

Không cần Prometheus cho desktop.

## Profile SQL

Chạy:

```sql
EXPLAIN QUERY PLAN
```

cho:

```text
history
batch lookup
queued jobs
script render segments
cache lookup
job recovery
```

## Baseline

Capture:

```text
cold startup
warm startup
single CapCut
10-job CapCut batch
single VieNeu
long VieNeu
history page 1
deep history page
50-item batch import
```

---

# Phase 1 — Database Quick Wins

## 1.1 Keep SQLite + WAL

Không đổi DB.

## 1.2 Add PRAGMA optimize

Create:

```text
app/db/maintenance.py
```

Run:

```sql
PRAGMA optimize;
```

sau migration hoặc lúc idle/shutdown.

## 1.3 Batch create in one transaction

Target:

```text
parse all
↓
validate all
↓
BEGIN IMMEDIATE
↓
capacity check once
↓
insert all jobs
↓
COMMIT once
↓
enqueue all IDs
```

Pseudo:

```python
await session.execute(text("BEGIN IMMEDIATE"))

current_count, current_chars = await load_batch_usage(...)

validate_batch_limits(
    current_count=current_count,
    current_chars=current_chars,
    new_items=items,
)

jobs = [build_job(...) for item in items]

session.add_all(jobs)
await session.commit()

for job in jobs:
    await scheduler.enqueue(job.id)
```

Benefits:

```text
N commits → 1 commit
N aggregate checks → 1 check
less writer contention
atomic creation
```

## 1.4 Replace OFFSET pagination

Target cursor pagination:

```http
GET /tts/jobs?limit=30
```

Response:

```json
{
  "items": [],
  "nextCursor": "..."
}
```

Query:

```sql
WHERE
  created_at < :created_at
  OR (
    created_at = :created_at
    AND id < :id
  )
ORDER BY created_at DESC, id DESC
LIMIT 31;
```

Không count toàn bộ rows mỗi request nếu UI không thật sự cần.

## 1.5 Workload indexes

Candidate:

```sql
CREATE INDEX ix_tts_jobs_status_created_id
ON tts_jobs(status, created_at DESC, id);
```

Candidate:

```sql
CREATE INDEX ix_tts_jobs_batch_position
ON tts_jobs(batch_id, batch_position);
```

Candidate:

```sql
CREATE INDEX ix_script_segments_render_ordinal
ON script_render_segments(render_id, ordinal);
```

Candidate:

```sql
CREATE INDEX ix_script_segments_render_status
ON script_render_segments(render_id, status);
```

Chỉ add index sau khi kiểm tra query plan.

## 1.6 Partial indexes

Candidate:

```sql
CREATE INDEX ix_tts_jobs_active_created
ON tts_jobs(created_at)
WHERE status IN ('queued', 'processing');
```

hoặc:

```sql
CREATE INDEX ix_tts_jobs_queued_created
ON tts_jobs(created_at)
WHERE status = 'queued';
```

## 1.7 Keep Alembic

Target:

```text
SQLAlchemy models
↓
Alembic
↓
SQLite
```

Long-term simplify startup migration về:

```text
backup if needed
↓
alembic upgrade head
↓
PRAGMA optimize
```

---

# Phase 2 — Provider-Aware Scheduler

## Goal

Không để VieNeu block CapCut.

## Problem

Nếu global workers cùng lấy VieNeu jobs nhưng VieNeu chỉ inference concurrency 1:

```text
worker 1 → VieNeu running
worker 2 → VieNeu waiting
worker 3 → VieNeu waiting

CapCut behind queue
→ blocked
```

## Target

Create:

```text
app/scheduler/
├── scheduler.py
├── lanes.py
├── policies.py
└── cancellation.py
```

Architecture:

```text
Scheduler
│
├── CapCut lane
│   ├── worker
│   ├── worker
│   └── worker
│
├── VieNeu lane
│   └── worker
│
└── Script lane
    └── worker
```

## Provider execution policy

```python
@dataclass(frozen=True)
class ProviderExecutionPolicy:
    job_concurrency: int
    chunk_concurrency: int
    cache_enabled: bool
```

Initial:

```text
CapCut:
  job_concurrency = 3
  chunk_concurrency = 2

VieNeu:
  job_concurrency = 1
  chunk_concurrency = 1
```

Config:

```text
CAPCUT_JOB_CONCURRENCY
CAPCUT_CHUNK_CONCURRENCY
VIENEU_JOB_CONCURRENCY
VIENEU_CHUNK_CONCURRENCY
```

Target API:

```python
await scheduler.enqueue(job_id)
await scheduler.cancel(job_id)
await scheduler.retry(job_id)
scheduler.health_snapshot()
```

---

# Phase 3 — Generic Audio Segment Cache

## Goal

Avoid repeated provider synthesis.

Create:

```text
audio_segment_cache
```

Suggested fields:

```text
fingerprint PK
provider_id
provider_version
voice_key
voice_revision
text_hash
style
rate
audio_path
mime_type
audio_duration
file_size
created_at
last_used_at
```

Fingerprint must include:

```text
provider_id
provider_version
model_version
text
voice
voice_revision
resource_id
style
rate
synthesis_options
```

Flow:

```text
chunk
↓
fingerprint
↓
cache lookup
├── hit → reuse
└── miss
    ↓
    provider synthesize
    ↓
    validate
    ↓
    cache write
```

Cache cleanup:

```text
LRU / last_used_at
disk pressure
optional retention
```

Không xóa cache aggressively.

---

# Phase 4 — Voice Resolution Cache

## Goal

Không query custom voice DB per chunk.

Target:

```text
1 custom voice lookup / job
```

Extend job snapshot:

```python
@dataclass(frozen=True)
class JobSnapshot:
    id: str
    provider_id: str
    voice_type: str
    resource_id: str | None
    resolved_voice_id: str | None
    reference_audio: str | None
    prompt_text: str | None
    voice_revision: str | None
    rate: float
    style: str | None
```

Optional small LRU:

```text
custom_voice_id
→ resolved metadata
```

Invalidate on update/delete/recreate.

---

# Phase 5 — Cancellation Registry

## Goal

Giảm DB refresh theo chunk.

Create:

```text
scheduler/cancellation.py
```

In-memory:

```text
job_id → asyncio.Event
```

Cancel:

```text
DB cancel_requested=true
+
event.set()
```

Worker:

```text
check event continuously
+
periodic DB check every 0.5–2s
```

---

# Phase 6 — Central Media Pipeline

## Goal

Centralize FFmpeg/audio operations.

Create:

```text
app/media/
├── storage.py
├── validation.py
├── probe.py
├── concat.py
├── transcode.py
└── export.py
```

API:

```python
await media.concat(...)
await media.transcode(...)
await media.export(...)
await media.probe(...)
```

Codec policy:

```text
mp3 → mp3
wav → pcm_s16le
m4a → aac
```

Temp file policy:

```text
temporary
↓
validate
↓
atomic rename
```

Add optional:

```text
MEDIA_FFMPEG_CONCURRENCY=2
```

để không saturate laptop CPU.

---

# Phase 7 — Optimize VieNeu Media Path

## Goal

Giảm FFmpeg spawn per chunk.

Current-like pattern:

```text
infer chunk
↓
save WAV
↓
FFmpeg encode MP3
↓
repeat N times
↓
final concat
```

Target one-off path:

```text
infer chunks
↓
keep PCM/WAV intermediates
↓
compose
↓
ONE final encode
```

Cache-aware path:

```text
cacheable segment
↓
encode immutable segment once
↓
reuse on next render
```

Media pipeline chọn strategy, provider không tự quyết final export.

---

# Phase 8 — Async Disk I/O Cleanup

Audit:

```text
open(..., "wb")
shutil.copy2
shutil.move
zipfile
large file reads
large file writes
```

Move large blocking operations to:

```python
await asyncio.to_thread(...)
```

Ưu tiên:

```text
large copy
export
ZIP creation
disk scans
cleanup
```

Không cần wrap mọi filesystem call nhỏ.

---

# Phase 9 — Startup Optimization

## Goal

API usable nhanh hơn.

Critical path:

```text
logging
security
database migration
job recovery
scheduler start
API ready
```

Background:

```text
VieNeu model preparation
model warmup
orphan cleanup
raw response cleanup
cache cleanup
PRAGMA optimize
```

Provider states:

```text
cold
warming
ready
unavailable
```

Health example:

```json
{
  "providers": {
    "capcut": "ready",
    "vieneu": "warming"
  }
}
```

VieNeu có thể lazy-load hoặc background warmup.

---

# Phase 10 — Unify Queue Infrastructure

Không merge DB tables ngay.

Keep:

```text
tts_jobs
script_renders
script_render_segments
```

Share infrastructure:

```text
enqueue
cancel
retry
recovery
priority
health
shutdown
metrics
```

Architecture:

```text
Scheduler
│
├── TTSExecutor
└── ScriptRenderExecutor
```

---

# Phase 11 — Repository Layer

Create:

```text
db/repositories/jobs.py
db/repositories/batches.py
db/repositories/scripts.py
db/repositories/voices.py
```

API handler:

```text
validate
↓
service
↓
repository
↓
response
```

Example:

```python
class JobRepository:
    async def get(self, job_id: str): ...
    async def create_many(self, jobs): ...
    async def list_cursor(self, cursor, limit): ...
    async def claim(self, job_id): ...
    async def mark_completed(self, ...): ...
```

Mục tiêu:

```text
clear transaction boundaries
easier query profiling
future DB adapter
```

---

# Phase 12 — SQLite Maintenance

Add:

```text
PRAGMA optimize
WAL size monitoring
cleanup policies
```

Không chạy `VACUUM` thường xuyên.

Chỉ manual/rare maintenance khi cần.

Retention có thể áp dụng cho:

```text
raw responses
temp audio
cache
failed artifacts
```

Không tự xóa history nếu user chưa cấu hình.

---

# Phase 13 — Configuration Cleanup

Replace:

```text
tts_queue_concurrency
tts_chunk_concurrency
```

with:

```text
CAPCUT_JOB_CONCURRENCY=3
CAPCUT_CHUNK_CONCURRENCY=2

VIENEU_JOB_CONCURRENCY=1
VIENEU_CHUNK_CONCURRENCY=1

MEDIA_FFMPEG_CONCURRENCY=2

TTS_PROGRESS_COMMIT_INTERVAL_SECONDS=1
TTS_PROGRESS_COMMIT_STEP_PERCENT=5
```

---

# Phase 14 — Scale-Ready Boundaries

Current:

```text
SQLite
in-process scheduler
local filesystem
same-process providers
```

Future adapters:

```text
PostgreSQL
distributed scheduler
object storage
remote/GPU workers
```

Domain layer không nên phụ thuộc trực tiếp vào concrete adapters.

---

# 15. Do Not Scale Desktop with Multiple Uvicorn Workers

Keep:

```text
1 FastAPI process
```

Không dùng:

```text
uvicorn --workers 4
```

vì sẽ duplicate:

```text
queues
memory
VieNeu model
runtime state
```

---

# 16. Optional Future — Separate VieNeu Process

Chỉ làm nếu profiling justify.

```text
Tauri
↓
FastAPI sidecar
↓
local IPC
↓
VieNeu inference process
```

Benefits:

```text
API responsive
model crash isolation
independent restart
future remote worker path
```

---

# 17. Priority Order

Highest value first:

```text
1. Batch creation in one transaction
2. Provider-aware scheduler
3. Generic segment cache
4. Cursor history pagination
5. Composite / partial indexes
6. Lazy/background VieNeu startup
7. Voice resolution once per job
8. Cancellation registry
9. Central media pipeline
10. Reduce VieNeu FFmpeg spawns
```

---

# 18. Recommended Phase Order

| Phase | Scope | Impact |
|---|---|---|
| 0 | profiling + SQL plans | foundation |
| 1 | DB batch/history/indexes | high / low risk |
| 2 | provider scheduler | very high |
| 3 | generic audio cache | very high |
| 4 | voice/cancel optimizations | medium-high |
| 5 | media abstraction | high |
| 6 | VieNeu media optimization | high |
| 7 | startup optimization | high UX |
| 8 | shared scheduler infrastructure | maintainability |
| 9 | repository layer | scalability |
| 10 | cleanup + maintenance | long-term |

---

# 19. Recommended Commit Sequence

```text
perf(api): add backend performance instrumentation
```

```text
perf(db): batch job creation into single transaction
```

```text
perf(db): add cursor history pagination and workload indexes
```

```text
refactor(queue): add provider-aware scheduler
```

```text
perf(tts): add fingerprint-based audio segment cache
```

```text
perf(vieneu): resolve custom voice once per job
```

```text
perf(queue): add in-memory cancellation registry
```

```text
refactor(media): centralize ffmpeg and audio operations
```

```text
perf(vieneu): reduce per-chunk ffmpeg encoding
```

```text
perf(api): move non-critical startup work to background
```

```text
refactor(api): unify job scheduler infrastructure
```

```text
refactor(db): introduce repository boundaries
```

```text
chore(db): add sqlite maintenance and optimization
```

---

# 20. Validation Strategy

Không cần viết test suite mới sớm.

Ưu tiên:

```text
1. API starts
2. current endpoints work
3. CapCut TTS works
4. VieNeu TTS works
5. mixed provider queue works
6. batch works
7. cache works
8. history works
9. existing tests
10. desktop sidecar
```

---

# 21. Performance Benchmarks

Before/after:

```text
cold startup
warm startup

CapCut single
CapCut 10-job batch

VieNeu short
VieNeu long

mixed:
3 VieNeu + 3 CapCut

50-item import

history:
100 rows
10k rows
100k rows

same script:
first render
second render
```

Track:

```text
P50
P95
total duration
DB transaction count
provider calls
FFmpeg process count
cache hit ratio
```

---

# 22. Expected Improvements

## Batch

```text
N transactions
→
1 transaction
```

## Provider scheduler

```text
CapCut no longer waits behind blocked VieNeu workers
```

## Cache

Repeated synthesis:

```text
provider call
→
cache hit
```

## VieNeu media

```text
N+1 FFmpeg processes
→
~1 final encode for one-off output
```

## Startup

```text
API/UI ready
before
VieNeu warmup completes
```

---

# 23. Definition of Done

```text
SQLite stable under mixed workload

batch create uses one transaction

history uses cursor pagination

hot queries use deliberate indexes

CapCut and VieNeu have independent execution lanes

VieNeu cannot occupy all CapCut workers

generic audio cache exists

custom voice resolution is not repeated per chunk

cancellation does not query DB every chunk

FFmpeg operations are centralized

VieNeu avoids unnecessary encoders

API starts before non-critical model/maintenance work

queue infrastructure has clear abstractions

DB access has clean repository boundaries

existing desktop behavior remains intact
```

---

# 24. Final Target

Desktop:

```text
Tauri
↓
FastAPI
↓
SQLite WAL
↓
Provider-aware scheduler
├── CapCut lane
├── VieNeu lane
└── Script lane
↓
Fingerprint cache
↓
Media pipeline
↓
Local storage
```

Future:

```text
FastAPI replicas
↓
PostgreSQL
↓
distributed scheduler
↓
TTS workers
↓
object storage
```

Domain code should remain mostly unchanged.

---

# 25. Coding Agent Prompt

```text
Read `VOID_MELODY_BACKEND_OPTIMIZATION_PLAN.md` completely before making changes.

Your task is to execute this backend optimization plan from beginning to end.

Core rules:

1. Treat the current repository as the source of truth.
2. Use this plan as the architectural and performance target.
3. Work phase-by-phase in the order described.
4. Do not introduce Redis, Celery, PostgreSQL, RabbitMQ, Kafka, microservices, or multiple Uvicorn workers.
5. Keep SQLite + WAL + SQLAlchemy + Alembic for the desktop app.
6. Preserve existing API contracts unless a change is explicitly required.
7. Preserve Tauri integration, auth, CapCut, VieNeu, FFmpeg, queue recovery, and user-facing behavior.
8. Do not optimize blindly: inspect current code and measure/query-plan first where practical.
9. Do not add indexes without checking the query patterns they serve.
10. Do not rewrite working provider logic unnecessarily.
11. Prefer moving shared infrastructure over copying logic.
12. Keep each phase reviewable.
13. Existing tests can be used for regression validation.
14. Do not write large new test suites early unless needed to verify a risky behavior.
15. Continue through the full plan unless blocked by a genuine technical issue.

Start with Phase 0.

Audit and instrument:
- FastAPI lifespan
- SQLite engine
- SQLAlchemy queries
- job creation
- batch creation
- history listing
- queue manager
- VieNeu provider
- CapCut provider
- chunk executor
- script render queue
- media/FFmpeg operations

Then implement all phases in sequence.

Critical priorities:
- batch insert transaction reduction
- provider-aware scheduler
- generic audio segment cache
- cursor pagination
- workload/partial indexes
- VieNeu startup warmup
- voice resolution reuse
- cancellation registry
- central media pipeline
- VieNeu FFmpeg reduction

At the end report:

## Completed phases
## Architecture changes
## Database changes
## Scheduler changes
## Cache changes
## Media changes
## Startup changes
## Performance comparison
## Validation
## Remaining technical debt

Validation statuses:
- API startup
- DB migration
- CapCut TTS
- VieNeu TTS
- mixed provider queue
- batch import
- history
- cache
- desktop sidecar
- existing tests

Mark each PASS / FAIL / NOT RUN.

Do not stop after the first phase unless a real blocker prevents continued implementation.
```
