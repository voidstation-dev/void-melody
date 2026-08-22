import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const tauriBinDir = path.join(projectRoot, "apps/web/src-tauri/bin")
const tauriDebugDir = path.join(projectRoot, "apps/web/src-tauri/target/debug")

function targetTriple() {
  if (process.platform === "darwin") {
    return process.arch === "arm64" ? "aarch64-apple-darwin" : "x86_64-apple-darwin"
  }
  if (process.platform === "win32") return "x86_64-pc-windows-msvc"
  if (process.platform === "linux") return "x86_64-unknown-linux-gnu"
  throw new Error(`Unsupported platform: ${process.platform}-${process.arch}`)
}

function syncBinary(sourceName, destinationName) {
  const source = path.join(tauriBinDir, sourceName)
  const destination = path.join(tauriDebugDir, destinationName)
  if (!fs.existsSync(source)) {
    throw new Error(`Missing ${source}. Run pnpm build:deps first.`)
  }
  fs.mkdirSync(tauriDebugDir, { recursive: true })
  fs.copyFileSync(source, destination)
  if (process.platform !== "win32") fs.chmodSync(destination, 0o755)
  console.log(`Synced ${sourceName} -> target/debug/${destinationName}`)
}

const extension = process.platform === "win32" ? ".exe" : ""
const triple = targetTriple()
syncBinary(`melody-api-${triple}${extension}`, `melody-api${extension}`)
syncBinary(`ffmpeg-${triple}${extension}`, `ffmpeg${extension}`)
