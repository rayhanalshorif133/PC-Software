import os
import sys
import shutil
import subprocess
from pathlib import Path
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "app_icon.ico"
UI_PATH = BASE_DIR / "ui"

# Find imageio_ffmpeg binary directory
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = Path(ffmpeg_exe).parent

print(f"[Build] Base Directory: {BASE_DIR}")
print(f"[Build] UI Directory: {UI_PATH}")
print(f"[Build] FFmpeg Directory: {ffmpeg_dir}")
print(f"[Build] App Icon: {ICON_PATH}")

# PyInstaller Arguments
pyinstaller_args = [
    sys.executable, "-m", "PyInstaller",
    "--name=Pro Downloader",
    "--noconfirm",
    "--onedir",
    "--windowed",
    f"--icon={ICON_PATH}",
    f"--add-data={UI_PATH};ui",
    f"--add-data={ffmpeg_dir};imageio_ffmpeg/binaries",
    "--hidden-import=webview",
    "--hidden-import=bottle",
    "--hidden-import=yt_dlp",
    "--hidden-import=imageio_ffmpeg",
    "--hidden-import=concurrent.futures",
    "--hidden-import=json",
    "--hidden-import=urllib",
    str(BASE_DIR / "app.py")
]

print("\n[Build] Running PyInstaller...")
cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in pyinstaller_args)
print(f"[Build] Command: {cmd_str}\n")

result = subprocess.run(pyinstaller_args, cwd=str(BASE_DIR))

if result.returncode == 0:
    print("\n=======================================================")
    print("  [SUCCESS] Pro Downloader.exe successfully built!")
    print(f"  Location: {BASE_DIR / 'dist' / 'Pro Downloader' / 'Pro Downloader.exe'}")
    print("=======================================================\n")
else:
    print("\n[ERROR] PyInstaller build failed with exit code:", result.returncode)
    sys.exit(result.returncode)

