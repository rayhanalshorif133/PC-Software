import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional, Set
import customtkinter as ctk
from PIL import Image

from src.detector import PersonDetector, get_resource_path
from src.extractor import FrameRecord, VideoAnalysisWorker, VideoMetadata
from src.ui_components import FrameCard, ImagePreviewDialog


class VideoFrameProApp(ctk.CTk):
    """
    Main Application Window for Video Frame Extraction & Person Detection.
    """

    def __init__(self):
        super().__init__()

        # Appearance & Themes
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Video to Frames & Person Detection Pro")
        self.geometry("1280x820")
        self.minsize(1080, 680)

        # Center window on screen
        self._center_window()

        # Set Window Icon if available
        self._set_app_icon()

        # State Variables
        self.video_info: Optional[dict] = None
        self.detector: Optional[PersonDetector] = None
        self.worker: Optional[VideoAnalysisWorker] = None
        
        # Temp session folder
        self.temp_session_dir = tempfile.mkdtemp(prefix="video_frame_pro_")
        
        # Frame records
        self.all_records: List[FrameRecord] = []
        self.full_body_face_records: List[FrameRecord] = []
        self.person_records: List[FrameRecord] = []
        self.no_person_records: List[FrameRecord] = []
        
        # Selection state (stores record.index)
        self.selected_indices: Set[int] = set()
        self.last_clicked_record: Optional[FrameRecord] = None
        
        # Active tab: "full_body_face", "person", "no_person", "all"
        self.current_tab = "full_body_face"
        
        # Pagination
        self.current_page = 1
        self.items_per_page = 24
        
        # Download directory (Default: User's Downloads folder)
        default_downloads = str(Path.home() / "Downloads" / "Video_Frames_Export")
        self.download_dir = default_downloads

        # Initialize detector in background
        self._init_detector()

        # Build UI
        self._build_layout()

        # Handle window close cleanup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        self.update_idletasks()
        w = 1280
        h = 820
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _set_app_icon(self):
        try:
            icon_p = get_resource_path(os.path.join("assets", "app_icon.ico"))
            if os.path.exists(icon_p):
                self.iconbitmap(icon_p)
        except Exception:
            pass

    def _init_detector(self):
        try:
            self.detector = PersonDetector()
        except Exception as e:
            messagebox.showerror(
                "Model Load Error",
                f"Could not load Person Detection Model:\n{e}\n\nPlease verify models/yolov5n.onnx exists.",
            )

    def _build_layout(self):
        # Main Grid Layout: Left sidebar (330px), Right content (flexible)
        self.grid_columnconfigure(0, weight=0, minsize=330)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_content()

    # ==========================================
    # LEFT SIDEBAR
    # ==========================================
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=330, corner_radius=0, fg_color="#18181b")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # App Header
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))

        title = ctk.CTkLabel(
            header,
            text="🎥 VideoFrame Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Full FPS Extractor & Human Detection",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        subtitle.pack(anchor="w")

        # Scrollable panel for settings
        scroll_panel = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        scroll_panel.pack(fill="both", expand=True, padx=12, pady=4)

        # Section 1: Video File Picker
        vid_sec = ctk.CTkFrame(scroll_panel, fg_color="#27272a", corner_radius=8)
        vid_sec.pack(fill="x", pady=6)

        v_lbl = ctk.CTkLabel(
            vid_sec,
            text="1. Video File (ভিডিও নির্বাচন)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc",
        )
        v_lbl.pack(anchor="w", padx=12, pady=(10, 6))

        self.btn_select_video = ctk.CTkButton(
            vid_sec,
            text="📂 Choose Video File...",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=34,
            command=self._select_video_file,
        )
        self.btn_select_video.pack(fill="x", padx=12, pady=(0, 8))

        # Metadata display
        self.meta_frame = ctk.CTkFrame(vid_sec, fg_color="#18181b", corner_radius=6)
        self.meta_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_file_name = ctk.CTkLabel(
            self.meta_frame,
            text="No video selected",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#e2e8f0",
            wraplength=270,
            justify="left",
        )
        self.lbl_file_name.pack(anchor="w", padx=8, pady=(6, 2))

        self.lbl_file_details = ctk.CTkLabel(
            self.meta_frame,
            text="Select an MP4, MKV, AVI or MOV video",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
            justify="left",
        )
        self.lbl_file_details.pack(anchor="w", padx=8, pady=(0, 6))

        # Section 2: Analysis Options
        opts_sec = ctk.CTkFrame(scroll_panel, fg_color="#27272a", corner_radius=8)
        opts_sec.pack(fill="x", pady=6)

        o_lbl = ctk.CTkLabel(
            opts_sec,
            text="2. Analysis Settings (সেটিংস)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc",
        )
        o_lbl.pack(anchor="w", padx=12, pady=(10, 6))

        # Frame extraction mode (Default: Full FPS - Every Frame!)
        mode_lbl = ctk.CTkLabel(
            opts_sec,
            text="Frame Rate Mode:",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
        )
        mode_lbl.pack(anchor="w", padx=12, pady=(2, 2))

        self.combo_step = ctk.CTkComboBox(
            opts_sec,
            values=[
                "Full FPS (Every Single Frame)",
                "Half FPS (Every 2nd Frame)",
                "Every 5th Frame",
                "1 Frame Per Second (Fast)",
            ],
            height=30,
        )
        self.combo_step.set("Full FPS (Every Single Frame)")
        self.combo_step.pack(fill="x", padx=12, pady=(0, 8))

        # Person Sensitivity Slider
        conf_hdr = ctk.CTkFrame(opts_sec, fg_color="transparent")
        conf_hdr.pack(fill="x", padx=12, pady=(4, 2))

        conf_lbl = ctk.CTkLabel(
            conf_hdr,
            text="Person Detection Sensitivity:",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
        )
        conf_lbl.pack(side="left")

        self.lbl_conf_val = ctk.CTkLabel(
            conf_hdr,
            text="35%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
        )
        self.lbl_conf_val.pack(side="right")

        self.slider_conf = ctk.CTkSlider(
            opts_sec,
            from_=0.15,
            to=0.85,
            number_of_steps=14,
            command=self._on_slider_change,
        )
        self.slider_conf.set(0.35)
        self.slider_conf.pack(fill="x", padx=12, pady=(0, 10))

        # Section 3: Action Buttons (Start / Stop)
        act_sec = ctk.CTkFrame(scroll_panel, fg_color="#27272a", corner_radius=8)
        act_sec.pack(fill="x", pady=6)

        self.btn_start = ctk.CTkButton(
            act_sec,
            text="🚀 Start Full Video Analysis",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#10b981",
            height=40,
            command=self._start_analysis,
        )
        self.btn_start.pack(fill="x", padx=12, pady=(12, 6))

        self.btn_stop = ctk.CTkButton(
            act_sec,
            text="⏹️ Stop / Cancel",
            font=ctk.CTkFont(size=12),
            fg_color="#b91c1c",
            hover_color="#dc2626",
            height=32,
            state="disabled",
            command=self._stop_analysis,
        )
        self.btn_stop.pack(fill="x", padx=12, pady=(0, 12))

        # Section 4: Save & Download Location
        save_sec = ctk.CTkFrame(scroll_panel, fg_color="#27272a", corner_radius=8)
        save_sec.pack(fill="x", pady=6)

        s_lbl = ctk.CTkLabel(
            save_sec,
            text="3. Download Folder (সেভ লোকেশন)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc",
        )
        s_lbl.pack(anchor="w", padx=12, pady=(10, 4))

        self.lbl_download_path = ctk.CTkLabel(
            save_sec,
            text=self.download_dir,
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
            wraplength=270,
            justify="left",
        )
        self.lbl_download_path.pack(anchor="w", padx=12, pady=(0, 6))

        path_btn_frame = ctk.CTkFrame(save_sec, fg_color="transparent")
        path_btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.btn_change_path = ctk.CTkButton(
            path_btn_frame,
            text="📁 Change Path",
            width=120,
            height=28,
            command=self._change_download_dir,
            fg_color="#3f3f46",
            hover_color="#52525b",
        )
        self.btn_change_path.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            path_btn_frame,
            text="📂 Open Folder",
            width=120,
            height=28,
            command=self._open_download_dir,
            fg_color="#3f3f46",
            hover_color="#52525b",
        )
        self.btn_open_folder.pack(side="right")

        # Format selector
        fmt_frame = ctk.CTkFrame(save_sec, fg_color="transparent")
        fmt_frame.pack(fill="x", padx=12, pady=(0, 10))

        fmt_lbl = ctk.CTkLabel(
            fmt_frame,
            text="Format:",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
        )
        fmt_lbl.pack(side="left")

        self.combo_export_fmt = ctk.CTkComboBox(
            fmt_frame,
            values=["JPG (High Quality)", "PNG (Lossless)"],
            width=160,
            height=26,
            font=ctk.CTkFont(size=11),
        )
        self.combo_export_fmt.set("JPG (High Quality)")
        self.combo_export_fmt.pack(side="right")

        # Bottom download action buttons
        dload_sec = ctk.CTkFrame(sidebar, fg_color="#18181b")
        dload_sec.pack(fill="x", padx=16, pady=12)

        self.btn_download_selected = ctk.CTkButton(
            dload_sec,
            text="⬇️ Download Selected (0)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#3b82f6",
            height=38,
            command=self._download_selected_frames,
        )
        self.btn_download_selected.pack(fill="x", pady=(0, 6))

        self.btn_download_all_tab = ctk.CTkButton(
            dload_sec,
            text="⬇️ Download All in Current Tab",
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            command=self._download_all_current_tab,
        )
        self.btn_download_all_tab.pack(fill="x", pady=(0, 6))

        self.btn_download_zip = ctk.CTkButton(
            dload_sec,
            text="📦 Download as ZIP Archive",
            font=ctk.CTkFont(size=11),
            fg_color="#0f766e",
            hover_color="#14b8a6",
            height=30,
            command=self._download_as_zip,
        )
        self.btn_download_zip.pack(fill="x")

    def _on_slider_change(self, value):
        pct = int(value * 100)
        self.lbl_conf_val.configure(text=f"{pct}%")

    # ==========================================
    # RIGHT / MAIN CONTENT AREA
    # ==========================================
    def _build_main_content(self):
        main_frame = ctk.CTkFrame(self, fg_color="#09090b", corner_radius=0)
        main_frame.grid(row=0, column=1, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # 1. Top Status & Progress Bar Header
        self._build_progress_header(main_frame)

        # 2. Filter Tabs & Selection Toolbar
        self._build_filter_and_tools(main_frame)

        # 3. Gallery Grid (Scrollable)
        self.gallery_scroll = ctk.CTkScrollableFrame(
            main_frame, fg_color="#09090b", corner_radius=0
        )
        self.gallery_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 8))
        self.gallery_scroll.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # 4. Pagination Footer
        self._build_pagination_footer(main_frame)

        # Initial Empty State
        self._render_empty_state("No frames extracted yet. Select a video and click 'Start Full Video Analysis'.")

    def _build_progress_header(self, parent):
        self.progress_container = ctk.CTkFrame(parent, fg_color="#18181b", corner_radius=8, height=85)
        self.progress_container.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        self.progress_container.grid_propagate(False)

        # Top line in progress container: status text + live speed/eta
        top_info = ctk.CTkFrame(self.progress_container, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_status = ctk.CTkLabel(
            top_info,
            text="Ready. Select a video to begin.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0",
        )
        self.lbl_status.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(
            top_info,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        self.lbl_stats.pack(side="right")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.progress_container, height=10)
        self.progress_bar.pack(fill="x", padx=16, pady=4)
        self.progress_bar.set(0.0)

        # Counter Badges underneath progress bar
        counter_line = ctk.CTkFrame(self.progress_container, fg_color="transparent")
        counter_line.pack(fill="x", padx=16, pady=(2, 8))

        self.lbl_count_fbf = ctk.CTkLabel(
            counter_line,
            text="🌟 Full Body & Face: 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#c084fc",
        )
        self.lbl_count_fbf.pack(side="left", padx=(0, 14))

        self.lbl_count_person = ctk.CTkLabel(
            counter_line,
            text="👤 All Person: 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10b981",
        )
        self.lbl_count_person.pack(side="left", padx=(0, 14))

        self.lbl_count_no_person = ctk.CTkLabel(
            counter_line,
            text="⚪ Hidden: 0",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.lbl_count_no_person.pack(side="left", padx=(0, 14))

        self.lbl_count_all = ctk.CTkLabel(
            counter_line,
            text="🎞️ Total: 0",
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8",
        )
        self.lbl_count_all.pack(side="left")

    def _build_filter_and_tools(self, parent):
        tool_frame = ctk.CTkFrame(parent, fg_color="#18181b", corner_radius=8)
        tool_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Row 1: Section / Category Segmented Buttons (Tabs)
        tab_row = ctk.CTkFrame(tool_frame, fg_color="transparent")
        tab_row.pack(fill="x", padx=12, pady=(10, 6))

        self.tab_selector = ctk.CTkSegmentedButton(
            tab_row,
            values=[
                "🌟 Full Body & Face (0)",
                "👤 All Person (0)",
                "⚪ Hidden / No Person (0)",
                "🎞️ All Frames (0)",
            ],
            command=self._on_tab_changed,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            selected_color="#7c3aed",
            selected_hover_color="#6d28d9",
        )
        self.tab_selector.set("🌟 Full Body & Face (0)")
        self.tab_selector.pack(side="left", fill="x", expand=True)

        # Row 2: Selection Tools Toolbar
        sel_row = ctk.CTkFrame(tool_frame, fg_color="transparent")
        sel_row.pack(fill="x", padx=12, pady=(0, 10))

        btn_sel_all = ctk.CTkButton(
            sel_row,
            text="Select All Page",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._select_all_page,
        )
        btn_sel_all.pack(side="left", padx=(0, 6))

        btn_sel_tab = ctk.CTkButton(
            sel_row,
            text="Select All Tab",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._select_all_tab,
        )
        btn_sel_tab.pack(side="left", padx=(0, 6))

        btn_desel = ctk.CTkButton(
            sel_row,
            text="Deselect All",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._deselect_all,
        )
        btn_desel.pack(side="left", padx=(0, 6))

        btn_invert = ctk.CTkButton(
            sel_row,
            text="Invert",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._invert_selection,
        )
        btn_invert.pack(side="left", padx=(0, 12))

        # Selected counter
        self.lbl_selected_count = ctk.CTkLabel(
            sel_row,
            text="Selected: 0 frames",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
        )
        self.lbl_selected_count.pack(side="left")

        # Items per page
        ipp_lbl = ctk.CTkLabel(
            sel_row,
            text="Per page:",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        ipp_lbl.pack(side="right", padx=(6, 4))

        self.combo_per_page = ctk.CTkComboBox(
            sel_row,
            values=["24", "36", "48", "72"],
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._on_per_page_change,
        )
        self.combo_per_page.set("24")
        self.combo_per_page.pack(side="right")

    def _build_pagination_footer(self, parent):
        footer = ctk.CTkFrame(parent, fg_color="#18181b", corner_radius=8, height=44)
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        footer.grid_propagate(False)

        foot_content = ctk.CTkFrame(footer, fg_color="transparent")
        foot_content.pack(fill="both", expand=True, padx=12)

        self.btn_first = ctk.CTkButton(
            foot_content,
            text="⏮ First",
            width=75,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._first_page,
        )
        self.btn_first.pack(side="left", padx=(0, 4), pady=8)

        self.btn_prev = ctk.CTkButton(
            foot_content,
            text="◀ Prev",
            width=75,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._prev_page,
        )
        self.btn_prev.pack(side="left", padx=(0, 12), pady=8)

        self.lbl_page_info = ctk.CTkLabel(
            foot_content,
            text="Page 1 of 1 (0 items)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1",
        )
        self.lbl_page_info.pack(side="left")

        self.btn_last = ctk.CTkButton(
            foot_content,
            text="Last ⏭",
            width=75,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._last_page,
        )
        self.btn_last.pack(side="right", padx=(4, 0), pady=8)

        self.btn_next = ctk.CTkButton(
            foot_content,
            text="Next ▶",
            width=75,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._next_page,
        )
        self.btn_next.pack(side="right", padx=(12, 0), pady=8)

    # ==========================================
    # VIDEO SELECTION & ANALYSIS
    # ==========================================
    def _select_video_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                (
                    "Video Files",
                    "*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm;*.m4v",
                ),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            self.video_info = VideoMetadata.get_info(file_path)
            self.lbl_file_name.configure(text=self.video_info["filename"])
            self.lbl_file_details.configure(
                text=(
                    f"{self.video_info['resolution']} • {self.video_info['fps']} FPS\n"
                    f"{self.video_info['total_frames']} frames • {self.video_info['duration_str']} • "
                    f"{self.video_info['size_mb']:.1f} MB"
                )
            )
            self.lbl_status.configure(
                text=f"Video Loaded: {self.video_info['filename']} ({self.video_info['total_frames']} frames)"
            )
            
            # Auto-set export directory name based on video name
            stem = Path(file_path).stem
            self.download_dir = str(Path.home() / "Downloads" / f"Frames_{stem}")
            self.lbl_download_path.configure(text=self.download_dir)

        except Exception as e:
            messagebox.showerror("Error", f"Could not read video file: {e}")

    def _start_analysis(self):
        if not self.video_info:
            messagebox.showwarning("No Video", "Please select a video file first!")
            return

        if not self.detector:
            messagebox.showerror("Error", "Person detector is not ready.")
            return

        # Determine step from combo
        mode_val = self.combo_step.get()
        if "Full FPS" in mode_val:
            step = 1
        elif "Half FPS" in mode_val:
            step = 2
        elif "Every 5th" in mode_val:
            step = 5
        elif "1 Frame Per Second" in mode_val:
            step = max(1, int(round(self.video_info["fps"])))
        else:
            step = 1

        conf_thresh = float(self.slider_conf.get())

        # Reset state for new run
        self.all_records.clear()
        self.full_body_face_records.clear()
        self.person_records.clear()
        self.no_person_records.clear()
        self.selected_indices.clear()
        self._update_selection_count_ui()
        self._clear_gallery()

        # Update UI state
        self.btn_start.configure(state="disabled")
        self.btn_select_video.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress_bar.set(0.0)
        self.lbl_status.configure(text="Extracting frames and detecting humans...")

        # Start background worker
        self.worker = VideoAnalysisWorker(
            video_path=self.video_info["path"],
            detector=self.detector,
            output_dir=self.temp_session_dir,
            step=step,
            conf_threshold=conf_thresh,
            on_progress=self._on_worker_progress,
            on_complete=self._on_worker_complete,
            on_error=self._on_worker_error,
        )
        self.worker.start()

    def _stop_analysis(self):
        if self.worker and self.worker.is_alive():
            self.lbl_status.configure(text="Stopping analysis...")
            self.worker.cancel()

    def _on_worker_progress(
        self,
        current: int,
        total: int,
        full_body_face_count: int,
        person_count: int,
        no_person_count: int,
        fps_calc: float,
        eta_str: str,
        record: Optional[FrameRecord],
    ):
        # Schedule on UI thread
        self.after(
            0,
            lambda: self._ui_update_progress(
                current, total, full_body_face_count, person_count, no_person_count, fps_calc, eta_str, record
            ),
        )

    def _ui_update_progress(
        self,
        current: int,
        total: int,
        full_body_face_count: int,
        person_count: int,
        no_person_count: int,
        fps_calc: float,
        eta_str: str,
        record: Optional[FrameRecord],
    ):
        pct = current / total if total > 0 else 0.0
        self.progress_bar.set(pct)
        self.lbl_status.configure(
            text=f"Analyzing Frame {current}/{total} ({int(pct * 100)}%)"
        )
        self.lbl_stats.configure(
            text=f"Speed: {fps_calc:.1f} FPS  •  ETA: {eta_str}"
        )

        self.lbl_count_fbf.configure(text=f"🌟 Full Body & Face: {full_body_face_count}")
        self.lbl_count_person.configure(text=f"👤 All Person: {person_count}")
        self.lbl_count_no_person.configure(text=f"⚪ Hidden: {no_person_count}")
        self.lbl_count_all.configure(text=f"🎞️ Total: {current}")

        if record:
            self.all_records.append(record)
            if record.has_person:
                self.person_records.append(record)
                if record.is_full_body_face:
                    self.full_body_face_records.append(record)
            else:
                self.no_person_records.append(record)

    def _on_worker_complete(self, records: List[FrameRecord]):
        self.after(0, lambda: self._ui_handle_complete(records))

    def _ui_handle_complete(self, records: List[FrameRecord]):
        self.btn_start.configure(state="normal")
        self.btn_select_video.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.progress_bar.set(1.0)

        fbf_len = len(self.full_body_face_records)
        p_len = len(self.person_records)
        self.lbl_status.configure(
            text=f"Analysis Complete! Found {fbf_len} Full Body & Face frames ({p_len} total person frames)."
        )
        self.lbl_stats.configure(text="Finished")

        # Update tab counts
        self._update_tab_labels()

        # Render first page of active tab
        self.current_page = 1
        self._render_current_page()

    def _on_worker_error(self, error: Exception):
        self.after(0, lambda: self._ui_handle_error(error))

    def _ui_handle_error(self, error: Exception):
        self.btn_start.configure(state="normal")
        self.btn_select_video.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        messagebox.showerror("Analysis Error", f"An error occurred during video analysis:\n{error}")

    # ==========================================
    # TABS & GALLERY RENDERING
    # ==========================================
    def _update_tab_labels(self):
        fbf_len = len(self.full_body_face_records)
        p_len = len(self.person_records)
        np_len = len(self.no_person_records)
        all_len = len(self.all_records)

        vals = [
            f"🌟 Full Body & Face ({fbf_len})",
            f"👤 All Person ({p_len})",
            f"⚪ Hidden / No Person ({np_len})",
            f"🎞️ All Frames ({all_len})",
        ]
        self.tab_selector.configure(values=vals)

        # Retain selection
        if self.current_tab == "full_body_face":
            self.tab_selector.set(vals[0])
        elif self.current_tab == "person":
            self.tab_selector.set(vals[1])
        elif self.current_tab == "no_person":
            self.tab_selector.set(vals[2])
        else:
            self.tab_selector.set(vals[3])

    def _on_tab_changed(self, value: str):
        if "Full Body" in value:
            self.current_tab = "full_body_face"
        elif "All Person" in value:
            self.current_tab = "person"
        elif "Hidden" in value:
            self.current_tab = "no_person"
        else:
            self.current_tab = "all"

        self.current_page = 1
        self._render_current_page()

    def _get_active_records(self) -> List[FrameRecord]:
        if self.current_tab == "full_body_face":
            return self.full_body_face_records
        elif self.current_tab == "person":
            return self.person_records
        elif self.current_tab == "no_person":
            return self.no_person_records
        else:
            return self.all_records

    def _clear_gallery(self):
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()

    def _render_empty_state(self, message: str):
        self._clear_gallery()
        empty_lbl = ctk.CTkLabel(
            self.gallery_scroll,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color="#64748b",
            pady=80,
        )
        empty_lbl.pack(fill="both", expand=True)
        self.lbl_page_info.configure(text="Page 1 of 1 (0 items)")

    def _render_current_page(self):
        self._clear_gallery()
        records = self._get_active_records()
        total_items = len(records)

        if total_items == 0:
            if self.current_tab == "full_body_face":
                msg = "No frames with full body and clear face found."
            elif self.current_tab == "person":
                msg = "No frames with person detected yet."
            elif self.current_tab == "no_person":
                msg = "No hidden frames without person."
            else:
                msg = "No frames extracted yet."
            self._render_empty_state(msg)
            return

        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.current_page = min(max(1, self.current_page), total_pages)

        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        page_records = records[start_idx:end_idx]

        # Update pagination controls
        self.lbl_page_info.configure(
            text=f"Page {self.current_page} of {total_pages} ({total_items} items)"
        )
        self.btn_first.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < total_pages else "disabled")
        self.btn_last.configure(state="normal" if self.current_page < total_pages else "disabled")

        # Determine columns based on available width
        scroll_width = max(800, self.gallery_scroll.winfo_width())
        card_w = 190
        cols = max(3, min(6, scroll_width // (card_w + 14)))

        # Configure grid columns
        for c in range(cols):
            self.gallery_scroll.grid_columnconfigure(c, weight=1, uniform="card")

        # Populate cards
        for i, rec in enumerate(page_records):
            r = i // cols
            c = i % cols
            is_sel = rec.index in self.selected_indices

            card = FrameCard(
                self.gallery_scroll,
                record=rec,
                is_selected=is_sel,
                on_toggle_select=self._toggle_card_select,
                on_preview=self._open_preview,
                card_width=card_w,
                card_height=210,
            )
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

    def _toggle_card_select(self, record: FrameRecord, selected: bool, is_shift: bool = False):
        if is_shift and self.last_clicked_record is not None:
            records = self._get_active_records()
            try:
                i1 = records.index(self.last_clicked_record)
                i2 = records.index(record)
                start_i, end_i = min(i1, i2), max(i1, i2)
                for r in records[start_i:end_i + 1]:
                    self.selected_indices.add(r.index)
            except ValueError:
                self.selected_indices.add(record.index)
            self._render_current_page()
        else:
            if selected:
                self.selected_indices.add(record.index)
            else:
                self.selected_indices.discard(record.index)
        self.last_clicked_record = record
        self._update_selection_count_ui()

    def _update_selection_count_ui(self):
        count = len(self.selected_indices)
        self.lbl_selected_count.configure(text=f"Selected: {count} frames")
        self.btn_download_selected.configure(text=f"⬇️ Download Selected ({count})")

    # ==========================================
    # SELECTION ACTIONS
    # ==========================================
    def _select_all_page(self):
        records = self._get_active_records()
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(records))
        for rec in records[start_idx:end_idx]:
            self.selected_indices.add(rec.index)
        self._update_selection_count_ui()
        self._render_current_page()

    def _select_all_tab(self):
        records = self._get_active_records()
        for rec in records:
            self.selected_indices.add(rec.index)
        self._update_selection_count_ui()
        self._render_current_page()

    def _deselect_all(self):
        self.selected_indices.clear()
        self._update_selection_count_ui()
        self._render_current_page()

    def _invert_selection(self):
        records = self._get_active_records()
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(records))
        for rec in records[start_idx:end_idx]:
            if rec.index in self.selected_indices:
                self.selected_indices.remove(rec.index)
            else:
                self.selected_indices.add(rec.index)
        self._update_selection_count_ui()
        self._render_current_page()

    # ==========================================
    # PAGINATION NAVIGATION
    # ==========================================
    def _on_per_page_change(self, val: str):
        try:
            self.items_per_page = int(val)
            self.current_page = 1
            self._render_current_page()
        except ValueError:
            pass

    def _first_page(self):
        self.current_page = 1
        self._render_current_page()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        records = self._get_active_records()
        total_pages = max(1, (len(records) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._render_current_page()

    def _last_page(self):
        records = self._get_active_records()
        total_pages = max(1, (len(records) + self.items_per_page - 1) // self.items_per_page)
        self.current_page = total_pages
        self._render_current_page()

    # ==========================================
    # PREVIEW & SINGLE DOWNLOAD
    # ==========================================
    def _open_preview(self, record: FrameRecord):
        records = self._get_active_records()
        try:
            idx = records.index(record)
        except ValueError:
            idx = 0

        ImagePreviewDialog(
            parent=self,
            records=records,
            current_idx=idx,
            is_selected_func=lambda rec: rec.index in self.selected_indices,
            on_toggle_select=self._toggle_card_select,
            on_download_single=self._download_single_frame,
        )

    def _download_single_frame(self, record: FrameRecord):
        try:
            os.makedirs(self.download_dir, exist_ok=True)
            fmt = self.combo_export_fmt.get() if hasattr(self, "combo_export_fmt") else "JPG"
            ext = "png" if "PNG" in fmt else "jpg"
            status_tag = "person" if record.has_person else "frame"
            dest_name = f"frame_{record.index + 1:06d}_{status_tag}.{ext}"
            dest_path = os.path.join(self.download_dir, dest_name)

            if ext == "png":
                img = cv2.imread(record.full_path)
                cv2.imwrite(dest_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            else:
                shutil.copy2(record.full_path, dest_path)

            messagebox.showinfo("Saved", f"HD Image saved successfully to:\n{dest_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image:\n{e}")

    # ==========================================
    # BULK DOWNLOADS & FOLDER ACTIONS
    # ==========================================
    def _change_download_dir(self):
        chosen = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=str(Path.home() / "Downloads"),
        )
        if chosen:
            self.download_dir = chosen
            self.lbl_download_path.configure(text=chosen)

    def _open_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self.download_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", self.download_dir])
        else:
            subprocess.run(["xdg-open", self.download_dir])

    def _download_selected_frames(self):
        if not self.selected_indices:
            messagebox.showwarning("None Selected", "Please select one or more frames to download.")
            return

        records_map = {rec.index: rec for rec in self.all_records}
        to_download = [records_map[i] for i in self.selected_indices if i in records_map]

        self._execute_batch_download(to_download, f"Downloaded {len(to_download)} selected frames")

    def _download_all_current_tab(self):
        records = self._get_active_records()
        if not records:
            messagebox.showwarning("Empty Tab", "Current tab has no frames to download.")
            return

        confirm = messagebox.askyesno(
            "Download All",
            f"Are you sure you want to download all {len(records)} frames in this tab to:\n{self.download_dir}?",
        )
        if not confirm:
            return

        self._execute_batch_download(records, f"Downloaded all {len(records)} frames")

    def _execute_batch_download(self, records: List[FrameRecord], success_msg: str):
        try:
            os.makedirs(self.download_dir, exist_ok=True)
            fmt = self.combo_export_fmt.get() if hasattr(self, "combo_export_fmt") else "JPG"
            ext = "png" if "PNG" in fmt else "jpg"
            saved_count = 0
            for rec in records:
                if os.path.exists(rec.full_path):
                    tag = "person" if rec.has_person else "frame"
                    fname = f"frame_{rec.index + 1:06d}_{tag}.{ext}"
                    dest = os.path.join(self.download_dir, fname)
                    if ext == "png":
                        img = cv2.imread(rec.full_path)
                        cv2.imwrite(dest, img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                    else:
                        shutil.copy2(rec.full_path, dest)
                    saved_count += 1

            res = messagebox.askyesno(
                "Download Complete",
                f"{success_msg} ({saved_count} HD frames)!\n\nFolder: {self.download_dir}\n\nWould you like to open the folder now?",
            )
            if res:
                self._open_download_dir()

        except Exception as e:
            messagebox.showerror("Download Error", f"An error occurred while saving frames:\n{e}")

    def _download_as_zip(self):
        if self.selected_indices:
            records_map = {rec.index: rec for rec in self.all_records}
            to_download = [records_map[i] for i in self.selected_indices if i in records_map]
            label = f"{len(to_download)} selected frames"
        else:
            to_download = self._get_active_records()
            label = f"all {len(to_download)} frames in current tab"

        if not to_download:
            messagebox.showwarning("No Frames", "No frames available to export as ZIP.")
            return

        import zipfile
        try:
            os.makedirs(self.download_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            stem = self.video_info["filename"] if self.video_info else "frames"
            stem_clean = os.path.splitext(stem)[0]
            zip_name = f"{stem_clean}_frames_{timestamp}.zip"
            zip_path = os.path.join(self.download_dir, zip_name)

            fmt = self.combo_export_fmt.get() if hasattr(self, "combo_export_fmt") else "JPG"
            ext = "png" if "PNG" in fmt else "jpg"

            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for rec in to_download:
                    if os.path.exists(rec.full_path):
                        tag = "person" if rec.has_person else "frame"
                        arcname = f"frame_{rec.index + 1:06d}_{tag}.{ext}"
                        if ext == "png":
                            img = cv2.imread(rec.full_path)
                            _, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                            zf.writestr(arcname, buf.tobytes())
                        else:
                            zf.write(rec.full_path, arcname=arcname)

            res = messagebox.askyesno(
                "ZIP Export Complete",
                f"Successfully exported {label} into:\n\n{zip_path}\n\nWould you like to open the folder now?",
            )
            if res:
                self._open_download_dir()

        except Exception as e:
            messagebox.showerror("ZIP Export Error", f"Failed to export ZIP:\n{e}")

    # ==========================================
    # CLEANUP
    # ==========================================
    def _on_close(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()

        try:
            if os.path.exists(self.temp_session_dir):
                shutil.rmtree(self.temp_session_dir, ignore_errors=True)
        except Exception:
            pass

        self.destroy()
