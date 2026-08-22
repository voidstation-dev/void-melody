import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { verifyDesktopBundle } from "./verify-desktop-bundle.mjs";

const manifest = JSON.stringify({
  schemaVersion: 1,
  supportedTargets: {
    "aarch64-apple-darwin": {},
    "x86_64-pc-windows-msvc": {},
  },
});

const tauriConfig = JSON.stringify({
  bundle: {
    externalBin: ["bin/melody-api", "bin/ffmpeg"],
    resources: {
      "bin/Voice.json": "bin/Voice.json",
      "../src/lib/desktop-runtime-manifest.json": "runtime/desktop-runtime-manifest.json",
    },
  },
});

const verifier = fileURLToPath(new URL("./verify-desktop-bundle.mjs", import.meta.url));

function readFixtureFile(relativePath) {
  if (relativePath === "apps/web/src/lib/desktop-runtime-manifest.json") return manifest;
  if (relativePath === "apps/web/src-tauri/tauri.conf.json") return tauriConfig;
  throw new Error(`Unexpected fixture read: ${relativePath}`);
}

function writeFixtureFile(rootDir, relativePath, content = "fixture") {
  const path = join(rootDir, relativePath);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, content);
}

describe("desktop bundle verifier", () => {
  it("requires Windows sidecar, ffmpeg, catalog and manifest", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "x86_64-pc-windows-msvc",
      exists: (relativePath) => relativePath !== "bin/ffmpeg.exe",
      size: () => 1,
      readFile: readFixtureFile,
    });

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("bin/ffmpeg.exe");
  });

  it("rejects env files and signing keys from bundle inputs", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: () => 1,
      readFile: readFixtureFile,
      files: [
        "bin/melody-api-aarch64-apple-darwin",
        "runtime/.env",
        "runtime/key.pem",
        "runtime/secrets.txt",
      ],
    });

    expect(result.ok).toBe(false);
    expect(result.forbidden).toEqual(["runtime/.env", "runtime/key.pem", "runtime/secrets.txt"]);
  });

  it("rejects model cache paths from bundle inputs", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: () => 1,
      readFile: readFixtureFile,
      files: ["bin/melody-api-aarch64-apple-darwin", "models/cache.bin"],
    });

    expect(result.ok).toBe(false);
    expect(result.forbidden).toEqual(["models/cache.bin"]);
  });

  it("rejects an empty target input", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: (relativePath) => (relativePath === "bin/ffmpeg" ? 0 : 1),
      readFile: readFixtureFile,
    });

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("bin/ffmpeg");
  });

  it("requires a schema v1 manifest entry for the selected target", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: () => 1,
      readFile: (relativePath) => {
        if (relativePath === "apps/web/src/lib/desktop-runtime-manifest.json") {
          return JSON.stringify({ schemaVersion: 1, supportedTargets: {} });
        }
        return tauriConfig;
      },
    });

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("apps/web/src/lib/desktop-runtime-manifest.json");
  });

  it("requires the manifest to be mapped into the installer runtime directory", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: () => 1,
      readFile: (relativePath) => {
        if (relativePath === "apps/web/src/lib/desktop-runtime-manifest.json") return manifest;
        return JSON.stringify({
          bundle: {
            externalBin: ["bin/melody-api", "bin/ffmpeg"],
            resources: { "bin/Voice.json": "bin/Voice.json" },
          },
        });
      },
    });

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("apps/web/src-tauri/tauri.conf.json");
  });

  it("rejects forbidden Tauri resource destinations", () => {
    const result = verifyDesktopBundle({
      rootDir: "/fixture",
      target: "aarch64-apple-darwin",
      exists: () => true,
      size: () => 1,
      readFile: (relativePath) => {
        if (relativePath === "apps/web/src/lib/desktop-runtime-manifest.json") return manifest;
        return JSON.stringify({
          bundle: {
            externalBin: ["bin/melody-api", "bin/ffmpeg"],
            resources: {
              "bin/Voice.json": "bin/Voice.json",
              "../src/lib/desktop-runtime-manifest.json": "runtime/desktop-runtime-manifest.json",
              "runtime-config.json": "runtime/.env",
            },
          },
        });
      },
    });

    expect(result.ok).toBe(false);
    expect(result.forbidden).toContain("runtime/.env");
  });

  it("accepts pnpm's argument separator before validating the target", () => {
    const result = spawnSync(process.execPath, [verifier, "--", "--target", "unsupported-target"], {
      encoding: "utf8",
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("Unsupported desktop bundle target: unsupported-target");
  });

  it("accepts required macOS inputs with the required Tauri resource mappings", () => {
    const rootDir = mkdtempSync(join(tmpdir(), "voidmelody-desktop-bundle-"));
    try {
      writeFixtureFile(rootDir, "apps/web/src-tauri/bin/melody-api-aarch64-apple-darwin");
      writeFixtureFile(rootDir, "apps/web/src-tauri/bin/ffmpeg");
      writeFixtureFile(rootDir, "apps/web/src-tauri/bin/Voice.json", "[]");
      writeFixtureFile(rootDir, "apps/web/src/lib/desktop-runtime-manifest.json", manifest);
      writeFixtureFile(rootDir, "apps/web/src-tauri/tauri.conf.json", tauriConfig);

      expect(verifyDesktopBundle({ rootDir, target: "aarch64-apple-darwin" })).toEqual({
        ok: true,
        missing: [],
        forbidden: [],
      });
    } finally {
      rmSync(rootDir, { recursive: true, force: true });
    }
  });
});
