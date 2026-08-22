# Minimal Voice Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved minimal v2 visual direction to preset and custom voice cards without changing voice data, preview playback, routing, or deletion behavior.

**Architecture:** Add one presentational `VoiceWaveform` primitive for the decorative audio row, then compose it inside the existing `PresetVoiceRow` and `CustomVoiceCard` components. Keep provider/status metadata text-only and keep actions wired to the existing `VoicePreviewButton`, links, menu, and delete dialog.

**Tech Stack:** React 19, Next.js App Router, TypeScript, Tailwind utility classes, Vitest, Testing Library, existing i18n and voice hooks.

## Global Constraints

- Use the approved palette: neutral card/page surfaces, dark ink, and one Melody coral accent.
- Do not change API contracts, pagination, preview caching, preview endpoint behavior, or the voice cloning workflow.
- The waveform is decorative and must use `aria-hidden="true"`.
- Preview controls remain real accessible buttons; use actions remain links; custom voice overflow actions remain keyboard accessible.
- Keep the existing responsive two-column layout and allow cards/metadata/actions to wrap on narrow screens.
- Follow TDD: each behavior test must fail before its production implementation is written.

---

### Task 1: Add the shared decorative waveform primitive

**Files:**
- Create: `apps/web/src/components/voices/voice-waveform.tsx`
- Create: `apps/web/src/components/voices/voice-waveform.test.tsx`

**Interfaces:**
- Produces `VoiceWaveform({ accent?: "coral" | "muted" })` as a presentational React component.
- Renders a root element with `data-testid="voice-waveform"` and `aria-hidden="true"`.
- Renders a fixed set of decorative bars with `data-testid="voice-waveform-bar"`; it does not accept audio data and does not imply real waveform analysis.

- [ ] **Step 1: Write the failing test**

```tsx
it("renders an aria-hidden decorative waveform with stable bars", () => {
  render(<VoiceWaveform />)

  expect(screen.getByTestId("voice-waveform")).toHaveAttribute("aria-hidden", "true")
  expect(screen.getAllByTestId("voice-waveform-bar")).toHaveLength(24)
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/voice-waveform.test.tsx`

Expected: FAIL because `voice-waveform.tsx` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement `VoiceWaveform` with 24 spans, a neutral default palette, an optional coral palette, and a fixed height pattern expressed through Tailwind classes or inline bar heights. Keep the root `aria-hidden` and avoid animation by default.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/voice-waveform.test.tsx`

Expected: 1 test passed.

### Task 2: Redesign the preset voice card

**Files:**
- Modify: `apps/web/src/components/voices/preset-voice-row.tsx`
- Modify: `apps/web/src/components/voices/preset-voice-row.test.tsx`

**Interfaces:**
- Keep the existing `PresetVoiceRow({ voice, onPlayStart? })` props and route `/?voice=<voiceType>`.
- Consume `VoiceWaveform` and the existing `VoicePreviewButton`.
- Preserve the existing `voices.sampleSentence`, `voices.presetBadge`, `voices.presetDescription`, `voices.useVoice`, and `voices.useVoiceTitle` translations.

- [ ] **Step 1: Extend the failing test**

Add assertions for the approved structure and metadata:

```tsx
expect(screen.getByText("CapCut")).toBeInTheDocument()
expect(screen.getByText("Tự nhiên")).toBeInTheDocument()
expect(screen.getByTestId("voice-waveform")).toBeInTheDocument()
expect(screen.getByRole("link", { name: /dùng giọng/i })).toHaveAttribute(
  "href",
  "/?voice=BV421_vivn_streaming",
)
```

The test should fail because the current card has no waveform or concise metadata row.

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/preset-voice-row.test.tsx`

Expected: FAIL on the missing waveform/metadata assertions.

- [ ] **Step 3: Implement the minimal card structure**

Replace the current tall card content with:

1. eyebrow containing preset label and language;
2. voice name and one-line description;
3. audio row with a circular `VoicePreviewButton`-compatible preview control and `VoiceWaveform`;
4. concise provider/style/context metadata;
5. footer link for `Dùng giọng →` and the existing preview button.

Use neutral surfaces and borders, dark text, coral only for waveform/preview emphasis, and focus-visible rings on every interactive element. Keep `onPlayStart` passed into `VoicePreviewButton`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/preset-voice-row.test.tsx`

Expected: all preset card tests passed.

### Task 3: Redesign the custom voice card with the same visual language

**Files:**
- Modify: `apps/web/src/components/voices/custom-voice-card.tsx`
- Modify: `apps/web/src/components/voices/custom-voice-card.test.tsx`

**Interfaces:**
- Keep `CustomVoiceCard({ voice, onDelete, deleting? })` unchanged.
- Preserve `VoiceActionsMenu`, `VoiceDeleteDialog`, `VoicePreviewButton`, and the custom voice route `/?voice=<id>`.
- Use `providerLabel(voice.provider_id)`, the existing duration fallback, quality score, and status fields.

- [ ] **Step 1: Extend the failing test**

Set `quality_score: 92` and assert the shared card language:

```tsx
expect(screen.getByText("VieNeu")).toBeInTheDocument()
expect(screen.getByText("Chất lượng 92/100")).toBeInTheDocument()
expect(screen.getByText("Sẵn sàng")).toBeInTheDocument()
expect(screen.getByTestId("voice-waveform")).toBeInTheDocument()
```

The test should fail against the current custom card because those compact metadata and waveform elements are absent.

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/custom-voice-card.test.tsx`

Expected: FAIL on the missing waveform/metadata assertions while the existing delete dialog test remains valid.

- [ ] **Step 3: Implement the minimal custom card structure**

Mirror the preset card hierarchy, using a coral eyebrow for custom/clone context, the custom description/readiness copy, provider/quality/status metadata, a coral waveform, and the existing overflow menu in the header. Keep the delete dialog mounted with the current callbacks and pending state.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/custom-voice-card.test.tsx`

Expected: all custom card tests passed.

### Task 4: Align the shared preview control with the minimal card

**Files:**
- Modify: `apps/web/src/components/voices/voice-preview-button.tsx`
- Modify: `apps/web/src/components/voices/voice-preview-button.test.tsx`

**Interfaces:**
- Keep `VoicePreviewButton` props and `useVoicePreview` behavior unchanged.
- Preserve loading, playing, retry, error text, `aria-label`, and `aria-pressed` behavior.

- [ ] **Step 1: Write the failing style contract test**

Add an assertion that the default preview button uses the compact rounded control style while retaining its accessible label:

```tsx
const button = screen.getByRole("button", { name: /nghe thử voice-1/i })
expect(button).toHaveClass("rounded-full")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/voice-preview-button.test.tsx`

Expected: FAIL because the current button uses `rounded-xl`.

- [ ] **Step 3: Implement the minimal style adjustment**

Change only the visual classes needed for the new card: rounded circular/compact preview treatment, neutral default surface, coral playing state, and preserved focus/error/loading classes. Do not touch the hook or request body.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm --dir apps/web exec vitest run src/components/voices/voice-preview-button.test.tsx`

Expected: all preview behavior tests passed.

### Task 5: Verify the complete voice library experience

**Files:**
- Verify: `apps/web/src/app/voices/page.tsx`
- Verify: `apps/web/src/components/voices/preset-voices-section.tsx`
- Verify: `apps/web/src/components/voices/my-voices-section.tsx`
- Verify: all changed voice component tests.

- [ ] **Step 1: Run the focused voice card suite**

Run: `pnpm --dir apps/web exec vitest run src/components/voices`

Expected: all voice component tests pass.

- [ ] **Step 2: Run the full web test suite**

Run: `pnpm test:web`

Expected: 0 failed tests.

- [ ] **Step 3: Run lint and TypeScript checks**

Run: `pnpm lint:web && pnpm --dir apps/web exec tsc --noEmit`

Expected: lint has no errors and TypeScript exits with code 0. Restore `apps/web/tsconfig.tsbuildinfo` if the compiler updates it.

- [ ] **Step 4: Run the production build and diff check**

Run: `pnpm --dir apps/web build && git diff --check`

Expected: production build exits 0 and `git diff --check` reports no whitespace errors. Restore generated `apps/web/out`/`tsconfig.tsbuildinfo` artifacts if they are tracked or generated locally.

- [ ] **Step 5: Check the rendered page in the running desktop app**

Open `/voices`, confirm both preset and custom cards use the same neutral hierarchy, preview controls remain usable, and the duplicate key warning is not introduced by this card change. Capture any unrelated existing warning separately rather than changing catalog identity behavior in this scope.
