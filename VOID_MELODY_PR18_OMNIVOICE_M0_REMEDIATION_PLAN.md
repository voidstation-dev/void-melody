# VOID MELODY — PR #18 OMNIVOICE M0 REMEDIATION PLAN

## Review target

- Repository: `voidstation-dev/void-melody`
- PR: `#18`
- PR title: `feat(omnivoice): implement Milestone M0 runtime foundation (O0-O2)`
- Base: `6ae329ab8dc5ec9c3119d49f2a79553e0b2ceff4`
- Head reviewed: `7bee84320d73962e444ff21c783aa04e433a0ca9`
- Review date: 2026-08-21
- CI observed: PASS
- API CI observed: `124 passed, 1 warning`
- Web CI observed: lint/typecheck/tests/build PASS

---

# 1. Verdict

PR #18 is moving in the correct architectural direction:

- OmniVoice is not added directly to the base API dependency set.
- The design uses an out-of-process worker and JSONL stdin/stdout IPC.
- No second FastAPI server or HTTP port was introduced.
- Stable provider ID `omnivoice` was added.
- `SynthesisOptions` was added additively.
- Existing CapCut and VieNeu provider signatures remain compatible.
- Runtime-client tests cover basic handshake, timeout, crash restart, mock synthesis, and prompt creation.

However, the PR should **not** yet be considered complete for M0.

Recommended status:

```text
O0 Re-baseline           🟧 IN_REVIEW
O1 Capability contract   🟥 BLOCKED
O2 Runtime IPC           🟥 BLOCKED
M0                       🟥 NOT READY
```

Merge recommendation:

```text
DO NOT MERGE YET.
Fix this PR in place, re-review M0, then merge.
```

---

# 2. Findings

| ID | Severity | Finding |
|---|---|---|
| PR18-R01 | CRITICAL | The production worker silently behaves as a mock and can report fake model/inference success |
| PR18-R02 | CRITICAL | RPC timeout does not stop a blocking synchronous worker request, poisoning later requests |
| PR18-R03 | HIGH | Reader loops use mutable `self._process`, creating cross-generation races after restart |
| PR18-R04 | HIGH | OmniVoice capability flags describe support but there is no runtime installation/readiness truth |
| PR18-R05 | HIGH | VieNeu descriptor still exposes `vieneu_core.Capabilities`, which lacks new common fields |
| PR18-R06 | HIGH | O0 is marked DONE while the model revision still floats on `main` |
| PR18-R07 | MEDIUM/HIGH | Runtime matrix labels platforms `Supported` without real/package verification |
| PR18-R08 | MEDIUM | Worker returns Python exception class names instead of stable app error codes |
| PR18-R09 | MEDIUM | stderr task is not owned/awaited; stdout cancellation is not awaited |
| PR18-R10 | MEDIUM | Worker accepts arbitrary model/audio/output paths without allowed-root validation |
| PR18-R11 | MEDIUM | Mock synthesis accepts effectively unbounded duration and allocates inefficiently |
| PR18-R12 | LOW/MEDIUM | `validate_voice_prompt` is missing from the worker RPC vocabulary planned for the integration |

---

# 3. PR18-R01 — CRITICAL
## Production worker must never silently fall back to mock behavior

Current worker behavior effectively does:

```text
load_model
  ↓
create {"mock_model": true}
  ↓
return status=loaded
```

It does not import real OmniVoice and does not verify the model.

Current `synthesize` writes a silent WAV and returns success.

Current `create_voice_prompt` writes JSON using a `.pt` extension and returns success.

That is acceptable for tests, but not as the default worker implementation.

If O3 later performs a smoke test against this worker, it can report READY even when:

- OmniVoice is not installed;
- the model was never downloaded;
- torch initialization is broken;
- the model path is wrong;
- inference is broken.

This violates the core invariant:

```text
READY = real runtime actually verified
```

## Required fix

Make worker mode explicit.

Production default:

```text
REAL
```

Tests only:

```text
MOCK
```

Suggested:

```text
python worker.py                  # REAL
python worker.py --mock           # MOCK
```

or an explicit environment variable used only by tests.

Recommended backend split:

```text
apps/omnivoice-worker/
├── worker.py
├── real_backend.py
└── mock_backend.py
```

Suggested contract:

```python
class OmniBackend(Protocol):
    def runtime_info(...)
    def load_model(...)
    def unload_model(...)
    def synthesize(...)
    def create_voice_prompt(...)
    def validate_voice_prompt(...)
```

Real mode must fail clearly when OmniVoice is absent:

```text
OMNI_PACKAGE_NOT_INSTALLED
```

Real mode must fail when model is absent:

```text
OMNI_MODEL_NOT_INSTALLED
```

Mock mode must be opt-in.

## Required tests

```text
test_real_worker_does_not_fallback_to_mock
test_mock_worker_requires_explicit_mode
test_real_worker_missing_package_fails
test_real_worker_missing_model_fails
```

---

# 4. PR18-R02 — CRITICAL
## Timeout must invalidate and restart the worker

Current client timeout behavior:

```text
wait_for(future)
  ↓
timeout
  ↓
remove pending future
  ↓
raise OMNI_RUNTIME_TIMEOUT
```

But the worker is synchronous.

If real inference is still executing, the worker cannot read the next request.

So:

```text
request A hangs
  ↓
parent times out
  ↓
A continues inside worker
  ↓
request B sent
  ↓
worker still busy with A
  ↓
B times out too
```

The worker is poisoned until the original inference returns.

## Required initial policy

For V1:

```text
RPC timeout
  ↓
mark current worker generation unhealthy
  ↓
terminate worker
  ↓
bounded wait
  ↓
kill if needed
  ↓
fail same-generation pending requests
  ↓
next request creates a fresh worker
```

Do not rely on graceful shutdown first when the worker is blocked in inference, because it cannot read the shutdown RPC.

## Required test

```text
worker mock method blocks for 1s
client timeout = 20ms
  ↓
OMNI_RUNTIME_TIMEOUT
  ↓
old PID terminated
  ↓
next ping
  ↓
new PID
  ↓
pong succeeds
```

The current timeout test checks only the error code and is insufficient.

---

# 5. PR18-R03 — HIGH
## Runtime reader tasks must be bound to a process generation

Current reader loops repeatedly dereference:

```python
self._process.stdout
self._process.stderr
```

`self._process` can be replaced after a restart.

Race:

```text
worker A crashes
  ↓
worker B starts
  ↓
self._process = B
  ↓
old reader task for A is still unwinding
```

Possible outcomes:

- old task starts reading worker B output;
- two tasks read the same stream;
- old task calls `_cancel_all_pending()`;
- new worker B requests get cancelled by old worker A cleanup.

## Required fix

Bind every task to an immutable process generation.

Example:

```python
generation = uuid.uuid4().hex
process = await asyncio.create_subprocess_exec(...)

self._generation = generation
self._process = process

stdout_task = asyncio.create_task(
    self._stdout_reader_loop(process, generation)
)
stderr_task = asyncio.create_task(
    self._stderr_reader_loop(process, generation)
)
```

Pending requests should track generation.

Old-generation cleanup may only fail old-generation pending RPCs.

## Required test

```text
start A
create pending request
kill A
immediately start B
create request B
allow A reader cleanup to run
assert request B still succeeds
```

---

# 6. PR18-R04 — HIGH
## Separate provider feature support from runtime readiness

The OmniVoice registry descriptor currently advertises:

```text
supports_voice_cloning = true
supports_multilingual = true
supports_voice_design = true
supports_target_duration = true
```

Those are valid **static provider features**.

They are not proof that the current machine can run the provider.

The system also needs:

```text
installed?
available?
model installed?
runtime smoke passed?
reason?
```

## Required contract

Keep:

```python
ProviderDescriptor
    id
    label
    version
    capabilities
```

Add a separate runtime status:

```python
ProviderRuntimeStatus
    provider_id
    installed
    available
    model_installed
    model_loaded
    status
    reason_code
    reason
```

Example before O3:

```json
{
  "provider_id": "omnivoice",
  "installed": false,
  "available": false,
  "model_installed": false,
  "model_loaded": false,
  "status": "not_installed",
  "reason_code": "OMNI_RUNTIME_NOT_INSTALLED"
}
```

This allows UI to correctly show:

```text
OmniVoice
Capabilities: multilingual, clone, design
Runtime: Not installed
```

Do not fake readiness.

---

# 7. PR18-R05 — HIGH
## Normalize capability type for every provider

PR #18 extends the app-level `Capabilities` class with:

```text
supports_multilingual
supports_voice_design
supports_target_duration
supports_text_normalization
supports_cross_lingual_clone
languages
```

But `_vieneu_descriptor()` still passes the `Capabilities` instance from `vieneu_core`.

That class does not contain the new fields.

Future common code can therefore fail:

```python
descriptor.capabilities.supports_multilingual
```

on VieNeu.

## Required fix

Every app registry descriptor should use:

```text
app.providers.registry.Capabilities
```

Normalize VieNeu core values into the app-level type.

Example:

```python
def _vieneu_descriptor():
    core = vieneu_default_descriptor()

    return ProviderDescriptor(
        id=core.id,
        label=core.label,
        version=core.version,
        capabilities=Capabilities(
            supports_preset_voices=core.capabilities.supports_preset_voices,
            supports_voice_cloning=core.capabilities.supports_voice_cloning,
            supports_streaming=core.capabilities.supports_streaming,
            supports_styles=core.capabilities.supports_styles,
            supports_batch=core.capabilities.supports_batch,
            supports_emotion_tags=core.capabilities.supports_emotion_tags,
            supports_multilingual=False,
            supports_voice_design=False,
            supports_target_duration=False,
            supports_text_normalization=False,
            supports_cross_lingual_clone=False,
            max_text_chars=core.capabilities.max_text_chars,
            sample_rate=core.capabilities.sample_rate,
            languages=("vi-VN", "en-US"),
        ),
    )
```

## Required tests

For every provider:

```python
assert isinstance(descriptor.capabilities, Capabilities)
```

and validate the complete common field set.

---

# 8. PR18-R06 — HIGH
## O0 cannot be DONE while model revision is floating

Current baseline report states:

```text
Model Revision: main
```

and says exact commit will be pinned during packaging.

But the master plan still says the exact model revision is to be resolved during O0.

The tracker marks:

```text
O0 = DONE
```

These conflict.

## Required fix

Preferred:

Resolve the exact Hugging Face model commit SHA now.

Record:

```text
model_repo = k2-fsa/OmniVoice
model_revision = <exact SHA>
resolved_at = 2026-08-21
```

Update:

```text
OMNIVOICE_BASELINE_REPORT.md
VOID_MELODY_OMNIVOICE_PROVIDER_SRT_EXECUTION_PLAN.md
```

Do not allow O3 to download floating `main`.

If pinning is intentionally deferred, O0 must not be DONE.

---

# 9. PR18-R07 — MEDIUM/HIGH
## Runtime matrix must distinguish target from verified support

Current runtime matrix labels several configurations:

```text
Supported
```

but PR #18 currently has source-level CI on Ubuntu using a mock worker.

Change the matrix to separate:

```text
Target
Contract Tested
Real Runtime Tested
Packaged Tested
```

Example:

| Platform | Target | Contract | Real OmniVoice | Packaged |
|---|---:|---:|---:|---:|
| Linux x64 CPU | Yes | PASS | NOT RUN | NOT RUN |
| Windows x64 CPU | Yes | NOT RUN | NOT RUN | NOT RUN |
| Windows x64 CUDA | Yes | NOT RUN | NOT RUN | NOT RUN |
| macOS arm64 MPS | Yes | NOT RUN | NOT RUN | NOT RUN |
| macOS x64 CPU | Optional | NOT RUN | NOT RUN | NOT RUN |

Only call a platform `Supported` after its appropriate release verification.

---

# 10. PR18-R08 — MEDIUM
## Use stable worker error codes

Current worker errors expose class names such as:

```text
ValueError
RuntimeError
```

Those are not stable API contracts.

Introduce:

```python
class WorkerError(Exception):
    code: str
```

Suggested codes:

```text
OMNI_METHOD_NOT_FOUND
OMNI_INVALID_REQUEST
OMNI_INVALID_PARAMS
OMNI_PACKAGE_NOT_INSTALLED
OMNI_MODEL_NOT_INSTALLED
OMNI_MODEL_LOAD_FAILED
OMNI_MODEL_NOT_LOADED
OMNI_INFERENCE_FAILED
OMNI_PROMPT_CREATE_FAILED
OMNI_PROMPT_INVALID
OMNI_OUTPUT_PATH_INVALID
OMNI_WORKER_INTERNAL_ERROR
```

Unknown exceptions map to:

```text
OMNI_WORKER_INTERNAL_ERROR
```

Do not expose Python implementation class names.

---

# 11. PR18-R09 — MEDIUM
## Own and await stdout/stderr tasks

Current client stores only stdout reader task.

stderr is fire-and-forget.

Shutdown cancels stdout but does not await it.

Required fields:

```python
self._stdout_task
self._stderr_task
```

Optionally:

```python
self._wait_task
```

Shutdown should:

```text
stop/terminate process
  ↓
await process exit
  ↓
cancel remaining readers
  ↓
await gather(..., return_exceptions=True)
  ↓
clear references
```

No unowned runtime task.

Shutdown should be idempotent.

---

# 12. PR18-R10 — MEDIUM
## Add allowed-root path validation primitives

Worker currently accepts arbitrary:

```text
model_path
audio_path
output_path
prompt output_path
```

Before real API/model integration, define allowed roots.

Suggested environment/config:

```text
VOID_OMNI_MODEL_ROOT
VOID_OMNI_OUTPUT_ROOT
VOID_OMNI_VOICE_ROOT
VOID_OMNI_TEMP_ROOT
```

For any file path:

```python
resolved = Path(value).resolve()
```

Ensure it is inside an approved root.

Reject outside/traversal paths with stable error codes.

---

# 13. PR18-R11 — MEDIUM
## Bound mock audio generation

Current mock WAV generation constructs large Python lists/format strings based on target duration.

Enforce a small mock-duration maximum.

Prefer chunked zero writes or bounded byte writes.

Tests should never be able to request an enormous mock WAV.

---

# 14. PR18-R12 — LOW/MEDIUM
## Add or explicitly defer `validate_voice_prompt`

The master architecture describes `validate_voice_prompt` as part of the worker RPC surface.

Add the RPC now if practical.

Mock response can validate the mock prompt metadata.

Real implementation can become fully meaningful in O6.

If intentionally delayed, change the master plan to explicitly say:

```text
validate_voice_prompt → O6
```

instead of silently omitting it.

---

# 15. Important pre-existing issue
## This is not caused by PR #18

The PR base commit already added:

```text
torch >= 2.13.0
torchaudio >= 2.11.0
```

to the main API for VieNeu voice cloning.

The current Ubuntu CI installs a large CUDA dependency stack as part of that base environment.

Do NOT revert this inside PR #18 without re-reviewing VieNeu cloning.

But update documentation wording.

Avoid saying:

```text
"Zero bloat in base installer"
```

Prefer:

```text
"OmniVoice introduces no additional OmniVoice/Transformers/model
dependencies into the base API environment."
```

Runtime isolation still provides:

- optional OmniVoice installation;
- isolated `transformers` version;
- independent model updates;
- failure isolation from FastAPI;
- no OmniVoice model in the base installer.

Track VieNeu/PyTorch base footprint separately if desired.

---

# 16. Fix order for PR #18

Keep the current PR scope at M0.

Do not start O3.

Implement in this order:

```text
F1  Separate real worker and explicit test mock
F2  Add process-generation ownership
F3  Restart poisoned worker after timeout
F4  Normalize provider capability types
F5  Add provider runtime availability contract
F6  Pin exact OmniVoice model revision
F7  Correct runtime matrix wording
F8  Add stable worker error codes
F9  Own/await all worker tasks
F10 Add path-validation primitives
F11 Expand tests
F12 Update tracker/docs
```

---

# 17. Suggested code structure

```text
apps/omnivoice-worker/
├── worker.py
├── backend.py
├── real_backend.py
└── mock_backend.py

apps/api/app/services/
└── omnivoice_runtime.py

apps/api/app/providers/
├── registry.py
└── runtime_status.py
```

Avoid adding real OmniVoice dependency to `apps/api/pyproject.toml`.

---

# 18. M0 acceptance criteria

## O0

- current base commit recorded;
- package version pinned;
- exact model revision pinned;
- base dependency state documented accurately;
- baseline tests documented;
- target vs verified platform states separated.

## O1

- stable `omnivoice` ID registered;
- common capability type normalized for all providers;
- feature support separated from runtime availability;
- OmniVoice absent appears NOT INSTALLED, not READY;
- CapCut unchanged;
- VieNeu unchanged.

## O2

- JSONL IPC is stable;
- stdout is protocol-only;
- logs are stderr-only;
- mock is explicit test-only;
- real mode cannot silently mock;
- timeout terminates poisoned worker;
- next request recovers on a fresh PID;
- process readers are generation-safe;
- old process cleanup cannot cancel new-generation RPCs;
- stdout/stderr tasks are owned and awaited;
- stable error codes exist;
- malformed requests are handled;
- unknown methods are handled;
- path validation primitives exist;
- shutdown leaves no child worker.

Only then:

```text
O0 🟩 DONE
O1 🟩 DONE
O2 🟩 DONE
M0 🟩 PASS
```

---

# 19. Tests to add

Required additions:

```text
test_real_worker_does_not_fallback_to_mock
test_mock_worker_requires_explicit_mode
test_real_worker_missing_package_fails
test_real_worker_missing_model_fails

test_timeout_terminates_worker
test_request_after_timeout_starts_new_pid

test_old_generation_reader_cannot_cancel_new_generation
test_restart_generation_isolation

test_shutdown_is_idempotent
test_reader_tasks_are_finished_after_shutdown

test_registry_uses_common_capability_type_for_all
test_vieneu_common_capability_fields_exist

test_omnivoice_runtime_status_not_installed

test_unknown_method_has_stable_code
test_invalid_request_has_stable_code

test_worker_rejects_path_outside_allowed_root
test_mock_duration_is_bounded
```

Keep all existing tests.

Current PR CI has 124 API tests; test count should increase, not decrease.

No real multi-GB OmniVoice model is required in normal PR CI.

---

# 20. What not to do in this PR

Do NOT implement:

```text
O3 runtime/model installer
O4 real provider TTS integration into queue
O5 job DB multilingual options
O6 custom voice schema/prompt persistence
O7 Voice Library multi-provider UI
O8 Voice Design UI
O9+ SRT
```

This PR is still the runtime foundation.

Make it trustworthy first.

---

# 21. Suggested commits on the existing branch

```text
fix(omnivoice): make mock worker explicitly test-only
fix(omnivoice): isolate worker process generations
fix(omnivoice): restart worker after rpc timeout
fix(tts): normalize provider capability contracts
feat(tts): add provider runtime availability status
fix(omnivoice): add stable worker error codes
test(omnivoice): cover timeout and restart races
docs(omnivoice): pin model revision and correct runtime matrix
```

---

# 22. Agent instruction

```text
Work only on PR #18 / Milestone M0.

Read:
VOID_MELODY_PR18_OMNIVOICE_M0_REMEDIATION_PLAN.md

Fix PR18-R01 through PR18-R12 in severity order.

Non-negotiable:
1. Production worker must NEVER silently use mock behavior.
2. RPC timeout must invalidate/restart a blocked synchronous worker.
3. Old worker reader tasks must never affect a newer process generation.
4. Provider feature capabilities and runtime availability are separate concepts.
5. All provider descriptors use one app-level capability contract.
6. O0 cannot be DONE while the OmniVoice model revision is floating `main`.
7. Do not regress CapCut or VieNeu.
8. Do not add OmniVoice/Transformers/model dependencies to the base API environment.
9. Do not implement O3 or later phases in this PR.

After changes:
- run full API tests;
- run web lint/typecheck/tests/build;
- verify process cleanup;
- verify timeout recovery uses a new PID;
- update OMNIVOICE_BASELINE_REPORT.md;
- update OMNIVOICE_RUNTIME_MATRIX.md;
- update the master plan tracker.

Do not mark O0/O1/O2 DONE until every M0 acceptance criterion passes.
```

---

# 23. Final re-review checklist

Before merging PR #18:

```text
[ ] Production worker cannot silently mock
[ ] Missing real runtime gives explicit failure
[ ] Timeout kills poisoned worker
[ ] Next request gets a fresh PID
[ ] Old reader cannot cancel new RPC
[ ] stderr/stdout tasks cleaned up
[ ] OmniVoice absent != OmniVoice ready
[ ] All provider capability types normalized
[ ] VieNeu has new common capability fields
[ ] Exact model revision pinned
[ ] Runtime matrix uses truthful verification states
[ ] Stable error codes
[ ] Path roots validated
[ ] Full API suite passes
[ ] Web CI passes
[ ] CapCut regression passes
[ ] VieNeu regression passes
```

If all checks pass:

```text
MERGE PR #18
  ↓
start O3 in a new PR
```
