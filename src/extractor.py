import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional
import cv2
from PIL import Image

from src.detector import PersonDetector


@dataclass
class FrameRecord:
    index: int
    timestamp_sec: float
    timestamp_str: str
    has_person: bool
    confidence: float
    boxes: list
    full_path: str
    thumb_path: str


class VideoAnalysisWorker(threading.Thread):
    """
    Background worker thread to extract video frames at full FPS and
    run person detection without blocking the UI.
    """

    def __init__(
        self,
        video_path: str,
        detector: PersonDetector,
        output_dir: str,
        step: int = 1,
        conf_threshold: float = 0.35,
        on_progress: Optional[Callable[[int, int, int, int, float, str, Optional[FrameRecord]], None]] = None,
        on_complete: Optional[Callable[[List[FrameRecord]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.detector = detector
        self.output_dir = output_dir
        self.step = max(1, step)
        self.conf_threshold = conf_threshold
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        
        self._is_cancelled = False
        self.records: List[FrameRecord] = []

    def cancel(self):
        """Signals the worker to stop processing gracefully."""
        self._is_cancelled = True

    def run(self):
        try:
            full_dir = os.path.join(self.output_dir, "full")
            thumb_dir = os.path.join(self.output_dir, "thumb")
            os.makedirs(full_dir, exist_ok=True)
            os.makedirs(thumb_dir, exist_ok=True)

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Could not open video file: {self.video_path}")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            
            # Target frames to process based on step
            target_frame_indices = list(range(0, total_frames, self.step))
            total_targets = len(target_frame_indices)
            
            current_frame_idx = 0
            processed_count = 0
            person_count = 0
            no_person_count = 0
            
            start_time = time.perf_counter()
            next_target_set = set(target_frame_indices)

            while cap.isOpened() and not self._is_cancelled:
                ret, frame = cap.read()
                if not ret:
                    break

                if current_frame_idx in next_target_set:
                    # Save full-res image
                    full_filename = f"frame_{current_frame_idx:06d}.jpg"
                    full_filepath = os.path.join(full_dir, full_filename)
                    cv2.imwrite(full_filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

                    # Save thumbnail (max width 280)
                    h, w = frame.shape[:2]
                    thumb_w = 280
                    thumb_h = max(1, int(280 * h / w))
                    thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
                    thumb_filename = f"thumb_{current_frame_idx:06d}.jpg"
                    thumb_filepath = os.path.join(thumb_dir, thumb_filename)
                    cv2.imwrite(thumb_filepath, thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])

                    # Person detection
                    has_person, max_conf, boxes = self.detector.detect(
                        frame, conf_threshold=self.conf_threshold
                    )

                    if has_person:
                        person_count += 1
                    else:
                        no_person_count += 1

                    # Timestamp formatting (MM:SS.ms)
                    t_sec = current_frame_idx / fps
                    mins = int(t_sec // 60)
                    secs = int(t_sec % 60)
                    milli = int((t_sec * 100) % 100)
                    t_str = f"{mins:02d}:{secs:02d}.{milli:02d}"

                    record = FrameRecord(
                        index=current_frame_idx,
                        timestamp_sec=t_sec,
                        timestamp_str=t_str,
                        has_person=has_person,
                        confidence=max_conf,
                        boxes=boxes,
                        full_path=full_filepath,
                        thumb_path=thumb_filepath,
                    )
                    self.records.append(record)
                    processed_count += 1

                    # Speed & ETA calculation
                    elapsed = time.perf_counter() - start_time
                    fps_calc = processed_count / elapsed if elapsed > 0 else 0.0
                    remaining_frames = total_targets - processed_count
                    eta_sec = remaining_frames / fps_calc if fps_calc > 0 else 0.0
                    
                    if eta_sec >= 60:
                        eta_str = f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
                    else:
                        eta_str = f"{int(eta_sec)}s"

                    # Notify progress
                    if self.on_progress:
                        self.on_progress(
                            processed_count,
                            total_targets,
                            person_count,
                            no_person_count,
                            fps_calc,
                            eta_str,
                            record,
                        )

                current_frame_idx += 1

            cap.release()

            if self.on_complete:
                self.on_complete(self.records)

        except Exception as e:
            if self.on_error:
                self.on_error(e)


class VideoMetadata:
    """Helper class to extract and format video info."""

    @staticmethod
    def get_info(video_path: str) -> dict:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        duration_sec = total_frames / fps if fps > 0 else 0
        mins = int(duration_sec // 60)
        secs = int(duration_sec % 60)
        dur_str = f"{mins:02d}:{secs:02d}"

        return {
            "path": video_path,
            "filename": os.path.basename(video_path),
            "size_mb": file_size_mb,
            "total_frames": total_frames,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "duration_sec": duration_sec,
            "duration_str": dur_str,
        }
