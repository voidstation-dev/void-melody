# VoidMelody Desktop

VoidMelody is a local-first desktop studio for creating text-to-speech audio. It combines a Tauri desktop shell, a Next.js interface, and a FastAPI sidecar that uses the bundled `capcut-tts-api` provider. It is an independent project and is not affiliated with CapCut or ByteDance.

> **Ghi chú tiếng Việt:** Ứng dụng chạy cục bộ trên máy; dữ liệu và tệp âm thanh được lưu trên máy của bạn.

## Architecture

```text
Tauri desktop app
  └─ Next.js UI (apps/web)
       └─ local FastAPI sidecar (apps/api)
            ├─ SQLite data store
            ├─ FFmpeg audio processing
            └─ capcut-tts-api submodule (vendor/capcut-tts-api)
```

The desktop app starts its API sidecar locally and passes a per-launch token to it. No API service is exposed to your network by default.

## Prerequisites

The supported desktop targets are macOS ARM64 (Apple Silicon) and Windows x64.

| Requirement | macOS ARM64 | Windows x64 |
| --- | --- | --- |
| Git | Git 2.30+ | Git for Windows 2.30+ |
| Node and pnpm | Node.js 20+ and Corepack | Node.js 20+ and Corepack |
| JavaScript package manager | `corepack prepare pnpm@10.11.0 --activate` | `corepack prepare pnpm@10.11.0 --activate` |
| Python tooling | Python 3.9+ and [uv](https://docs.astral.sh/uv/) | Python 3.9+ and [uv](https://docs.astral.sh/uv/) |
| Tauri build tooling | Rust stable and Xcode Command Line Tools (`xcode-select --install`) | Rust stable with the MSVC toolchain and Visual Studio 2022 Build Tools (Desktop development with C++, MSVC v143, and a Windows SDK) |
| Runtime tools | `ffmpeg` on `PATH` (for example, `brew install ffmpeg`) | `ffmpeg` on `PATH` (for example, `winget install Gyan.FFmpeg`) and Microsoft Edge WebView2 Runtime |

After installing FFmpeg on Windows, open a new terminal so its `PATH` change is available. The scripts below are identical in PowerShell, Command Prompt, macOS Terminal, and CI; do not use `source`, shell activation commands, or platform-specific path separators.

## Fresh clone, setup, and run

Clone with submodules so the local TTS provider is available:

```bash
git clone --recurse-submodules https://github.com/voidstation-dev/void-melody.git
cd void-melody
corepack prepare pnpm@10.11.0 --activate
pnpm setup:desktop
pnpm dev:desktop
```

`pnpm setup:desktop` installs the pinned JavaScript dependencies, initializes the TTS submodule recursively, applies the tracked VoidMelody compatibility patch, synchronizes the API virtual environment with `uv`, builds the API sidecar, and copies FFmpeg and the voice catalog into the desktop bundle inputs.

For an existing clone that was not created recursively, run:

```bash
pnpm setup:vendor
pnpm setup:desktop
```

To develop the browser UI without the desktop shell, run `pnpm dev:web`. To run the API by itself at `http://127.0.0.1:8000`, use:

```bash
pnpm setup:api
pnpm dev:api
```

> **Ghi chú tiếng Việt:** Lần cài đầu tiên cần Internet để tải dependencies. Sau đó, dùng `pnpm dev:desktop` để mở ứng dụng desktop.

## Test and build

Run the API and UI test suites:

```bash
pnpm test:api
pnpm test:web
```

Create a desktop release bundle for the current platform:

```bash
pnpm build:desktop
```

Build artifacts are written below `apps/web/src-tauri/target/release/bundle/`:

| Platform | Typical artifacts |
| --- | --- |
| macOS ARM64 | `dmg/VoidMelody_<version>_aarch64.dmg` and `macos/VoidMelody.app` |
| Windows x64 | `msi/` and `nsis/` installers |

The API sidecar input is generated at `apps/web/src-tauri/bin/melody-api-<target-triple>` (with `.exe` on Windows). These generated files are ignored by Git.

## Installed desktop app and first launch

The installer package is self-contained: it bundles the API sidecar, FFmpeg, the `Voice.json` catalog, and the desktop runtime manifest for its native target. End users do **not** need to install Python, Node.js, pnpm, Rust, or FFmpeg, and do not need to create a `.env` file or set shell, user, or system environment variables. The prerequisites above apply only to development builds from this repository.

On the first launch, VoidMelody can download the VieNeu model artifacts that are not already present. They are stored in the app data directory, not inside the installed `.app` bundle or installer directory. Keep the app online until that first model download finishes; later launches reuse the local cache.

Before starting the local API, the app checks its native platform and the bundled runtime files. A failure screen distinguishes an app-injected environment value from a missing installer resource. Use **Copy diagnostic report** and send only that sanitized report to support. Do not send a `.env` file, token, private/signing key, absolute-path details, or a full environment-variable dump.

Apple Developer ID notarization and Windows Authenticode code signing are release-policy work separate from this runtime packaging. Until the relevant certificates are configured, Gatekeeper or SmartScreen warnings may occur; they do not mean that an environment variable is missing.

## Release and update workflow

### One-time release signing setup

Generate the updater signer once and keep the private key outside the repository:

```bash
pnpm --dir apps/web tauri signer generate -w ~/.tauri/voidmelody-updater.key
```

Copy the generated public key into `apps/web/src-tauri/tauri.conf.json` at `plugins.updater.pubkey`. Do not commit, print, or share the private key at `~/.tauri/voidmelody-updater.key`.

In the GitHub repository settings, add these Actions secrets:

- `TAURI_SIGNING_PRIVATE_KEY`: the private key stored in `~/.tauri/voidmelody-updater.key`.
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: the signer password, if one was used (leave it empty for the current unencrypted key).

The release workflow receives these secrets only in the Tauri build step. `GITHUB_TOKEN` is used only to upload the release assets.

### Draft release process

1. Set the same version in `apps/web/src-tauri/tauri.conf.json`, `apps/web/src-tauri/Cargo.toml`, and `apps/web/package.json`, then add its exact `## [X.Y.Z]` section to `CHANGELOG.md`.
2. From a clean checkout, run `pnpm setup:desktop`, `pnpm test:api`, `pnpm test:web`, and `pnpm build:desktop` on each supported platform.
3. Run `pnpm test:release-metadata` locally. The helper rejects any non-`vX.Y.Z` tag, version mismatch, or missing changelog section.
4. Commit the version change, create an exact tag such as `v0.2.2`, and push the tag. The workflow builds only macOS ARM64 and Windows x64, then creates a draft release with installers, updater archives/signatures, and `latest.json`.
5. Test the draft artifacts before selecting **Publish release** in GitHub. Publishing remains a manual action.

### On-demand release builds

The release workflow also exposes a `workflow_dispatch` trigger for running the pipeline without a tag push. Provide the exact `vX.Y.Z` tag to build (it must equal the version in `tauri.conf.json`, `Cargo.toml`, and `apps/web/package.json`). This is useful for re-running a failed release build or rebuilding the artifact set after adding the updater signing secret. The workflow still creates (or updates) a draft release for that tag.

### Updater smoke tests and rollback

For the first migration, install a manually built or existing `0.1.0` application, publish the signed `0.2.0` draft, and confirm that the application upgrades to `0.2.0` from the updater prompt. For the next release, install `0.2.0`, publish a signed `0.2.1` draft, and confirm the `0.2.0` to `0.2.1` updater path, including download, install, and restart.

Do not attempt to replace a published release in place. To roll back a bad release, first unpublish it, then issue and publish a higher fixed version (for example, `0.2.2`) so installed clients can move forward safely.

> **Ghi chú tiếng Việt:** Mỗi bản phát hành cần build trên từng hệ điều hành để tạo đúng file cài đặt và sidecar cho nền tảng đó.

## Troubleshooting

### `capcut-tts-api` is empty or missing

Initialize it from the repository root:

```bash
pnpm setup:vendor
git submodule status --recursive
```

If the URL changed, run `git submodule sync --recursive` before `pnpm setup:vendor`.

The setup command applies `patches/capcut-tts-api-succeed-status.patch` so CapCut task responses accept both `success` and `succeed`. This intentionally leaves the submodule worktree modified after setup; the reproducible patch itself is committed in the parent repository. `pnpm setup:api` reinstalls only this local Python package so existing virtual environments also receive the patch.

### FFmpeg cannot be found

Install FFmpeg and confirm the executable is visible in a new terminal:

```bash
ffmpeg -version
pnpm setup:desktop
```

On macOS, `brew install ffmpeg` is the usual installation method. On Windows, `winget install Gyan.FFmpeg` is one option. The setup workflow copies the discovered binary into the desktop bundle inputs.

### Windows build fails because WebView2 or MSVC is missing

Install the Evergreen WebView2 Runtime and Visual Studio 2022 Build Tools with Desktop development with C++, MSVC v143, and a Windows SDK. Restart the terminal, then run `rustup default stable-msvc` and `pnpm setup:desktop` again.

### macOS says the app cannot be opened, or it hangs on "Starting local environment..."

Unsigned local and release builds are tagged with a `com.apple.quarantine` attribute by Gatekeeper. In Finder, Control-click the app, choose **Open**, and confirm the prompt to dismiss the open dialog.

If the app launches but never leaves the "Starting local environment..." screen, the quarantine attribute is also being applied to the bundled `melody-api` sidecar binary, which macOS then refuses to launch silently. The Tauri shell plugin spawns the sidecar but no port is ever printed, so the desktop UI waits forever. Clear the attribute recursively and relaunch:

```bash
xattr -cr /Applications/VoidMelody.app
```

This phase signs only the Tauri updater artifacts; Apple Developer ID code signing and notarization are not configured, so Gatekeeper quarantine is expected for downloaded builds.

### Windows SmartScreen warns about the installer

Unsigned installers can trigger SmartScreen. Prefer the release artifact from this repository and verify its source before continuing. This phase signs only the Tauri updater artifacts; Windows Authenticode is not configured, so SmartScreen warnings are expected.
