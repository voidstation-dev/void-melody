# Void Melody — Vite + TanStack Migration Plan

> Target: migrate `apps/web` from Next.js static export to a lean Tauri-first frontend stack using Vite, TanStack Router, TanStack Query, Tailwind CSS v4, and shadcn/ui New York style without changing core product behavior.

## 1. Goals

### Primary goals

- Replace Next.js as the frontend build/runtime layer with Vite.
- Replace Next App Router with TanStack Router.
- Keep and standardize TanStack Query for server/API state.
- Upgrade Tailwind CSS v3 to Tailwind CSS v4.
- Normalize shadcn/ui to New York style with `rsc: false`.
- Preserve Tauri 2, Python API, sidecars, updater, FFmpeg, OmniVoice, auth, queue, and all existing product flows.
- Make route, API, form, and client state ownership explicit.
- Keep every migration phase independently testable and revertible.

### Non-goals

- No backend rewrite.
- No Tauri/Rust architectural rewrite.
- No OmniVoice/provider rewrite.
- No major visual redesign during infrastructure migration.
- No switch to TanStack Start.
- No React Hook Form to TanStack Form migration.
- No Zustand replacement unless a later feature requires it.

---

## 2. Current State

`apps/web` currently uses:

- Next.js 16
- React 19
- TanStack Query v5
- Tailwind CSS v3
- shadcn CLI
- Tauri 2
- Zustand
- React Hook Form + Zod
- Vitest + Testing Library + Playwright

Current web build flow:

```text
Next.js
  -> next build
  -> static export to apps/web/out
  -> Tauri frontendDist = ../out
```

Current routes:

```text
src/app/
├── layout.tsx
├── page.tsx
├── history/page.tsx
├── scripts/page.tsx
├── settings/page.tsx
├── vieneu/page.tsx
└── voices/page.tsx
```

Current providers in root layout:

```text
QueryProvider
ThemeProvider
I18nProvider
AuthProvider
TauriProvider
UpdateProvider
AuthGuard
QueueProvider
UpdateModal
```

Current Next-specific dependencies that must disappear:

```text
next
eslint-config-next
next/link
next/navigation
next/font
next-env.d.ts
next.config.mjs
src/app/* routing semantics
```

---

## 3. Target Architecture

```text
Tauri 2
  |
  +-- Vite
  |    +-- React 19
  |    +-- TanStack Router
  |    +-- TanStack Query
  |    +-- Zustand
  |    +-- React Hook Form + Zod
  |    +-- shadcn/ui New York
  |    +-- Tailwind CSS v4
  |
  +-- Tauri APIs / plugins
  |    +-- updater
  |    +-- dialog
  |    +-- shell
  |    +-- process
  |
  +-- sidecars
       +-- melody-api
       +-- ffmpeg
```

### State ownership rule

| State type | Owner |
|---|---|
| API/server data | TanStack Query |
| Route/navigation | TanStack Router |
| URL filters/search params | TanStack Router |
| Form state | React Hook Form |
| Validation | Zod |
| Global client-only state | Zustand |
| Local ephemeral UI state | React state |
| Desktop/runtime state | Tauri contexts/services |

Rule of thumb:

```text
Server state -> Query
URL state    -> Router
Form state   -> RHF
Client state -> Zustand / local state
Runtime      -> Tauri
```

---

## 4. Target Packages

### Add

```text
vite
@vitejs/plugin-react
@tailwindcss/vite
@tanstack/react-router
@tanstack/router-plugin
@tanstack/react-router-devtools
@tanstack/react-query-devtools
```

### Keep

```text
react
react-dom
@tanstack/react-query
zustand
react-hook-form
@hookform/resolvers
zod
shadcn
radix-ui
lucide-react
class-variance-authority
clsx
tailwind-merge
sonner
tw-animate-css
@tauri-apps/api
@tauri-apps/plugin-dialog
@tauri-apps/plugin-process
@tauri-apps/plugin-shell
@tauri-apps/plugin-updater
vitest
@testing-library/react
@testing-library/jest-dom
@testing-library/user-event
@playwright/test
```

### Remove when migration is green

```text
next
eslint-config-next
autoprefixer        # only if no longer used
```

---

## 5. Target Filesystem

```text
apps/web/
├── index.html
├── package.json
├── components.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
│
├── src/
│   ├── main.tsx
│   ├── router.tsx
│   ├── routeTree.gen.ts
│   │
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── index.tsx
│   │   ├── history.tsx
│   │   ├── scripts.tsx
│   │   ├── settings.tsx
│   │   ├── vieneu.tsx
│   │   └── voices.tsx
│   │
│   ├── app/
│   │   ├── app-providers.tsx
│   │   └── app-shell.tsx
│   │
│   ├── components/
│   │   ├── ui/
│   │   ├── app-shell/
│   │   ├── auth/
│   │   ├── tts/
│   │   ├── settings/
│   │   └── update/
│   │
│   ├── features/
│   │   ├── tts/
│   │   ├── voices/
│   │   ├── history/
│   │   ├── scripts/
│   │   └── settings/
│   │
│   ├── api/
│   ├── queries/
│   ├── mutations/
│   ├── contexts/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── stores/
│   ├── types/
│   ├── locales/
│   └── styles/
│       └── globals.css
│
└── src-tauri/
```

---

# Phase 0 — Establish Baseline

## Objective

Capture current behavior before infrastructure changes.

## Tasks

- [ ] Create migration branch, recommended: `refactor/vite-tanstack`.
- [ ] Run `pnpm lint:web`.
- [ ] Run `pnpm test:web`.
- [ ] Run `pnpm build:ui`.
- [ ] Run `pnpm dev:desktop`.
- [ ] Record existing failures separately from migration regressions.
- [ ] Capture screenshots of primary views.
- [ ] Smoke-test Tauri desktop flows.

## Smoke-test checklist

- [ ] App launches.
- [ ] Authentication/license flow works.
- [ ] Generate/TTS flow works.
- [ ] Scripts works.
- [ ] Voice Lab works.
- [ ] Voices works.
- [ ] History works.
- [ ] Settings works.
- [ ] Queue works.
- [ ] Audio download works.
- [ ] Updater UI initializes.
- [ ] FFmpeg sidecar can be invoked.
- [ ] `melody-api` sidecar can be invoked.

## Exit criteria

- [ ] Baseline is documented.
- [ ] Current known issues are separated from migration issues.
- [ ] Current production desktop app is reproducibly buildable.

---

# Phase 1 — Introduce Vite Build Pipeline

## Objective

Replace Next as bundler/dev server while keeping product behavior unchanged.

## Create

```text
apps/web/index.html
apps/web/vite.config.ts
apps/web/src/main.tsx
apps/web/src/vite-env.d.ts
apps/web/tsconfig.app.json
apps/web/tsconfig.node.json
```

## Modify

```text
apps/web/package.json
apps/web/tsconfig.json
apps/web/eslint.config.mjs
```

## Initial package scripts

Target:

```json
{
  "scripts": {
    "dev": "vite --port 3000",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "tauri": "tauri"
  }
}
```

If `tsc -b` creates too much migration noise initially, temporarily use:

```json
"build": "vite build"
```

Then restore explicit type-checking after routing is migrated.

## Initial `vite.config.ts`

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
})
```

TanStack Router plugin will be inserted in Phase 2 before `react()`.

## Initial `index.html`

```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta
      name="description"
      content="A premium Text to Speech Studio created by VoidStation."
    />
    <title>Melody - Text to Speech Studio</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

## Important constraint

Do **not** remove Next dependencies until Vite can render the application shell and production build is green.

## Exit criteria

- [ ] `pnpm --dir apps/web dev` starts Vite on port 3000.
- [ ] Vite renders a React root.
- [ ] `pnpm --dir apps/web build` emits `apps/web/dist`.
- [ ] No Tauri changes yet except temporary local validation if required.

---

# Phase 2 — Migrate Next App Router to TanStack Router

## Objective

Replace Next route semantics with TanStack Router using file-based routes.

## Add dependencies

```text
@tanstack/react-router
@tanstack/router-plugin
@tanstack/react-router-devtools
```

## Update `vite.config.ts`

Target plugin order:

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import path from "node:path"

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
})
```

## Route mapping

| Current Next route | TanStack route |
|---|---|
| `src/app/page.tsx` | `src/routes/index.tsx` |
| `src/app/history/page.tsx` | `src/routes/history.tsx` |
| `src/app/scripts/page.tsx` | `src/routes/scripts.tsx` |
| `src/app/settings/page.tsx` | `src/routes/settings.tsx` |
| `src/app/vieneu/page.tsx` | `src/routes/vieneu.tsx` |
| `src/app/voices/page.tsx` | `src/routes/voices.tsx` |
| `src/app/layout.tsx` | `src/routes/__root.tsx` + `src/app/app-providers.tsx` |

## Create `src/router.tsx`

Recommended initial history mode for Tauri: hash history.

```ts
import { createHashHistory, createRouter } from "@tanstack/react-router"
import { routeTree } from "./routeTree.gen"

const hashHistory = createHashHistory()

export const router = createRouter({
  routeTree,
  history: hashHistory,
  defaultPreload: "intent",
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
```

## Create `src/main.tsx`

```tsx
import React from "react"
import ReactDOM from "react-dom/client"
import { RouterProvider } from "@tanstack/react-router"
import { router } from "@/router"
import "@/styles/globals.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
```

## Route policy

Use hash history first because the desktop bundle does not have a traditional web server rewrite layer.

Target URLs:

```text
/#/
/#/scripts
/#/vieneu
/#/voices
/#/history
/#/settings
```

Browser history may be evaluated later after explicit Tauri deep-link/reload verification.

## Exit criteria

- [ ] All six routes render.
- [ ] Back/forward navigation works.
- [ ] Cold launch to app root works.
- [ ] Deep route navigation works inside Tauri.
- [ ] No Next route component is required at runtime.

---

# Phase 3 — Migrate Root Layout and App Providers

## Objective

Preserve provider ordering while removing framework-specific root layout behavior.

## Create

```text
src/app/app-providers.tsx
src/app/app-shell.tsx
src/routes/__root.tsx
```

## Recommended provider composition

```tsx
<QueryClientProvider client={queryClient}>
  <ThemeProvider>
    <I18nProvider>
      <AuthProvider>
        <TauriProvider>
          <UpdateProvider>
            <AuthGuard>
              <QueueProvider>
                <Outlet />
              </QueueProvider>
            </AuthGuard>

            <UpdateModal />
          </UpdateProvider>
        </TauriProvider>
      </AuthProvider>
    </I18nProvider>
  </ThemeProvider>
</QueryClientProvider>
```

## Remove Next-only root concerns

- [ ] Remove `next/font/google`.
- [ ] Move document title/description to `index.html` or route head metadata strategy.
- [ ] Remove `<html>` and `<body>` rendering from React root layout.
- [ ] Remove `suppressHydrationWarning` unless another dependency specifically requires it.
- [ ] Remove `"use client"` directives as files are migrated.

## Font recommendation

Prefer one of:

1. Local/self-hosted Geist font files managed by normal CSS.
2. `@fontsource` package.
3. System font stack if product does not require exact Geist rendering.

Do not depend on a framework font loader after migration.

## Exit criteria

- [ ] Provider order remains functionally equivalent.
- [ ] Auth guard behavior is unchanged.
- [ ] Queue lifecycle is unchanged.
- [ ] Updater modal lifecycle is unchanged.
- [ ] No `next/font` import remains.

---

# Phase 4 — Migrate Navigation to TanStack Router

## Objective

Remove `next/link` and `next/navigation` dependencies.

## Current pattern to remove

```tsx
import Link from "next/link"
import { usePathname } from "next/navigation"
```

## Target pattern

```tsx
import { Link } from "@tanstack/react-router"
```

Use route-native active styling:

```tsx
<Link
  to="/voices"
  activeProps={{
    className: "bg-primary/10 text-primary font-bold shadow-xs",
  }}
  inactiveProps={{
    className: "text-muted-foreground hover:bg-muted hover:text-foreground",
  }}
>
  Voices
</Link>
```

## Tasks

- [ ] Migrate sidebar links.
- [ ] Search for every `next/link` import.
- [ ] Search for every `next/navigation` import.
- [ ] Replace `router.push` / `replace` with TanStack navigation APIs.
- [ ] Replace pathname comparisons with typed route matching or active props.

## Exit criteria

- [ ] No `next/link` import remains.
- [ ] No `next/navigation` import remains.
- [ ] Navigation is type-safe.
- [ ] Active sidebar state is correct for every route.

---

# Phase 5 — Integrate Vite Output with Tauri

## Objective

Switch Tauri frontend build output from Next `out` to Vite `dist`.

## Modify

`apps/web/src-tauri/tauri.conf.json`

From:

```json
"frontendDist": "../out"
```

To:

```json
"frontendDist": "../dist"
```

Keep:

```json
"devUrl": "http://localhost:3000",
"beforeDevCommand": "pnpm run dev",
"beforeBuildCommand": "pnpm run build"
```

## Critical regression tests

- [ ] `pnpm dev:desktop` launches Vite automatically.
- [ ] `pnpm build:desktop` uses Vite production output.
- [ ] `melody-api` sidecar still resolves.
- [ ] FFmpeg sidecar still resolves.
- [ ] `bin/Voice.json` resource still resolves.
- [ ] updater plugin still initializes.
- [ ] shell plugin works.
- [ ] dialog plugin works.
- [ ] process plugin works.

## Exit criteria

- [ ] Development desktop build works.
- [ ] Production desktop build works.
- [ ] Sidecars/resources are unaffected.

---

# Phase 6 — Tailwind CSS v3 to v4

## Objective

Migrate CSS infrastructure only after Vite + Router + Tauri are stable.

## Package changes

Add/update:

```text
tailwindcss@latest
@tailwindcss/vite
```

Remove when unused:

```text
autoprefixer
```

## Move global stylesheet

From:

```text
src/app/globals.css
```

To:

```text
src/styles/globals.css
```

## Replace v3 directives

Remove:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Use:

```css
@import "tailwindcss";
```

## Configuration direction

Prefer CSS-first Tailwind v4 configuration.

Target removal after migration:

```text
tailwind.config.ts
postcss.config.js   # if nothing else uses PostCSS
```

## Token migration

Preserve existing visual values first. Do not redesign tokens while moving to v4.

Recommended sequence:

1. Port existing CSS variables exactly.
2. Make shadcn v4 utilities resolve correctly.
3. Run visual regression check.
4. Only then consider OKLCH/token cleanup.

## Exit criteria

- [ ] Tailwind v4 is active.
- [ ] `@tailwind` v3 directives are gone.
- [ ] Existing screens have no intentional visual changes.
- [ ] Production CSS is emitted correctly in Vite build.

---

# Phase 7 — Normalize shadcn/ui to New York

## Objective

Move the existing shadcn setup to the requested New York style without overwriting product-specific customizations.

## Target `components.json`

Conceptually:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/styles/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

## Migration policy

Do **not** regenerate every component and overwrite the current UI.

Migrate in groups:

1. [ ] button / input / label / textarea
2. [ ] dialog / sheet / popover / tooltip
3. [ ] select / dropdown-menu / command
4. [ ] form
5. [ ] table
6. [ ] sidebar/navigation primitives
7. [ ] sonner/toast

For every customized component:

```text
existing component
  -> compare with current New York output
  -> manually reconcile
  -> preserve app-specific behavior/classes
```

## Exit criteria

- [ ] `style` is New York.
- [ ] `rsc` is false.
- [ ] All UI primitives compile with Tailwind v4.
- [ ] No application-specific behavior is lost.

---

# Phase 8 — Standardize TanStack Query

## Objective

Keep Query v5 but introduce predictable query/mutation ownership and reusable query options.

## Recommended structure

```text
src/
├── api/
│   ├── client.ts
│   ├── auth.ts
│   ├── voices.ts
│   ├── history.ts
│   └── tts.ts
│
├── queries/
│   ├── auth.queries.ts
│   ├── voices.queries.ts
│   ├── history.queries.ts
│   └── providers.queries.ts
│
└── mutations/
    ├── generate.mutation.ts
    └── voices.mutation.ts
```

## Query pattern

```ts
import { queryOptions } from "@tanstack/react-query"
import { getVoices } from "@/api/voices"

export const voiceQueries = {
  all: () => ["voices"] as const,

  list: () =>
    queryOptions({
      queryKey: [...voiceQueries.all(), "list"],
      queryFn: getVoices,
    }),
}
```

## Rules

- [ ] API functions do not own React state.
- [ ] Components should not manually mirror Query data into Zustand.
- [ ] Query keys are centralized by domain.
- [ ] Mutations invalidate/update known query keys.
- [ ] Raw `useEffect(fetch...)` patterns are replaced where they represent server/API state.

## Keep current defaults initially

```ts
queries: {
  staleTime: 60_000,
  refetchOnWindowFocus: false,
}
```

Tune later based on real data behavior.

## Exit criteria

- [ ] API state ownership is explicit.
- [ ] Query keys are predictable.
- [ ] No duplicate global cache exists for server state.

---

# Phase 9 — Integrate Router + Query

## Objective

Use route loaders to preload Query data and improve navigation responsiveness.

## Router context

```ts
import type { QueryClient } from "@tanstack/react-query"

export interface RouterContext {
  queryClient: QueryClient
}
```

## Router creation

```ts
export const router = createRouter({
  routeTree,
  history: hashHistory,
  context: {
    queryClient,
  },
  defaultPreload: "intent",
})
```

## Example route loader

```ts
export const Route = createFileRoute("/voices")({
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(
      voiceQueries.list(),
    ),
  component: VoicesPage,
})
```

## Expected flow

```text
hover/focus navigation
  -> Router intent preload
  -> route loader
  -> Query cache warm
  -> navigate
  -> render from cache
```

## Exit criteria

- [ ] Appropriate read-heavy routes preload data.
- [ ] No duplicate request is caused by route loader + component query.
- [ ] Loading states are simpler and consistent.

---

# Phase 10 — Move Filter State to Router Search Params

## Objective

Move navigation-relevant filters from component-only state to typed URL search state.

## Candidate examples

```text
/history?provider=omnivoice&status=completed
/voices?language=vi&gender=female
```

## Use URL state when it should be

- shareable
- reload-safe
- back/forward aware
- bookmarkable
- deep-linkable

## Keep local state when it is

- transient
- visual-only
- not meaningful outside the current component lifecycle

## Exit criteria

- [ ] Important filters survive reload.
- [ ] Back/forward restores filter state.
- [ ] Search params are validated/typed.

---

# Phase 11 — Environment Variable Migration

## Objective

Remove all Next environment assumptions.

## Search for

```text
process.env.NEXT_PUBLIC_*
process.env.* used in browser code
```

## Migrate public frontend values to

```text
import.meta.env.VITE_*
```

Example:

```ts
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
```

## Add typings if required

```ts
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

## Security rule

Anything exposed through `VITE_*` is frontend-public. Never migrate secrets into Vite-prefixed variables.

## Exit criteria

- [ ] No browser code depends on `NEXT_PUBLIC_*`.
- [ ] No frontend secret is accidentally exposed.

---

# Phase 12 — TypeScript Cleanup

## Objective

Remove Next-specific TypeScript config and improve type safety after runtime migration is stable.

## Remove

- [ ] Next TS plugin.
- [ ] `.next/types/**/*.ts` includes.
- [ ] `.next/dev/types/**/*.ts` includes.
- [ ] `next-env.d.ts`.

## Progressive strictness

Do not enable every strict option during Vite/Router migration.

Recommended order:

1. [ ] Make Vite + Router compile with current tolerance.
2. [ ] Enable `strict: true`.
3. [ ] Fix domain by domain.
4. [ ] Consider `noUncheckedIndexedAccess: true`.

## Exit criteria

- [ ] No Next TS config remains.
- [ ] `strict: true` is enabled or has a separately tracked follow-up issue with remaining blockers.

---

# Phase 13 — Remove Next Compatibility Layer

## Objective

Delete framework artifacts only after Tauri dev/build is proven stable.

## Delete

```text
apps/web/next.config.mjs
apps/web/next-env.d.ts
apps/web/src/app/
```

Delete when Tailwind v4 migration is complete:

```text
apps/web/tailwind.config.ts
apps/web/postcss.config.js   # if unused
```

## Remove dependencies

```text
next
eslint-config-next
```

## Repository-wide searches

All should return zero product-code matches:

```text
next/link
next/navigation
next/font
from "next"
from 'next'
"use client"
NEXT_PUBLIC_
.next/
```

## Exit criteria

- [ ] Next is absent from `apps/web/package.json`.
- [ ] No Next build files remain.
- [ ] No Next runtime imports remain.

---

# Recommended PR Sequence

## PR 1 — Baseline

```text
chore(web): establish frontend migration baseline
```

Scope:

- tests
- screenshots/checklist
- no runtime architecture changes

## PR 2 — Vite

```text
build(web): migrate frontend build pipeline to Vite
```

Scope:

- Vite config
- index.html
- Vite entry
- package scripts
- no Query refactor
- no UI redesign

## PR 3 — TanStack Router

```text
refactor(web): migrate routing to TanStack Router
```

Scope:

- route tree
- root route
- navigation
- hash history

## PR 4 — Tauri frontend output

```text
build(desktop): switch Tauri frontend output to Vite
```

Scope:

- `frontendDist`
- desktop smoke tests
- sidecars/resources validation

## PR 5 — Tailwind v4

```text
style(web): migrate Tailwind CSS to v4
```

Scope:

- CSS engine only
- preserve current appearance

## PR 6 — shadcn New York

```text
refactor(ui): normalize shadcn to New York style
```

Scope:

- component primitives
- no feature redesign

## PR 7 — Query architecture

```text
refactor(data): standardize TanStack Query ownership
```

Scope:

- query options
- mutations
- API boundaries

## PR 8 — Router + Query preloading

```text
perf(web): add route-aware query preloading
```

Scope:

- router context
- route loaders
- `ensureQueryData`

## PR 9 — Remove Next

```text
chore(web): remove Next.js compatibility layer
```

Scope:

- delete Next files/deps
- repository-wide cleanup

## PR 10 — Strict TypeScript

```text
refactor(web): tighten TypeScript configuration
```

Scope:

- strictness only
- no product behavior changes

---

# File-by-File Change Matrix

## Create

```text
apps/web/index.html
apps/web/vite.config.ts
apps/web/tsconfig.app.json
apps/web/tsconfig.node.json
apps/web/src/main.tsx
apps/web/src/router.tsx
apps/web/src/vite-env.d.ts
apps/web/src/routes/__root.tsx
apps/web/src/routes/index.tsx
apps/web/src/routes/history.tsx
apps/web/src/routes/scripts.tsx
apps/web/src/routes/settings.tsx
apps/web/src/routes/vieneu.tsx
apps/web/src/routes/voices.tsx
apps/web/src/app/app-providers.tsx
apps/web/src/app/app-shell.tsx
apps/web/src/styles/globals.css
```

Generated:

```text
apps/web/src/routeTree.gen.ts
```

## Move / migrate content

```text
src/app/page.tsx             -> src/routes/index.tsx
src/app/history/page.tsx     -> src/routes/history.tsx
src/app/scripts/page.tsx     -> src/routes/scripts.tsx
src/app/settings/page.tsx    -> src/routes/settings.tsx
src/app/vieneu/page.tsx      -> src/routes/vieneu.tsx
src/app/voices/page.tsx      -> src/routes/voices.tsx
src/app/layout.tsx           -> __root.tsx + app-providers.tsx
src/app/globals.css          -> src/styles/globals.css
```

## Modify

```text
apps/web/package.json
apps/web/components.json
apps/web/tsconfig.json
apps/web/eslint.config.mjs
apps/web/src-tauri/tauri.conf.json
apps/web/src/components/app-shell/app-sidebar.tsx
apps/web/src/components/providers/query-provider.tsx
```

Plus every file importing:

```text
next/link
next/navigation
next/font
```

## Delete at end

```text
apps/web/next.config.mjs
apps/web/next-env.d.ts
apps/web/src/app/
apps/web/tailwind.config.ts
apps/web/postcss.config.js   # if unused
```

---

# Testing Strategy

## Unit/component

Keep Vitest + Testing Library.

Required coverage during migration:

- [ ] auth guard behavior
- [ ] app shell rendering
- [ ] sidebar active state
- [ ] voices page
- [ ] updater settings
- [ ] queue state where practical

## Router tests

Add focused tests for:

- [ ] root route renders
- [ ] all routes resolve
- [ ] navigation transitions
- [ ] search param validation
- [ ] unknown routes / not-found behavior

## Query tests

Test:

- [ ] query keys
- [ ] mutation invalidation
- [ ] loader prefetching
- [ ] no duplicate request after `ensureQueryData`

## Tauri smoke tests

Manual or automated where possible:

- [ ] cold start
- [ ] app reload
- [ ] navigate all routes
- [ ] generate audio
- [ ] queue job
- [ ] download audio
- [ ] open dialog
- [ ] run FFmpeg
- [ ] sidecar connectivity
- [ ] updater check

---

# Migration Risks

## Risk 1 — Tauri navigation/deep routing

Mitigation:

- Start with hash history.
- Test cold launch and reload explicitly.
- Do not optimize for pretty URLs before desktop reliability is proven.

## Risk 2 — Font differences

Mitigation:

- Replace `next/font` separately.
- Capture typography screenshots before migration.

## Risk 3 — Tailwind v4 visual regression

Mitigation:

- Preserve existing tokens first.
- Do not combine token redesign with engine migration.

## Risk 4 — shadcn overwrite

Mitigation:

- Never bulk-regenerate customized components blindly.
- Diff New York primitives one component group at a time.

## Risk 5 — environment variable exposure

Mitigation:

- Audit every `process.env` usage.
- Treat all `VITE_*` variables as public.

## Risk 6 — Query/Zustand duplication

Mitigation:

- Do not mirror API responses into Zustand unless the state has true client-only semantics.

## Risk 7 — scope explosion

Mitigation:

- No visual redesign during Vite/Router/Tailwind infrastructure PRs.
- No backend/provider refactor inside frontend migration PRs.

---

# Definition of Done

The migration is complete only when all items below are true.

## Build/runtime

- [ ] Vite is the only frontend bundler/dev server.
- [ ] `pnpm dev:web` works.
- [ ] `pnpm build:ui` works.
- [ ] `pnpm dev:desktop` works.
- [ ] `pnpm build:desktop` works.
- [ ] Tauri loads `../dist`.

## Routing

- [ ] TanStack Router owns all app routes.
- [ ] Hash history is stable in desktop builds.
- [ ] Navigation is type-safe.
- [ ] Back/forward works.
- [ ] No `next/link` remains.
- [ ] No `next/navigation` remains.

## Data

- [ ] TanStack Query remains the owner of API/server state.
- [ ] Query keys are centralized.
- [ ] Relevant routes preload Query data.
- [ ] Zustand is not duplicating server state.

## UI/CSS

- [ ] Tailwind CSS v4 is active.
- [ ] shadcn uses New York style.
- [ ] `rsc` is false.
- [ ] Existing major views have no unintended visual regressions.

## Next removal

- [ ] `next` dependency is removed.
- [ ] `eslint-config-next` is removed.
- [ ] `next.config.mjs` is deleted.
- [ ] `next-env.d.ts` is deleted.
- [ ] `src/app` is deleted after route migration.
- [ ] No `next/font` remains.
- [ ] No `"use client"` compatibility directives remain.

## Product behavior

- [ ] Auth/license works.
- [ ] Generate/TTS works.
- [ ] Scripts works.
- [ ] Voice Lab works.
- [ ] Voices works.
- [ ] History works.
- [ ] Settings works.
- [ ] Queue works.
- [ ] Audio download works.
- [ ] updater works.
- [ ] FFmpeg works.
- [ ] melody-api sidecar works.

---

# Recommended Final Stack

```text
Tauri 2
+ Vite
+ React 19
+ TanStack Router
+ TanStack Query v5
+ Zustand
+ React Hook Form
+ Zod
+ Tailwind CSS v4
+ shadcn/ui New York
+ radix-ui
```

This architecture treats Void Melody as what it actually is: a Tauri desktop application with a React client, rather than a server-rendered web application. The migration should therefore remove framework-specific web-server abstractions while preserving all desktop/runtime and product behavior.
