import os
import shutil
import subprocess
import sys


def build(onefile: bool = False):
    print("=" * 60)
    print("Building VideoFramePro Windows Executable...")
    print(f"Mode: {'Single File (--onefile)' if onefile else 'Folder Distribution (--onedir)'}")
    print("=" * 60)

    # Ensure icon and model exist
    icon_path = os.path.join("assets", "app_icon.ico")
    model_path = os.path.join("models", "yolov5n.onnx")

    if not os.path.exists(model_path):
        print(f"ERROR: Model file {model_path} not found!")
        return False

    app_name = "VideoFramePro_Standalone" if onefile else "VideoFramePro"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--clean",
        "--name",
        app_name,
        "--add-data",
        f"{model_path};models",
        "--collect-all",
        "customtkinter",
    ]

    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        cmd.extend(["--add-data", f"{icon_path};assets"])

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.append("main.py")

    print("Running PyInstaller command:")
    print(" ".join(cmd))
    print("-" * 60)

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("=" * 60)
        print("BUILD SUCCESSFUL!")
        if onefile:
            exe_path = os.path.abspath(os.path.join("dist", "VideoFramePro.exe"))
            print(f"Executable created at: {exe_path}")
        else:
            exe_dir = os.path.abspath(os.path.join("dist", "VideoFramePro"))
            exe_path = os.path.join(exe_dir, "VideoFramePro.exe")
            print(f"Application folder created at: {exe_dir}")
            print(f"Main Executable: {exe_path}")
        print("=" * 60)
        return True
    else:
        print("=" * 60)
        print(f"BUILD FAILED with returncode: {result.returncode}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    build(onefile=is_onefile)
