# Pro Downloader - Desktop Video & Audio Downloader

A modern, high-speed desktop application for downloading and managing online videos and music, built with Python, PyWebView (Microsoft Edge Chromium), `yt-dlp`, and bundled FFmpeg.

---

## ✨ Features

- **Sleek Cyber-Glassmorphism UI**:
  - Custom dark title bar with Pro Downloader vector icon and Windows 11 style window controls.
  - Left navigation sidebar with `⚡ PRO ACTIVE`, quick collection filters, clips & movies badges.
  - Top search engine bar with one-click **Paste from Clipboard**, URL input, **Analyze**, and **Fast Download** buttons.
  - Dynamic fallback thumbnails so video cards always look crisp without broken image icons.
  - Category filter tabs: All Media, Clips & Shorts, Movies & Videos, Audio MP3.
- **Unlimited High-Speed Media Downloader**:
  - Download single videos, shorts, or entire playlists.
  - Choose quality: **Best Available (4K/2K/1080p)**, **1080p Full HD**, **720p HD**, **480p Standard**, or **Audio Only (MP3 320kbps)**.
  - Merges video and audio streams seamlessly using bundled FFmpeg (`imageio-ffmpeg`).
  - Real-time animated progress bar: percentage, download speed (MB/s), ETA, and file size.
- **Built-in Media Player & Library**:
  - Play downloaded MP4/WebM videos and MP3 audio directly inside the desktop app.
  - Open containing folder in Windows Explorer with one click.
  - Import local video files (`MP4`, `MKV`, `WEBM`, etc.) from your computer into your collection.
  - Configurable download folder in Preferences.

---

## 🚀 How to Run

### Option 1: Double-click `run.bat`
Simply double-click `run.bat` in Windows Explorer.

### Option 2: Run via Terminal
```powershell
python app.py
```

---

## 📦 Dependencies
- `python >= 3.10`
- `pywebview >= 6.2.1`
- `yt-dlp >= 2026.8.19`
- `imageio-ffmpeg >= 0.6.0`
- `bottle >= 0.13.4`
