# Voice Lab baseline report

Date: 2026-08-20
Branch: `feature/voice-lab-cloning`
Base commit: `b35417ca01ba41e25208656032dcee1e7c1d4413`
App version: `0.2.7`
VieNeu vendor revision: `a8c9fbf99749d5ce45c89111f71558d6ceef3424`

## Repository state

- Existing user change preserved: `vendor/capcut-tts-api` (submodule/worktree state).
- The repository metadata had three pre-existing malformed version strings. They were corrected minimally so the test runners could start:
  - `package.json`
  - `apps/web/package.json`
  - `apps/api/pyproject.toml`

## Checks

| Check | Result | Notes |
|---|---|---|
| API suite | PASS — 105 tests | `cd apps/api && PYTHONPATH=../../packages/vieneu-core/src .venv/bin/python -m pytest tests -q` |
| VieNeu core suite | PASS — 35 tests | `cd packages/vieneu-core && PYTHONPATH=src ../../apps/api/.venv/bin/python -m pytest tests -q` |
| Web lint | PASS — 0 errors, 1 existing warning | `pnpm lint:web` |
| Web typecheck | PASS | `cd apps/web && pnpm exec tsc --noEmit` |
| Release metadata tests | PASS — 10 tests | `pnpm test:release-metadata` |
| Web suite | PASS — 44 tests | The sidecar startup timeout was aligned with the existing 15-second failure contract. |
| Tauri check | Not run in this environment | Requires the desktop toolchain and generated sidecar assets. |

The API smoke scripts outside `apps/api/tests` are not part of the test suite: some perform real CapCut network calls and some write to the installed application's data directory. They were not used as a release gate.

## Existing custom voice contract

The current `tts_custom_voices` table contains:

```text
id, display_name, reference_audio_path, transcript, consent_given, created_at
```

The current custom voice storage root is `settings.custom_voices_dir` (`MELODY_DATA_DIR/voices`, defaulting to the repository data directory). The existing API contract remains:

```text
POST   /api/v1/tts/voices/clone
GET    /api/v1/tts/voices/custom
DELETE /api/v1/tts/voices/custom/{voice_id}
```

Existing CapCut routing and the shared VieNeu provider/queue remain unchanged at this checkpoint.

## Parity matrix

| Existing behavior | Baseline | Voice Lab compatibility requirement |
|---|---|---|
| CapCut preset TTS | Covered by existing provider/queue tests | No route, provider, or concurrency regression |
| VieNeu preset TTS | Covered by existing provider tests | Preserve `provider_id=vieneu` and shared model manager |
| Custom voice create/list/delete | Covered by `test_voice_cloning.py` | Existing rows remain readable, usable, and deletable |
| TTS queue and batch | Covered by existing API tests | Custom voice IDs reuse the existing job/queue/provider contracts |

## Regression fixture

The schema and API tests provide the regression fixture for a custom voice row: a row is created through the current clone contract, read through the custom voice list endpoint, resolved by the VieNeu provider, and deleted through the existing delete endpoint. The fixture now also covers migrated metadata, path-safe filenames, selected long-audio segments, and cleanup on failure.

## Gate decision

P0 is complete. The baseline is frozen and all automated API, core, web, lint, typecheck, and release-metadata gates used for this implementation are passing. Tauri packaging remains an environment-dependent check and was not run here.
