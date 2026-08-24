# Melody Brand Asset Pack

Generated asset pack for the Void Melody web app and Tauri desktop app.

## Folder structure

### `brand/`
Master branding assets:
- `melody-mark-*` = icon only
- `melody-wordmark-*` = icon + Melody text
- white variants = use on dark backgrounds
- black variants = use on light backgrounds
- PNG + lossless WebP masters included

### `web/`
Ready for `apps/web/public/`:
- `favicon.ico`
- `favicon-16x16.png`
- `favicon-32x32.png`
- `apple-touch-icon.png`
- `pwa-192x192.png`
- `pwa-512x512.png`
- additional icon sizes
- `site.webmanifest`
- header logo assets

Suggested copy:

```bash
cp -R melody-brand-assets/web/* apps/web/public/
```

Example HTML:

```html
<link rel="icon" href="/favicon.ico" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<link rel="manifest" href="/site.webmanifest" />
```

### `tauri/icons/`
Ready for `apps/web/src-tauri/icons/`.

Includes:
- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.png`
- `icon.ico`
- `icon.icns`
- Windows Store/MSIX Square logo variants

Suggested copy:

```bash
cp -R melody-brand-assets/tauri/icons/* apps/web/src-tauri/icons/
```

Expected Tauri config:

```json
"icon": [
  "icons/32x32.png",
  "icons/128x128.png",
  "icons/128x128@2x.png",
  "icons/icon.icns",
  "icons/icon.ico"
]
```

## Recommended usage

- App/launcher icon: `melody-mark-white-*` or files under `tauri/icons/`
- Sidebar compact mark: `web/melody-logo-mark.png`
- Dark header/title surface: `web/melody-logo-header-white.png`
- Light surface: `web/melody-logo-header-black.png`
- Website/PWA icons: files under `web/`

## Note

The supplied identity is a monochrome white logo. For usability on light surfaces, this pack also includes a derived black monochrome variant while preserving the same mark and geometry.
