import manifest from "./desktop-runtime-manifest.json";

export type DesktopTarget =
  | "aarch64-apple-darwin"
  | "x86_64-pc-windows-msvc";

export type SidecarEnvironmentInput = {
  apiToken: string;
  dataDir: string;
  catalogPath: string;
};

export type SidecarEnvironment = Record<string, string>;

export type SidecarEnvironmentManifest = {
  requiredSidecarEnv: readonly string[];
};

export type PreflightReport = {
  ok: boolean;
  missing: string[];
};

export const desktopRuntimeManifest = manifest;

export function buildSidecarEnvironment({
  apiToken,
  dataDir,
  catalogPath,
}: SidecarEnvironmentInput): SidecarEnvironment {
  return {
    PYTHONUNBUFFERED: "1",
    APP_ENV: "production",
    API_HOST: "127.0.0.1",
    API_PORT: "0",
    MELODY_API_TOKEN: apiToken,
    MELODY_DATA_DIR: dataDir,
    MELODY_CATALOG_PATH: catalogPath,
    TTS_APPLY_RATE_WITH_FFMPEG: "true",
    TTS_QUEUE_CONCURRENCY: "1",
    TTS_CHUNK_CONCURRENCY: "1",
  };
}

export function validateSidecarEnvironment(
  env: Record<string, string | undefined>,
  runtimeManifest: SidecarEnvironmentManifest = manifest,
): PreflightReport {
  const missing = runtimeManifest.requiredSidecarEnv.filter((name) => {
    const value = env[name];
    return value === undefined || value.trim().length === 0;
  });

  return {
    ok: missing.length === 0,
    missing: [...missing],
  };
}

export function formatPreflightFailure(report: PreflightReport): string {
  if (report.ok || report.missing.length === 0) {
    return "Runtime preflight passed";
  }

  return `Missing runtime configuration: ${report.missing.join(", ")}`;
}
