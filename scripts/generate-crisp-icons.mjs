import fs from "node:fs"
import path from "node:path"
import { execFileSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const ffmpeg = path.join(projectRoot, "apps/web/src-tauri/bin/ffmpeg-x86_64-pc-windows-msvc.exe")
const whiteMarkPng = path.join(
  projectRoot,
  "MELODY_FULL_BRAND_ASSET_PACK/melody-brand-assets/brand/melody-mark-white-1024.png",
)
const tauriIconsDir = path.join(projectRoot, "apps/web/src-tauri/icons")
const webPublicDir = path.join(projectRoot, "apps/web/public")
const scratchDir = path.join(projectRoot, "apps/web/src-tauri/target/icon-gen-temp")

fs.mkdirSync(scratchDir, { recursive: true })

// 1. Decode white mark to raw RGBA using ffmpeg
console.log("Decoding 1024x1024 mark via ffmpeg...")
const rawMarkRgba = execFileSync(ffmpeg, ["-v", "error", "-i", whiteMarkPng, "-f", "rawvideo", "-pix_fmt", "rgba", "-"], {
  maxBuffer: 32 * 1024 * 1024,
})

const SIZE = 1024
const buffer = Buffer.alloc(SIZE * SIZE * 4)

// Rounded squircle helper (superellipse or smooth rounded rect)
const RADIUS = 210
const BORDER_WIDTH = 12

function getDistanceToRoundedBox(x, y, w, h, r) {
  // Center is (w/2, h/2)
  const cx = w / 2
  const cy = h / 2
  const px = Math.abs(x - cx) - (cx - r - 20)
  const py = Math.abs(y - cy) - (cy - r - 20)
  
  const ox = Math.max(px, 0)
  const oy = Math.max(py, 0)
  const outsideDist = Math.sqrt(ox * ox + oy * oy)
  const insideDist = Math.min(Math.max(px, py), 0)
  return outsideDist + insideDist - r
}

console.log("Rendering high-contrast dark container badge...")

for (let y = 0; y < SIZE; y++) {
  const t = y / SIZE
  // Dark void gradient: #0D1322 -> #05070E
  const bgR = Math.round(13 * (1 - t) + 5 * t)
  const bgG = Math.round(19 * (1 - t) + 7 * t)
  const bgB = Math.round(34 * (1 - t) + 14 * t)

  for (let x = 0; x < SIZE; x++) {
    const idx = (y * SIZE + x) * 4
    const d = getDistanceToRoundedBox(x, y, SIZE, SIZE, RADIUS)
    
    // Anti-aliased alpha
    let alpha = 0
    if (d <= 0) {
      alpha = 1
    } else if (d < 1.5) {
      alpha = 1 - (d / 1.5)
    }

    if (alpha <= 0) {
      buffer[idx] = 0
      buffer[idx + 1] = 0
      buffer[idx + 2] = 0
      buffer[idx + 3] = 0
      continue
    }

    // Border highlight
    let r = bgR
    let g = bgG
    let b = bgB

    if (d > -BORDER_WIDTH) {
      const borderT = (d + BORDER_WIDTH) / BORDER_WIDTH
      // subtle cyan-slate glow rim: #38BDF8 on top rim, #1E293B on bottom
      const rimR = Math.round(30 * (1 - t * 0.5))
      const rimG = Math.round(41 * (1 - t * 0.4))
      const rimB = Math.round(59 * (1 - t * 0.3))
      r = Math.round(r * (1 - borderT * 0.6) + rimR * (borderT * 0.6))
      g = Math.round(g * (1 - borderT * 0.6) + rimG * (borderT * 0.6))
      b = Math.round(b * (1 - borderT * 0.6) + rimB * (borderT * 0.6))
    }

    buffer[idx] = r
    buffer[idx + 1] = g
    buffer[idx + 2] = b
    buffer[idx + 3] = Math.round(alpha * 255)
  }
}

// Composite the white mark in center at ~74% scale with slight contrast enhancement
// Mark is 1024x1024, let's sample it scaled down to center
const MARK_SCALE = 0.74
const MARK_OFFSET = (SIZE * (1 - MARK_SCALE)) / 2

for (let y = 0; y < SIZE; y++) {
  const markY = Math.round((y - MARK_OFFSET) / MARK_SCALE)
  if (markY < 0 || markY >= SIZE) continue

  for (let x = 0; x < SIZE; x++) {
    const markX = Math.round((x - MARK_OFFSET) / MARK_SCALE)
    if (markX < 0 || markX >= SIZE) continue

    const markIdx = (markY * SIZE + markX) * 4
    const markA = rawMarkRgba[markIdx + 3] / 255
    if (markA <= 0) continue

    const dstIdx = (y * SIZE + x) * 4
    const dstA = buffer[dstIdx + 3] / 255
    if (dstA <= 0) continue

    const markR = rawMarkRgba[markIdx]
    const markG = rawMarkRgba[markIdx + 1]
    const markB = rawMarkRgba[markIdx + 2]

    // Alpha blending: over
    const outA = markA + dstA * (1 - markA)
    buffer[dstIdx] = Math.round((markR * markA + buffer[dstIdx] * dstA * (1 - markA)) / outA)
    buffer[dstIdx + 1] = Math.round((markG * markA + buffer[dstIdx + 1] * dstA * (1 - markA)) / outA)
    buffer[dstIdx + 2] = Math.round((markB * markA + buffer[dstIdx + 2] * dstA * (1 - markA)) / outA)
    buffer[dstIdx + 3] = Math.round(outA * 255)
  }
}

// 2. Write master 1024x1024 PNG
const masterPng = path.join(scratchDir, "master-1024.png")
console.log("Encoding master 1024x1024 PNG...")
execFileSync(
  ffmpeg,
  ["-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "1024x1024", "-i", "-", "-v", "error", masterPng],
  { input: buffer },
)

function generateSizePng(targetSize, outPath) {
  execFileSync(
    ffmpeg,
    [
      "-y",
      "-i",
      masterPng,
      "-vf",
      `scale=${targetSize}:${targetSize}:flags=lanczos`,
      "-v",
      "error",
      outPath,
    ],
  )
}

console.log("Generating all icon resolutions...")
const SIZES = [16, 24, 32, 44, 48, 64, 71, 89, 107, 128, 142, 150, 180, 192, 256, 284, 310, 512]
for (const s of SIZES) {
  generateSizePng(s, path.join(scratchDir, `icon-${s}x${s}.png`))
}

// 3. Build multi-resolution icon.ico with PNG frames
const icoSizes = [16, 24, 32, 48, 64, 128, 256]
const icoPngBuffers = icoSizes.map((s) => fs.readFileSync(path.join(scratchDir, `icon-${s}x${s}.png`)))

let headerLength = 6 + icoSizes.length * 16
let currentOffset = headerLength

const icoHeader = Buffer.alloc(headerLength)
icoHeader.writeUInt16LE(0, 0) // reserved
icoHeader.writeUInt16LE(1, 2) // type: 1 = ICO
icoHeader.writeUInt16LE(icoSizes.length, 4) // number of images

for (let i = 0; i < icoSizes.length; i++) {
  const size = icoSizes[i]
  const pngBuf = icoPngBuffers[i]
  const dirOffset = 6 + i * 16

  icoHeader.writeUInt8(size === 256 ? 0 : size, dirOffset) // width
  icoHeader.writeUInt8(size === 256 ? 0 : size, dirOffset + 1) // height
  icoHeader.writeUInt8(0, dirOffset + 2) // color count
  icoHeader.writeUInt8(0, dirOffset + 3) // reserved
  icoHeader.writeUInt16LE(1, dirOffset + 4) // color planes
  icoHeader.writeUInt16LE(32, dirOffset + 6) // bits per pixel
  icoHeader.writeUInt32LE(pngBuf.length, dirOffset + 8) // size of image data
  icoHeader.writeUInt32LE(currentOffset, dirOffset + 12) // offset of image data

  currentOffset += pngBuf.length
}

const finalIcoBuffer = Buffer.concat([icoHeader, ...icoPngBuffers])
const outIcoPath = path.join(tauriIconsDir, "icon.ico")
fs.writeFileSync(outIcoPath, finalIcoBuffer)
console.log("Written crisp icon.ico to", outIcoPath)

// Also write favicon.ico to web public
fs.writeFileSync(path.join(webPublicDir, "favicon.ico"), finalIcoBuffer)

// 4. Update specific Tauri icons
fs.copyFileSync(path.join(scratchDir, "icon-32x32.png"), path.join(tauriIconsDir, "32x32.png"))
fs.copyFileSync(path.join(scratchDir, "icon-128x128.png"), path.join(tauriIconsDir, "128x128.png"))
fs.copyFileSync(path.join(scratchDir, "icon-256x256.png"), path.join(tauriIconsDir, "128x128@2x.png"))
fs.copyFileSync(path.join(scratchDir, "icon-512x512.png"), path.join(tauriIconsDir, "icon.png"))
fs.copyFileSync(path.join(scratchDir, "icon-64x64.png"), path.join(tauriIconsDir, "64x64.png"))

// Windows Store Square Logos
const squareMap = {
  "Square30x30Logo.png": 32,
  "Square44x44Logo.png": 44,
  "Square71x71Logo.png": 71,
  "Square89x89Logo.png": 89,
  "Square107x107Logo.png": 107,
  "Square142x142Logo.png": 142,
  "Square150x150Logo.png": 150,
  "Square284x284Logo.png": 284,
  "Square310x310Logo.png": 310,
  "StoreLogo.png": 48,
}
for (const [name, s] of Object.entries(squareMap)) {
  fs.copyFileSync(path.join(scratchDir, `icon-${s}x${s}.png`), path.join(tauriIconsDir, name))
}

// 5. Update Web Public icons
fs.copyFileSync(path.join(scratchDir, "icon-512x512.png"), path.join(webPublicDir, "app-icon.png"))
fs.copyFileSync(path.join(scratchDir, "icon-128x128.png"), path.join(webPublicDir, "melody-logo-mark.png"))
fs.copyFileSync(path.join(scratchDir, "icon-180x180.png"), path.join(webPublicDir, "apple-touch-icon.png"))
fs.copyFileSync(path.join(scratchDir, "icon-192x192.png"), path.join(webPublicDir, "pwa-192x192.png"))
fs.copyFileSync(path.join(scratchDir, "icon-512x512.png"), path.join(webPublicDir, "pwa-512x512.png"))
fs.copyFileSync(path.join(scratchDir, "icon-32x32.png"), path.join(webPublicDir, "favicon-32x32.png"))
fs.copyFileSync(path.join(scratchDir, "icon-16x16.png"), path.join(webPublicDir, "favicon-16x16.png"))

console.log("All crisp icons generated and synced successfully!")
