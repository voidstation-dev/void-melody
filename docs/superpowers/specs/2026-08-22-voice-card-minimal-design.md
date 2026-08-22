# Voice Library Card — Minimal Design

## Status

Approved visual direction: minimal v2, confirmed by the user on 2026-08-22.

## Problem

The Voice Library cards currently reserve a large amount of vertical space for low-value decoration. Preset and cloned voices also feel like separate UI systems, which makes the catalog harder to scan and weakens the primary actions: preview a voice and use it.

## Design direction

Use one quiet card language for both preset and custom voices:

- white card on the existing neutral page background;
- black/dark ink for primary text and actions;
- one Melody coral accent for waveform activity, custom-voice context, and hover emphasis;
- thin waveform row as the visual center of the card;
- no colored status badges, secondary panels, or decorative statistics;
- compact metadata separated by small dot dividers;
- text-first actions: `Dùng giọng →` and the circular play control.

The card should feel like a small audio object in a studio library, not a marketing tile.

## Card structure

```text
┌──────────────────────────────────────────────────┐
│ eyebrow: type · language                    …   │
│ Voice name                                       │
│ One-line description                             │
│                                                  │
│  ●  waveform waveform waveform              0:06 │
│                                                  │
│ provider · style · quality/status                │
├──────────────────────────────────────────────────┤
│ Dùng giọng →                       supporting text│
└──────────────────────────────────────────────────┘
```

1. Header: eyebrow, voice name, one-line description, and the existing overflow menu where applicable.
2. Audio row: circular preview/play control, lightweight waveform, and duration when available.
3. Metadata row: concise provider and voice properties with dot separators.
4. Footer: primary use action and a quiet contextual hint.

## Data mapping

Preset voice cards keep the existing `Voice` fields:

- eyebrow: preset label + `languageCode`;
- name: `displayName`;
- description: existing preset description translation;
- metadata: provider label, natural style, and catalog context;
- preview id: `voiceType`;
- use route: `/?voice=<voiceType>`.

Custom voice cards keep the existing `CustomVoice` fields:

- eyebrow: custom/clone label;
- name: `display_name`;
- description: readiness/custom description translation;
- metadata: provider label, quality score when present, and status;
- preview id: `id`;
- use route: `/?voice=<id>`;
- overflow menu: retain delete action and confirmation dialog.

No API contract or voice-preview behavior changes are required.

## Interaction and accessibility

- The preview control remains a real `<button>` with an accessible label containing the voice name.
- Preview loading, playing, retry, and error states remain visible through the existing `VoicePreviewButton`.
- The use action remains a real link and retains its current keyboard focus ring.
- Overflow actions remain keyboard accessible and keep the current alert dialog for deletion.
- Hover raises the card slightly and strengthens the border; this is supplementary and must not be the only state cue.
- Respect reduced motion by keeping transforms/transitions non-essential.
- The waveform is decorative and must not be announced as content.

## Responsive behavior

- Two-column grid on wide screens remains the default for catalog browsing.
- Cards collapse naturally to one column below the existing responsive breakpoint.
- Metadata wraps without truncation; the title remains readable rather than being forced into a fixed height.
- Footer actions remain reachable at narrow widths and may wrap only when necessary.

## Scope

In scope:

- restyle `PresetVoiceRow` and `CustomVoiceCard` to the shared minimal structure;
- adjust `VoicePreviewButton` styling only where required to match the new card;
- preserve existing localization keys and add only copy needed for concise metadata;
- update component tests for structure, routes, preview labels, menu actions, and responsive-safe class behavior where practical.

Out of scope:

- changing the catalog API or pagination;
- generating real waveform data from audio;
- changing voice preview caching or playback logic;
- redesigning the page header, stats, filters, or tabs;
- changing the voice cloning workflow.

## Acceptance criteria

- Preset and custom cards visibly share the same hierarchy and spacing.
- Cards no longer look empty: the audio row and metadata occupy the space with useful information.
- The palette is predominantly neutral with one coral accent.
- Preview, use, delete, loading, error, and keyboard states continue to work.
- Existing web tests, lint, TypeScript checks, and production build pass.
