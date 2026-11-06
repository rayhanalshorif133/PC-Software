"""
Build script to package V-Editor into a standalone Windows Desktop Executable (.exe)
with official Windows 11 application manifest and metadata to prevent SmartScreen blocks.
"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=== Building V-Editor Windows 11 Desktop Application (.exe) ===")
    
    dist_dir = os.path.join(BASE_DIR, 'dist')
    ui_dir = os.path.join(BASE_DIR, 'ui')
    icon_path = os.path.join(BASE_DIR, 'icon.ico')
    ffmpeg_path = os.path.join(BASE_DIR, 'ffmpeg.exe')
    sample_path = os.path.join(BASE_DIR, 'test_sample.mp4')
    version_file = os.path.join(BASE_DIR, 'version.txt')
    manifest_file = os.path.join(BASE_DIR, 'manifest.xml')

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=V-Editor',
        '--noconsole',
        '--onedir',
        f'--icon={icon_path}',
        f'--version-file={version_file}',
        f'--manifest={manifest_file}',
        f'--add-data={ui_dir};ui',
        f'--add-data={sample_path};.',
        f'--add-binary={ffmpeg_path};.',
        '--collect-all=webview',
        '--collect-all=imageio_ffmpeg',
        '--clean',
        '-y',
        os.path.join(BASE_DIR, 'app.py')
    ]

    print("Running command:\n", " ".join(cmd))
    res = subprocess.run(cmd, cwd=BASE_DIR)

    if res.returncode == 0:
        exe_path = os.path.join(dist_dir, 'V-Editor', 'V-Editor.exe')
        # Run Unblock-File via powershell on the newly created exe
        try:
            subprocess.run(['powershell', '-Command', f'Unblock-File -Path "{exe_path}"'], capture_output=True)
            print("[+] Executable unblocked successfully.")
        except Exception:
            pass

        print("\n=======================================================")
        print(" BUILD SUCCESSFUL!")
        print(f" Executable path: {exe_path}")
        print("=======================================================\n")
    else:
        print("\n[!] Build failed with return code:", res.returncode)

if __name__ == '__main__':
    build()
