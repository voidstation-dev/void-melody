import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const verifier = join(repositoryRoot, 'scripts', 'verify-release-assets.mjs');

function createFixture(target) {
  const root = mkdtempSync(join(tmpdir(), 'voidmelody-release-assets-'));
  const bundleDirectory = join(root, 'apps', 'web', 'src-tauri', 'target', target, 'release', 'bundle');
  mkdirSync(bundleDirectory, { recursive: true });
  return { root, bundleDirectory };
}

function createFile(path, contents = 'fixture') {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, contents);
}

function runVerifier(root, target, windowsUpdater) {
  const argumentsList = [verifier, '--root', root, '--target', target];
  if (windowsUpdater) argumentsList.push('--windows-updater', windowsUpdater);
  return spawnSync(process.execPath, argumentsList, { encoding: 'utf8' });
}

test('accepts the signed macOS DMG and app updater archive in the target bundle directory', () => {
  const { root, bundleDirectory } = createFixture('aarch64-apple-darwin');
  try {
    createFile(join(bundleDirectory, 'dmg', 'VoidMelody_0.3.0_aarch64.dmg'));
    const updaterArchive = join(bundleDirectory, 'macos', 'VoidMelody.app.tar.gz');
    createFile(updaterArchive);
    createFile(`${updaterArchive}.sig`);

    const result = runVerifier(root, 'aarch64-apple-darwin');
    assert.equal(result.status, 0, result.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('accepts the configured signed NSIS updater archive and setup executable', () => {
  const { root, bundleDirectory } = createFixture('x86_64-pc-windows-msvc');
  try {
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.exe'));
    const updaterArchive = join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.nsis.zip');
    createFile(updaterArchive);
    createFile(`${updaterArchive}.sig`);

    const result = runVerifier(root, 'x86_64-pc-windows-msvc', 'nsis');
    assert.equal(result.status, 0, result.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('accepts a configured signed MSI updater archive', () => {
  const { root, bundleDirectory } = createFixture('x86_64-pc-windows-msvc');
  try {
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.exe'));
    const updaterArchive = join(bundleDirectory, 'msi', 'VoidMelody_0.3.0_x64_en-US.msi.zip');
    createFile(updaterArchive);
    createFile(`${updaterArchive}.sig`);

    const result = runVerifier(root, 'x86_64-pc-windows-msvc', 'msi');
    assert.equal(result.status, 0, result.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a Windows updater archive outside its configured Tauri bundle directory', () => {
  const { root, bundleDirectory } = createFixture('x86_64-pc-windows-msvc');
  try {
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.exe'));
    const misplacedArchive = join(bundleDirectory, 'msi', 'VoidMelody_0.3.0_x64-setup.nsis.zip');
    createFile(misplacedArchive);
    createFile(`${misplacedArchive}.sig`);

    const result = runVerifier(root, 'x86_64-pc-windows-msvc', 'nsis');
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Missing Windows NSIS updater archive/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects an updater archive without its matching signature', () => {
  const { root, bundleDirectory } = createFixture('x86_64-pc-windows-msvc');
  try {
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.exe'));
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.nsis.zip'));

    const result = runVerifier(root, 'x86_64-pc-windows-msvc', 'nsis');
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /matching updater signature/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a zero-byte updater archive even when its matching signature exists', () => {
  const { root, bundleDirectory } = createFixture('aarch64-apple-darwin');
  try {
    createFile(join(bundleDirectory, 'dmg', 'VoidMelody_0.3.0_aarch64.dmg'));
    const updaterArchive = join(bundleDirectory, 'macos', 'VoidMelody.app.tar.gz');
    createFile(updaterArchive, '');
    createFile(`${updaterArchive}.sig`);

    const result = runVerifier(root, 'aarch64-apple-darwin');
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Required release asset is empty/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a zero-byte updater signature', () => {
  const { root, bundleDirectory } = createFixture('x86_64-pc-windows-msvc');
  try {
    createFile(join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.exe'));
    const updaterArchive = join(bundleDirectory, 'nsis', 'VoidMelody_0.3.0_x64-setup.nsis.zip');
    createFile(updaterArchive);
    createFile(`${updaterArchive}.sig`, '');

    const result = runVerifier(root, 'x86_64-pc-windows-msvc', 'nsis');
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Required release asset is empty/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
