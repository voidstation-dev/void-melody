const fs = require('fs');
const path = require('path');
const https = require('https');
const { pipeline } = require('stream/promises');

const targetDir = path.join(__dirname, '../src-tauri/bin');
fs.mkdirSync(targetDir, { recursive: true });

// Static FFmpeg builds from eugeneware/ffmpeg-static (the npm `ffmpeg-static`
// package). These are self-contained binaries with no Homebrew/dynamic
// library dependencies, so they run on any macOS/Windows machine — unlike
// `which ffmpeg`, which copies a dynamic-linked Homebrew build that crashes
// with `dyld: Library not loaded` on machines without the exact Cellar.
const FFMPEG_STATIC_RELEASE_TAG = 'b6.1.1';
const FFMPEG_STATIC_REPO = 'eugeneware/ffmpeg-static';

function download(url, dest) {
  return new Promise((resolve, reject) => {
    if (fs.existsSync(dest)) {
      fs.chmodSync(dest, 0o644);
    }
    const file = fs.createWriteStream(dest);
    https
      .get(url, (response) => {
        // Follow GitHub release redirects (302 -> objects.githubusercontent.com).
        if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
          response.destroy();
          file.close();
          fs.unlinkSync(dest);
          return resolve(download(response.headers.location, dest));
        }
        if (response.statusCode !== 200) {
          file.close();
          fs.unlinkSync(dest);
          return reject(new Error(`HTTP ${response.statusCode} for ${url}`));
        }
        pipeline(response, file).then(resolve).catch(reject);
      })
      .on('error', (err) => {
        file.close();
        if (fs.existsSync(dest)) fs.unlinkSync(dest);
        reject(err);
      });
  });
}

function platformAsset() {
  const platform = process.platform;
  const arch = process.arch;
  if (platform === 'darwin') {
    return arch === 'arm64' ? 'ffmpeg-darwin-arm64' : 'ffmpeg-darwin-x64';
  }
  if (platform === 'win32') {
    return 'ffmpeg-win32-x64';
  }
  if (platform === 'linux') {
    return 'ffmpeg-linux-x64';
  }
  throw new Error(`Unsupported platform for static ffmpeg: ${platform}-${arch}`);
}

async function main() {
  const ext = process.platform === 'win32' ? '.exe' : '';
  const targetPath = path.join(targetDir, `ffmpeg${ext}`);
  const asset = platformAsset();
  const url = `https://github.com/${FFMPEG_STATIC_REPO}/releases/download/${FFMPEG_STATIC_RELEASE_TAG}/${asset}`;

  console.log(`Downloading static FFmpeg from ${url}`);
  await download(url, targetPath);
  fs.chmodSync(targetPath, 0o755);
  console.log(`Successfully wrote static FFmpeg to ${targetPath}`);

  // Create target-specific copies for Tauri externalBin
  if (process.platform === 'darwin') {
    fs.copyFileSync(targetPath, path.join(targetDir, 'ffmpeg-aarch64-apple-darwin'));
    fs.copyFileSync(targetPath, path.join(targetDir, 'ffmpeg-x86_64-apple-darwin'));
  } else if (process.platform === 'win32') {
    fs.copyFileSync(targetPath, path.join(targetDir, 'ffmpeg-x86_64-pc-windows-msvc.exe'));
    fs.copyFileSync(targetPath, path.join(targetDir, 'ffmpeg-aarch64-pc-windows-msvc.exe'));
  } else if (process.platform === 'linux') {
    fs.copyFileSync(targetPath, path.join(targetDir, 'ffmpeg-x86_64-unknown-linux-gnu'));
  }
}

main().catch((err) => {
  console.error('Failed to fetch static ffmpeg.', err);
  process.exit(1);
});

const voiceJsonSrc = path.join(__dirname, '../../../vendor/capcut-tts-api/Voice.json');
const voiceJsonDest = path.join(targetDir, 'Voice.json');
if (fs.existsSync(voiceJsonSrc)) {
  fs.copyFileSync(voiceJsonSrc, voiceJsonDest);
  console.log(`Successfully copied Voice.json to ${voiceJsonDest}`);
} else {
  console.warn(`Warning: Voice.json not found at ${voiceJsonSrc}`);
}

// Create dummy files for the *other* platform's ffmpeg name so the Tauri
// bundler can always resolve both `ffmpeg` and `ffmpeg.exe` resources. The
// runner only downloads the binary for its own platform; the unused platform
// placeholder stays empty and is never executed at runtime.
const dummyFiles = ['ffmpeg', 'ffmpeg.exe'];
dummyFiles.forEach((file) => {
  const filePath = path.join(targetDir, file);
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, '');
    console.log(`Created dummy file for missing platform binary: ${file}`);
  }
});
