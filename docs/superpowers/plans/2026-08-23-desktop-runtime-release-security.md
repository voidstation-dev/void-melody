# Desktop Runtime Release Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove sidecar output and inherited host secrets from the packaged desktop startup path, and run every desktop-runtime release check in CI.

**Architecture:** Keep the renderer responsible only for detecting the loopback port and reporting structured launch outcomes. Add a minimal PyInstaller entrypoint that snapshots an explicit allowlist, clears `os.environ`, restores that contract, and only then imports and runs `app.main`; the shell plugin can continue passing its runtime map without exposing inherited variables to application imports.

**Tech Stack:** React/Vitest, Tauri shell plugin, Python/PyInstaller/pytest, pnpm, GitHub Actions.

## Global Constraints

- Do not create or push a tag.
- Do not place secrets in source code or packaged bundle inputs.
- Preserve Keychain/trial behavior and the existing stale-sidecar restart/no-unhandled-rejection flow.
- Preserve required desktop variables: `PYTHONUNBUFFERED`, `APP_ENV`, `API_HOST`, `API_PORT`, `MELODY_API_TOKEN`, `MELODY_DATA_DIR`, `MELODY_CATALOG_PATH`, `TTS_*`, and model-cache paths controlled by the desktop runtime.
- Restore tracked generated TypeScript metadata before committing.

---

### Task 1: Safe renderer-side sidecar startup errors

**Files:**
- Modify: `apps/web/src/contexts/tauri-provider.tsx`
- Test: `apps/web/src/contexts/tauri-provider.test.tsx`

**Interfaces:**
- Consumes: shell sidecar stdout/stderr events and `error`/`close` lifecycle payloads.
- Produces: only safe startup error strings (`Sidecar process error: <reason>` and `Sidecar exited before API became ready (<exit reason>)`) while retaining loopback port detection.

- [x] **Step 1: Write failing renderer tests**

```tsx
act(() => {
  sidecar.stderrHandlers[0]("token=secret /Users/alice/Library/Application Support/VoidMelody");
  sidecar.processEventHandlers.close[0]({ code: 3, signal: null });
});
expect(screen.queryByText(/token=secret|\/Users\/alice/)).not.toBeInTheDocument();
expect(screen.getByText(/exit code 3/)).toBeInTheDocument();
```

- [x] **Step 2: Run the focused Vitest file and verify it fails because raw sidecar output is rendered.**

Run: `pnpm --dir apps/web exec vitest run src/contexts/tauri-provider.test.tsx`

- [x] **Step 3: Remove raw-output buffering and raw console logging, retaining safe port parsing and lifecycle reason handling.**

```ts
sidecar.on("close", ({ code, signal }) => {
  rejectStartup(new Error(`Sidecar exited before API became ready (${exitReason})`));
});
```

- [x] **Step 4: Re-run the focused renderer test.**

### Task 2: API-sidecar environment isolation before imports

**Files:**
- Create: `apps/api/sidecar_entrypoint.py`
- Create: `apps/api/tests/test_sidecar_entrypoint.py`
- Modify: `apps/api/build.py`
- Modify: `apps/web/src/lib/desktop-runtime-preflight.ts`
- Modify: `apps/web/src/lib/desktop-runtime-preflight.test.ts`

**Interfaces:**
- Consumes: the explicit runtime map injected by `buildSidecarEnvironment`.
- Produces: an allowlisted `os.environ` before `app.main` imports, retaining application configuration and model cache locations while removing inherited signing/Hugging Face credentials.

- [x] **Step 1: Write failing Python environment-isolation regression tests.**

```python
isolated = isolate_sidecar_environment({
    "HF_TOKEN": "host-secret",
    "TAURI_SIGNING_PRIVATE_KEY": "host-key",
    "APP_ENV": "production",
    "MELODY_API_TOKEN": "runtime-token",
})
assert "HF_TOKEN" not in isolated
assert isolated["MELODY_API_TOKEN"] == "runtime-token"
```

- [x] **Step 2: Run the focused pytest file and verify it fails because the entrypoint does not exist.**

Run: `cd apps/api && uv run python -m pytest tests/test_sidecar_entrypoint.py -q`

- [x] **Step 3: Add an allowlist-only entrypoint, point PyInstaller at it, and explicitly derive model-cache paths from `MELODY_DATA_DIR`.**

```python
runtime_environment = isolate_sidecar_environment(os.environ)
os.environ.clear()
os.environ.update(runtime_environment)
runpy.run_module("app.main", run_name="__main__")
```

- [x] **Step 4: Add/update TypeScript expectations for the explicit model-cache values and run focused Python and web tests.**

### Task 3: Release runtime test wiring

**Files:**
- Modify: `package.json`
- Modify: `.github/workflows/release.yml`
- Test: `scripts/verify-desktop-bundle.test.mjs`

**Interfaces:**
- Consumes: pnpm script execution.
- Produces: `test:desktop-runtime` runs both Node’s sidecar freshness test and Vitest’s bundle verifier; release CI invokes it before packaging.

- [x] **Step 1: Update the test script to invoke Vitest for its Vitest file and retain the Node test command.**

```json
"test:desktop-runtime": "node --test scripts/sync-tauri-dev-binaries.test.mjs && vitest run scripts/verify-desktop-bundle.test.mjs"
```

- [x] **Step 2: Add `pnpm test:desktop-runtime` to the release workflow before the packaging action.**

- [x] **Step 3: Run `pnpm test:desktop-runtime` and verify both test runners execute.**

### Task 4: Release validation and commit

**Files:**
- Modify only files from Tasks 1–3 and this plan.

- [x] **Step 1: Run focused tests, then `pnpm test:desktop-runtime`, `pnpm test:web`, `pnpm test:api`, `pnpm test:release-metadata`, and practical TypeScript/lint checks.**
- [x] **Step 2: Restore any tracked generated TypeScript metadata changed by verification.**
- [x] **Step 3: Inspect the final diff, request code review, address material findings, and commit with a security-focused message.**
