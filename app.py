"""
V-Editor - Desktop Mobile Video Editor
Backend server, native bridge, and FFmpeg video processing engine.
"""

import os
import sys
import re
import json
import shutil
import socket
import mimetypes
import threading
import subprocess
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Determine base paths
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UI_DIR = os.path.join(BASE_DIR, 'ui')

# Locate FFmpeg binary
def get_ffmpeg_exe():
    if getattr(sys, 'frozen', False):
        cand1 = os.path.join(BASE_DIR, 'ffmpeg.exe')
        if os.path.exists(cand1):
            return cand1
        cand2 = os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe')
        if os.path.exists(cand2):
            return cand2

    local_cand = os.path.join(BASE_DIR, 'ffmpeg.exe')
    if os.path.exists(local_cand):
        return local_cand

    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print("imageio_ffmpeg error:", e)

    system_cand = shutil.which('ffmpeg')
    if system_cand:
        return system_cand

    raise RuntimeError("FFmpeg executable could not be found.")

FFMPEG_EXE = get_ffmpeg_exe()
print(f"[V-Editor] Using FFmpeg: {FFMPEG_EXE}")

# Global window reference at module level (Do NOT attach to Api class to prevent serialization recursion!)
GLOBAL_WINDOW = None

# Automatically detect current PC's Downloads folder
def get_downloads_folder():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
            for subkey in ['{374DE290-123F-4565-9164-39C4925E467B}', 'Downloads']:
                try:
                    val, _ = winreg.QueryValueEx(key, subkey)
                    expanded = os.path.expandvars(val)
                    if os.path.exists(expanded):
                        return os.path.normpath(expanded)
                except FileNotFoundError:
                    pass
    except Exception:
        pass
    std = os.path.join(os.path.expanduser('~'), 'Downloads')
    if os.path.exists(std):
        return os.path.normpath(std)
    return os.path.normpath(os.path.expanduser('~'))

import hashlib
import tempfile

SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.veditor_settings.json')

def load_settings():
    defaults = {
        'export_dir': get_downloads_folder(),
        'last_video_path': '',
        'last_open_dir': ''
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    defaults.update(data)
                    if not defaults.get('export_dir') or not os.path.exists(defaults['export_dir']):
                        defaults['export_dir'] = get_downloads_folder()
                    return defaults
        except Exception:
            pass
    return defaults

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print("[V-Editor] Failed to save settings:", e)

# Fast Video Thumbnail Generator & Disk Cache
class VideoThumbnailCache:
    def __init__(self, ffmpeg_exe):
        self.ffmpeg_exe = ffmpeg_exe
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'veditor_thumb_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.jobs = {}
        self.lock = threading.Lock()

    def resolve_path(self, video_path):
        if not video_path:
            return ""
        if video_path in ['test_sample.mp4', '/test_sample.mp4']:
            return os.path.normpath(os.path.join(BASE_DIR, 'test_sample.mp4'))
        if not os.path.isabs(video_path):
            local_cand = os.path.join(BASE_DIR, video_path)
            if os.path.exists(local_cand):
                return os.path.normpath(local_cand)
        return os.path.normpath(os.path.abspath(video_path))

    def get_video_id(self, video_path):
        norm = self.resolve_path(video_path)
        try:
            st = os.stat(norm)
            key = f"{norm}_{st.st_size}_{st.st_mtime}"
        except Exception:
            key = norm
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def ensure_thumbnails(self, video_path):
        resolved = self.resolve_path(video_path)
        if not resolved or not os.path.exists(resolved):
            return None

        video_id = self.get_video_id(resolved)
        thumb_folder = os.path.join(self.cache_dir, video_id)

        with self.lock:
            if resolved in self.jobs and os.path.exists(thumb_folder):
                return self.jobs[resolved]

            os.makedirs(thumb_folder, exist_ok=True)
            job = {
                'dir': thumb_folder,
                'done': False,
                'fps': 2.0,
                'video_path': resolved
            }
            self.jobs[resolved] = job

        existing = [f for f in os.listdir(thumb_folder) if f.startswith('thumb_') and f.endswith('.jpg')]
        if len(existing) > 5:
            job['done'] = True
            job['count'] = len(existing)
            return job

        def worker():
            try:
                pattern = os.path.join(thumb_folder, 'thumb_%04d.jpg')
                cmd = [
                    self.ffmpeg_exe,
                    '-y',
                    '-i', resolved,
                    '-vf', 'fps=2,scale=120:-1',
                    '-q:v', '6',
                    pattern
                ]
                creationflags = 0x08000000 if os.name == 'nt' else 0
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
                job['done'] = True
                job['count'] = len([f for f in os.listdir(thumb_folder) if f.startswith('thumb_') and f.endswith('.jpg')])
            except Exception as e:
                print("[V-Editor] Thumbnail extraction failed:", e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return job

    def get_thumb_path_for_time(self, video_path, time_sec):
        resolved = self.resolve_path(video_path)
        job = self.ensure_thumbnails(resolved)
        if not job:
            return None

        idx = max(1, int(round(time_sec * job['fps'])) + 1)
        thumb_folder = job['dir']
        filename = f"thumb_{idx:04d}.jpg"
        target_file = os.path.join(thumb_folder, filename)

        waited = 0.0
        while not os.path.exists(target_file) and not job.get('done', False) and waited < 0.4:
            import time
            time.sleep(0.04)
            waited += 0.04

        if os.path.exists(target_file):
            return target_file

        try:
            files = sorted([f for f in os.listdir(thumb_folder) if f.startswith('thumb_') and f.endswith('.jpg')])
            if files:
                best = files[0]
                best_diff = 999999
                for f in files:
                    try:
                        f_idx = int(f.replace('thumb_', '').replace('.jpg', ''))
                        diff = abs(f_idx - idx)
                        if diff < best_diff:
                            best_diff = diff
                            best = f
                        if diff == 0:
                            break
                    except ValueError:
                        continue
                return os.path.join(thumb_folder, best)
        except Exception:
            pass

        return None

THUMBNAIL_CACHE = VideoThumbnailCache(FFMPEG_EXE)

# Threaded HTTP Server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class VideoRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Range, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ['/', '/index.html']:
            self.serve_file(os.path.join(UI_DIR, 'index.html'), 'text/html')
        elif path.startswith('/ui/') or path in ['/style.css', '/app.js']:
            filename = os.path.basename(path)
            filepath = os.path.join(UI_DIR, filename)
            mime, _ = mimetypes.guess_type(filepath)
            self.serve_file(filepath, mime or 'application/octet-stream')
        elif path == '/test_sample.mp4':
            sample_path = os.path.join(BASE_DIR, 'test_sample.mp4')
            self.serve_range(sample_path, 'video/mp4')
        elif path == '/video_stream':
            query = urllib.parse.parse_qs(parsed.query)
            video_path = query.get('path', [None])[0]
            if video_path:
                video_path = urllib.parse.unquote(video_path)
                if os.path.exists(video_path):
                    mime, _ = mimetypes.guess_type(video_path)
                    self.serve_range(video_path, mime or 'video/mp4')
                    return
            self.send_error(404, 'Video not found')
        elif path == '/thumb':
            query = urllib.parse.parse_qs(parsed.query)
            video_path = query.get('path', [None])[0]
            time_str = query.get('t', ['0'])[0]
            if video_path:
                video_path = urllib.parse.unquote(video_path)
                try:
                    time_sec = float(time_str)
                except ValueError:
                    time_sec = 0.0

                thumb_file = THUMBNAIL_CACHE.get_thumb_path_for_time(video_path, time_sec)
                if thumb_file and os.path.exists(thumb_file):
                    self.serve_image(thumb_file)
                    return
            self.send_response(204)
            self.end_headers()
        elif path == '/ensure_thumbnails':
            query = urllib.parse.parse_qs(parsed.query)
            video_path = query.get('path', [None])[0]
            if video_path:
                video_path = urllib.parse.unquote(video_path)
                THUMBNAIL_CACHE.ensure_thumbnails(video_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            rel = path.lstrip('/')
            filepath = os.path.join(UI_DIR, rel)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                mime, _ = mimetypes.guess_type(filepath)
                self.serve_file(filepath, mime or 'application/octet-stream')
            else:
                self.send_error(404, 'File not found')

    def serve_image(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            pass

    def serve_file(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_error(404, 'File not found')
            return
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            pass

    def serve_range(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_error(404, 'File not found')
            return
        try:
            filesize = os.path.getsize(filepath)
            range_header = self.headers.get('Range', None)

            if not range_header:
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(filesize))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile, length=64 * 1024)
                return

            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if not match:
                self.send_error(416, 'Requested Range Not Satisfiable')
                return

            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else filesize - 1
            if start >= filesize:
                self.send_error(416, 'Requested Range Not Satisfiable')
                return
            end = min(end, filesize - 1)

            chunk_size = end - start + 1
            self.send_response(206)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Range', f'bytes {start}-{end}/{filesize}')
            self.send_header('Content-Length', str(chunk_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()

            with open(filepath, 'rb') as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_len = min(64 * 1024, bytes_left)
                    chunk = f.read(read_len)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    bytes_left -= len(chunk)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            pass

# Check audio track presence using FFmpeg probe
def check_has_audio(video_path):
    try:
        res = subprocess.run([FFMPEG_EXE, '-i', video_path], capture_output=True, text=True, timeout=5)
        return 'Audio:' in res.stderr
    except Exception:
        return False

# Video Export Function
def run_ffmpeg_export(payload):
    try:
        source_path = payload.get('sourcePath')
        if not source_path or not os.path.exists(source_path):
            sample = os.path.join(BASE_DIR, 'test_sample.mp4')
            if os.path.exists(sample):
                source_path = sample
            else:
                return {'success': False, 'error': f"Source file does not exist: {source_path}"}

        source_path = os.path.abspath(source_path)

        output_path = payload.get('outputPath')
        settings = load_settings()
        default_dir = settings.get('export_dir', get_downloads_folder())

        if not output_path:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(default_dir, f"V_Editor_{ts}.mp4")

        # Make sure path is absolute and directory exists
        if not os.path.isabs(output_path):
            output_path = os.path.join(default_dir, output_path)

        output_path = os.path.normpath(output_path)
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            # Persist export folder for future exports
            settings['export_dir'] = out_dir
            save_settings(settings)

        clips = payload.get('clips', [])
        if not clips:
            return {'success': False, 'error': 'No clips to export.'}

        has_audio = check_has_audio(source_path)

        # Build FFmpeg filtergraph
        filter_parts = []
        concat_streams = []
        total_target_duration = 0.0

        for i, c in enumerate(clips):
            start = float(c.get('sourceStart', 0.0))
            end = float(c.get('sourceEnd', 0.0))
            speed = float(c.get('speed', 1.0))
            volume = float(c.get('volume', 1.0))
            reverse = bool(c.get('reverse', False))

            eff_dur = (end - start) / speed
            total_target_duration += eff_dur

            # Video filter
            vf_filters = [f"trim=start={start:.3f}:end={end:.3f}", "setpts=PTS-STARTPTS"]
            if abs(speed - 1.0) > 0.01:
                vf_filters.append(f"setpts=(1/{speed})*PTS")
            if reverse:
                vf_filters.append("reverse")

            # Resolution scaling if requested
            res_opt = payload.get('resolution', 'original')
            if res_opt == '1080p':
                vf_filters.append("scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))'")
            elif res_opt == '720p':
                vf_filters.append("scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))'")

            filter_parts.append(f"[0:v]{','.join(vf_filters)}[v{i}]")

            # Audio filter
            if has_audio:
                af_filters = [f"atrim=start={start:.3f}:end={end:.3f}", "asetpts=PTS-STARTPTS"]
                if abs(speed - 1.0) > 0.01:
                    s = speed
                    while s < 0.5:
                        af_filters.append("atempo=0.5")
                        s /= 0.5
                    while s > 2.0:
                        af_filters.append("atempo=2.0")
                        s /= 2.0
                    af_filters.append(f"atempo={s:.3f}")
                if abs(volume - 1.0) > 0.01:
                    af_filters.append(f"volume={volume:.2f}")
                if reverse:
                    af_filters.append("areverse")

                filter_parts.append(f"[0:a]{','.join(af_filters)}[a{i}]")
                concat_streams.append(f"[v{i}][a{i}]")
            else:
                concat_streams.append(f"[v{i}]")

        n = len(clips)
        if has_audio:
            concat_filter = f"{''.join(concat_streams)}concat=n={n}:v=1:a=1[outv][outa]"
            filter_parts.append(concat_filter)
            map_args = ['-map', '[outv]', '-map', '[outa]']
        else:
            concat_filter = f"{''.join(concat_streams)}concat=n={n}:v=1:a=0[outv]"
            filter_parts.append(concat_filter)
            map_args = ['-map', '[outv]']

        fc = ";".join(filter_parts)

        cmd = [
            FFMPEG_EXE, '-y',
            '-i', source_path,
            '-filter_complex', fc,
            *map_args,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'fast',
            '-crf', '22',
        ]
        if has_audio:
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])

        cmd.extend(['-progress', 'pipe:1', output_path])

        print(f"[V-Editor] Exporting to: {output_path}")

        # Use stderr=subprocess.STDOUT to combine streams and prevent pipe deadlock!
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            line = line.strip()
            if line.startswith('out_time_us='):
                val = line.split('=', 1)[1]
                try:
                    us = int(val)
                    cur_sec = us / 1000000.0
                    if total_target_duration > 0:
                        pct = min(99.0, (cur_sec / total_target_duration) * 100.0)
                        if GLOBAL_WINDOW:
                            GLOBAL_WINDOW.evaluate_js(f"window.updateExportProgress({pct:.1f}, 'Encoding: {int(pct)}%');")
                except Exception:
                    pass

        process.wait()

        if process.returncode != 0:
            error_tail = "".join(output_lines[-20:])
            print("[V-Editor] Export failed:", error_tail)
            return {'success': False, 'error': f"FFmpeg failed with code {process.returncode}:\n{error_tail}"}

        if GLOBAL_WINDOW:
            GLOBAL_WINDOW.evaluate_js("window.updateExportProgress(100.0, 'Export complete!');")

        return {'success': True, 'outputPath': output_path}

    except Exception as e:
        print("[V-Editor] Export exception:", e)
        return {'success': False, 'error': str(e)}

# PyWebView Bridge API (Contains NO references to Window object to prevent cyclic recursion!)
class VideoEditorApi:
    def get_sample_path(self):
        sample = os.path.join(BASE_DIR, 'test_sample.mp4')
        if os.path.exists(sample):
            THUMBNAIL_CACHE.ensure_thumbnails(sample)
            return os.path.abspath(sample)
        return ""

    def get_last_video_path(self):
        settings = load_settings()
        last_path = settings.get('last_video_path', '')
        if last_path and os.path.exists(last_path):
            abs_path = os.path.abspath(last_path)
            THUMBNAIL_CACHE.ensure_thumbnails(abs_path)
            return abs_path
        return ""

    def set_last_video_path(self, file_path):
        if not file_path:
            return False
        if file_path in ['test_sample.mp4', '/test_sample.mp4']:
            file_path = os.path.join(BASE_DIR, 'test_sample.mp4')
        if os.path.exists(file_path):
            abs_path = os.path.abspath(file_path)
            settings = load_settings()
            settings['last_video_path'] = abs_path
            settings['last_open_dir'] = os.path.dirname(abs_path)
            save_settings(settings)
            THUMBNAIL_CACHE.ensure_thumbnails(abs_path)
            return True
        return False

    def prepare_thumbnails(self, file_path):
        if not file_path:
            return False
        if file_path in ['test_sample.mp4', '/test_sample.mp4']:
            file_path = os.path.join(BASE_DIR, 'test_sample.mp4')
        if os.path.exists(file_path):
            THUMBNAIL_CACHE.ensure_thumbnails(file_path)
            return True
        return False

    def get_default_save_path(self, video_title=""):
        settings = load_settings()
        export_dir = settings.get('export_dir')
        if not export_dir or not os.path.exists(export_dir):
            export_dir = get_downloads_folder()
            settings['export_dir'] = export_dir
            save_settings(settings)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        clean_title = re.sub(r'[^\w\-_\.]', '_', video_title).strip('_') if video_title else ""
        if clean_title:
            base_title, _ = os.path.splitext(clean_title)
            filename = f"{base_title}_edited_{ts}.mp4"
        else:
            filename = f"V_Editor_Export_{ts}.mp4"

        return os.path.normpath(os.path.join(export_dir, filename))

    def open_video_dialog(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            settings = load_settings()
            initialdir = settings.get('last_open_dir')
            if not initialdir or not os.path.exists(initialdir):
                last_path = settings.get('last_video_path')
                if last_path and os.path.exists(last_path):
                    initialdir = os.path.dirname(last_path)
                else:
                    initialdir = os.path.expanduser('~')

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            chosen = filedialog.askopenfilename(
                parent=root,
                title="Select Video File",
                initialdir=initialdir,
                filetypes=[
                    ("Video Files", "*.mp4;*.mov;*.avi;*.mkv;*.webm;*.flv;*.m4v"),
                    ("All Files", "*.*")
                ]
            )
            root.destroy()
            if chosen:
                chosen = os.path.normpath(chosen)
                self.set_last_video_path(chosen)
                return chosen
            return ""
        except Exception as e:
            print("[V-Editor] open dialog error:", e)
            return ""

    def choose_save_path(self, current_path=""):
        settings = load_settings()
        default_dir = settings.get('export_dir', get_downloads_folder())

        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            if current_path and os.path.isabs(current_path):
                initialdir = os.path.dirname(current_path)
                initialfile = os.path.basename(current_path)
            else:
                initialdir = default_dir
                initialfile = os.path.basename(current_path) if current_path else "V_Editor_Export.mp4"

            chosen = filedialog.asksaveasfilename(
                parent=root,
                title="Choose Save Destination for Exported Video",
                initialdir=initialdir,
                initialfile=initialfile,
                defaultextension=".mp4",
                filetypes=[("MP4 Video (*.mp4)", "*.mp4"), ("All Files", "*.*")]
            )
            root.destroy()
            if chosen:
                chosen = os.path.normpath(chosen)
                # Persist chosen directory for future exports!
                settings['export_dir'] = os.path.dirname(chosen)
                save_settings(settings)
                return chosen
            return ""
        except Exception as e:
            print("[V-Editor] save dialog error:", e)
            return ""

    def export_video(self, payload):
        return run_ffmpeg_export(payload)

    def open_folder(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            return True
        except Exception:
            return False

    def play_exported_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            os.startfile(os.path.normpath(file_path))
            return True
        except Exception:
            return False

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def main():
    global GLOBAL_WINDOW
    import webview

    port = find_free_port()
    server = ThreadedHTTPServer(('127.0.0.1', port), VideoRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[V-Editor] Server running on http://127.0.0.1:{port}/")

    api = VideoEditorApi()
    window = webview.create_window(
        title='V-Editor - Desktop Video Editor',
        url=f'http://127.0.0.1:{port}/',
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color='#0a0a0c'
    )
    GLOBAL_WINDOW = window

    webview.start(debug=False)

if __name__ == '__main__':
    main()
