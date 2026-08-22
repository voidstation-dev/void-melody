import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const helper = join(repositoryRoot, 'scripts', 'release-metadata.mjs');
const releaseWorkflow = join(repositoryRoot, '.github', 'workflows', 'release.yml');

function createFixture({
  tauri = '0.2.0',
  cargo = '0.2.0',
  cargoDocument,
  web = '0.2.0',
  changelog,
} = {}) {
  const root = mkdtempSync(join(tmpdir(), 'voidmelody-release-metadata-'));
  mkdirSync(join(root, 'apps', 'web', 'src-tauri'), { recursive: true });
  mkdirSync(join(root, 'apps', 'web', 'src-tauri', 'src'), { recursive: true });
  writeFileSync(join(root, 'apps', 'web', 'src-tauri', 'tauri.conf.json'), JSON.stringify({ version: tauri }));
  writeFileSync(
    join(root, 'apps', 'web', 'src-tauri', 'Cargo.toml'),
    cargoDocument ?? `[package]\nname = "app"\nversion = "${cargo}"\nedition = "2021"\n`,
  );
  writeFileSync(join(root, 'apps', 'web', 'src-tauri', 'src', 'lib.rs'), 'pub fn fixture() {}\n');
  writeFileSync(join(root, 'apps', 'web', 'package.json'), JSON.stringify({ name: 'voidmelody-web', version: web }));
  writeFileSync(join(root, 'CHANGELOG.md'), changelog ?? '# Changelog\n\n## [0.2.0] - 2026-08-02\n\n### Added\n\n- Signed updater artifacts.\n\n## [0.1.0] - 2026-07-01\n\n### Added\n\n- Initial release.\n');
  return root;
}

function runHelper(root, { tag = 'v0.2.0', githubOutput } = {}) {
  const args = [helper, '--root', root, '--tag', tag];
  if (githubOutput) args.push('--github-output');
  return spawnSync(process.execPath, args, {
    encoding: 'utf8',
    env: { ...process.env, ...(githubOutput ? { GITHUB_OUTPUT: githubOutput } : {}) },
  });
}

function parseGithubOutput(outputPath) {
  const content = readFileSync(outputPath, 'utf8');
  const lines = content.split('\n');
  const values = {};
  for (let index = 0; index < lines.length - 1; index += 1) {
    const [name, delimiter] = lines[index].split('<<');
    if (!delimiter) continue;
    const end = lines.indexOf(delimiter, index + 1);
    values[name] = lines.slice(index + 1, end).join('\n');
    index = end;
  }
  return values;
}

test('reads matching versions and emits exactly the requested changelog section', () => {
  const root = createFixture();
  try {
    const result = runHelper(root);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(result.stdout), {
      version: '0.2.0',
      tag: 'v0.2.0',
      notes: '### Added\n\n- Signed updater artifacts.',
    });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a tag that is not an exact vX.Y.Z match for the source version', () => {
  const root = createFixture();
  try {
    const result = runHelper(root, { tag: 'v0.2.0-beta.1' });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /must match vX\.Y\.Z/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects leading zeroes in every numeric component of a release tag', () => {
  const root = createFixture();
  try {
    for (const tag of ['v00.2.0', 'v0.02.0', 'v0.2.00']) {
      const result = runHelper(root, { tag });
      assert.notEqual(result.status, 0, tag);
      assert.match(result.stderr, /must match vX\.Y\.Z/, tag);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects leading zeroes in JSON source metadata', () => {
  const root = createFixture({ tauri: '00.2.0' });
  try {
    const result = runHelper(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Tauri config .* must contain a stable X\.Y\.Z version/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reads Cargo package version through Cargo metadata with valid alternative TOML formatting', () => {
  const root = createFixture({
    cargoDocument: `# Cargo accepts indentation and literal strings.\n[package]\n  edition = '2021'\n  version = '0.2.0' # release\n  name = 'app'\n`,
  });
  try {
    const result = runHelper(root);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).version, '0.2.0');
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a well-formed tag whose version differs from the source metadata', () => {
  const root = createFixture();
  try {
    const result = runHelper(root, { tag: 'v0.2.1' });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /does not equal source version "0\.2\.0"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects mismatched versions across Tauri, Cargo, and web package metadata', () => {
  const root = createFixture({ cargo: '0.2.1' });
  try {
    const result = runHelper(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Cargo package version is "0\.2\.1" but expected "0\.2\.0"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects a changelog that lacks the exact version section', () => {
  const root = createFixture({
    changelog: '# Changelog\n\n## [0.2.0-beta.1] - 2026-08-02\n\n- Preview.\n',
  });
  try {
    const result = runHelper(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /CHANGELOG\.md is missing an exact \[0\.2\.0\] section/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('writes multiline release notes through GITHUB_OUTPUT without delimiter collisions', () => {
  const root = createFixture({
    changelog: '# Changelog\n\n## [0.2.0] - 2026-08-02\n\nVOIDMELODY_RELEASE_NOTES_0\n\nSecond line.\n',
  });
  const githubOutput = join(root, 'github-output.txt');
  try {
    const result = runHelper(root, { githubOutput });
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(parseGithubOutput(githubOutput), {
      version: '0.2.0',
      tag: 'v0.2.0',
      notes: 'VOIDMELODY_RELEASE_NOTES_0\n\nSecond line.',
    });
    assert.doesNotMatch(readFileSync(githubOutput, 'utf8'), /notes<<VOIDMELODY_RELEASE_NOTES_0\n/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('release workflow installs Rust before metadata validation on two serialized targets', () => {
  const workflow = readFileSync(releaseWorkflow, 'utf8');
  assert.ok(
    workflow.indexOf('- name: Install Rust stable') < workflow.indexOf('- name: Validate release metadata'),
    'cargo must be installed before the metadata validator invokes cargo metadata',
  );
  assert.match(workflow, /^\s+max-parallel:\s+1\s*$/m);
  assert.deepEqual(
    [...workflow.matchAll(/^\s+target:\s+([^\s#]+)\s*$/gm)].map((match) => match[1]),
    ['aarch64-apple-darwin', 'x86_64-pc-windows-msvc'],
  );
});

test('release workflow runs signed asset preflight before the draft release action', () => {
  const workflow = readFileSync(releaseWorkflow, 'utf8');
  assert.match(
    workflow,
    /ref:\s+\${{ github\.event_name == 'workflow_dispatch' && format\('refs\/tags\/\{0\}', inputs\.tag\) \|\| github\.ref }}/,
  );
  assert.match(
    workflow,
    /RELEASE_TAG:\s+\${{ github\.event_name == 'workflow_dispatch' && inputs\.tag \|\| github\.ref_name }}/,
  );
  assert.ok(
    workflow.indexOf('- name: Verify checkout matches release tag') > workflow.indexOf('- name: Validate release metadata'),
  );
  const buildAction = workflow.indexOf('- name: Build Tauri app');
  const signingKey = workflow.indexOf('- name: Require updater signing private key');
  const releaseAssetTests = workflow.indexOf('- name: Run release asset verification tests');
  const macosPreflight = workflow.indexOf('- name: Preflight signed macOS release bundle');
  const windowsPreflight = workflow.indexOf('- name: Preflight signed Windows release bundle');
  assert.ok(releaseAssetTests > signingKey);
  assert.ok(macosPreflight > signingKey && macosPreflight < buildAction);
  assert.ok(windowsPreflight > signingKey && windowsPreflight < buildAction);
  assert.ok(workflow.indexOf('- name: Verify generated macOS release assets') > buildAction);
  assert.ok(workflow.indexOf('- name: Verify generated Windows release assets') > buildAction);
  assert.match(workflow, /^\s+fail-fast:\s+true\s*$/m);
  assert.match(workflow, /pnpm --dir apps\/web tauri build --target aarch64-apple-darwin/);
  assert.match(workflow, /pnpm --dir apps\/web tauri build --target x86_64-pc-windows-msvc/);
  assert.match(workflow, /node scripts\/verify-release-assets\.mjs --target x86_64-pc-windows-msvc --windows-updater nsis/);
  assert.doesNotMatch(workflow, /if \[ -n "\$\{\{ github\.event\.inputs\.tag \}\}" \]/);
});
