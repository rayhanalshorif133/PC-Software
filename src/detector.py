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
    High-performance, lightweight Person & Full-Body/Face Detector using
    YOLOv5n ONNX + OpenCV YuNet DNN.
    """

    def __init__(self, model_path: str = None, face_model_path: str = None):
        if model_path is None:
            model_path = get_resource_path(os.path.join("models", "yolov5n.onnx"))
            
        if not os.path.exists(model_path):
            alt_path = os.path.join("models", "yolov5n.onnx")
            if os.path.exists(alt_path):
                model_path = alt_path
            else:
                raise FileNotFoundError(f"Person model file not found at: {model_path}")
                
        self.model_path = model_path
        self.net = cv2.dnn.readNetFromONNX(self.model_path)
        
        # Optimize backend if available
        try:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        except Exception:
            pass
        
        # Warm up YOLO
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        blob = cv2.dnn.blobFromImage(dummy, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        self.net.forward()

        # Face Detector (YuNet)
        if face_model_path is None:
            face_model_path = get_resource_path(os.path.join("models", "yunet.onnx"))
        if not os.path.exists(face_model_path):
            alt_face = os.path.join("models", "yunet.onnx")
            if os.path.exists(alt_face):
                face_model_path = alt_face

        self.face_detector = None
        if os.path.exists(face_model_path):
            try:
                self.face_detector = cv2.FaceDetectorYN_create(
                    model=face_model_path,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.50,
                    nms_threshold=0.3,
                    top_k=10,
                )
            except Exception as e:
                print(f"Warning: Could not initialize YuNet face detector: {e}")

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.35, nms_threshold: float = 0.45):
        """
        Detects if a person is present and verifies full body with clean face.
        
        Returns:
            has_person (bool): True if at least one person detected.
            max_conf (float): Maximum confidence score.
            boxes (list): Person boxes [{'box': [x, y, w, h], 'conf': float}]
            is_full_body_face (bool): True if full body + clean face detected.
            face_boxes (list): Face boxes [{'box': [x, y, w, h], 'conf': float}]
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
        
        # YOLOv5 class 0: person
        obj_conf = out[0, :, 4]
        person_cls_conf = out[0, :, 5]
        scores = obj_conf * person_cls_conf
        
        mask = scores >= conf_threshold
        if not np.any(mask):
            max_c = float(np.max(scores)) if len(scores) > 0 else 0.0
            return False, max_c, [], False, []
            
        candidate_indices = np.where(mask)[0]
        boxes_list = []
        confidences_list = []
        
        for idx in candidate_indices:
            cx, cy, bw, bh = out[0, idx, 0:4]
            x1 = int(round((cx - bw / 2 - dw) / scale))
            y1 = int(round((cy - bh / 2 - dh) / scale))
            bw_orig = int(round(bw / scale))
            bh_orig = int(round(bh / scale))
            
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
        has_person = len(final_boxes) > 0

        # Check for Full Body + Clean Face
        is_full_body_face = False
        detected_face_boxes = []

        if has_person and self.face_detector is not None:
            for item in final_boxes:
                bx, by, bw, bh = item["box"]
                aspect = bh / bw if bw > 0 else 0
                rel_h = bh / h
                
                # Full figure: vertical tall aspect ratio >= 1.5, height >= 18% of frame
                is_full_figure = (aspect >= 1.5) and (rel_h >= 0.18)
                
                if is_full_figure:
                    # Crop upper 45% (Head & Face area)
                    y1 = max(0, by - 10)
                    y2 = min(h, by + int(bh * 0.45))
                    x1 = max(0, bx - 10)
                    x2 = min(w, bx + bw + 10)
                    
                    if (y2 - y1) > 20 and (x2 - x1) > 20:
                        roi = frame[y1:y2, x1:x2]
                        rh, rw = roi.shape[:2]
                        
                        # Downscale ROI for sub-10ms face detection
                        roi_scale = min(1.0, 320.0 / rw) if rw > 0 else 1.0
                        roi_resized = cv2.resize(roi, (int(rw * roi_scale), int(rh * roi_scale)))
                        
                        self.face_detector.setInputSize((roi_resized.shape[1], roi_resized.shape[0]))
                        _, faces = self.face_detector.detect(roi_resized)
                        
                        if faces is not None and len(faces) > 0:
                            for face in faces:
                                f_score = float(face[-1])
                                if f_score >= 0.50:
                                    is_full_body_face = True
                                    # Convert face coordinates back to original frame
                                    fx = int(round(face[0] / roi_scale)) + x1
                                    fy = int(round(face[1] / roi_scale)) + y1
                                    fw = int(round(face[2] / roi_scale))
                                    fh = int(round(face[3] / roi_scale))
                                    detected_face_boxes.append({
                                        "box": [fx, fy, fw, fh],
                                        "conf": f_score
                                    })
                                    break
                if is_full_body_face:
                    break

        return has_person, max_c, final_boxes, is_full_body_face, detected_face_boxes

    @staticmethod
    def draw_detections(frame: np.ndarray, boxes: list, face_boxes: list = None) -> np.ndarray:
        """Draws bounding boxes and labels for body and face."""
        vis_frame = frame.copy()
        
        # 1. Person body boxes (Green)
        for item in boxes:
            x, y, w, h = item["box"]
            conf = item["conf"]
            cv2.rectangle(vis_frame, (x, y), (x + w, y + h), (0, 220, 100), 2)
            
            label = f"Person {int(conf * 100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            cv2.rectangle(vis_frame, (x, max(0, y - th - 6)), (x + tw + 6, max(0, y)), (0, 220, 100), -1)
            cv2.putText(vis_frame, label, (x + 3, max(th, y - 4)), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
            
        # 2. Face boxes (Bright Gold/Cyan)
        if face_boxes:
            for f_item in face_boxes:
                fx, fy, fw, fh = f_item["box"]
                f_conf = f_item["conf"]
                cv2.rectangle(vis_frame, (fx, fy), (fx + fw, fy + fh), (245, 180, 0), 2)
                f_label = f"Face {int(f_conf * 100)}%"
                (ftw, fth), _ = cv2.getTextSize(f_label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(vis_frame, (fx, max(0, fy - fth - 6)), (fx + ftw + 6, max(0, fy)), (245, 180, 0), -1)
                cv2.putText(vis_frame, f_label, (fx + 3, max(fth, fy - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
                
        return vis_frame
