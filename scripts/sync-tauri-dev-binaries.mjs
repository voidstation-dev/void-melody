import fs from "node:fs"
import path from "node:path"
import { execFileSync } from "node:child_process"
import { fileURLToPath, pathToFileURL } from "node:url"

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

export function assertSidecarFresh(metadata, currentRevision) {
  if (!metadata || typeof metadata.source_revision !== "string") {
    throw new Error("Missing API sidecar build metadata. Run pnpm build:deps first.")
  }
  if (metadata.source_revision !== currentRevision) {
    throw new Error(
      `Found stale API sidecar built from ${metadata.source_revision}; current source is ${currentRevision}. Run pnpm build:deps first.`,
    )
  }
}

function sourceRevision() {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: projectRoot,
      encoding: "utf8",
    }).trim()
  } catch {
    throw new Error("Cannot determine the current source revision. Run this command inside the Git checkout.")
  }
}

function syncBinary(sourceName, destinationName, currentRevision) {
  const source = path.join(tauriBinDir, sourceName)
  const destination = path.join(tauriDebugDir, destinationName)
  if (!fs.existsSync(source)) {
    throw new Error(`Missing ${source}. Run pnpm build:deps first.`)
  }
  if (sourceName.startsWith("melody-api-")) {
    const metadataPath = `${source}.manifest.json`
    if (!fs.existsSync(metadataPath)) {
      throw new Error(`Missing ${metadataPath}. Run pnpm build:deps first.`)
    }
    let metadata
    try {
      metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"))
    } catch {
      throw new Error(`Invalid ${metadataPath}. Run pnpm build:deps first.`)
    }
    assertSidecarFresh(metadata, currentRevision)
  }
  fs.mkdirSync(tauriDebugDir, { recursive: true })
  try {
    if (fs.existsSync(destination)) {
      const sourceStat = fs.statSync(source)
      const destStat = fs.statSync(destination)
      if (sourceStat.size === destStat.size && sourceStat.mtimeMs <= destStat.mtimeMs) {
        console.log(`Up to date: ${sourceName} -> target/debug/${destinationName}`)
        return
      }
    }
    fs.copyFileSync(source, destination)
    if (process.platform !== "win32") fs.chmodSync(destination, 0o755)
    console.log(`Synced ${sourceName} -> target/debug/${destinationName}`)
  } catch (err) {
    if (err.code === "EBUSY" || err.code === "EPERM") {
      if (fs.existsSync(destination)) {
        const sourceStat = fs.statSync(source)
        const destStat = fs.statSync(destination)
        if (sourceStat.size === destStat.size) {
          console.warn(
            `[sync-tauri-dev-binaries] Warning: ${destinationName} is currently locked by a running process, but matching binary already exists. Skipping copy.`,
          )
          return
        }
      }
      const processName = path.parse(destinationName).name
      throw new Error(
        `Cannot overwrite ${destinationName} (resource busy or locked).\n` +
          `An instance of ${processName} is likely still running in the background.\n` +
          `Terminate the process (e.g. Stop-Process -Name "${processName}" in PowerShell) and retry.`,
        { cause: err },
      )
    }
    throw err
  }
}

const extension = process.platform === "win32" ? ".exe" : ""
const triple = targetTriple()
const currentRevision = sourceRevision()

export function syncBinaries() {
  syncBinary(`melody-api-${triple}${extension}`, `melody-api${extension}`, currentRevision)
  syncBinary(`ffmpeg-${triple}${extension}`, `ffmpeg${extension}`, currentRevision)
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  syncBinaries()
}
