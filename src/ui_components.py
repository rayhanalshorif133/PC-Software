import os
import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk
from PIL import Image, ImageTk

from src.detector import PersonDetector
from src.extractor import FrameRecord


class FrameCard(ctk.CTkFrame):
    """
    Card component displaying an extracted frame thumbnail, metadata,
    and a checkbox for multi-select.
    """

    def __init__(
        self,
        master,
        record: FrameRecord,
        is_selected: bool,
        on_toggle_select: Callable[[FrameRecord, bool], None],
        on_preview: Callable[[FrameRecord], None],
        card_width: int = 190,
        card_height: int = 210,
        **kwargs,
    ):
        super().__init__(
            master,
            width=card_width,
            height=card_height,
            corner_radius=8,
            border_width=2 if is_selected else 1,
            border_color="#3b8ed0" if is_selected else "#2b2b2b",
            fg_color="#1c1d21" if not is_selected else "#1e293b",
            **kwargs,
        )
        self.record = record
        self.is_selected = is_selected
        self.on_toggle_select = on_toggle_select
        self.on_preview = on_preview
        self.card_width = card_width
        self.card_height = card_height

        self.grid_propagate(False)
        self.pack_propagate(False)

        # Image thumbnail
        self._thumb_img = None
        self._load_thumbnail()

        # Top Info Bar: Checkbox + Status badge
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=6, pady=(6, 2))

        self.check_var = ctk.BooleanVar(value=is_selected)
        self.checkbox = ctk.CTkCheckBox(
            top_bar,
            text="",
            variable=self.check_var,
            width=20,
            checkbox_width=18,
            checkbox_height=18,
            command=self._on_check_changed,
        )
        self.checkbox.pack(side="left")

        # Badge
        if getattr(record, "is_full_body_face", False):
            badge_text = "🌟 Full Body & Face"
            badge_color = "#7c3aed"  # Vibrant Purple
            text_color = "#ffffff"
        elif record.has_person:
            badge_text = f"👤 {int(record.confidence * 100)}%"
            badge_color = "#10b981"  # Emerald green
            text_color = "#ffffff"
        else:
            badge_text = "⚪ Hidden"
            badge_color = "#475569"  # Slate gray
            text_color = "#cbd5e1"

        badge = ctk.CTkLabel(
            top_bar,
            text=badge_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=text_color,
            fg_color=badge_color,
            corner_radius=4,
            padx=6,
            pady=1,
        )
        badge.pack(side="right")

        # Thumbnail button/label
        self.thumb_label = ctk.CTkLabel(
            self,
            text="" if self._thumb_img else "Loading...",
            image=self._thumb_img,
            cursor="hand2",
            corner_radius=6,
        )
        self.thumb_label.pack(fill="x", expand=True, padx=6, pady=2)
        self.thumb_label.bind("<Button-1>", lambda e: self.on_preview(self.record))
        self.thumb_label.bind("<Double-Button-1>", lambda e: self.on_preview(self.record))

        # Bottom Bar: Frame # and Timestamp
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=6, pady=(2, 6))

        frame_lbl = ctk.CTkLabel(
            bottom_bar,
            text=f"#{record.index + 1}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
        )
        frame_lbl.pack(side="left")

        time_lbl = ctk.CTkLabel(
            bottom_bar,
            text=record.timestamp_str,
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        time_lbl.pack(side="right")

        # Allow clicking frame background to toggle selection
        self.bind("<Button-1>", self._on_card_clicked)

    def _load_thumbnail(self):
        try:
            if os.path.exists(self.record.thumb_path):
                pil_img = Image.open(self.record.thumb_path)
                # Fit inside card width
                target_w = self.card_width - 16
                aspect = pil_img.height / pil_img.width if pil_img.width > 0 else 0.56
                target_h = int(target_w * aspect)
                target_h = min(max(target_h, 80), 120)
                
                self._thumb_img = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(target_w, target_h),
                )
        except Exception:
            self._thumb_img = None

    def _on_check_changed(self, is_shift: bool = False):
        self.is_selected = self.check_var.get()
        self._update_appearance()
        self.on_toggle_select(self.record, self.is_selected, is_shift)

    def _on_card_clicked(self, event):
        is_shift = bool(event.state & 1) if hasattr(event, "state") else False
        new_val = not self.check_var.get()
        self.check_var.set(new_val)
        self._on_check_changed(is_shift=is_shift)

    def set_selected(self, val: bool):
        self.check_var.set(val)
        self.is_selected = val
        self._update_appearance()

    def _update_appearance(self):
        if self.is_selected:
            self.configure(border_color="#38bdf8", border_width=2, fg_color="#1e293b")
        else:
            self.configure(border_color="#2b2b2b", border_width=1, fg_color="#1c1d21")


class ImagePreviewDialog(ctk.CTkToplevel):
    """
    High-resolution preview dialog with zoom, bounding box toggling,
    and previous/next navigation.
    """

    def __init__(
        self,
        parent,
        records: list,
        current_idx: int,
        is_selected_func: Callable[[FrameRecord], bool],
        on_toggle_select: Callable[[FrameRecord, bool], None],
        on_download_single: Callable[[FrameRecord], None],
    ):
        super().__init__(parent)
        self.title("Frame Preview - High Resolution")
        self.geometry("960x700")
        self.minsize(720, 520)

        self.records = records
        self.current_idx = current_idx
        self.is_selected_func = is_selected_func
        self.on_toggle_select = on_toggle_select
        self.on_download_single = on_download_single

        self.show_boxes = ctk.BooleanVar(value=True)

        # Make modal-like
        self.grab_set()
        self.focus_set()

        # Keyboard shortcuts
        self.bind("<Left>", lambda e: self._prev_frame())
        self.bind("<Right>", lambda e: self._next_frame())
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        self._display_frame()

    def _build_ui(self):
        # Top bar
        top_bar = ctk.CTkFrame(self, fg_color="#18181b", height=50)
        top_bar.pack(fill="x", side="top")

        self.title_label = ctk.CTkLabel(
            top_bar,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f8fafc",
        )
        self.title_label.pack(side="left", padx=16, pady=10)

        # Toggle boxes switch
        self.box_switch = ctk.CTkSwitch(
            top_bar,
            text="Show Person Box",
            variable=self.show_boxes,
            command=self._display_frame,
            font=ctk.CTkFont(size=12),
        )
        self.box_switch.pack(side="right", padx=16)

        # Bottom Bar: Navigation & Action
        bottom_bar = ctk.CTkFrame(self, fg_color="#18181b", height=56)
        bottom_bar.pack(fill="x", side="bottom")

        # Prev button
        self.prev_btn = ctk.CTkButton(
            bottom_bar,
            text="◀ Previous Frame",
            width=130,
            command=self._prev_frame,
            fg_color="#334155",
            hover_color="#475569",
        )
        self.prev_btn.pack(side="left", padx=12, pady=12)

        # Select Checkbox
        self.select_var = ctk.BooleanVar()
        self.select_chk = ctk.CTkCheckBox(
            bottom_bar,
            text="Select this frame for download",
            variable=self.select_var,
            command=self._on_select_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.select_chk.pack(side="left", padx=20)

        # Download button
        self.download_btn = ctk.CTkButton(
            bottom_bar,
            text="💾 Download This Image",
            width=160,
            fg_color="#059669",
            hover_color="#10b981",
            command=self._download_current,
        )
        self.download_btn.pack(side="right", padx=12, pady=12)

        # Next button
        self.next_btn = ctk.CTkButton(
            bottom_bar,
            text="Next Frame ▶",
            width=130,
            command=self._next_frame,
            fg_color="#334155",
            hover_color="#475569",
        )
        self.next_btn.pack(side="right", padx=12, pady=12)

        # Center Canvas / Image Container
        self.img_container = ctk.CTkFrame(self, fg_color="#09090b")
        self.img_container.pack(fill="both", expand=True, padx=8, pady=8)

        self.img_label = ctk.CTkLabel(self.img_container, text="")
        self.img_label.pack(fill="both", expand=True)

    def _display_frame(self):
        if not (0 <= self.current_idx < len(self.records)):
            return

        rec: FrameRecord = self.records[self.current_idx]
        
        # Update title & checkbox
        if getattr(rec, "is_full_body_face", False):
            badge = "[🌟 Full Body & Clean Face]"
        elif rec.has_person:
            badge = f"[👤 Person {int(rec.confidence * 100)}%]"
        else:
            badge = "[⚪ No Person / Hidden]"
        self.title_label.configure(
            text=f"Frame #{rec.index + 1} • Time: {rec.timestamp_str} • {badge} ({self.current_idx + 1} of {len(self.records)})"
        )
        
        self.select_var.set(self.is_selected_func(rec))

        # Load image (with or without boxes)
        if os.path.exists(rec.full_path):
            import cv2
            img_bgr = cv2.imread(rec.full_path)
            if self.show_boxes.get() and rec.boxes:
                img_bgr = PersonDetector.draw_detections(
                    img_bgr, rec.boxes, getattr(rec, "face_boxes", [])
                )
                
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)

            # Fit to container
            max_w = max(400, self.winfo_width() - 40)
            max_h = max(300, self.winfo_height() - 150)
            
            # Preserve aspect ratio
            pil_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(pil_img.width, pil_img.height),
            )
            self.img_label.configure(image=ctk_img)
            self.img_label.image = ctk_img

        self.prev_btn.configure(state="normal" if self.current_idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_idx < len(self.records) - 1 else "disabled")

    def _prev_frame(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._display_frame()

    def _next_frame(self):
        if self.current_idx < len(self.records) - 1:
            self.current_idx += 1
            self._display_frame()

    def _on_select_toggle(self):
        if 0 <= self.current_idx < len(self.records):
            rec = self.records[self.current_idx]
            self.on_toggle_select(rec, self.select_var.get())

    def _download_current(self):
        if 0 <= self.current_idx < len(self.records):
            rec = self.records[self.current_idx]
            self.on_download_single(rec)
