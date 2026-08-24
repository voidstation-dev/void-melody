import fs from "node:fs"
import path from "node:path"
import { execFileSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const ffmpeg = path.join(projectRoot, "apps/web/src-tauri/bin/ffmpeg-x86_64-pc-windows-msvc.exe")
const blackMark1024 = path.join(
  projectRoot,
  "MELODY_FULL_BRAND_ASSET_PACK/melody-brand-assets/brand/melody-mark-black-1024.png",
)
const whiteMark1024 = path.join(
  projectRoot,
  "MELODY_FULL_BRAND_ASSET_PACK/melody-brand-assets/brand/melody-mark-white-1024.png",
)
const publicDir = path.join(projectRoot, "apps/web/public")

for (const s of [64, 128, 256, 512]) {
  execFileSync(ffmpeg, [
    "-y",
    "-i",
    blackMark1024,
    "-vf",
    `scale=${s}:${s}:flags=lanczos`,
    "-v",
    "error",
    path.join(publicDir, `melody-mark-black-${s}.png`),
  ])
  execFileSync(ffmpeg, [
    "-y",
    "-i",
    whiteMark1024,
    "-vf",
    `scale=${s}:${s}:flags=lanczos`,
    "-v",
    "error",
    path.join(publicDir, `melody-mark-white-${s}.png`),
  ])
}

fs.copyFileSync(path.join(publicDir, "melody-mark-black-128.png"), path.join(publicDir, "melody-mark-black.png"))
fs.copyFileSync(path.join(publicDir, "melody-mark-white-128.png"), path.join(publicDir, "melody-mark-white.png"))

console.log("Successfully generated theme-aware marks!")
