# OmniVoice Provider Boundary Design

## Scope

Phase 1 establishes OmniVoice as an isolated scheduler target. It does not expose Voice Design APIs, create OmniVoice voices, instantiate the ML runtime, or change VieNeu enrollment semantics.

Deliverables:

- OmniVoice execution settings: one job, one chunk, 180-second inference timeout.
- An `omnivoice` execution policy and queue lane.
- Provider affinity across enqueue, delayed retry, recovery, and batch jobs.
- Fail-closed routing for unsupported or unavailable providers. No fallback to CapCut or VieNeu.
- Regression coverage for existing CapCut and VieNeu lanes.

## Architecture

The existing `ExecutionLane` abstraction remains unchanged. `TTSQueueManager` and `UnifiedScheduler` gain an `omnivoice` lane using the same generic lane implementation as CapCut and VieNeu.

The queue provider registry remains dependency-injectable. Phase 1 does not create `OmniVoiceProvider`; later provider work supplies it. Lane availability and provider implementation availability are separate checks:

- A known provider ID selects only its matching lane.
- A missing lane raises a stable routing error before enqueue.
- A missing provider implementation fails the job explicitly inside the worker; it never selects another provider.

No OmniVoice branch is added to `CloneOrchestrator`, `VieneuEnrollmentService`, `VieneuProvider`, or `voice_resolver.py`.

## Data Flow

Normal enqueue:

```text
tts_jobs.provider_id=omnivoice
    -> queue_manager.enqueue(provider_id="omnivoice")
    -> omnivoice ExecutionLane
    -> generic worker executor
```

Automatic retry passes the persisted `job.provider_id` to `enqueue_after`. Manual retry copies `provider_id` into the replacement row. Startup recovery returns `RecoveredJob.provider_id`; startup enqueue uses that value. Batch creation stores and enqueues each item's provider ID.

## Error Handling

Routing rejects unknown provider IDs and configured provider IDs without a matching lane. This replaces the current silent CapCut fallback. Legacy callers that omit `provider_id` retain the existing CapCut default.

The scheduler change does not probe or start OmniVoice. Runtime/model readiness belongs to later phases. Consequently, Phase 1 tests use injected providers and lane inspection; they require no OmniVoice package, model, CUDA, or worker process.

## Testing

TDD coverage will prove:

- Default policies include OmniVoice concurrency `1/1`.
- OmniVoice enqueue enters only the OmniVoice lane.
- Delayed retry remains in the OmniVoice lane.
- Unknown providers fail closed.
- Recovery preserves `provider_id="omnivoice"`.
- Batch rows preserve their provider discriminator.
- Existing CapCut/VieNeu lane isolation and queue tests still pass.

Focused scheduler tests run first. Provider registry, recovery, endpoint retry, worker, OmniVoice runtime/worker, and VieNeu provider/clone regressions run before Phase 1 is declared complete.

## Deferred Work

Runtime Manager support, model lifecycle, `OmniVoiceProvider`, database schema, resolver, preview/commit services, APIs, UI, Voice Library, and Audio Studio integration remain separate dependency-ordered phases. This keeps Phase 1 testable without introducing unreachable production behavior.
