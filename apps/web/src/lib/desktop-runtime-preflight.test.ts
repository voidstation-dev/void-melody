import { describe, expect, it } from "vitest";
import {
  buildSidecarEnvironment,
  evaluateNativePreflight,
  formatPreflightFailure,
  validateSidecarEnvironment,
} from "./desktop-runtime-preflight";

describe("desktop runtime preflight", () => {
  it("rejects a Windows report when the target-specific sidecar is absent", () => {
    const result = evaluateNativePreflight({
      platform: "windows",
      arch: "x86_64",
      targetTriple: "x86_64-pc-windows-msvc",
      hostEnvironmentRequired: [],
      resources: [
        { name: "bin/Voice.json", present: true },
        { name: "bin/ffmpeg.exe", present: true },
        { name: "bin/melody-api-x86_64-pc-windows-msvc.exe", present: false },
      ],
    });

    expect(result.ok).toBe(false);
    expect(result.missingResources).toEqual([
      "bin/melody-api-x86_64-pc-windows-msvc.exe",
    ]);
  });

  it("rejects reports from an unsupported platform", () => {
    const result = evaluateNativePreflight({
      platform: "unsupported",
      arch: "x86_64",
      targetTriple: "unsupported",
      hostEnvironmentRequired: [],
      resources: [],
    });

    expect(result).toEqual({
      ok: false,
      missingResources: [],
      unsupportedReason: "unsupported-platform",
    });
  });

  it("rejects a target triple that does not match the reported platform", () => {
    const result = evaluateNativePreflight({
      platform: "windows",
      arch: "x86_64",
      targetTriple: "aarch64-apple-darwin",
      hostEnvironmentRequired: [],
      resources: [
        { name: "bin/Voice.json", present: true },
        { name: "bin/ffmpeg", present: true },
        { name: "bin/melody-api-aarch64-apple-darwin", present: true },
      ],
    });

    expect(result).toEqual({
      ok: false,
      missingResources: [],
      unsupportedReason: "unsupported-target",
    });
  });

  it("rejects reports that require host environment configuration", () => {
    const result = evaluateNativePreflight({
      platform: "macos",
      arch: "aarch64",
      targetTriple: "aarch64-apple-darwin",
      hostEnvironmentRequired: ["PATH"],
      resources: [
        { name: "bin/Voice.json", present: true },
        { name: "bin/ffmpeg", present: true },
        { name: "bin/melody-api-aarch64-apple-darwin", present: true },
      ],
    });

    expect(result).toEqual({
      ok: false,
      missingResources: [],
      unsupportedReason: "host-environment-required",
    });
  });

  it("accepts a complete macOS report with no host dependencies", () => {
    const result = evaluateNativePreflight({
      platform: "macos",
      arch: "aarch64",
      targetTriple: "aarch64-apple-darwin",
      hostEnvironmentRequired: [],
      resources: [
        { name: "bin/Voice.json", present: true },
        { name: "bin/ffmpeg", present: true },
        { name: "bin/melody-api-aarch64-apple-darwin", present: true },
      ],
    });

    expect(result).toEqual({
      ok: true,
      missingResources: [],
      unsupportedReason: null,
    });
  });

  it("builds all required sidecar variables without persisting the token", () => {
    const env = buildSidecarEnvironment({
      apiToken: "runtime-token",
      dataDir: "/Users/test/Library/Application Support/VoidMelody",
      catalogPath: "/Applications/VoidMelody.app/Contents/Resources/bin/Voice.json",
    });

    expect(env).toEqual(expect.objectContaining({
      PYTHONUNBUFFERED: "1",
      APP_ENV: "production",
      API_HOST: "127.0.0.1",
      API_PORT: "0",
      MELODY_API_TOKEN: "runtime-token",
      MELODY_DATA_DIR: "/Users/test/Library/Application Support/VoidMelody",
      MELODY_CATALOG_PATH: "/Applications/VoidMelody.app/Contents/Resources/bin/Voice.json",
      TTS_APPLY_RATE_WITH_FFMPEG: "true",
      TTS_QUEUE_CONCURRENCY: "1",
      TTS_CHUNK_CONCURRENCY: "1",
    }));
    expect(Object.keys(env)).not.toContain("TAURI_SIGNING_PRIVATE_KEY");
  });

  it("reports missing injected variables by name only", () => {
    const result = validateSidecarEnvironment({ APP_ENV: "production" });

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("MELODY_API_TOKEN");
    expect(JSON.stringify(result)).not.toContain("runtime-token");
  });

  it("treats empty and whitespace-only values as missing", () => {
    const result = validateSidecarEnvironment({
      APP_ENV: "production",
      MELODY_API_TOKEN: "  ",
    });

    expect(result.missing).toContain("MELODY_API_TOKEN");
  });

  it("formats only missing variable names in a preflight failure", () => {
    expect(formatPreflightFailure({
      ok: false,
      missing: ["MELODY_API_TOKEN", "MELODY_DATA_DIR"],
    })).toBe("Missing runtime configuration: MELODY_API_TOKEN, MELODY_DATA_DIR");
  });

  it("does not emit malformed value-bearing missing entries", () => {
    const message = formatPreflightFailure({
      ok: false,
      missing: ["MELODY_API_TOKEN=secret"],
    });

    expect(message).not.toContain("MELODY_API_TOKEN=secret");
    expect(message).toBe("Missing runtime configuration");
  });
});
