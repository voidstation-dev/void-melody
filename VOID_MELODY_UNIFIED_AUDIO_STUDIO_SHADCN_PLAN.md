# Void Melody — Unified Audio Studio Implementation Plan

> Mục tiêu: gộp hai feature **Tạo âm thanh** và **Kịch bản cảm xúc** thành một workflow duy nhất trong Void Melody, dùng **shadcn/ui + Tailwind CSS v4**, đồng thời giữ nguyên business logic TTS hiện tại và giảm trùng lặp UI/logic.

---

# 1. Product Goal

Thay vì bắt người dùng chọn giữa:

```text
Tạo âm thanh
Kịch bản cảm xúc
```

Void Melody sẽ có một workflow duy nhất:

```text
Nội dung
→ Cảm xúc / Delivery
→ Giọng đọc
→ Output
→ Preflight
→ Tạo audio
```

User không còn phải hiểu trước sự khác nhau giữa “Tạo âm thanh” và “Kịch bản cảm xúc”.

---

# 2. Navigation mới

Sidebar hiện tại:

```text
Tạo âm thanh
Kịch bản cảm xúc
Phòng thu giọng
Thư viện giọng
Lịch sử
Cài đặt
```

Sidebar target:

```text
TẠO
  Tạo audio
  Phòng thu giọng

THƯ VIỆN
  Thư viện giọng
  Lịch sử

CÀI ĐẶT
  Cài đặt
```

## Quyết định

- Bỏ `Kịch bản cảm xúc` khỏi primary sidebar.
- Logic của feature này được merge vào màn `Tạo audio`.
- Route cũ `/scripts` có thể redirect về `/` sau khi migration ổn định.

---

# 3. Header mới

Không dùng tab điều hướng trùng lặp như:

```text
Tạo audio | Kịch bản cảm xúc
```

Header chỉ nên thể hiện:

```text
Tạo audio mới

Viết nội dung, thêm cảm xúc, chọn giọng đọc và xuất audio.

Đã lưu tự động lúc 15:05
[Lưu nháp] [...]
```

Có thể thêm workflow indicator nhẹ:

```text
① Nội dung & Cảm xúc
→
② Giọng đọc & Xuất
```

Nhưng đây chỉ là progress indicator, không phải navigation tab.

---

# 4. Layout tổng thể

Desktop layout:

```text
┌─────────────┬────────────────────────────────────┬──────────────────────┐
│             │                                    │                      │
│   Sidebar   │           Editor Area              │    Render Panel      │
│             │                                    │                      │
│   220px     │             flexible               │       320px          │
│             │                                    │                      │
└─────────────┴────────────────────────────────────┴──────────────────────┘
```

Target sizing:

```text
Sidebar: 220–240px
Main:    minmax(0, 1fr)
Right:   320–350px
```

Responsive:

```text
small desktop
→ collapse sidebar
→ right panel thành Sheet
→ main editor full width
```

---

# 5. Shadcn Components

Ưu tiên dùng shadcn primitives.

| UI | shadcn |
|---|---|
| Shell | Sidebar |
| Main block | Card |
| Editor | Textarea |
| Actions | Button |
| Tags | Badge / Button |
| Tag picker | Popover + Command |
| Voice selector | Popover + Command |
| Speed | Slider |
| Output | ToggleGroup |
| Advanced section | Collapsible |
| Info | Tooltip |
| More actions | DropdownMenu |
| Validation | Alert |
| Divider | Separator |
| Mobile right panel | Sheet |
| Loading | Skeleton |
| Confirmation | AlertDialog |
| Job progress | Progress |
| Toast | Sonner |

Mục tiêu:

```text
~90% UI primitives từ shadcn
```

Custom component chỉ dùng cho domain-specific UI.

---

# 6. Target Feature Structure

```text
src/features/audio-studio/
│
├── components/
│   ├── audio-studio-page.tsx
│   ├── audio-studio-header.tsx
│   ├── script-editor.tsx
│   ├── import-toolbar.tsx
│   ├── emotion-panel.tsx
│   ├── emotion-tag.tsx
│   ├── delivery-panel.tsx
│   ├── voice-selector.tsx
│   ├── speed-control.tsx
│   ├── output-format.tsx
│   ├── render-preflight.tsx
│   └── generate-audio-button.tsx
│
├── hooks/
│   ├── use-script-analysis.ts
│   ├── use-audio-shortcuts.ts
│   └── use-audio-studio.ts
│
├── lib/
│   ├── script-parser.ts
│   ├── delivery-tags.ts
│   ├── emotion-tags.ts
│   └── preflight.ts
│
├── schemas/
│   └── audio-job.schema.ts
│
├── store/
│   └── audio-studio.store.ts
│
└── types.ts
```

Không để `audio-studio-page.tsx` trở thành một file rất lớn.

---

# 7. Main Editor Area

Main editor gồm ba block.

---

## 7.1 Nội dung kịch bản

UI:

```text
Nội dung kịch bản

[Dán] [Nhập TXT/SRT] [Nhập file] [Nhập thư mục]

┌─────────────────────────────────────────────┐
│                                             │
│ Dán hoặc nhập nội dung kịch bản vào đây... │
│                                             │
│                                             │
│                                             │
└─────────────────────────────────────────────┘

0 / 500,000 ký tự                    0 đoạn
```

Shadcn:

```text
Card
Button
Textarea
Tooltip
DropdownMenu
```

## Component

```text
ScriptEditor
ImportToolbar
```

## Nguyên tắc

- Reuse import logic hiện tại.
- Không rewrite file/SRT parser nếu đang chạy tốt.
- Chỉ đưa UI và logic shared vào feature mới.

---

# 8. Ngữ điệu & Cảm xúc

Thay vì để “Kịch bản cảm xúc” là page riêng, đưa trực tiếp vào editor.

UI:

```text
Ngữ điệu & cảm xúc
Thêm cách thể hiện cho toàn bài hoặc chèn vào từng đoạn.

[Cười] [Thở dài] [Hắng giọng]

[Bình tĩnh] [Vui] [Buồn] [Sợ hãi]
[Tức giận] [Bất ngờ] [Căng thẳng]
[Bí ẩn] [Kể chuyện]

[+ Thêm]
```

Visual semantics:

```text
Native cues    → green
Emotion intent → amber
Delivery       → blue
```

## Tooltip

Ví dụ:

```text
Native cue
Được engine hỗ trợ trực tiếp.
```

```text
Emotion
Melody dùng để sắp xếp và xử lý kịch bản.
```

## Shadcn

```text
Card
Badge
Button
Tooltip
Popover
Command
```

---

# 9. Delivery nâng cao

Mặc định collapsed.

UI:

```text
Delivery nâng cao                     [⌄]

Chậm
Nhanh
Ngắt ngắn
Ngắt dài
Nhấn mạnh
Nhẹ nhàng
Thì thầm
```

Dùng:

```text
Collapsible
```

Không cần Accordion nếu chỉ có một section.

---

# 10. Right Render Panel

Right panel sticky:

```text
sticky top-4
```

Gồm:

```text
Voice
Speed
Output
Preflight
CTA
```

---

# 11. Voice Selector

UI:

```text
Giọng đọc

┌──────────────────────────────┐
│ Minh Đức · Preset            │
│ vi-VN · Giọng nam            │
└──────────────────────────────┘
```

Click mở:

```text
Popover
└── Command
    ├── Search
    ├── Preset
    ├── Favorite
    └── Provider
```

Shadcn:

```text
Popover
Command
Badge
Avatar
```

Reuse voice data và provider logic hiện tại.

---

# 12. Speed Control

UI:

```text
Tốc độ đọc                    1.0x

────────●──────────

CHẬM HƠN                NHANH HƠN
```

Shadcn:

```text
Slider
Badge
```

Component:

```text
SpeedControl
```

---

# 13. Output Format

UI:

```text
Định dạng xuất      48 kHz · mono

[ MP3 ] [ WAV ]
```

Dùng:

```text
ToggleGroup
```

Không dùng hai Button độc lập.

Component:

```text
OutputFormat
```

---

# 14. Render Preflight

Giữ dark card để tạo hierarchy.

UI:

```text
Render preflight

12                5
đoạn văn bản      native cue

✓ Voice hỗ trợ VieNeu
✓ 5/5 native cues hợp lệ
✓ Cache theo segment
⚠ 1 emotion chỉ xử lý như intent

[Xem chi tiết →]
```

Preflight phải reactive.

Không cần user bấm “Review script” mới chạy.

## Shadcn

```text
Card
Separator
Button
Alert
ScrollArea
```

---

# 15. CTA

CTA nằm ngay dưới preflight.

UI:

```text
┌──────────────────────────────┐
│ ✨ Tạo audio                  │
│ Ctrl + Enter                 │
└──────────────────────────────┘
```

States:

```text
empty
→ disabled

invalid
→ disabled

ready
→ primary

processing
→ spinner/progress

completed
→ result/history
```

Dùng:

```text
Button size="lg"
Progress
```

---

# 16. State Ownership

Không tạo một mega Zustand store cho mọi thứ.

## TanStack Query

Dùng cho:

```text
voices
voice presets
provider capability
generation jobs
history
```

## Audio Studio client state

Dùng cho:

```text
content
tone
emotion tags
delivery tags
selected voice
speed
output format
```

Có thể dùng:

```text
local state
```

hoặc:

```text
feature Zustand store
```

nếu nhiều component cùng truy cập.

---

# 17. Tag Model

Không hardcode arrays trực tiếp trong component.

```ts
type DeliveryTag = {
  id: string
  label: string

  type:
    | "native"
    | "emotion"
    | "delivery"

  engine?: string[]

  token: string
}
```

Example:

```ts
{
  id: "laugh",
  label: "Cười",
  type: "native",
  token: "[cười]",
  engine: ["vieneu"],
}
```

```ts
{
  id: "calm",
  label: "Bình tĩnh",
  type: "emotion",
  token: "[bình tĩnh]",
}
```

---

# 18. Tag Insertion Flow

```text
tag click
↓
cursor position
↓
insert token
↓
update content
↓
parser reruns
↓
preflight updates
```

Không tạo hai tag systems riêng cho normal audio và emotional script.

---

# 19. Script Parser

Unified parser input:

```text
[sợ hãi] Linh nghe thấy tiếng động phía sau.

[bình tĩnh] Nam nói: Chỉ là gió thôi.
```

Target output:

```ts
type ScriptSegment = {
  id: string

  text: string

  cues: {
    type:
      | "native"
      | "emotion"
      | "delivery"

    value: string
  }[]
}
```

Parser output thêm:

```text
segments
characters
native cue count
emotion count
unsupported cues
estimated jobs
```

`RenderPreflight` dùng output này.

---

# 20. Generation Flow

Không đổi backend contract nếu không bắt buộc.

Unified flow:

```text
Editor
↓
Parser
↓
Preflight
↓
Build generation request
↓
Current queue
↓
TTS
↓
Output
```

Nếu script không có tag cảm xúc:

```text
normal generation path
```

Nếu có native/emotion/delivery:

```text
enhanced script path
```

User không cần biết backend có nhiều path.

---

# 21. Routing

Sau TanStack Router migration:

```text
/
```

là Audio Studio.

Sidebar:

```tsx
<Link to="/">
  Tạo audio
</Link>
```

Legacy:

```text
/scripts
```

sau khi merge ổn:

```text
redirect /
```

Không giữ hai UI song song lâu dài.

---

# 22. Autosave Draft

Không bắt buộc phase đầu.

Đưa vào sau khi generation flow ổn định.

Draft model:

```ts
{
  content,
  tags,
  voice,
  speed,
  format,
  updatedAt,
}
```

Có thể bắt đầu bằng local persistence.

UI:

```text
Đã lưu tự động lúc 15:05
```

---

# 23. Implementation Phases

---

## Phase 1 — Navigation & Sidebar

### Goal

Làm rõ information architecture.

### Tasks

- Replace sidebar hiện tại bằng shadcn Sidebar.
- Group navigation thành:
  - Tạo
  - Thư viện
  - Cài đặt
- Remove `Kịch bản cảm xúc` khỏi primary navigation.
- Giữ route cũ hoạt động tạm thời.

### Shadcn

```text
Sidebar
SidebarHeader
SidebarContent
SidebarGroup
SidebarGroupLabel
SidebarMenu
SidebarMenuItem
SidebarMenuButton
SidebarFooter
```

### Done when

```text
Sidebar rõ hierarchy
Không còn duplicate primary navigation
```

---

## Phase 2 — Audio Studio Shell

### Goal

Tạo unified page layout.

### Create

```text
audio-studio-page.tsx
audio-studio-header.tsx
```

### Layout

```tsx
<div className="grid min-h-0 grid-cols-[minmax(0,1fr)_21rem] gap-4">
  <main>
    ...
  </main>

  <aside>
    ...
  </aside>
</div>
```

### Done when

```text
Main editor render
Right panel render
Desktop layout stable
```

---

## Phase 3 — Script Editor

### Goal

Migrate UI của feature Tạo âm thanh vào Audio Studio.

### Create

```text
script-editor.tsx
import-toolbar.tsx
```

### Reuse

```text
paste
TXT/SRT
file
folder
character counter
```

### Rule

Không rewrite import/file pipeline nếu đang hoạt động.

---

## Phase 4 — Merge Emotional Script UI

### Goal

Đưa emotional script capability vào Audio Studio.

### Reuse

```text
native cue definitions
emotion definitions
tag insertion
SRT parsing
script review logic
provider-specific behavior
segment parsing
```

### Move shared logic to

```text
features/audio-studio/lib/
```

### Create

```text
emotion-panel.tsx
emotion-tag.tsx
delivery-panel.tsx
```

### Done when

```text
User có thể thêm emotion/native cue ngay trong Audio Studio
```

---

## Phase 5 — Voice & Output Controls

### Create

```text
voice-selector.tsx
speed-control.tsx
output-format.tsx
```

### Shadcn

```text
Popover
Command
Slider
ToggleGroup
Badge
```

### Reuse

```text
voice data
selected voice state
provider compatibility
speed behavior
output config
```

---

## Phase 6 — Unified Parser

### Goal

Một parser cho normal + emotional script.

### Create

```text
script-parser.ts
emotion-tags.ts
delivery-tags.ts
```

### Parser output

```text
segments
characters
native cues
emotion intents
delivery tags
unsupported cues
estimated jobs
```

### Done when

```text
normal script parse
emotional script parse
preflight có đủ metadata
```

Không cần viết test suite mới ở phase này nếu parser có thể verify bằng current data và smoke check.

---

## Phase 7 — Render Preflight

### Create

```text
render-preflight.tsx
preflight.ts
```

### Show

```text
segment count
native cue count
emotion count
provider support
unsupported tags
estimated jobs
```

### Behavior

```text
valid
→ CTA enabled

blocking issue
→ CTA disabled
```

---

## Phase 8 — Connect Generation

### Goal

Connect Audio Studio với generation pipeline hiện tại.

### Flow

```text
content
↓
parser
↓
preflight
↓
request builder
↓
queue
↓
TTS
```

### Rule

Không rewrite backend/TTS pipeline nếu không cần.

---

## Phase 9 — Keyboard Shortcuts

Add:

```text
Ctrl + Enter
→ Generate
```

Optional:

```text
Ctrl + S
→ Save draft
```

Create:

```text
use-audio-shortcuts.ts
```

---

## Phase 10 — Draft & Autosave

### Optional after core flow

Create:

```text
use-audio-studio.ts
```

hoặc store persistence.

### Save

```text
content
tags
voice
speed
format
```

### UI

```text
Đã lưu tự động lúc ...
```

---

## Phase 11 — Legacy `/scripts`

Khi unified Audio Studio ổn:

```text
/scripts
→ redirect /
```

Có thể giữ compatibility route một thời gian ngắn.

Không maintain hai feature UIs song song.

---

## Phase 12 — Cleanup Duplicate Logic

Search và cleanup:

```text
emotional-script-page
old generate page
duplicate tag definitions
duplicate voice selector
duplicate parser
duplicate preflight
duplicate generation UI
```

Target:

```text
ONE editor
ONE tag system
ONE voice selector
ONE parser
ONE preflight
ONE generation flow
```

---

# 24. Suggested File Migration

## Current likely areas

```text
src/components/emotional-script/
src/components/tts/
src/app/page.tsx
src/app/scripts/page.tsx
```

## Target

```text
src/features/audio-studio/
```

Move logic, không copy duplicate.

---

# 25. Visual Hierarchy Rules

## Main surface

```text
background
→ muted

cards
→ white / card

right preflight
→ dark contrast

CTA
→ primary violet
```

## Tag colors

```text
native
→ green

emotion
→ amber

delivery
→ blue
```

Không dùng quá nhiều màu ngoài ba semantic group này.

---

# 26. Header Rules

Header chỉ nên show:

```text
page title
short description
autosave status
draft action
more actions
```

Không show feature tabs trùng với sidebar.

---

# 27. Sidebar Rules

Sidebar chỉ dùng cho page-level navigation.

Không dùng sidebar cho:

```text
mode
editor state
emotion mode
output mode
```

Các mode này phải nằm trong content.

---

# 28. UX Rule

User phải có thể bắt đầu chỉ bằng:

```text
1. Dán text
2. Chọn voice
3. Tạo audio
```

Emotion/delivery là optional enhancement.

Không bắt user phải hiểu emotional scripting để dùng basic TTS.

---

# 29. Responsive Behavior

Desktop:

```text
Sidebar + Main + Right Panel
```

Narrow desktop:

```text
Collapsed Sidebar + Main + Right Panel
```

Very narrow:

```text
Sidebar Sheet
Main
Render Settings Sheet
```

Use shadcn:

```text
Sidebar
Sheet
```

---

# 30. Implementation Order

Recommended:

```text
Phase 1
Sidebar

Phase 2
Audio Studio shell

Phase 3
Editor/import

Phase 4
Emotion/delivery merge

Phase 5
Voice/output

Phase 6
Parser

Phase 7
Preflight

Phase 8
Generation

Phase 9
Shortcuts

Phase 10
Autosave

Phase 11
Legacy route redirect

Phase 12
Cleanup
```

Không làm tất cả cùng một commit.

---

# 31. Recommended Commits

```text
refactor(ui): simplify Melody sidebar navigation
```

```text
feat(audio-studio): add unified audio studio shell
```

```text
refactor(audio-studio): migrate script editor and import controls
```

```text
feat(audio-studio): integrate emotion and delivery controls
```

```text
refactor(audio-studio): unify voice and output controls
```

```text
refactor(audio-studio): add unified script parser
```

```text
feat(audio-studio): add render preflight
```

```text
refactor(audio-studio): connect existing generation pipeline
```

```text
feat(audio-studio): add keyboard shortcuts and draft state
```

```text
refactor(routes): redirect legacy emotional script route
```

```text
chore(audio-studio): remove duplicated legacy UI
```

---

# 32. Validation Strategy

Không cần viết test cases mới sớm.

Ưu tiên:

```text
1. build
2. UI render
3. navigation
4. existing TTS works
5. emotion tags work
6. voice selection works
7. queue works
8. output works
9. lint
10. existing tests
```

Smoke check thủ công:

```text
basic TTS
emotional script
TXT/SRT import
voice select
speed
MP3/WAV
queue
history
FFmpeg
provider compatibility
```

---

# 33. Definition of Done

User sidebar chỉ còn:

```text
Tạo audio
Phòng thu giọng
Thư viện giọng
Lịch sử
Cài đặt
```

Trong `Tạo audio`:

```text
Nội dung
+
Emotion
+
Delivery
+
Voice
+
Speed
+
Output
+
Preflight
+
Generate
```

Không còn câu hỏi:

```text
“Tôi nên chọn Tạo âm thanh hay Kịch bản cảm xúc?”
```

Technical target:

```text
ONE editor
ONE tag system
ONE parser
ONE voice selector
ONE generation flow
ONE preflight
```

---

# 34. Prompt cho Coding Agent

```text
Read `VOID_MELODY_UNIFIED_AUDIO_STUDIO_SHADCN_PLAN.md` completely before making changes.

Your task is to implement this plan from beginning to end.

Core rules:

1. Treat the current repository as source of truth.
2. Use this document as the architecture and UX target.
3. Execute phases in order.
4. Do not redesign unrelated pages.
5. Use shadcn/ui primitives wherever appropriate.
6. Do not create custom primitives when shadcn already provides a suitable component.
7. Preserve current TTS, provider, queue, FFmpeg, Tauri, auth, history and output behavior.
8. Reuse existing working business logic instead of rewriting it.
9. Move shared logic instead of copying it.
10. Do not keep two duplicate Audio/Emotional Script implementations after migration.
11. Do not write new automated tests early unless required to diagnose a concrete regression.
12. Use build/lint/existing tests/smoke checks as migration validation.
13. Keep each phase coherent and reviewable.
14. Continue through all phases unless a true blocker prevents progress.

First audit the existing implementations of:
- current Create Audio page
- Emotional Script page
- sidebar/navigation
- TTS components
- queue
- voice selection
- script parsing
- delivery/native cues
- provider-specific logic

Then implement the plan phase-by-phase.

At the end provide:

- completed phases
- changed files
- reused existing logic
- removed duplicated logic
- shadcn components used
- legacy routes remaining
- build status
- lint status
- existing test status
- smoke-check results
- remaining technical debt

Do not stop after Phase 1. Continue through the full plan unless blocked.
```
