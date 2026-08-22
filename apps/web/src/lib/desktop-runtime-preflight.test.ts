import { describe, expect, it } from "vitest";
import {
  buildSidecarEnvironment,
  formatPreflightFailure,
  validateSidecarEnvironment,
} from "./desktop-runtime-preflight";

describe("desktop runtime preflight", () => {
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
});
