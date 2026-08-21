import os
import platform
import shutil
import subprocess


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
        "pyinstaller",
        "--name",
        "melody-api",
        "--paths",
        ".",
        "--hidden-import=aiosqlite",
        "--hidden-import=app.utils.audio_utils",
        "--hidden-import=vieneu_core",
        "--hidden-import=vieneu",
        "--hidden-import=vieneu_utils",
        "--hidden-import=sea_g2p",
        "--hidden-import=librosa",
        "--hidden-import=soundfile",
        "--hidden-import=onnxruntime",
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
        "app/main.py",
    ]


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
        print(f"Copying {ffmpeg_src} to {ffmpeg_dest}")
        shutil.copy2(ffmpeg_src, ffmpeg_dest)

    print("Done!")


if __name__ == "__main__":
    main()
