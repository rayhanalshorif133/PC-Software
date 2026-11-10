import os
import sys

# Windows DPI Awareness for crisp text and UI
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from src.app import VideoFrameProApp


def main():
    app = VideoFrameProApp()
    app.mainloop()


if __name__ == "__main__":
    main()
