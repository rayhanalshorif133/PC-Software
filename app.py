import os
import sys
import json
import time
import socket
import threading
import subprocess
import mimetypes
import re
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import webview
from bottle import Bottle, request, response, static_file, abort
import yt_dlp
import imageio_ffmpeg

# Project directories
BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
# Project directories & Bundled Asset Paths (PyInstaller Support)
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    BASE_DIR = Path(__file__).resolve().parent

UI_DIR = BUNDLE_DIR / "ui"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = BASE_DIR / "library.json"

# Get bundled ffmpeg executable
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = "ffmpeg"
print(f"[Engine] Using FFmpeg from: {FFMPEG_PATH}")

# Bottle Web Server
server_app = Bottle()

# Active downloads tracker
active_downloads = {}
download_cancel_flags = {}

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

PORT = get_free_port()

def json_response(data):
    response.content_type = 'application/json; charset=utf-8'
    return json.dumps(data, ensure_ascii=False)

@server_app.route('/')
def serve_index():
    return static_file('index.html', root=str(UI_DIR))

@server_app.route('/<filename:path>')
def serve_static(filename):
    return static_file(filename, root=str(UI_DIR))

@server_app.route('/stream')
def stream_media():
    filepath = request.query.get('path')
    if not filepath or not os.path.exists(filepath):
        abort(404, "File not found")
    file_path = Path(filepath)
    return static_file(file_path.name, root=str(file_path.parent))

# System Downloads Folder Auto-Detection & Verification
def get_system_downloads_folder():
    """Returns the current user's Downloads folder on Windows / macOS / Linux."""
    try:
        user_downloads = Path.home() / "Downloads"
        if user_downloads.exists():
            return str(user_downloads)
        user_downloads.mkdir(parents=True, exist_ok=True)
        return str(user_downloads)
    except Exception:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        return str(DOWNLOADS_DIR)

def ensure_valid_download_folder(lib):
    """Validates if download_folder exists on this computer; if not, automatically sets it to the current PC's Downloads folder."""
    settings = lib.setdefault("settings", {})
    current_folder = settings.get("download_folder")
    
    # If folder is missing, invalid, or belongs to another PC user
    if not current_folder or not os.path.exists(current_folder) or not os.path.isdir(current_folder):
        auto_folder = get_system_downloads_folder()
        settings["download_folder"] = auto_folder
        save_library(lib)
        print(f"[Engine] Download path automatically verified & set for this PC: {auto_folder}")
    return lib

def sanitize_folder_name(name):
    """Sanitizes a playlist title into a valid directory name on Windows/macOS/Linux."""
    if not name:
        return "Playlist"
    # Replace forbidden Windows characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name).strip('. \t\r\n')
    # Collapse multiple spaces or underscores
    cleaned = re.sub(r'[_\s]+', ' ', cleaned).strip()
    # Limit length to avoid Windows path length overflow
    if len(cleaned) > 80:
        cleaned = cleaned[:80].strip('. ')
    return cleaned if cleaned else "Playlist"

# 10-Minute History Retention Constant
HISTORY_RETENTION_SECONDS = 10 * 60  # 10 minutes

def prune_expired_download_history(lib):
    """Automatically removes completed download items older than 10 minutes from library history."""
    if not lib or "downloaded" not in lib:
        return lib
    
    current_now = time.time()
    valid_items = []
    has_changed = False
    
    for item in lib.get("downloaded", []):
        completed_time = item.get("completed_at")
        if completed_time is not None:
            # Keep if within 10 minutes (600 seconds)
            if (current_now - float(completed_time)) <= HISTORY_RETENTION_SECONDS:
                valid_items.append(item)
            else:
                has_changed = True
                print(f"[History Auto-Clean] Removed expired download from history (>10m): {item.get('title')}")
        else:
            # For items without a completion timestamp, set to now
            item["completed_at"] = current_now
            valid_items.append(item)
            has_changed = True

    if has_changed:
        lib["downloaded"] = valid_items
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as fw:
                json.dump(lib, fw, indent=2, ensure_ascii=False)
        except Exception:
            pass
            
    return lib

# Library Management Lock for thread-safety across concurrent workers
library_lock = threading.Lock()

def load_library():
    with library_lock:
        if not DATA_FILE.exists():
            auto_folder = get_system_downloads_folder()
            initial_lib = {
                "downloaded": [],
                "settings": {
                    "download_folder": auto_folder,
                    "default_quality": "best"
                }
            }
            try:
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(initial_lib, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return initial_lib
        
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "downloaded" not in data:
                    data["downloaded"] = []
                if "settings" not in data:
                    data["settings"] = {"download_folder": get_system_downloads_folder(), "default_quality": "best"}
                
                # Check and fix folder for this specific computer
                settings = data.setdefault("settings", {})
                current_folder = settings.get("download_folder")
                if not current_folder or not os.path.exists(current_folder) or not os.path.isdir(current_folder):
                    auto_folder = get_system_downloads_folder()
                    settings["download_folder"] = auto_folder
                    try:
                        with open(DATA_FILE, 'w', encoding='utf-8') as fw:
                            json.dump(data, fw, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                
                # Prune completed downloads history older than 10 minutes
                data = prune_expired_download_history(data)
                return data
        except Exception as e:
            print(f"[Library] Error loading library: {e}")
            auto_folder = get_system_downloads_folder()
            return {"downloaded": [], "settings": {"download_folder": auto_folder, "default_quality": "best"}}

def save_library(data):
    with library_lock:
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Library] Error saving library: {e}")


class DesktopApi:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    # Library API
    def get_library(self):
        return load_library()

    def get_settings(self):
        lib = load_library()
        return lib.get("settings", {
            "download_folder": str(DOWNLOADS_DIR),
            "default_quality": "best"
        })

    def save_settings(self, new_settings):
        lib = load_library()
        lib["settings"] = new_settings
        save_library(lib)
        return {"success": True}

    def select_download_folder(self):
        if not self._window:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    def open_in_folder(self, filepath):
        try:
            if filepath and os.path.exists(filepath):
                subprocess.Popen(f'explorer /select,"{os.path.abspath(filepath)}"')
            else:
                settings = self.get_settings()
                folder = settings.get("download_folder", str(DOWNLOADS_DIR))
                os.startfile(folder)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_local_media(self):
        if not self._window:
            return None
        file_types = ('Video Files (*.mp4;*.mkv;*.webm;*.avi;*.mov)', 'All Files (*.*)')
        results = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
        if not results:
            return {"success": False, "message": "No files selected"}

        lib = load_library()
        added_count = 0

        for path in results:
            if not os.path.exists(path):
                continue
            name = Path(path).stem
            item_id = f"local_{int(time.time()*1000)}_{added_count}"
            size_mb = os.path.getsize(path) / (1024 * 1024)

            item = {
                "id": item_id,
                "title": name,
                "thumbnail": "",
                "duration": f"{int(size_mb)} MB",
                "type": "video",
                "date": time.strftime("%Y-%m-%d"),
                "file_path": path,
                "is_local": True
            }
            lib.setdefault("downloaded", []).insert(0, item)
            added_count += 1

        save_library(lib)
        return {"success": True, "count": added_count, "library": lib}

    def delete_item(self, item_id, delete_file=False):
        lib = load_library()
        if "downloaded" in lib:
            for item in lib["downloaded"]:
                if item.get("id") == item_id:
                    if delete_file and item.get("file_path") and os.path.exists(item.get("file_path")):
                        try:
                            os.remove(item.get("file_path"))
                        except Exception as ex:
                            print(f"Error removing file: {ex}")
            lib["downloaded"] = [item for item in lib["downloaded"] if item.get("id") != item_id]
        save_library(lib)
        return {"success": True, "library": lib}

    def clear_download_history(self, delete_files=False):
        """Clears all completed download records from library history."""
        lib = load_library()
        if delete_files and "downloaded" in lib:
            for item in lib["downloaded"]:
                fp = item.get("file_path")
                if fp and os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except Exception as ex:
                        print(f"Error removing file: {ex}")
        lib["downloaded"] = []
        save_library(lib)
        print("[History] Cleared all completed download records.")
        return {"success": True, "library": lib}

    def cancel_all_downloads(self):
        """Cancels and stops all running and queued downloads immediately."""
        count = len(active_downloads)
        for dl_id in list(active_downloads.keys()):
            download_cancel_flags[dl_id] = True
            if dl_id in active_downloads:
                active_downloads[dl_id]["status"] = "cancelled"
        active_downloads.clear()
        print(f"[Engine] Stopped all {count} running/queued downloads.")
        return {"success": True, "count": count, "message": "All downloads cancelled"}

    def get_active_downloads(self):
        return {"success": True, "downloads": list(active_downloads.values())}

    # YouTube Info & Downloader
    def fetch_info(self, url, mode="auto"):
        """Extracts video or playlist info using yt-dlp."""
        url = (url or '').strip()
        if not url:
            return {"success": False, "error": "URL cannot be empty"}

        # Detect playlist ID in url
        playlist_match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
        playlist_id = playlist_match.group(1) if playlist_match else None
        has_video_id = bool('watch?v=' in url or 'youtu.be/' in url or '/shorts/' in url or '/v/' in url)

        # Should fetch playlist?
        fetch_as_playlist = (mode == "playlist") or (mode == "auto" and not has_video_id and playlist_id is not None)

        if fetch_as_playlist and playlist_id:
            playlist_canonical_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
                'extractor_args': {'youtube': {'player_client': ['web', 'android']}}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(playlist_canonical_url, download=False)
                    if not info:
                        return {"success": False, "error": "Could not extract playlist details."}

                    raw_entries = list(info.get('entries', []))
                    entries = []
                    for idx, entry in enumerate(raw_entries[:500]):
                        if entry:
                            thumb = entry.get('thumbnail') or (entry.get('thumbnails', [{}])[-1].get('url', '') if entry.get('thumbnails') else '')
                            entry_id = entry.get('id') or str(idx)
                            duration_val = entry.get('duration') or 0
                            duration_str = entry.get('duration_string') or (f"{int(duration_val) // 60}:{int(duration_val) % 60:02d}" if duration_val else "Unknown")
                            entries.append({
                                "id": entry_id,
                                "index": idx + 1,
                                "title": entry.get('title') or f"Video {idx+1}",
                                "thumbnail": thumb,
                                "duration": duration_str,
                                "duration_secs": duration_val,
                                "url": entry.get('url') or f"https://www.youtube.com/watch?v={entry_id}"
                            })

                    return {
                        "success": True,
                        "is_playlist": True,
                        "title": info.get('title', 'YouTube Playlist'),
                        "count": len(entries),
                        "entries": entries,
                        "thumbnail": entries[0]['thumbnail'] if (entries and entries[0].get('thumbnail')) else '',
                        "url": playlist_canonical_url,
                        "playlist_id": playlist_id
                    }
            except Exception as e:
                return {"success": False, "error": f"Playlist Extraction Error: {str(e)}"}

        # Single Video Mode
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['web', 'android']}}
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"success": False, "error": "Could not extract video details."}

                title = info.get('title', 'YouTube Video')
                duration = info.get('duration', 0)
                duration_str = info.get('duration_string') or (f"{duration // 60}:{duration % 60:02d}" if duration else "00:00")
                thumbnail = info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url', '') if info.get('thumbnails') else '')
                channel = info.get('uploader') or info.get('channel', 'YouTube')

                formats = [
                    {"id": "best", "label": "Best Available (4K / 2K / 1080p)", "ext": "mp4", "quality_tag": "MAX"},
                    {"id": "1080p", "label": "1080p Full HD", "ext": "mp4", "quality_tag": "FHD"},
                    {"id": "720p", "label": "720p HD", "ext": "mp4", "quality_tag": "HD"},
                    {"id": "480p", "label": "480p Standard", "ext": "mp4", "quality_tag": "SD"},
                    {"id": "mp3", "label": "Audio Only (MP3 320kbps)", "ext": "mp3", "quality_tag": "MP3"}
                ]

                return {
                    "success": True,
                    "is_playlist": False,
                    "has_playlist": bool(playlist_id is not None),
                    "playlist_id": playlist_id,
                    "id": info.get('id', ''),
                    "title": title,
                    "channel": channel,
                    "duration": duration,
                    "duration_string": duration_str,
                    "thumbnail": thumbnail,
                    "formats": formats,
                    "url": url
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_download(self, payload):
        """Starts downloading in a separate background thread."""
        url = payload.get("url")
        quality = payload.get("quality", "best")
        title = payload.get("title", "YouTube Video")
        thumbnail = payload.get("thumbnail", "")
        duration = payload.get("duration", 0)

        download_id = f"dl_{int(time.time()*1000)}"
        download_cancel_flags[download_id] = False

        lib = load_library()
        settings = lib.get("settings", {})
        download_folder = settings.get("download_folder", str(DOWNLOADS_DIR))
        
        # If part of a playlist or subfolder requested
        playlist_title = (payload.get("playlist_title") or payload.get("folder") or "").strip()
        if playlist_title:
            subfolder = sanitize_folder_name(playlist_title)
            download_folder = os.path.join(download_folder, subfolder)
            
        os.makedirs(download_folder, exist_ok=True)

        download_info = {
            "id": download_id,
            "url": url,
            "title": title,
            "thumbnail": thumbnail,
            "quality": quality,
            "status": "downloading",
            "progress": 0,
            "speed": "Starting...",
            "eta": "Calculating...",
            "downloaded": "0 MB",
            "total": "Calculating..."
        }
        active_downloads[download_id] = download_info

        t = threading.Thread(
            target=self._download_worker,
            args=(download_id, url, quality, download_folder, title, thumbnail, duration),
            daemon=True
        )
        t.start()

        return {"success": True, "download_id": download_id, "download": download_info}

    def start_playlist_download(self, payload):
        """Starts 3-worker concurrent parallel downloading of selected playlist items into dedicated playlist folder."""
        entries = payload.get("entries", [])
        quality = payload.get("quality", "best")
        playlist_title = (payload.get("title") or payload.get("playlist_title") or "Playlist").strip()

        if not entries:
            return {"success": False, "error": "No playlist entries provided."}

        lib = load_library()
        settings = lib.get("settings", {})
        base_download_folder = settings.get("download_folder", str(DOWNLOADS_DIR))
        
        # Create dedicated subfolder for the playlist inside the base download directory
        subfolder_name = sanitize_folder_name(playlist_title)
        playlist_download_folder = os.path.join(base_download_folder, subfolder_name)
        os.makedirs(playlist_download_folder, exist_ok=True)
        print(f"[Playlist Engine] Creating & targeting playlist folder: {playlist_download_folder}")

        total_count = len(entries)
        # Prepare and register initial download items in active_downloads with 'queued' status
        for idx, entry in enumerate(entries):
            entry_url = entry.get("url")
            entry_title = entry.get("title", f"Playlist Video {idx+1}")
            entry_thumb = entry.get("thumbnail", "")
            dl_id = f"dl_pl_{int(time.time()*1000)}_{idx}_{entry.get('id', idx)}"
            entry["_dl_id"] = dl_id
            download_cancel_flags[dl_id] = False

            dl_info = {
                "id": dl_id,
                "url": entry_url,
                "title": f"[{idx+1}/{total_count}] {entry_title}",
                "thumbnail": entry_thumb,
                "quality": quality,
                "status": "queued",
                "progress": 0,
                "speed": "In Queue",
                "eta": "Waiting (Max 3 Parallel)",
                "downloaded": "0 MB",
                "total": "Queued"
            }
            active_downloads[dl_id] = dl_info

        def execute_single_download(entry, idx):
            dl_id = entry.get("_dl_id")
            if download_cancel_flags.get(dl_id, False):
                if dl_id in active_downloads:
                    del active_downloads[dl_id]
                return

            entry_url = entry.get("url")
            entry_title = entry.get("title", f"Playlist Video {idx+1}")
            entry_thumb = entry.get("thumbnail", "")
            entry_dur = entry.get("duration_secs", 0)

            if dl_id in active_downloads:
                active_downloads[dl_id]["status"] = "downloading"
                active_downloads[dl_id]["speed"] = "Connecting..."
                active_downloads[dl_id]["eta"] = "Starting..."

            try:
                self._download_worker(dl_id, entry_url, quality, playlist_download_folder, entry_title, entry_thumb, entry_dur)
            except Exception as ex:
                print(f"[Playlist Worker] Error downloading entry {entry_title}: {ex}")
                if dl_id in active_downloads:
                    del active_downloads[dl_id]

        def playlist_pool_runner():
            from concurrent.futures import ThreadPoolExecutor
            # Run up to 3 concurrent downloads in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(execute_single_download, entry, idx) for idx, entry in enumerate(entries)]
                for f in futures:
                    try:
                        f.result()
                    except Exception as e:
                        print(f"[Playlist Pool] Task error: {e}")

        t = threading.Thread(target=playlist_pool_runner, daemon=True)
        t.start()

        return {"success": True, "count": total_count, "message": f"Started {total_count} downloads (3 parallel processes)."}

    def cancel_download(self, download_id):
        if download_id in download_cancel_flags:
            download_cancel_flags[download_id] = True
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "cancelled"
                del active_downloads[download_id]
            return {"success": True}
        return {"success": False, "error": "Download ID not found"}

    def _download_worker(self, download_id, url, quality, download_folder, title, thumbnail, duration):
        output_template = os.path.join(download_folder, '%(title).180B.%(ext)s')

        def progress_hook(d):
            if download_cancel_flags.get(download_id, False):
                raise Exception("Download cancelled by user")

            status = d.get('status')
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                percent = (downloaded / total * 100) if total > 0 else 0

                speed = d.get('speed') or 0
                speed_str = f"{speed / (1024*1024):.1f} MB/s" if speed else "0 MB/s"

                eta = d.get('eta')
                eta_str = f"{eta}s" if eta else "Calculating..."

                downloaded_mb = f"{downloaded / (1024*1024):.1f} MB"
                total_mb = f"{total / (1024*1024):.1f} MB" if total else "Unknown"

                update_data = {
                    "id": download_id,
                    "status": "downloading",
                    "progress": round(percent, 1),
                    "speed": speed_str,
                    "eta": eta_str,
                    "downloaded": downloaded_mb,
                    "total": total_mb
                }
                if download_id in active_downloads:
                    active_downloads[download_id].update(update_data)

                if self._window:
                    try:
                        self._window.evaluate_js(f"window.onDownloadProgress && window.onDownloadProgress({json.dumps(update_data)})")
                    except Exception:
                        pass

            elif status == 'finished':
                update_data = {
                    "id": download_id,
                    "status": "processing",
                    "progress": 99.5,
                    "speed": "Merging & Finalizing...",
                    "eta": "Almost done"
                }
                if download_id in active_downloads:
                    active_downloads[download_id].update(update_data)

                if self._window:
                    try:
                        self._window.evaluate_js(f"window.onDownloadProgress && window.onDownloadProgress({json.dumps(update_data)})")
                    except Exception:
                        pass

        ydl_opts = {
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'ffmpeg_location': FFMPEG_PATH,
            'windowsfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['web', 'android']}}
        }

        if quality == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            })
        else:
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4'
            }]

            if quality == '1080p':
                ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
            elif quality == '720p':
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'
            elif quality == '480p':
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best'
            else: # best
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)

                if 'entries' in info_dict and info_dict['entries']:
                    first_entry = list(info_dict['entries'])[0]
                    downloaded_file = ydl.prepare_filename(first_entry)
                    actual_title = first_entry.get('title', title)
                    actual_thumb = first_entry.get('thumbnail') or thumbnail
                    actual_duration = first_entry.get('duration', duration)
                else:
                    downloaded_file = ydl.prepare_filename(info_dict)
                    actual_title = info_dict.get('title', title)
                    actual_thumb = info_dict.get('thumbnail') or thumbnail
                    actual_duration = info_dict.get('duration', duration)

                if quality == 'mp3':
                    downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp3'
                else:
                    downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp4'

            duration_str = f"{actual_duration // 60}:{actual_duration % 60:02d}" if actual_duration else "Unknown"

            new_item = {
                "id": download_id,
                "title": actual_title,
                "thumbnail": actual_thumb,
                "duration": duration_str,
                "type": "audio" if quality == 'mp3' else "video",
                "date": time.strftime("%Y-%m-%d"),
                "completed_at": time.time(),
                "file_path": downloaded_file,
                "url": url,
                "quality": quality
            }

            lib = load_library()
            lib.setdefault("downloaded", []).insert(0, new_item)
            save_library(lib)

            if download_id in active_downloads:
                del active_downloads[download_id]

            complete_data = {
                "id": download_id,
                "status": "completed",
                "item": new_item,
                "message": f"Successfully downloaded: {actual_title}"
            }
            if self._window:
                try:
                    self._window.evaluate_js(f"window.onDownloadComplete && window.onDownloadComplete({json.dumps(complete_data)})")
                except Exception:
                    pass

        except Exception as e:
            error_msg = str(e)
            if download_id in active_downloads:
                del active_downloads[download_id]

            error_data = {
                "id": download_id,
                "status": "error",
                "error": error_msg
            }
            if self._window:
                try:
                    self._window.evaluate_js(f"window.onDownloadError && window.onDownloadError({json.dumps(error_data)})")
                except Exception:
                    pass


# Singleton API instance
api = DesktopApi()

# REST Endpoints for fallback / web browser mode
@server_app.route('/api/fetch_info', method=['POST', 'GET'])
def http_fetch_info():
    data = request.json or {}
    url = data.get('url') or request.query.get('url')
    mode = data.get('mode') or request.query.get('mode', 'auto')
    return json_response(api.fetch_info(url, mode))

@server_app.route('/api/start_download', method='POST')
def http_start_download():
    payload = request.json or {}
    return json_response(api.start_download(payload))

@server_app.route('/api/start_playlist_download', method='POST')
def http_start_playlist_download():
    payload = request.json or {}
    return json_response(api.start_playlist_download(payload))

@server_app.route('/api/cancel_download', method='POST')
def http_cancel_download():
    payload = request.json or {}
    return json_response(api.cancel_download(payload.get('id')))

@server_app.route('/api/cancel_all', method='POST')
def http_cancel_all():
    return json_response(api.cancel_all_downloads())

@server_app.route('/api/active_downloads', method='GET')
def http_active_downloads():
    return json_response(api.get_active_downloads())

@server_app.route('/api/library', method='GET')
def http_get_library():
    return json_response(api.get_library())

@server_app.route('/api/delete_item', method='POST')
def http_delete_item():
    payload = request.json or {}
    return json_response(api.delete_item(payload.get('id'), payload.get('delete_file', False)))

@server_app.route('/api/clear_history', method='POST')
def http_clear_history():
    payload = request.json or {}
    return json_response(api.clear_download_history(payload.get('delete_files', False)))

@server_app.route('/api/settings', method=['GET', 'POST'])
def http_settings():
    if request.method == 'POST':
        return json_response(api.save_settings(request.json or {}))
    return json_response(api.get_settings())

@server_app.route('/api/open_folder', method='POST')
def http_open_folder():
    payload = request.json or {}
    return json_response(api.open_in_folder(payload.get('filepath', '')))


def start_server():
    server_app.run(host='127.0.0.1', port=PORT, quiet=True)

def main():
    # Verify and set correct download folder for current host PC on startup
    initial_lib = load_library()
    active_folder = initial_lib.get("settings", {}).get("download_folder", "")
    print(f"[Pro Downloader] Ready! Verified Download Folder: {active_folder}")

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(0.4)

    window = webview.create_window(
        title="Pro Downloader",
        url=f"http://127.0.0.1:{PORT}",
        width=1240,
        height=820,
        min_size=(980, 660),
        frameless=False,
        easy_drag=True,
        js_api=api
    )

    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
