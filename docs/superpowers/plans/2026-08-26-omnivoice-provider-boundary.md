# OmniVoice Provider Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route every `provider_id=omnivoice` TTS job through an isolated OmniVoice lane without allowing CapCut or VieNeu fallback.

**Architecture:** Reuse `ExecutionLane`. Add OmniVoice settings/policy/lane wiring, make lane lookup fail closed, then make worker provider lookup fail explicitly when no matching implementation exists. Persisted job provider IDs remain authoritative for retry, recovery, and batch paths.

**Tech Stack:** Python 3.10+, asyncio, SQLAlchemy 2, pytest, pytest-asyncio.

## Global Constraints

- Stable provider ID: `omnivoice`.
- Job concurrency: `1`; chunk concurrency: `1`; inference timeout: `180` seconds.
- No OmniVoice changes in `CloneOrchestrator`, `VieneuEnrollmentService`, `VieneuProvider`, or `voice_resolver.py`.
- No ML dependencies or weights added to core.
- Explicit missing/unknown providers fail closed. Omitted `provider_id` retains the CapCut default.

---

## File Map

- `apps/api/app/config.py`: OmniVoice execution defaults.
- `apps/api/app/scheduler/policies.py`: policy plus stable routing error/helper.
- `apps/api/app/scheduler/scheduler.py`: OmniVoice lane in `UnifiedScheduler`.
- `apps/api/app/workers/queue_manager.py`: OmniVoice lane in the active manager.
- `apps/api/app/workers/tts_worker.py`: fail on missing provider implementation.
- `apps/api/tests/test_queue_manager.py`: queue/lane routing.
- `apps/api/tests/test_backend_optimizations.py`: scheduler isolation and batch affinity.
- `apps/api/tests/test_job_recovery.py`: recovery affinity.
- `apps/api/tests/test_tts_worker.py`: no provider fallback.

### Task 1: Fail-Closed Lane Selection

**Files:**

- Modify: `apps/api/app/scheduler/policies.py`
- Modify: `apps/api/app/scheduler/scheduler.py`
- Modify: `apps/api/app/workers/queue_manager.py`
- Test: `apps/api/tests/test_queue_manager.py`

**Interfaces:**

- Produces: `ProviderRoutingError(code: str, message: str)`.
- Produces: `select_execution_lane(lanes: Mapping[str, T], provider_id: str | None) -> T`.
- Contract: `None` selects `capcut`; explicit missing IDs raise `PROVIDER_LANE_NOT_CONFIGURED`.

- [ ] **Step 1: Write failing routing tests**

```python
from app.scheduler.policies import ProviderRoutingError


@pytest.mark.asyncio
async def test_explicit_unknown_provider_does_not_fall_back_to_capcut():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True

    with pytest.raises(ProviderRoutingError) as exc_info:
        await manager.enqueue("job-unknown", provider_id="unknown")

    assert exc_info.value.code == "PROVIDER_LANE_NOT_CONFIGURED"
    assert manager.queue.empty()


@pytest.mark.asyncio
async def test_omitted_provider_keeps_capcut_default():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True

    assert await manager.enqueue("job-default") is True
    _, _, job_id = await manager.queue.get()
    assert job_id == "job-default"
    manager.queue.task_done()
```

- [ ] **Step 2: Verify RED**

Run: `uv run --project apps/api pytest apps/api/tests/test_queue_manager.py -q`

Expected: unknown provider enters CapCut instead of raising.

- [ ] **Step 3: Implement the minimal routing primitive**

```python
T = TypeVar("T")


class ProviderRoutingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def select_execution_lane(lanes: Mapping[str, T], provider_id: str | None) -> T:
    lane_id = "capcut" if provider_id is None else provider_id
    try:
        return lanes[lane_id]
    except KeyError as exc:
        raise ProviderRoutingError(
            "PROVIDER_LANE_NOT_CONFIGURED",
            f"No execution lane configured for provider '{lane_id}'.",
        ) from exc
```

Use it in `enqueue` and `enqueue_after` in both scheduler classes. Preserve `UnifiedScheduler.enqueue` database lookup.

- [ ] **Step 4: Verify GREEN**

Run: `uv run --project apps/api pytest apps/api/tests/test_queue_manager.py -q`

Expected: zero failures.

- [ ] **Step 5: Commit**

```powershell
git add apps/api/app/scheduler/policies.py apps/api/app/scheduler/scheduler.py apps/api/app/workers/queue_manager.py apps/api/tests/test_queue_manager.py
git commit -m "fix: fail closed on missing provider lanes"
```

### Task 2: OmniVoice Execution Policy and Lane

**Files:**

- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/scheduler/policies.py`
- Modify: `apps/api/app/scheduler/scheduler.py`
- Modify: `apps/api/app/workers/queue_manager.py`
- Test: `apps/api/tests/test_queue_manager.py`
- Test: `apps/api/tests/test_backend_optimizations.py`

**Interfaces:**

- Consumes: `select_execution_lane(...)`.
- Produces settings: `omnivoice_job_concurrency`, `omnivoice_chunk_concurrency`, `omnivoice_inference_timeout_seconds`.
- Produces: default OmniVoice policy and `lanes["omnivoice"]` in both default schedulers.

- [ ] **Step 1: Write failing lane tests**

```python
@pytest.mark.asyncio
async def test_omnivoice_enqueue_uses_only_omnivoice_lane():
    manager = TTSQueueManager(provider_registry={"capcut": object()})
    manager.accepting_jobs = True

    assert await manager.enqueue("job-omni", provider_id="omnivoice") is True
    assert manager.lanes["omnivoice"].queue.qsize() == 1
    assert manager.lanes["capcut"].queue.empty()
    assert manager.lanes["vieneu"].queue.empty()


@pytest.mark.asyncio
async def test_omnivoice_delayed_retry_stays_in_omnivoice_lane():
    manager = TTSQueueManager(provider_registry={"capcut": object()})
    manager.accepting_jobs = True

    await manager.enqueue_after(
        "job-omni-retry", delay_seconds=0, provider_id="omnivoice"
    )
    await asyncio.sleep(0)

    assert manager.lanes["omnivoice"].queue.qsize() == 1
    assert manager.lanes["capcut"].queue.empty()
```

Extend `test_scheduler_lane_isolation` with a blocked OmniVoice job; assert CapCut/VieNeu work independently.

- [ ] **Step 2: Verify RED**

Run: `uv run --project apps/api pytest apps/api/tests/test_queue_manager.py apps/api/tests/test_backend_optimizations.py::test_scheduler_lane_isolation -q`

Expected: OmniVoice lane missing.

- [ ] **Step 3: Add settings, policy, and lanes**

```python
omnivoice_job_concurrency: int = 1
omnivoice_chunk_concurrency: int = 1
omnivoice_inference_timeout_seconds: float = 180.0
```

Add the policy entry. Add an OmniVoice `ExecutionLane` to default multi-lane construction in both schedulers. Preserve `TTSQueueManager(concurrency=N)` as CapCut-only compatibility mode.

- [ ] **Step 4: Verify GREEN**

Run: `uv run --project apps/api pytest apps/api/tests/test_queue_manager.py apps/api/tests/test_backend_optimizations.py::test_scheduler_lane_isolation -q`

Expected: zero failures.

- [ ] **Step 5: Commit**

```powershell
git add apps/api/app/config.py apps/api/app/scheduler/policies.py apps/api/app/scheduler/scheduler.py apps/api/app/workers/queue_manager.py apps/api/tests/test_queue_manager.py apps/api/tests/test_backend_optimizations.py
git commit -m "feat: add omnivoice scheduler lane"
```

### Task 3: Provider Implementation and Persisted Affinity

**Files:**

- Modify: `apps/api/app/workers/tts_worker.py`
- Modify: `apps/api/tests/test_tts_worker.py`
- Modify: `apps/api/tests/test_job_recovery.py`
- Modify: `apps/api/tests/test_backend_optimizations.py`

**Interfaces:**

- Contract: worker uses only `provider_registry[job.provider_id]`.
- Error: missing implementation persists non-retryable `PROVIDER_NOT_CONFIGURED`.
- CapCut construction is allowed only when `provider_registry is None` and the persisted provider is `capcut`.
- Existing recovery and batch APIs stay unchanged; tests lock OmniVoice affinity.

- [ ] **Step 1: Write failing worker test**

```python
@pytest.mark.asyncio
async def test_omnivoice_job_never_falls_back_to_capcut(
    async_session_factory, monkeypatch
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="omni-no-fallback",
            voice_type="omni-voice",
            voice_display_name="Omni voice",
            language_code="vi-VN",
            provider_id="omnivoice",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    capcut = MagicMock(side_effect=AssertionError("CapCut fallback used"))
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr("app.workers.tts_worker.CapCutProvider", capcut)

    await execute_tts_job_step(job_id, provider_registry={})

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded.status == "failed"
        assert reloaded.error_code == "PROVIDER_NOT_CONFIGURED"
    capcut.assert_not_called()
```

Add a recovery row with `provider_id="omnivoice"`; assert the returned item's literal provider ID. Expand the batch test to create CapCut, VieNeu, OmniVoice rows; assert all three literal IDs.

- [ ] **Step 2: Verify RED**

Run: `uv run --project apps/api pytest apps/api/tests/test_tts_worker.py::test_omnivoice_job_never_falls_back_to_capcut apps/api/tests/test_job_recovery.py apps/api/tests/test_backend_optimizations.py::test_single_transaction_batch_creation -q`

Expected: CapCut constructor invoked for OmniVoice.

- [ ] **Step 3: Reject missing implementations**

Resolve the provider inside the worker's caught failure path:

```python
active_provider = (
    CapCutProvider(catalog_path=settings.capcut_catalog_path)
    if provider_registry is None and job.provider_id == "capcut"
    else (provider_registry or {}).get(job.provider_id)
)
if active_provider is None:
    raise TTSJobError(
        code="PROVIDER_NOT_CONFIGURED",
        message=f"Provider '{job.provider_id}' is not configured.",
        retryable=False,
    )
```

Do not add provider-specific synthesis branches.

- [ ] **Step 4: Verify GREEN**

Run: `uv run --project apps/api pytest apps/api/tests/test_tts_worker.py::test_omnivoice_job_never_falls_back_to_capcut apps/api/tests/test_job_recovery.py apps/api/tests/test_backend_optimizations.py::test_single_transaction_batch_creation -q`

Expected: zero failures.

- [ ] **Step 5: Run Phase 1 regression suite**

```powershell
uv run --project apps/api pytest apps/api/tests/test_provider_registry.py apps/api/tests/test_queue_manager.py apps/api/tests/test_backend_optimizations.py apps/api/tests/test_job_recovery.py apps/api/tests/test_endpoints.py apps/api/tests/test_tts_worker.py apps/api/tests/test_omnivoice_runtime.py apps/api/tests/test_omnivoice_worker_unit.py apps/api/tests/test_vieneu_provider.py apps/api/tests/test_clone_orchestrator.py apps/api/tests/test_voice_cloning.py apps/api/tests/test_custom_voice_jobs.py -q
```

Expected: zero failures.

- [ ] **Step 6: Check scope and diff**

```powershell
git diff --check
git status --short
git diff -- apps/api/app apps/api/tests
```

Confirm no protected VieNeu files changed; no ML dependencies added.

- [ ] **Step 7: Commit**

```powershell
git add apps/api/app/workers/tts_worker.py apps/api/tests/test_tts_worker.py apps/api/tests/test_job_recovery.py apps/api/tests/test_backend_optimizations.py
git commit -m "fix: preserve provider affinity in tts execution"
```

## Completion Gate

- OmniVoice enqueue/retry use only `lanes["omnivoice"]`.
- Unknown providers raise `PROVIDER_LANE_NOT_CONFIGURED`.
- Missing OmniVoice implementation yields `PROVIDER_NOT_CONFIGURED`; CapCut remains untouched.
- Recovery/batch persistence retain `provider_id="omnivoice"`.
- Selected scheduler, runtime, worker, and VieNeu regression tests pass.
- `git diff --check` exits zero.
