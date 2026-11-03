# CineCut Studio - Desktop Video Editor & Splitter

A modern, fast desktop video editor built with **Electron**, **FFmpeg**, and **Node.js** for Windows.

## 🚀 Features

- **Sleek Studio Interface**: Dark modern theme with responsive canvas timeline, glowing playhead, and glassmorphic UI.
- **Easy Video Import**: Drag and drop any video (`.mp4`, `.mkv`, `.mov`, `.webm`, `.avi`) or click **Open Video**.
- **Sample Video Included**: Click **Try Sample** to test right away with a built-in test video.
- **Precision Video Player**:
  - Play / Pause (Spacebar)
  - Frame-by-frame stepping (`<|` / `|>`)
  - 5-second skip forward / backward (`<<` / `>>`)
  - Exact timecode display (`HH:MM:SS.ms`)
  - Playback speed control (`0.5x` to `2.0x`)
  - Volume slider and Fullscreen mode
- **Split on the Fly**:
  - Click **Split Clip [S]** or press keyboard shortcut **`S`** while playing or paused to split clips at the exact playhead position.
- **Delete & Trim**:
  - Select any clip and hit **Delete** / **Backspace** or click the trash button.
  - Delete middle unwanted sections and merge the remaining video clips seamlessly.
- **Live Edit Preview**:
  - Toggle **Live Preview Edited Cut** to preview the final cut in the player without rendering (automatically jumps across cut regions).
- **Export & Merge**:
  - Choose output destination folder and file name.
  - Real-time animated **Progress Bar** (0% - 100%) with processed time, encoding speed multiplier, and FPS.
  - Frame-accurate H.264 + AAC encoding with zero audio/video desync.
  - One-click **Open in Folder** and **Play Output Video** after conversion.

---

## 📦 How to Run

### Option 1: Standalone Portable EXE (No setup needed)
Double-click the ready-to-run `.exe` located at:
```
dist\CineCut-Studio.exe
```

### Option 2: Run in Development Mode
```bash
npm start
```

### Option 3: Rebuild the Portable EXE
```bash
npm run dist
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Space` | Play / Pause |
| `S` | Split clip at current playhead position |
| `Delete` / `Backspace` | Delete selected clip |
| `Left Arrow` / `Right Arrow` | Skip 5s backward / forward |
| `Shift` + `Left` / `Right` | Skip 1s backward / forward |
| `M` | Mute / Unmute Audio |

