# Changelog

All notable changes to VoidMelody Desktop are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2026-08-24

### Added

- Integrated official Melody brand asset pack with high-resolution multi-format icons and PWA manifest.
- Added theme-adaptive brand marks for seamless contrast across Light and Dark modes.
- Modernized web application architecture with Vite and TanStack Router with instant intent-based prefetching.
- Optimized multi-tier client query caching for fast navigation across all views.

### Fixed

- Enhanced desktop sidecar binary synchronization with resilient file lock handling and smart cache validation.
- Fixed washed out / blurry desktop icon on Windows taskbar with high-contrast squircle container badge.

## [0.3.2] - 2026-08-23

### Fixed

- Configure ad-hoc macOS bundle signing to prevent Apple Silicon releases from being classified as damaged by Gatekeeper.

## [0.3.0] - 2026-08-21

### Added

- Integrated VieNeu TTS & OmniVoice Runtime for local neural voice cloning and speech synthesis.
- Complete redesign of Voice Library cards with studio descriptions, clean metadata tags, and unified action buttons.
- Modernized Voice Selector dropdown with sound wave avatar icons and clean category tabs.
- Full localization (i18n) support with structured dictionary schema for Vietnamese and English.
- Enhanced Audio Download Dialog with hyphen-separated tag append and right-aligned compact actions.
- Resilient sidecar process supervision and safe background task termination capabilities in Tauri.

### Fixed

- Fixed transparent download format dropdown menu overlap in Job Queue cards.
- Fixed ONNX runtime error message overflow with clean text wrapping and scrollbox.
- Fixed orphaned sidecar processes locking binary during app restarts.

## [0.2.6] - 2026-08-05

### Added

- Added ability to configure custom download paths for batch imports and manual job downloads.
- Backend now automatically copies generated audio files to the specified export folder (MP3/M4A).
- Native desktop folder picker for selecting export directories.

### Fixed

- Resolved React Hook dependencies and useEffect warnings.

## [0.2.4] - 2026-08-04

### Fixed

- Bundled FFmpeg is now a self-contained static build (from `eugeneware/ffmpeg-static`) instead of the Homebrew dynamic-linked binary, so TTS audio processing no longer crashes with `dyld: Library not loaded: .../libavdevice.62.dylib` on machines without the exact Homebrew Cellar. The release workflow no longer installs FFmpeg via brew/choco; `setup-ffmpeg.js` downloads the portable binary for the runner platform.

## [0.2.3] - 2026-08-04

### Fixed

- Desktop UI now surfaces a startup timeout with an `xattr -cr` workaround hint when the local API sidecar is blocked by macOS Gatekeeper quarantine, instead of hanging on "Starting local environment..." indefinitely.
- Documented the macOS quarantine workaround (Finder Open + `xattr -cr`) and Windows SmartScreen "Run anyway" flow in the README troubleshooting section.

## [0.2.2] - 2026-08-03

### Fixed

- Release workflow now produces the full updater artifact set (`latest.json`, signed `.sig` files, and the Windows NSIS updater archive) by gating the build on the updater signing secret, and uploads workflow artifacts for every bundle.
- Enabled `bundle.createUpdaterArtifacts` in the Tauri config so the bundler emits signed `.sig` files and the `latest.json` updater manifest is uploaded for auto-update.
- Pinned `tauri-apps/tauri-action` to a verified release tag instead of a mutable major branch.
- Added `workflow_dispatch` trigger so the release pipeline can be run on-demand without a tag push.
- Fixed TypeScript error with ImportedTextFile type in TTS Studio.
- Updated Node.js version in Github Actions to resolve deprecation warning.

### Changed

- Restored mandatory API and web test gates (`pnpm test:api`, `pnpm test:web`) in the release workflow before the desktop build.

## [0.2.1] - 2026-08-03

### Fixed
- Fixed TypeScript error with ImportedTextFile type in TTS Studio.
- Updated Node.js version in Github Actions to resolve deprecation warning.

## [0.2.0] - 2026-08-02

### Added

- Signed updater archives and signatures for the desktop application.
- Cross-platform desktop tooling for macOS ARM64 and Windows x64 release builds.
- Signed draft GitHub releases that publish installers, updater artifacts, and `latest.json` only after manual review.
