#!/usr/bin/env node

import { existsSync, readdirSync } from 'node:fs';
import { basename, join, relative, resolve } from 'node:path';

function fail(message) {
  throw new Error(message);
}

function parseArguments(argumentsList) {
  const options = { root: process.cwd() };
  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === '--root') options.root = argumentsList[++index];
    else if (argument === '--target') options.target = argumentsList[++index];
    else if (argument === '--windows-updater') options.windowsUpdater = argumentsList[++index];
    else fail(`Unknown argument: ${argument}`);
  }
  if (!options.root) fail('--root requires a directory');
  if (!options.target) fail('--target requires a Rust target triple');
  if (options.windowsUpdater && !['nsis', 'msi'].includes(options.windowsUpdater)) {
    fail('--windows-updater must be nsis or msi');
  }
  return options;
}

function filesBelow(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...filesBelow(path));
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

function requireMatchingSignature(archive, files) {
  if (!files.includes(`${archive}.sig`)) {
    fail(`Missing matching updater signature for ${archive}`);
  }
}

function pathBelow(bundleDirectory, path) {
  return relative(bundleDirectory, path).replaceAll('\\', '/');
}

function verifyMacos(bundleDirectory, files) {
  const dmgFiles = files.filter((path) => pathBelow(bundleDirectory, path).startsWith('dmg/') && path.endsWith('.dmg'));
  if (dmgFiles.length === 0) fail(`Missing macOS DMG below ${join(bundleDirectory, 'dmg')}`);

  const updaterArchives = files.filter((path) => {
    const pathFromBundle = pathBelow(bundleDirectory, path);
    return pathFromBundle.startsWith('macos/') && path.endsWith('.app.tar.gz');
  });
  if (updaterArchives.length === 0) {
    fail(`Missing macOS app updater archive below ${join(bundleDirectory, 'macos')}`);
  }
  for (const archive of updaterArchives) requireMatchingSignature(archive, files);
}

function verifyWindows(bundleDirectory, files, windowsUpdater) {
  const nsisInstaller = files.find((path) => {
    const pathFromBundle = pathBelow(bundleDirectory, path);
    return pathFromBundle.startsWith('nsis/') && basename(path).endsWith('-setup.exe');
  });
  if (!nsisInstaller) fail(`Missing Windows NSIS setup executable below ${join(bundleDirectory, 'nsis')}`);

  const updaterType = windowsUpdater ?? 'nsis';
  const updaterArchives = files.filter((path) => {
    const pathFromBundle = pathBelow(bundleDirectory, path);
    return pathFromBundle.startsWith(`${updaterType}/`) && path.endsWith(`.${updaterType}.zip`);
  });
  if (updaterArchives.length === 0) {
    fail(`Missing Windows ${updaterType.toUpperCase()} updater archive below ${bundleDirectory}`);
  }
  for (const archive of updaterArchives) requireMatchingSignature(archive, files);
}

function verifyReleaseAssets(root, target, windowsUpdater) {
  const bundleDirectory = resolve(root, 'apps', 'web', 'src-tauri', 'target', target, 'release', 'bundle');
  const files = filesBelow(bundleDirectory);
  if (target === 'aarch64-apple-darwin') verifyMacos(bundleDirectory, files);
  else if (target === 'x86_64-pc-windows-msvc') verifyWindows(bundleDirectory, files, windowsUpdater);
  else fail(`Unsupported release target: ${target}`);
  process.stdout.write(`Verified release assets for ${target} in ${bundleDirectory}\n`);
}

try {
  const options = parseArguments(process.argv.slice(2));
  verifyReleaseAssets(resolve(options.root), options.target, options.windowsUpdater);
} catch (error) {
  process.stderr.write(`verify-release-assets: ${error.message}\n`);
  process.exitCode = 1;
}
