# Changelog

All notable changes to VoidMelody Desktop are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.5] - 2026-08-31

### Added

- **TweakCN-Inspired Multi-Theme Palette Engine**: Integrated 20+ rich theme presets spanning Studio & Minimal, Cyber & Tech, Nature, Pastel, and Classic Vintage aesthetics with persistent localStorage syncing.
- **Visual Theme Palette Picker**: Added interactive theme catalog with 4-color dot preview swatches, real-time name & description fuzzy search, category filter pills, and random theme shuffle button.
- **Dynamic Corner Radius Customizer**: Added live radius slider with 5 quick-click presets (from 0.25rem sharp to 1.25rem soft) that reacts instantly across all application components.
- **Settings Studio Tabbed Redesign**: Restructured settings into an organized 3-tab layout (General, License, Local AI) with segmented controls.

### Fixed

- **Light & System Theme Toggle Synchronization**: Fixed light mode transition issue caused by DOM class race conditions when switching from system theme.
- **Bilingual Theme Descriptions**: Added full English and Vietnamese localization for all theme preset titles and descriptions.

## [0.4.4] - 2026-08-31

### Added

- **Audio Studio UX Revamp & Expandable Floating Bar**: Redesigned floating action bar into a sleek, compact single-row dock with smooth CSS Grid accordion preflight inspection drawer and real-time validation checks.
- **Smart Tag Autocomplete & Inline Ribbon**: Added trigger-based autocompletion for expression, delivery, and emotion tags with keyboard navigation.
- **Minimalist Audio Track Job Queue**: Streamlined job queue cards into a 2-line clean layout (Voice + Duration, Tag + Script preview) with responsive right-side actions.
- **OmniVoice Phase 2 Foundation**: Added voice design endpoints, model orchestration service, and license plan entitlement enforcement.

### Fixed

- **Job Queue Layout on Small Screens**: Resolved text overlapping and badge truncation on laptop and compact viewport sizes.
- **Auto-Save Draft Synchronization**: Enhanced auto-save to immediately purge stale localStorage drafts when editor text is cleared.
- **Full Application Translations**: Completed missing localization keys across all studio components.

## [0.4.3] - 2026-08-25

### Added

- **Speech Transcription API & Model Selector**: Integrated automatic speech-to-text (STT) for Voice Lab audio reference segmentation with CPU/GPU recommended model catalog (Whisper/Faster-Whisper/CapCut STT).
- **Redesigned Calibration & Preview Audio Players**: Custom interactive audio players with play/pause, scrubbers, real-time waveform timing, quality/similarity metrics, and format export options (WAV, MP3, M4A).
- **Studio Quick-Start & Presets**: Enhanced "Use in Studio" section with quick speech prompt templates (Original transcript, Greetings, Storytelling, Tech news) and direct one-click navigation to Audio Studio.

### Fixed

- **Numpy Array Truth Value in TTS Worker**: Fixed ambiguous truth value evaluation bug when synthesizing preview jobs with cloned voice profiles.
- **Audio Output Signature & Transcoding**: Resolved `Audio output is empty or has an invalid signature` error by ensuring proper WAV-to-MP3 transcoding in single and multi-chunk concatenation pipelines.
- **Calibration Audio Serving & FileResponse**: Fixed 500 error on `/calibration/audio` by importing `FileResponse` and using authenticated `apiFetchBlob`.
- **Responsive Layout & Text Wrapping**: Fixed badge line wrapping and card layout in the Voice Lab sidebar.

## [0.4.2] - 2026-08-25

### Added

- **VieNeu Audio Studio Speed Optimization**: Comprehensive speed improvements for VieNeu TTS in Audio Studio:
  - Macro text chunking (~1024 chars/chunk) reducing provider dispatch overhead by over 55%.
  - Zero-copy cache path with batched database transactions.
  - Lossless intermediate audio pipeline with single-pass final MP3 encoding and true lossless WAV output.
  - Adaptive local runtime autotuning with CPU concurrency bounds (1–4 workers) and GPU batching with dynamic OOM fallback.
  - Non-blocking background warmup for VieNeu engine and custom voice artifacts.

### Fixed

- **Voice Clone v2 Zero Re-Enrollment**: Guaranteed zero `prepare_reference` calls during Audio Studio generation with Enrollment v2 profiles.
- **Provider Lane Routing**: Ensured jobs strictly preserve provider isolation across single, batch, retry, and recovery queues.

## [0.4.1] - 2026-08-25

### Added

- **Full Application i18n Localization**: Completed end-to-end typed internationalization (Vietnamese & English) across Audio Studio, Voice Lab, Voice Library, Job Queue, History, Settings, and Bootstrap screens with zero hardcoded UI strings.
- **Modern Voice Selector**: Replaced native select elements with accessible shadcn/ui Combobox and Command primitives supporting instant keyword search, regional and gender filters, and custom vs preset tabs.

### Fixed

- **Desktop Setup & PyInstaller Build**: Resolved `pnpm setup:desktop` hook failure by cleanly excluding unused optional Python dependencies (`pandas`, `matplotlib`, `tkinter`, `IPython`, `pytest`) from sidecar packaging.
- **Audio Combine & FFmpeg Pipeline**: Fixed bundled FFmpeg executable resolution and temporary file concatenation path handling during multi-segment audio export.
- **Text Area Overflow**: Fixed Vietnamese multi-byte input overflow and improved editor word-wrapping dynamics in Audio Studio.
- **Voice Badges & Preview Samples**: Accurately distinguished VieNeu preset vs cloned custom voice badges and enhanced default preview sentences for custom voice clones.
- **Download Modal Styling**: Fixed button overflow and alignment issues on hover in the Audio Studio download dialog.

## [0.4.0] - 2026-08-24

### Added

- **VieNeu True Enrollment v2**: 1-time tensor feature extraction (`speaker_emb`, `ref_codes`) eliminating re-enrollment overhead during synthesis.
- **Reference Analysis v2**: Energy percentile SNR estimation, noise floor (dBFS), stability subscores, and 1-click Auto Pick Best Segment.
- **Conditional Denoising**: Auto / Off / On background noise reduction pipeline for reference audio samples.
- **Calibration Audio & Similarity Scoring**: Automatic cosine similarity verification and calibration audio playback for enrolled profiles.
- **Unified Audio Studio**: Modern shadcn/ui script composer with real-time emotion tagging, delivery controls, preflight check, and batch synthesis.
- **Quick Switchers**: Dynamic Dark/Light theme toggle and instant Vietnamese/English language toggle in header.

### Fixed

- Fixed database migration schema synchronization for custom voice enrollment profiles.
- Fixed preview audio playback and download formats in Voice Lab.

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
