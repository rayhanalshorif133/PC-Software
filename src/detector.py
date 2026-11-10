import os
import sys
import cv2
import numpy as np


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    full_path = os.path.join(base_path, relative_path)
    if os.path.exists(full_path):
        return full_path
    
    # Fallback to local cwd
    local_path = os.path.abspath(relative_path)
    if os.path.exists(local_path):
        return local_path
        
    return full_path


class PersonDetector:
    """
    High-performance, lightweight Person Detector using YOLOv5n ONNX and OpenCV DNN.
    Detects COCO class 0 (person).
    """

    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = get_resource_path(os.path.join("models", "yolov5n.onnx"))
            
        if not os.path.exists(model_path):
            # Check current working directory or other candidates
            alt_path = os.path.join("models", "yolov5n.onnx")
            if os.path.exists(alt_path):
                model_path = alt_path
            else:
                raise FileNotFoundError(f"Model file not found at: {model_path}")
                
        self.model_path = model_path
        self.net = cv2.dnn.readNetFromONNX(self.model_path)
        
        # Optimize backend if available
        try:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        except Exception:
            pass
        
        # Warm up
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        blob = cv2.dnn.blobFromImage(dummy, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        self.net.forward()

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.35, nms_threshold: float = 0.45):
        """
        Detects if a person is present in the frame.
        
        Returns:
            has_person (bool): True if at least one person detected above conf_threshold.
            max_conf (float): Maximum confidence score for person class.
            boxes (list): List of dicts [{'box': [x1, y1, w, h], 'conf': float}]
        """
        h, w = frame.shape[:2]
        
        # Letterbox 640x640 resize
        scale = min(640.0 / h, 640.0 / w)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        
        dw = (640 - nw) // 2
        dh = (640 - nh) // 2
        
        canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
        canvas[dh:dh + nh, dw:dw + nw] = resized
        
        blob = cv2.dnn.blobFromImage(canvas, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()
        
        # YOLOv5 output shape: (1, 25200, 85)
        # Class 0: person
        obj_conf = out[0, :, 4]
        person_cls_conf = out[0, :, 5]
        scores = obj_conf * person_cls_conf
        
        mask = scores >= conf_threshold
        if not np.any(mask):
            max_c = float(np.max(scores)) if len(scores) > 0 else 0.0
            return False, max_c, []
            
        candidate_indices = np.where(mask)[0]
        boxes_list = []
        confidences_list = []
        
        for idx in candidate_indices:
            cx, cy, bw, bh = out[0, idx, 0:4]
            # Convert letterbox coordinates back to original frame
            x1 = int(round((cx - bw / 2 - dw) / scale))
            y1 = int(round((cy - bh / 2 - dh) / scale))
            bw_orig = int(round(bw / scale))
            bh_orig = int(round(bh / scale))
            
            # Clamp to frame bounds
            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            bw_orig = max(1, min(w - x1, bw_orig))
            bh_orig = max(1, min(h - y1, bh_orig))
            
            boxes_list.append([x1, y1, bw_orig, bh_orig])
            confidences_list.append(float(scores[idx]))
            
        indices = cv2.dnn.NMSBoxes(boxes_list, confidences_list, conf_threshold, nms_threshold)
        final_boxes = []
        if len(indices) > 0:
            for i in indices.flatten():
                final_boxes.append({
                    "box": boxes_list[i],
                    "conf": confidences_list[i]
                })
                
        max_c = float(max(confidences_list)) if confidences_list else 0.0
        return len(final_boxes) > 0, max_c, final_boxes

    @staticmethod
    def draw_detections(frame: np.ndarray, boxes: list) -> np.ndarray:
        """Draws bounding boxes and confidence badges on a copy of the frame."""
        vis_frame = frame.copy()
        for item in boxes:
            x, y, w, h = item["box"]
            conf = item["conf"]
            # Bright cyan/green bounding box
            cv2.rectangle(vis_frame, (x, y), (x + w, y + h), (0, 220, 100), 2)
            
            label = f"Person {int(conf * 100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Label background banner
            cv2.rectangle(vis_frame, (x, max(0, y - th - 6)), (x + tw + 6, max(0, y)), (0, 220, 100), -1)
            cv2.putText(vis_frame, label, (x + 3, max(th, y - 4)), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
            
        return vis_frame
