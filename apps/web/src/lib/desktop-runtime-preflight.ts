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

export type RuntimePreflight = {
  platform: "macos" | "windows" | "unsupported";
  arch: string;
  targetTriple: string;
  resources: Array<{
    name: string;
    present: boolean;
  }>;
  hostEnvironmentRequired: string[];
};

export type NativePreflightEvaluation = {
  ok: boolean;
  missingResources: string[];
  unsupportedReason:
    | "unsupported-platform"
    | "unsupported-target"
    | "host-environment-required"
    | null;
};

export const desktopRuntimeManifest = manifest;

function isDesktopTarget(targetTriple: string): targetTriple is DesktopTarget {
  return targetTriple in manifest.supportedTargets;
}

export function evaluateNativePreflight(
  report: RuntimePreflight,
): NativePreflightEvaluation {
  if (report.platform !== "macos" && report.platform !== "windows") {
    return {
      ok: false,
      missingResources: [],
      unsupportedReason: "unsupported-platform",
    };
  }

  if (!isDesktopTarget(report.targetTriple)) {
    return {
      ok: false,
      missingResources: [],
      unsupportedReason: "unsupported-target",
    };
  }

  const target = manifest.supportedTargets[report.targetTriple];
  const targetArchitecture = report.targetTriple.split("-", 1)[0];
  if (
    target.platform !== report.platform
    || report.arch !== targetArchitecture
  ) {
    return {
      ok: false,
      missingResources: [],
      unsupportedReason: "unsupported-target",
    };
  }

  if (
    report.hostEnvironmentRequired.length !== manifest.hostEnvironmentRequired.length
    || report.hostEnvironmentRequired.some(
      (name, index) => name !== manifest.hostEnvironmentRequired[index],
    )
  ) {
    return {
      ok: false,
      missingResources: [],
      unsupportedReason: "host-environment-required",
    };
  }

  const requiredResources = [
    ...manifest.requiredResources,
    target.ffmpeg,
    target.sidecar,
  ];
  const missingResources = requiredResources.filter((name) =>
    !report.resources.some(
      (resource) => resource.name === name && resource.present,
    ),
  );

  return {
    ok: missingResources.length === 0,
    missingResources,
    unsupportedReason: null,
  };
}

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
  const knownNames = new Set([
    ...manifest.requiredSidecarEnv,
    ...manifest.requiredResources,
  ]);
  const safeMissing = report.missing.filter((name) => knownNames.has(name));

  if (report.ok) {
    return "Runtime preflight passed";
  }

  if (safeMissing.length === 0) {
    return "Missing runtime configuration";
  }

  return `Missing runtime configuration: ${safeMissing.join(", ")}`;
}
