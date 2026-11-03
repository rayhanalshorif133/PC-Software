"""
video_extractor.py
Core video to image extraction engine using OpenCV.
Thread-safe, robust unicode path support, progress tracking, and cancelable.
"""

import os
import time
import cv2
import numpy as np
from typing import Callable, Optional, Dict, Any, Tuple


class VideoInfo:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.exists = os.path.exists(filepath)
        self.filesize_mb = os.path.getsize(filepath) / (1024 * 1024) if self.exists else 0
        
        self.total_frames = 0
        self.fps = 0.0
        self.width = 0
        self.height = 0
        self.duration_seconds = 0.0
        self.is_valid = False
        self.error_message = ""
        
        self._load_metadata()

    def _load_metadata(self):
        if not self.exists:
            self.error_message = f"File not found: {self.filepath}"
            return

        cap = cv2.VideoCapture(self.filepath)
        if not cap.isOpened():
            self.error_message = f"Unable to open video file: {self.filename}"
            return

        try:
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = float(cap.get(cv2.CAP_PROP_FPS))
            self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Guard against invalid fps or frames
            if self.fps <= 0 or np.isnan(self.fps):
                self.fps = 25.0  # fallback assumption
            
            if self.total_frames > 0 and self.fps > 0:
                self.duration_seconds = self.total_frames / self.fps
            else:
                self.duration_seconds = 0.0

            self.is_valid = True
        except Exception as e:
            self.error_message = str(e)
        finally:
            cap.release()

    @property
    def duration_formatted(self) -> str:
        seconds = int(self.duration_seconds)
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    @property
    def resolution_formatted(self) -> str:
        return f"{self.width}x{self.height}"


class VideoExtractor:
    def __init__(self):
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    @staticmethod
    def calculate_target_frames(video_info: VideoInfo, mode: str, value: float) -> Tuple[int, list]:
        """
        Calculates exact target frame indices based on mode and value.
        Modes:
          - 'fps': Extract at 'value' frames per second (e.g. 1.0 fps, 2.0 fps)
          - 'interval_frames': Extract every 'value' frames (e.g. every 10 frames)
          - 'interval_seconds': Extract every 'value' seconds (e.g. every 2.0 seconds)
          - 'all': Extract all frames
        """
        if not video_info.is_valid or video_info.total_frames <= 0:
            return 0, []

        total_frames = video_info.total_frames
        native_fps = video_info.fps

        if mode == 'all':
            frame_indices = list(range(0, total_frames))
        elif mode == 'fps':
            target_fps = max(0.01, float(value))
            step = native_fps / target_fps
            frame_indices = []
            curr = 0.0
            while int(curr) < total_frames:
                idx = int(curr)
                if not frame_indices or frame_indices[-1] != idx:
                    frame_indices.append(idx)
                curr += step
        elif mode == 'interval_frames':
            step = max(1, int(round(value)))
            frame_indices = list(range(0, total_frames, step))
        elif mode == 'interval_seconds':
            sec_step = max(0.01, float(value))
            step = max(1.0, sec_step * native_fps)
            frame_indices = []
            curr = 0.0
            while int(curr) < total_frames:
                idx = int(curr)
                if not frame_indices or frame_indices[-1] != idx:
                    frame_indices.append(idx)
                curr += step
        else:
            frame_indices = list(range(0, total_frames))

        return len(frame_indices), frame_indices

    def extract(
        self,
        video_info: VideoInfo,
        output_dir: str,
        frame_indices: list,
        image_format: str = "jpg",
        image_quality: int = 95,
        filename_prefix: str = "frame",
        naming_style: str = "counter",  # 'counter' or 'timestamp'
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_thumbnail: Optional[Callable[[np.ndarray], None]] = None
    ) -> Dict[str, Any]:
        """
        Extract frames and save images safely to output_dir.
        Thread-safe execution with cancellation check.
        """
        self._is_cancelled = False
        os.makedirs(output_dir, exist_ok=True)

        total_to_extract = len(frame_indices)
        if total_to_extract == 0:
            return {"success": False, "error": "No frames to extract", "saved_count": 0}

        ext = f".{image_format.lower()}"
        if ext == ".jpeg":
            ext = ".jpg"

        # OpenCV compression parameters
        encode_params = []
        if ext in [".jpg", ".jpeg"]:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(image_quality)]
        elif ext == ".png":
            # 0 to 9, where 3 is balanced speed/compression
            encode_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
        elif ext == ".webp":
            encode_params = [int(cv2.IMWRITE_WEBP_QUALITY), int(image_quality)]

        cap = cv2.VideoCapture(video_info.filepath)
        if not cap.isOpened():
            return {"success": False, "error": "Failed to open video file", "saved_count": 0}

        saved_count = 0
        current_frame_pos = 0
        pad_width = max(5, len(str(total_to_extract)))
        start_time = time.time()
        last_progress_time = 0.0

        try:
            for i, target_frame in enumerate(frame_indices):
                if self._is_cancelled:
                    return {
                        "success": False,
                        "cancelled": True,
                        "saved_count": saved_count,
                        "total_target": total_to_extract,
                        "elapsed_seconds": time.time() - start_time
                    }

                # Frame jumping logic:
                # If target is sequential or within a few frames, grabbing is much faster than seeking
                diff = target_frame - current_frame_pos
                if 0 <= diff <= 15:
                    for _ in range(diff):
                        cap.grab()
                        current_frame_pos += 1
                    ret, frame = cap.read()
                    current_frame_pos += 1
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    current_frame_pos = target_frame
                    ret, frame = cap.read()
                    current_frame_pos += 1

                if not ret or frame is None:
                    continue

                # Generate filename
                if naming_style == "timestamp":
                    timestamp_sec = target_frame / video_info.fps
                    mins = int(timestamp_sec // 60)
                    secs = int(timestamp_sec % 60)
                    millis = int((timestamp_sec - int(timestamp_sec)) * 1000)
                    file_name = f"{filename_prefix}_{mins:02d}m{secs:02d}s{millis:03d}ms{ext}"
                else:
                    file_name = f"{filename_prefix}_{saved_count + 1:0{pad_width}d}{ext}"

                out_path = os.path.join(output_dir, file_name)

                # Unicode-safe image saving on Windows
                success_enc, buffer = cv2.imencode(ext, frame, encode_params)
                if success_enc:
                    with open(out_path, "wb") as f:
                        buffer.tofile(f)
                    saved_count += 1

                # Progress reporting (throttle to avoid GUI stutter, e.g. every 50ms or every frame if small)
                now = time.time()
                if (now - last_progress_time > 0.05) or (i == total_to_extract - 1):
                    last_progress_time = now
                    elapsed = max(0.001, now - start_time)
                    fps_speed = saved_count / elapsed
                    percent = int((i + 1) / total_to_extract * 100)
                    remaining_items = total_to_extract - (i + 1)
                    eta_seconds = remaining_items / fps_speed if fps_speed > 0 else 0

                    if on_progress:
                        on_progress({
                            "current": i + 1,
                            "total": total_to_extract,
                            "saved_count": saved_count,
                            "percentage": percent,
                            "speed_fps": fps_speed,
                            "elapsed_seconds": elapsed,
                            "eta_seconds": eta_seconds,
                            "current_filename": file_name
                        })

                    if on_thumbnail:
                        on_thumbnail(frame)

        except Exception as e:
            return {"success": False, "error": str(e), "saved_count": saved_count}
        finally:
            cap.release()

        elapsed_total = time.time() - start_time
        return {
            "success": True,
            "cancelled": False,
            "saved_count": saved_count,
            "total_target": total_to_extract,
            "elapsed_seconds": elapsed_total,
            "output_dir": output_dir
        }

