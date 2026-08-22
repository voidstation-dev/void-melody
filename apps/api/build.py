import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_target_triple():
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "linux":
        return "x86_64-unknown-linux-gnu"

    return "unknown"


def get_pyinstaller_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "melody-api",
        "--paths",
        ".",
        "--hidden-import=app.main",
        "--hidden-import=aiosqlite",
        "--hidden-import=app.utils.audio_utils",
        "--hidden-import=vieneu_core",
        "--hidden-import=vieneu",
        "--hidden-import=vieneu_utils",
        "--hidden-import=sea_g2p",
        "--hidden-import=librosa",
        "--hidden-import=soundfile",
        "--hidden-import=onnxruntime",
        "--hidden-import=huggingface_hub",
        "--collect-all=sea_g2p",
        "--collect-all=vieneu",
        "--collect-all=vieneu_utils",
        "--collect-all=onnxruntime",
        "--add-data",
        "alembic.ini:.",
        "--add-data",
        "alembic:alembic",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath",
        "./dist",
        "sidecar_entrypoint.py",
    ]


def get_source_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_sidecar_manifest(destination: str, target_triple: str) -> None:
    manifest_path = Path(f"{destination}.manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_revision": get_source_revision(),
                "target_triple": target_triple,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main():
    target_triple = get_target_triple()
    print(f"Detected target triple: {target_triple}")

    # Run PyInstaller
    subprocess.run(get_pyinstaller_command(), check=True)

    # Copy to src-tauri/bin
    src_bin = "dist/melody-api"
    if platform.system().lower() == "windows":
        src_bin += ".exe"

    dest_dir = "../web/src-tauri/bin"
    os.makedirs(dest_dir, exist_ok=True)

    dest_bin = f"{dest_dir}/melody-api-{target_triple}"
    if platform.system().lower() == "windows":
        dest_bin += ".exe"

    print(f"Copying {src_bin} to {dest_bin}")
    shutil.copy2(src_bin, dest_bin)
    write_sidecar_manifest(dest_bin, target_triple)
    
    # Also copy Voice.json if present
    voice_json_src = "../../vendor/capcut-tts-api/Voice.json"
    if os.path.exists(voice_json_src):
        print(f"Copying {voice_json_src} to {dest_dir}/Voice.json")
        shutil.copy2(voice_json_src, f"{dest_dir}/Voice.json")

    # Also copy ffmpeg if present in path
    ffmpeg_src = shutil.which("ffmpeg")
    if ffmpeg_src:
        ffmpeg_dest = f"{dest_dir}/ffmpeg"
        if platform.system().lower() == "windows":
            ffmpeg_dest += ".exe"
        # setup-ffmpeg.js provisions a portable static binary before this
        # script runs. Keep it instead of replacing it with a Homebrew/dynamic
        # build, which may fail to launch on another machine and can preserve
        # read-only permissions that break the next build.
        ffmpeg_is_provisioned = os.path.exists(ffmpeg_dest) and os.path.getsize(ffmpeg_dest) > 0
        if ffmpeg_is_provisioned:
            print(f"FFmpeg already provisioned at {ffmpeg_dest}")
        else:
            print(f"Copying {ffmpeg_src} to {ffmpeg_dest}")
            shutil.copy2(ffmpeg_src, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)

    print("Done!")


if __name__ == "__main__":
    main()
