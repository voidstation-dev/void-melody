#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const MANIFEST_PATH = "apps/web/src/lib/desktop-runtime-manifest.json";
const TAURI_CONFIG_PATH = "apps/web/src-tauri/tauri.conf.json";

const TARGET_INPUTS = {
  "aarch64-apple-darwin": [
    "bin/melody-api-aarch64-apple-darwin",
    "bin/ffmpeg",
    "bin/Voice.json",
  ],
  "x86_64-pc-windows-msvc": [
    "bin/melody-api-x86_64-pc-windows-msvc.exe",
    "bin/ffmpeg.exe",
    "bin/Voice.json",
  ],
};

const REQUIRED_EXTERNAL_BINARIES = ["bin/melody-api", "bin/ffmpeg"];
const REQUIRED_RESOURCES = {
  "bin/Voice.json": "bin/Voice.json",
  "../src/lib/desktop-runtime-manifest.json": "runtime/desktop-runtime-manifest.json",
};

function sourcePath(rootDir, relativePath) {
  if (relativePath.startsWith("bin/")) {
    return join(rootDir, "apps", "web", "src-tauri", relativePath);
  }
  return join(rootDir, relativePath);
}

function listFiles(directory, prefix = "") {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = `${prefix}${entry.name}`;
    if (entry.isDirectory()) return listFiles(join(directory, entry.name), `${relativePath}/`);
    return entry.isFile() ? [relativePath] : [];
  });
}

function isForbiddenInput(relativePath) {
  const normalized = relativePath.replaceAll("\\", "/").toLowerCase();
  return (
    /(^|\/)\.env(?:$|[._-])/.test(normalized)
    || /\.(?:key|pem)$/.test(normalized)
    || normalized.includes("secret")
    || normalized.includes("token")
    || /(?:^|\/)(?:model|models|cache)(?:$|[\/_.-])/.test(normalized)
  );
}

function parseJson(readFile, relativePath) {
  try {
    return JSON.parse(readFile(relativePath));
  } catch {
    return undefined;
  }
}

function hasRequiredTauriMapping(config) {
  if (!config || typeof config !== "object") return false;
  const bundle = config.bundle;
  if (!bundle || typeof bundle !== "object") return false;
  if (!Array.isArray(bundle.externalBin) || !REQUIRED_EXTERNAL_BINARIES.every((path) => bundle.externalBin.includes(path))) {
    return false;
  }
  if (!bundle.resources || Array.isArray(bundle.resources) || typeof bundle.resources !== "object") return false;
  return Object.entries(REQUIRED_RESOURCES).every(([source, destination]) => bundle.resources[source] === destination);
}

function configuredBundleInputs(config) {
  if (!config?.bundle || typeof config.bundle !== "object") return [];
  const externalBin = Array.isArray(config.bundle.externalBin) ? config.bundle.externalBin : [];
  const resources = config.bundle.resources;
  const resourcePaths = resources && !Array.isArray(resources) && typeof resources === "object"
    ? Object.entries(resources).flatMap(([source, destination]) => [source, destination])
    : [];
  return [...externalBin, ...resourcePaths];
}

export function verifyDesktopBundle({ rootDir, target, exists, size, readFile, files } = {}) {
  const requiredInputs = TARGET_INPUTS[target];
  if (!rootDir || !requiredInputs) {
    return { ok: false, missing: [MANIFEST_PATH], forbidden: [] };
  }

  const fileExists = exists ?? ((relativePath) => existsSync(sourcePath(rootDir, relativePath)));
  const fileSize = size ?? ((relativePath) => {
    try {
      return statSync(sourcePath(rootDir, relativePath)).size;
    } catch {
      return 0;
    }
  });
  const read = readFile ?? ((relativePath) => readFileSync(sourcePath(rootDir, relativePath), "utf8"));
  const missing = [];
  const requireNonEmpty = (relativePath) => {
    if (!fileExists(relativePath) || fileSize(relativePath) <= 0) missing.push(relativePath);
  };

  for (const relativePath of [...requiredInputs, MANIFEST_PATH]) requireNonEmpty(relativePath);

  const manifest = parseJson(read, MANIFEST_PATH);
  if (manifest?.schemaVersion !== 1 || !manifest.supportedTargets?.[target]) {
    missing.push(MANIFEST_PATH);
  }

  const tauriConfig = parseJson(read, TAURI_CONFIG_PATH);
  if (!hasRequiredTauriMapping(tauriConfig)) missing.push(TAURI_CONFIG_PATH);

  const bundleFiles = files ?? listFiles(join(rootDir, "apps", "web", "src-tauri", "bin"), "bin/");
  const forbidden = [...new Set([...bundleFiles, ...configuredBundleInputs(tauriConfig)])]
    .filter(isForbiddenInput);

  const uniqueMissing = [...new Set(missing)];
  return {
    ok: uniqueMissing.length === 0 && forbidden.length === 0,
    missing: uniqueMissing,
    forbidden,
  };
}

function inferredTarget() {
  if (process.platform === "darwin" && process.arch === "arm64") return "aarch64-apple-darwin";
  if (process.platform === "win32" && process.arch === "x64") return "x86_64-pc-windows-msvc";
  return undefined;
}

function parseArguments(argumentsList) {
  let target;
  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--") continue;
    if (argument !== "--target") throw new Error(`Unknown argument: ${argument}`);
    target = argumentsList[++index];
    if (!target) throw new Error("--target requires a target triple");
  }
  target ??= inferredTarget();
  if (!target) throw new Error("Unsupported desktop bundle target for this host");
  if (!TARGET_INPUTS[target]) throw new Error(`Unsupported desktop bundle target: ${target}`);
  if (target !== inferredTarget()) throw new Error(`Desktop bundle target mismatch: ${target}`);
  return target;
}

function main() {
  try {
    const target = parseArguments(process.argv.slice(2));
    const result = verifyDesktopBundle({ rootDir: resolve(dirname(fileURLToPath(import.meta.url)), ".."), target });
    if (!result.ok) {
      process.stderr.write(`desktop bundle verification failed for target ${target}\n`);
      for (const relativePath of result.missing) process.stderr.write(`missing: ${relativePath}\n`);
      for (const relativePath of result.forbidden) process.stderr.write(`forbidden: ${relativePath}\n`);
      process.exitCode = 1;
      return;
    }
    process.stdout.write(`desktop bundle inputs verified for target ${target}\n`);
  } catch (error) {
    process.stderr.write(`desktop bundle verification failed: ${error.message}\n`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
