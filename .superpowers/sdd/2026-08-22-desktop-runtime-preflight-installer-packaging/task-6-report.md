# Task 6 report — desktop runtime preflight installer packaging

## Status

Documentation is complete and committed. Native macOS ARM64 setup, input verification, bundle creation, static bundle inspection, and packaged startup smoke were run on this host. The complete `pnpm build:desktop` command is **not release-ready**: it exits 1 because an updater public key is configured but `TAURI_SIGNING_PRIVATE_KEY` is unset. It creates the `.app`, `.dmg`, and unsigned `.app.tar.gz`, but cannot create the required `.app.tar.gz.sig`.

Windows was not run and is not inferred from this macOS host. It requires the `windows-2025` release matrix.

## Commits

- `f04cf8ce35ee42fe2dc11af07852642979f145ed` — `docs: document desktop runtime diagnostics`

## Files changed

- `README.md` — added the self-contained installer, first-launch VieNeu cache, sanitized diagnostics, secret-handling, and signing/notarization guidance required by Task 6.
- `.superpowers/sdd/2026-08-22-desktop-runtime-preflight-installer-packaging/task-6-report.md` — this execution report.

## Commands and results

| Command | Result |
| --- | --- |
| `pnpm setup:desktop` | PASS (exit 0). Generated the ARM64 API sidecar, ARM64 FFmpeg, and `Voice.json` bundle inputs. PyInstaller emitted non-fatal optional-import/platform warnings. |
| `pnpm test:api` | PASS (exit 0): 168 passed, 1 Starlette/httpx deprecation warning. Re-run during final verification with the same result. |
| `pnpm test:web` | PASS (exit 0): 24 files / 98 tests. Re-run standalone after final-verification investigation with the same result. |
| `pnpm --dir apps/web lint` | PASS (exit 0) with 3 existing warnings: anonymous default export in `eslint.config.mjs`, and two React-hook warnings in `emotional-script-page.tsx`. |
| `pnpm --dir apps/web exec tsc --noEmit` | PASS (exit 0). |
| `pnpm build:desktop` | FAIL (exit 1). The native build generated `VoidMelody.app`, `VoidMelody_0.3.0_aarch64.dmg`, and `VoidMelody.app.tar.gz`; Tauri then stopped with: `A public key has been found, but no private key. Make sure to set TAURI_SIGNING_PRIVATE_KEY environment variable.` No private key was added or accessed. |
| `pnpm test:release-metadata` | PASS (exit 0): 10 passed. |
| `pnpm --dir apps/web exec vitest run src/components/update/update-modal.test.tsx` | PASS (exit 0): 5 passed. This isolated rerun investigated one transient final-verification failure. |

The initially parallelized final-verification batch had one `pnpm test:web` failure (97/98): `UpdateModal`'s focus assertion observed `body` rather than `Update now`. The same test file immediately passed in isolation and the full suite then passed standalone (98/98). No Task 6 code changed, so no unrelated fix was made.

## Native macOS ARM64 smoke evidence

- Host: `Darwin arm64`; native target: `aarch64-apple-darwin`.
- `pnpm verify:desktop-bundle` ran inside `pnpm build:desktop` and reported `desktop bundle inputs verified for target aarch64-apple-darwin` before packaging.
- The final app contains ARM64 Mach-O executables at `Contents/MacOS/app`, `Contents/MacOS/melody-api`, and `Contents/MacOS/ffmpeg`; it also contains `Contents/Resources/bin/Voice.json` and `Contents/Resources/runtime/desktop-runtime-manifest.json`.
- `tar -tzf apps/web/src-tauri/target/release/bundle/macos/VoidMelody.app.tar.gz` confirmed the same sidecar, FFmpeg, voice catalog, and runtime-manifest paths in the updater archive.
- A scan of the built `.app` found no `.env`, key/pem, secret/token, model, or cache-style file inputs.
- `open -na apps/web/src-tauri/target/release/bundle/macos/VoidMelody.app`, followed by a 15-second wait, showed the built `app` process and its bundled `melody-api` sidecar processes. Only those test processes were terminated afterwards.
- The updater archive signature is absent because the build ended before signing; this is the concrete reason the installer artifact set is incomplete.

## Not verified on this host

- A fully successful macOS release artifact set, specifically `VoidMelody.app.tar.gz.sig`, cannot be verified without the release signing secret. This task did not alter Keychain or configure any certificate/private key.
- The existing `/Applications/VoidMelody.app` was not overwritten. Therefore, installation of this new build into `/Applications` was deliberately not performed.
- There is no controlled desktop UI automation in this session. The visible first-launch report (`macOS ARM64`, `aarch64-apple-darwin`, all resources present, no shell-profile export) was not asserted on screen; process-level startup through the packaged sidecar was verified instead.
- The interactive functional smoke (generate short audio, preview, export, restart, and prove a new VieNeu model cache in app data while not writing to `.app`) was not completed. It requires UI interaction and may require the first model download.
- Windows x64 installer, NSIS/MSI/updater artifacts, Windows first-launch preflight, SmartScreen behavior, and functional smoke were not run. They require the `windows-2025` release matrix; no Windows outcome is claimed here.

## Cleanup and self-review

- Restored all generated tracked changes from setup/build/tests: `apps/web/out/**`, `apps/web/tsconfig.tsbuildinfo`, `apps/web/next-env.d.ts`, and `apps/api/uv.lock`.
- Restored both vendor worktrees and removed their generated `build/` and egg-info output.
- Removed the verified ignored build output paths: `apps/web/.next`, `apps/web/src-tauri/bin`, `apps/web/src-tauri/target`, `apps/api/build`, `apps/api/dist`, and `apps/api/melody-api.spec`.
- Final documentation review confirmed that README distinguishes developer prerequisites from packaged-app requirements; describes bundled sidecar/FFmpeg; explains the app-data VieNeu cache; directs users to send only the sanitized report; forbids `.env`, token, key, and environment-dump sharing; and separates code-signing/notarization policy from missing environment variables.
- `git diff --check` passed before the documentation commit. No Keychain command was run and no generated artifact was staged.

## Concerns

- Release packaging remains blocked until the authorized release environment supplies `TAURI_SIGNING_PRIVATE_KEY`; the missing signature must not be treated as a missing user environment variable.
- The observed one-off focus assertion failure should be monitored in CI, but it reproduced as passing in both the isolated and standalone-full reruns and is outside this documentation-only task.
