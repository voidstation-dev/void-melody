# Remove OmniVoice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely eliminate the OmniVoice engine, worker, services, and associated Voice Design artifacts from the codebase so that only VieNeu, CapCut, and VoxCPM2 remain.

**Architecture:** Remove `apps/omnivoice-worker`, clean up all OmniVoice provider adapters, models, schemas, and endpoints in `apps/api`, create an Alembic forward migration to drop `tts_omnivoice_voices`, and remove all OmniVoice and Voice Design UI components and routes in `apps/web`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 19, Vite, TanStack Router, Vitest, Pytest.

## Global Constraints

- Retain full functionality of CapCut, VieNeu, and VoxCPM2 without any regressions.
- All backend tests (`uv run python -m pytest`) and web tests (`pnpm test`) must pass cleanly.
- Maintain Alembic migration chain integrity via a forward migration dropping `tts_omnivoice_voices`.
- No lingering references to `omnivoice` or `voice_design` in active code paths.

---

### Task 1: Delete OmniVoice Worker and Api Adapters

**Files:**
- Delete: `apps/omnivoice-worker/` (entire directory: `backend.py`, `errors.py`, `mock_backend.py`, `path_utils.py`, `real_backend.py`, `worker.py`)
- Delete: `apps/api/app/providers/omnivoice_provider.py`
- Delete: `apps/api/app/services/omnivoice_model_service.py`
- Delete: `apps/api/app/services/omnivoice_runtime.py`
- Delete: `apps/api/app/services/omnivoice_voice_resolver.py`
- Delete: `apps/api/app/services/voice_design/` (entire directory)
- Delete: `apps/api/app/api/v1/voice_design.py`
- Delete: `apps/api/app/models/omnivoice_voice.py`
- Delete: `apps/api/app/schemas/omnivoice_voice.py`
- Delete: `apps/api/app/schemas/voice_design.py`

**Interfaces:**
- Consumes: None
- Produces: Clean removal of obsolete OmniVoice files.

- [ ] **Step 1: Delete `apps/omnivoice-worker` directory**
- [ ] **Step 2: Delete `apps/api/app/providers/omnivoice_provider.py`**
- [ ] **Step 3: Delete `apps/api/app/services/omnivoice_*.py` and `apps/api/app/services/voice_design/`**
- [ ] **Step 4: Delete `apps/api/app/api/v1/voice_design.py`**
- [ ] **Step 5: Delete `apps/api/app/models/omnivoice_voice.py`, `apps/api/app/schemas/omnivoice_voice.py`, `apps/api/app/schemas/voice_design.py`**

---

### Task 2: Update Core Backend Modules

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/scheduler/policies.py`
- Modify: `apps/api/app/scheduler/scheduler.py`
- Modify: `apps/api/app/workers/queue_manager.py`
- Modify: `apps/api/app/workers/tts_worker.py`
- Modify: `apps/api/app/providers/registry.py`
- Modify: `apps/api/app/providers/runtime_status.py`
- Modify: `apps/api/app/models/__init__.py`
- Modify: `apps/api/app/services/voice_resolver.py`
- Modify: `apps/api/app/services/runtime_manager/models.py`
- Modify: `apps/api/app/services/runtime_manager/manifests.py`
- Modify: `apps/api/app/services/runtime_manager/service.py`
- Modify: `apps/api/app/services/plan_enforcement.py`
- Modify: `apps/api/app/api/v1/router.py`
- Modify: `apps/api/app/api/v1/voices.py`

**Interfaces:**
- Consumes: Remaining providers (`capcut`, `vieneu`, `voxcpm2`)
- Produces: Scheduler, registry, router, resolver, and workers operating strictly on CapCut, VieNeu, and VoxCPM2.

- [ ] **Step 1: Remove OmniVoice settings from `apps/api/app/config.py`**
Remove:
```python
    omnivoice_job_concurrency: int = 1
    omnivoice_chunk_concurrency: int = 1
    omnivoice_inference_timeout_seconds: float = 180.0
```

- [ ] **Step 2: Remove OmniVoice policy and lane from `policies.py`, `scheduler.py`, `queue_manager.py`**
In `apps/api/app/scheduler/policies.py`: Remove `"omnivoice"` from `get_default_policies()`.
In `apps/api/app/scheduler/scheduler.py`: Remove `OmniVoiceProvider` import, provider entry, and `"omnivoice"` lane.
In `apps/api/app/workers/queue_manager.py`: Remove `OmniVoiceProvider` import, provider entry, and `"omnivoice"` lane.

- [ ] **Step 3: Clean up `tts_worker.py`**
In `apps/api/app/workers/tts_worker.py`:
Change `is_local_wav = job.provider_id in ("vieneu", "omnivoice", "voxcpm2")` to `job.provider_id in ("vieneu", "voxcpm2")`.
Remove `elif job.provider_id == "omnivoice":` synthesis dispatch block.

- [ ] **Step 4: Update `registry.py` and `runtime_status.py`**
In `apps/api/app/providers/registry.py`: Remove `OMNIVOICE = "omnivoice"`, `_omnivoice_descriptor()`, and its registration.
In `apps/api/app/providers/runtime_status.py`: Remove `OMNIVOICE` import and `if provider_id == OMNIVOICE:` handling block.

- [ ] **Step 5: Update `models/__init__.py`, `voice_resolver.py`, `router.py`, `runtime_manager`**
In `apps/api/app/models/__init__.py`: Remove `OmniVoiceVoiceModel` import and `__all__` entry.
In `apps/api/app/services/voice_resolver.py`: Remove `OmniVoiceVoiceModel` import and fallback resolution query for OmniVoice.
In `apps/api/app/api/v1/router.py`: Remove `voice_design` import and `api_router.include_router(voice_design.router, ...)`.
In `apps/api/app/services/runtime_manager/models.py`: Set `KNOWN_RUNTIME_IDS = ("vieneu", "speech")`.
In `apps/api/app/services/runtime_manager/manifests.py`: Remove `"omnivoice"` from `known_manifests()`.
In `apps/api/app/services/runtime_manager/service.py`: Update `status_all()` to check `("vieneu", "speech")`.

- [ ] **Step 6: Update `plan_enforcement.py` and `api/v1/voices.py`**
In `apps/api/app/services/plan_enforcement.py`: Remove `"omnivoice"` from `DEFAULT_FEATURES["providers"]` and `MASTER_UNLIMITED_FEATURES["providers"]`.
In `apps/api/app/api/v1/voices.py`:
- Remove `OmniVoiceVoiceModel` and OmniVoice schemas imports.
- Remove `_serialize_omnivoice_voice`.
- In `list_custom_voices`: remove `if include_omnivoice:` query for `OmniVoiceVoiceModel` (keep VoxCPM2 query intact).
- In `get_custom_voice`: remove OmniVoice check.
- In `delete_custom_voice`: remove OmniVoice check and artifact deletion block.

---

### Task 3: Alembic Forward Migration to Drop `tts_omnivoice_voices`

**Files:**
- Create: `apps/api/alembic/versions/<revision>_drop_tts_omnivoice_voices_table.py`
- Modify: `apps/api/app/services/database_migrations.py`

**Interfaces:**
- Consumes: Previous head revision `a9c4f2e8b1d7`
- Produces: Database schema without `tts_omnivoice_voices` table.

- [ ] **Step 1: Create Alembic migration dropping `tts_omnivoice_voices`**
File: `apps/api/alembic/versions/b1e2d3c4a5f6_drop_tts_omnivoice_voices_table.py`
```python
"""drop tts_omnivoice_voices table

Revision ID: b1e2d3c4a5f6
Revises: a9c4f2e8b1d7
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1e2d3c4a5f6'
down_revision: Union[str, Sequence[str], None] = 'a9c4f2e8b1d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Drop table if exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'tts_omnivoice_voices' in tables:
        op.drop_table('tts_omnivoice_voices')

def downgrade() -> None:
    pass
```

- [ ] **Step 2: Update `database_migrations.py`**
Remove `OMNIVOICE_VOICE_TABLE = "tts_omnivoice_voices"` and `POST_BASELINE_OMNIVOICE_VOICE_COLUMNS`.
Remove checks for `_table_exists(connection, OMNIVOICE_VOICE_TABLE)`.

---

### Task 4: Clean Up Backend Tests

**Files:**
- Delete:
  - `apps/api/tests/test_omnivoice_worker_unit.py`
  - `apps/api/tests/test_omnivoice_runtime.py`
  - `apps/api/tests/test_omnivoice_provider_isolation.py`
  - `apps/api/tests/test_omnivoice_provider.py`
  - `apps/api/tests/test_omnivoice_model_service.py`
  - `apps/api/tests/test_voice_design.py`
  - `apps/api/tests/test_voice_design_endpoints.py`
- Modify:
  - `apps/api/tests/test_provider_registry.py`
  - `apps/api/tests/test_voxcpm_provider.py`
  - `apps/api/tests/test_plan_enforcement.py`
  - `apps/api/tests/test_tts_worker.py`
  - `apps/api/tests/test_runtime_manager.py`
  - `apps/api/tests/test_job_recovery.py`
  - `apps/api/tests/test_voxcpm_resource_coordinator.py`
  - `apps/api/tests/test_voxcpm_worker_unit.py`
  - `apps/api/tests/test_voxcpm_real_backend.py`
  - `apps/api/tests/conftest.py`

- [ ] **Step 1: Delete dedicated omnivoice and voice_design test files**
- [ ] **Step 2: Update `test_provider_registry.py` and `test_voxcpm_provider.py`**
Assert `{CAPCUT, VIENEU, VOXCPM2}` as the set of registered provider IDs. Remove `test_omnivoice_descriptor_shape` and `test_omnivoice_runtime_status_not_installed`.
- [ ] **Step 3: Update `test_plan_enforcement.py` and `conftest.py`**
Remove `"omnivoice"` from provider lists.
- [ ] **Step 4: Update `test_tts_worker.py`, `test_runtime_manager.py`, `test_job_recovery.py`, `test_voxcpm_resource_coordinator.py`**
Remove omnivoice tests from `test_tts_worker.py`.
Update `test_runtime_manager.py` expected packs to `{"vieneu", "speech"}`.
Update `test_job_recovery.py` custom job provider to `"voxcpm2"`.
Update `test_voxcpm_resource_coordinator.py` dummy registered runtime to `"dummy_runtime"`.
- [ ] **Step 5: Run backend test suite**
Run: `cd apps/api && uv run python -m pytest`
Expected: All backend tests pass.

---

### Task 5: Frontend Clean Up (`apps/web`)

**Files:**
- Delete:
  - `apps/web/src/components/voices/omnivoice-design-card.tsx`
  - `apps/web/src/components/voice-design/` (entire folder: `voice-design-modal.tsx`)
  - `apps/web/src/routes/voice-design.tsx`
  - `apps/web/src/api/voice-design.ts`
  - `apps/web/src/types/voice-design.ts`
- Modify:
  - `apps/web/src/components/voices/my-voices-section.tsx`
  - `apps/web/src/components/voices/create-voice-dialog.tsx`
  - `apps/web/src/components/voices/voice-library-empty.tsx`
  - `apps/web/src/components/voices/voice-library-utils.ts`
  - `apps/web/src/routes/voices.tsx`
  - `apps/web/src/features/audio-studio/components/studio-floating-bar.tsx`
  - `apps/web/src/locales/vi.ts` & `apps/web/src/locales/en.ts`
  - `apps/web/src/routeTree.gen.ts`

- [ ] **Step 1: Delete frontend Voice Design & OmniVoice files**
- [ ] **Step 2: Update `my-voices-section.tsx`**
Remove `OmniVoiceDesignCard` import and `isOmni` condition. Directly render `<CustomVoiceCard />` for all items.
- [ ] **Step 3: Update `create-voice-dialog.tsx`**
Replace the Voice Design button with a VoxCPM2 Clone button (`navigate({ to: "/voxcpm" })`) with appropriate icon and label, offering clear navigation between VieNeu Clone (`/vieneu`) and VoxCPM2 Clone (`/voxcpm`).
- [ ] **Step 4: Update `voice-library-empty.tsx`**
Replace `/voice-design` link with `/voxcpm` link.
- [ ] **Step 5: Update `voice-library-utils.ts`, `routes/voices.tsx`, and `studio-floating-bar.tsx`**
Remove `"omnivoice"` case in `providerLabel`.
Remove `"omnivoice"` filter mapping and search keyword in `voices.tsx`.
Remove `"omnivoice"` branch in `studio-floating-bar.tsx`.
- [ ] **Step 6: Update locales (`vi.ts`, `en.ts`)**
Remove unused `design*` keys.
- [ ] **Step 7: Regenerate TanStack router tree and run web test suite**
Run: `pnpm --dir apps/web test`
Expected: All 26 test files and all tests pass cleanly.

---

### Task 6: End-to-End Verification

- [ ] **Step 1: Run full repository test suite**
Commands:
`cd apps/api && uv run python -m pytest`
`pnpm --dir apps/web test`
- [ ] **Step 2: Verify `rg -i "omnivoice"` produces zero code hits**
Ensure no lingering references in active code (`apps/api`, `apps/web`, `scripts`, `packages`).
