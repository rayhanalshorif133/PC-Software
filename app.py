"""
app.py
Desktop GUI for Video to Image Converter using CustomTkinter.
Supports FPS extraction, interval extraction, real-time percentage progress,
live thumbnail preview, cancelation, and unicode Windows file paths.
"""

import os
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import numpy as np

from video_extractor import VideoInfo, VideoExtractor


class VideoToImageApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Video to Image Converter Pro | ভিডিও টু ইমেজ সফটওয়্যার")
        self.geometry("900x820")
        self.minsize(800, 700)
        
        # Color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State variables
        self.video_info: VideoInfo = None
        self.extractor: VideoExtractor = None
        self.is_converting = False
        self.target_frame_indices = []

        # UI Variables
        self.video_path_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="fps")  # 'fps', 'interval_seconds', 'interval_frames', 'all'
        self.param_value_var = tk.StringVar(value="1.0")
        self.format_var = tk.StringVar(value="JPG")
        self.quality_var = tk.IntVar(value=95)
        self.prefix_var = tk.StringVar(value="frame")
        self.naming_var = tk.StringVar(value="counter")  # 'counter' or 'timestamp'

        # Build UI
        self._build_ui()

        # Update initial calculations
        self._recalculate_estimate()

    def _build_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#e2e8f0", "#1e293b"))
        header.pack(fill="x", padx=0, pady=0)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="x", padx=25, pady=12)

        title_label = ctk.CTkLabel(
            header_content,
            text="🎬 Video to Image Converter Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        title_label.pack(side="left")

        sub_label = ctk.CTkLabel(
            header_content,
            text="ভিডিও থেকে ইমেজ এক্সট্র্যাক্টর • FPS ও পার্সেন্টেজ ট্র্যাকার",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8")
        )
        sub_label.pack(side="left", padx=15)

        self.theme_btn = ctk.CTkButton(
            header_content,
            text="🌓 Theme",
            width=70,
            height=28,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray25"),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right")

        # Scrollable container for main content
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. Video Selection Card
        self._build_video_card(self.scroll_container)

        # 2. Extraction & FPS Settings Card
        self._build_settings_card(self.scroll_container)

        # 3. Output Configuration Card
        self._build_output_card(self.scroll_container)

        # 4. Progress & Preview Card
        self._build_progress_card(self.scroll_container)

        # Bottom Control Bar
        self._build_control_bar()

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def _build_video_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=6, padx=5)

        card_title = ctk.CTkLabel(
            card,
            text="1. ভিডিও সিলেক্ট করুন (Select Video)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.pack(anchor="w", padx=15, pady=(10, 5))

        file_row = ctk.CTkFrame(card, fg_color="transparent")
        file_row.pack(fill="x", padx=15, pady=5)

        self.video_entry = ctk.CTkEntry(
            file_row,
            textvariable=self.video_path_var,
            placeholder_text="কোনো ভিডিও সিলেক্ট করা হয়নি (Select a video file)...",
            height=34
        )
        self.video_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(
            file_row,
            text="📁 ব্রাউজ ভিডিও...",
            width=130,
            height=34,
            command=self._on_browse_video
        )
        browse_btn.pack(side="right")

        # Video metadata info box
        self.info_frame = ctk.CTkFrame(card, fg_color=("#f1f5f9", "#0f172a"), corner_radius=8)
        self.info_frame.pack(fill="x", padx=15, pady=(5, 12))

        self.info_label = ctk.CTkLabel(
            self.info_frame,
            text="ℹ️ ভিডিও সিলেক্ট করলে তার ডিউরেশন, FPS, রেজোলিউশন ও ফ্রেম সংখ্যা এখানে প্রদর্শিত হবে।",
            font=ctk.CTkFont(size=12),
            text_color=("#475569", "#94a3b8"),
            justify="left"
        )
        self.info_label.pack(padx=12, pady=8, anchor="w")

    def _build_settings_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=6, padx=5)

        card_title = ctk.CTkLabel(
            card,
            text="2. FPS ও কনভার্সন অপশন (FPS & Extraction Settings)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.pack(anchor="w", padx=15, pady=(10, 5))

        # Mode Selection
        mode_label = ctk.CTkLabel(
            card,
            text="কিসের ভিত্তিতে ছবি এক্সট্র্যাক্ট করবেন তা নির্বাচন করুন:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        mode_label.pack(anchor="w", padx=15, pady=(2, 4))

        self.mode_segmented = ctk.CTkSegmentedButton(
            card,
            values=[
                "🎯 টার্গেট FPS",
                "⏱️ সেকেন্ড পর পর",
                "🎞️ ফ্রেম পর পর",
                "🌟 সব ফ্রেম (Full)"
            ],
            command=self._on_mode_change
        )
        self.mode_segmented.set("🎯 টার্গেট FPS")
        self.mode_segmented.pack(fill="x", padx=15, pady=5)

        # Parameter Input & Presets Row
        self.param_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.param_frame.pack(fill="x", padx=15, pady=6)

        self.param_label = ctk.CTkLabel(
            self.param_frame,
            text="প্রতি সেকেন্ডে কয়টি ছবি নিবেন (Target FPS):",
            font=ctk.CTkFont(size=12)
        )
        self.param_label.pack(side="left", padx=(0, 10))

        self.param_entry = ctk.CTkEntry(
            self.param_frame,
            textvariable=self.param_value_var,
            width=90,
            height=32
        )
        self.param_entry.pack(side="left", padx=(0, 15))
        self.param_value_var.trace_add("write", lambda *args: self._recalculate_estimate())

        # Quick preset buttons container
        self.preset_frame = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.preset_frame.pack(side="left", fill="x", expand=True)
        self._update_presets_ui()

        # Dynamic Estimate Box
        self.estimate_frame = ctk.CTkFrame(card, fg_color=("#e0f2fe", "#0c4a6e"), corner_radius=8)
        self.estimate_frame.pack(fill="x", padx=15, pady=(6, 12))

        self.estimate_label = ctk.CTkLabel(
            self.estimate_frame,
            text="📊 আনুমানিক ছবি সংখ্যা: ০ টি",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#0369a1", "#38bdf8")
        )
        self.estimate_label.pack(side="left", padx=15, pady=8)

        self.estimate_detail_label = ctk.CTkLabel(
            self.estimate_frame,
            text="ভিডিও সিলেক্ট করুন হিসাব দেখতে",
            font=ctk.CTkFont(size=12),
            text_color=("#0284c7", "#7dd3fc")
        )
        self.estimate_detail_label.pack(side="right", padx=15, pady=8)

    def _build_output_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=6, padx=5)

        card_title = ctk.CTkLabel(
            card,
            text="3. আউটপুট ফোল্ডার ও ফরম্যাট (Output Settings)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.pack(anchor="w", padx=15, pady=(10, 5))

        # Output folder row
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(fill="x", padx=15, pady=5)

        self.output_entry = ctk.CTkEntry(
            folder_row,
            textvariable=self.output_dir_var,
            placeholder_text="আউটপুট ফোল্ডার সিলেক্ট করুন (Choose folder to save images)...",
            height=34
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_out_btn = ctk.CTkButton(
            folder_row,
            text="📁 ফোল্ডার নির্বাচন",
            width=130,
            height=34,
            command=self._on_browse_output
        )
        browse_out_btn.pack(side="left", padx=(0, 5))

        self.open_folder_btn = ctk.CTkButton(
            folder_row,
            text="📂 খুলুন",
            width=70,
            height=34,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray25"),
            command=self._open_output_folder
        )
        self.open_folder_btn.pack(side="right")

        # Format & Quality options row
        opts_row = ctk.CTkFrame(card, fg_color="transparent")
        opts_row.pack(fill="x", padx=15, pady=(5, 12))

        # Format
        fmt_label = ctk.CTkLabel(opts_row, text="ফরম্যাট:", font=ctk.CTkFont(size=12, weight="bold"))
        fmt_label.grid(row=0, column=0, sticky="w", padx=(0, 5))

        self.fmt_menu = ctk.CTkOptionMenu(
            opts_row,
            values=["JPG", "PNG", "WEBP"],
            variable=self.format_var,
            width=90,
            command=self._on_format_changed
        )
        self.fmt_menu.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Quality
        self.qual_label = ctk.CTkLabel(opts_row, text="কোয়ালিটি (95%):", font=ctk.CTkFont(size=12))
        self.qual_label.grid(row=0, column=2, sticky="w", padx=(0, 5))

        self.qual_slider = ctk.CTkSlider(
            opts_row,
            from_=50,
            to=100,
            number_of_steps=50,
            variable=self.quality_var,
            width=130,
            command=self._on_quality_slider
        )
        self.qual_slider.grid(row=0, column=3, sticky="w", padx=(0, 20))

        # Prefix
        prefix_label = ctk.CTkLabel(opts_row, text="ফাইলের নাম প্রিফিক্স:", font=ctk.CTkFont(size=12))
        prefix_label.grid(row=0, column=4, sticky="w", padx=(0, 5))

        self.prefix_entry = ctk.CTkEntry(opts_row, textvariable=self.prefix_var, width=100)
        self.prefix_entry.grid(row=0, column=5, sticky="w")

    def _build_progress_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=6, padx=5)

        card_title = ctk.CTkLabel(
            card,
            text="4. লাইভ প্রগ্রেস ও স্ট্যাটাস (Progress & Status)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.pack(anchor="w", padx=15, pady=(10, 5))

        # Progress bar & Percentage header
        top_prog = ctk.CTkFrame(card, fg_color="transparent")
        top_prog.pack(fill="x", padx=15, pady=(2, 4))

        self.status_badge = ctk.CTkLabel(
            top_prog,
            text="অপেক্ষারত (Ready)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#16a34a", "#4ade80")
        )
        self.status_badge.pack(side="left")

        self.percent_label = ctk.CTkLabel(
            top_prog,
            text="0%",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#2563eb", "#60a5fa")
        )
        self.percent_label.pack(side="right")

        # Smooth Progress Bar
        self.progressbar = ctk.CTkProgressBar(card, height=14)
        self.progressbar.pack(fill="x", padx=15, pady=4)
        self.progressbar.set(0)

        # Progress detail row + Live preview
        detail_container = ctk.CTkFrame(card, fg_color="transparent")
        detail_container.pack(fill="x", padx=15, pady=(6, 12))

        # Left side stats
        stats_frame = ctk.CTkFrame(detail_container, fg_color="transparent")
        stats_frame.pack(side="left", fill="both", expand=True)

        self.saved_count_label = ctk.CTkLabel(
            stats_frame,
            text="📁 সেভ হয়েছে: ০ / ০ টি ছবি",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.saved_count_label.pack(anchor="w", pady=2)

        self.speed_label = ctk.CTkLabel(
            stats_frame,
            text="⚡ প্রসেসিং স্পিড: 0.0 fps",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.speed_label.pack(anchor="w", pady=2)

        self.time_label = ctk.CTkLabel(
            stats_frame,
            text="⏱️ সময় অতিবাহিত: 00:00 | সময় বাকি: 00:00",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.time_label.pack(anchor="w", pady=2)

        # Right side Live Thumbnail Preview
        preview_container = ctk.CTkFrame(detail_container, width=160, height=90, corner_radius=6)
        preview_container.pack(side="right", padx=(10, 0))
        preview_container.pack_propagate(False)

        self.preview_label = ctk.CTkLabel(
            preview_container,
            text="লাইভ প্রিভিউ\n(Live Frame)",
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        self.preview_label.pack(expand=True)

    def _build_control_bar(self):
        control_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("#e2e8f0", "#1e293b"))
        control_bar.pack(fill="x", side="bottom")

        bar_inner = ctk.CTkFrame(control_bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=20, pady=12)

        self.start_btn = ctk.CTkButton(
            bar_inner,
            text="🚀 কনভার্ট শুরু করুন (Convert to Images)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color=("#16a34a", "#22c55e"),
            hover_color=("#15803d", "#16a34a"),
            command=self._start_conversion
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            bar_inner,
            text="⏹ থামান (Cancel)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            width=130,
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
            state="disabled",
            command=self._cancel_conversion
        )
        self.cancel_btn.pack(side="right")

    # ---------------- UI Event Handlers ----------------

    def _on_browse_video(self):
        filetypes = [
            ("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.ts"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="ভিডিও ফাইল নির্বাচন করুন", filetypes=filetypes)
        if chosen:
            self.video_path_var.set(chosen)
            self._load_selected_video(chosen)

    def _load_selected_video(self, filepath: str):
        self.video_info = VideoInfo(filepath)
        if not self.video_info.is_valid:
            messagebox.showerror("ত্রুটি (Error)", f"ভিডিও ফাইল পড়া যায়নি:\n{self.video_info.error_message}")
            self.info_label.configure(
                text=f"❌ ত্রুটি: {self.video_info.error_message}",
                text_color="#ef4444"
            )
            return

        # Populate info label
        info_text = (
            f"🎬 ফাইল: {self.video_info.filename} ({self.video_info.filesize_mb:.1f} MB)   |   "
            f"⏱️ ডিউরেশন: {self.video_info.duration_formatted}   |   "
            f"📐 রেজোলিউশন: {self.video_info.resolution_formatted}   |   "
            f"🎞️ মূল FPS: {self.video_info.fps:.2f}   |   "
            f"🔢 মোট ফ্রেম: {self.video_info.total_frames:,}"
        )
        self.info_label.configure(text=info_text, text_color=("#0f172a", "#f8fafc"))

        # Default output folder: subfolder next to the video
        video_dir = os.path.dirname(filepath)
        video_base_name = os.path.splitext(self.video_info.filename)[0]
        default_out = os.path.join(video_dir, f"{video_base_name}_images")
        self.output_dir_var.set(default_out)
        self.prefix_var.set(video_base_name[:12].replace(" ", "_"))

        self._recalculate_estimate()

    def _on_browse_output(self):
        chosen = filedialog.askdirectory(title="আউটপুট ফোল্ডার নির্বাচন করুন")
        if chosen:
            self.output_dir_var.set(chosen)

    def _open_output_folder(self):
        out_dir = self.output_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("সতর্কতা", "কোনো আউটপুট ফোল্ডার সেট করা নেই!")
            return
        
        os.makedirs(out_dir, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(out_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", out_dir])
            else:
                subprocess.Popen(["xdg-open", out_dir])
        except Exception as e:
            messagebox.showerror("ত্রুটি", f"ফোল্ডার খোলা যায়নি:\n{str(e)}")

    def _on_mode_change(self, mode_str: str):
        if "টার্গেট FPS" in mode_str:
            self.mode_var.set("fps")
            self.param_label.configure(text="প্রতি সেকেন্ডে কয়টি ছবি নিবেন (Target FPS):")
            self.param_value_var.set("1.0")
            self.param_entry.configure(state="normal")
        elif "সেকেন্ড পর পর" in mode_str:
            self.mode_var.set("interval_seconds")
            self.param_label.configure(text="প্রতি কতো সেকেন্ড পর পর ছবি নিবেন (Seconds):")
            self.param_value_var.set("1.0")
            self.param_entry.configure(state="normal")
        elif "ফ্রেম পর পর" in mode_str:
            self.mode_var.set("interval_frames")
            self.param_label.configure(text="প্রতি কতো ফ্রেম পর পর ছবি নিবেন (Frames):")
            self.param_value_var.set("30")
            self.param_entry.configure(state="normal")
        elif "সব ফ্রেম" in mode_str:
            self.mode_var.set("all")
            self.param_label.configure(text="ভিডিওর সব ফ্রেম এক্সট্র্যাক্ট হবে:")
            self.param_value_var.set("Full")
            self.param_entry.configure(state="disabled")

        self._update_presets_ui()
        self._recalculate_estimate()

    def _update_presets_ui(self):
        # Clear old preset buttons
        for child in self.preset_frame.winfo_children():
            child.destroy()

        mode = self.mode_var.get()
        presets = []
        if mode == "fps":
            presets = [("0.5 FPS", "0.5"), ("1 FPS", "1.0"), ("2 FPS", "2.0"), ("5 FPS", "5.0")]
        elif mode == "interval_seconds":
            presets = [("0.5s", "0.5"), ("1.0s", "1.0"), ("2.0s", "2.0"), ("5.0s", "5.0")]
        elif mode == "interval_frames":
            presets = [("১০ ফ্রেম", "10"), ("৩০ ফ্রেম", "30"), ("৬০ ফ্রেম", "60")]

        for label, val in presets:
            btn = ctk.CTkButton(
                self.preset_frame,
                text=label,
                width=55,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color=("gray80", "gray28"),
                hover_color=("gray70", "gray20"),
                command=lambda v=val: self.param_value_var.set(v)
            )
            btn.pack(side="left", padx=3)

    def _on_format_changed(self, choice: str):
        if choice in ["JPG", "WEBP"]:
            self.qual_slider.configure(state="normal")
            self.qual_label.configure(text_color=("black", "white"))
        else:
            self.qual_slider.configure(state="disabled")
            self.qual_label.configure(text_color="gray50")

    def _on_quality_slider(self, val):
        self.qual_label.configure(text=f"কোয়ালিটি ({int(val)}%):")

    def _recalculate_estimate(self):
        if not self.video_info or not self.video_info.is_valid:
            self.estimate_label.configure(text="📊 আনুমানিক ছবি সংখ্যা: ০ টি")
            self.estimate_detail_label.configure(text="ভিডিও সিলেক্ট করুন হিসাব দেখতে")
            self.target_frame_indices = []
            return

        mode = self.mode_var.get()
        val_str = self.param_value_var.get().strip()

        try:
            val = float(val_str) if mode != "all" else 1.0
        except ValueError:
            val = 1.0

        count, indices = VideoExtractor.calculate_target_frames(self.video_info, mode, val)
        self.target_frame_indices = indices

        # Approximate size
        # JPG average ~ 150KB, PNG ~ 1.5MB, WEBP ~ 100KB depending on resolution
        scale_res = (self.video_info.width * self.video_info.height) / (1920 * 1080)
        fmt = self.format_var.get().upper()
        if fmt == "PNG":
            avg_kb = 1200 * scale_res
        elif fmt == "WEBP":
            avg_kb = 120 * scale_res
        else:
            avg_kb = 200 * scale_res

        est_mb = (count * avg_kb) / 1024

        self.estimate_label.configure(text=f"📊 মোট ছবি হবে: {count:,} টি")
        self.estimate_detail_label.configure(
            text=f"আনুমানিক সাইজ: ~{est_mb:.1f} MB | মূল ফ্রেম: {self.video_info.total_frames:,}"
        )

    # ---------------- Conversion Execution ----------------

    def _start_conversion(self):
        if self.is_converting:
            return

        # Validations
        if not self.video_info or not self.video_info.is_valid:
            messagebox.showwarning("সতর্কতা", "দয়া করে একটি সঠিক ভিডিও ফাইল নির্বাচন করুন!")
            return

        out_dir = self.output_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("সতর্কতা", "দয়া করে আউটপুট ফোল্ডার নির্বাচন করুন!")
            return

        self._recalculate_estimate()
        if not self.target_frame_indices:
            messagebox.showwarning("সতর্কতা", "এক্সট্র্যাক্ট করার মতো কোনো ফ্রেম পাওয়া যায়নি!")
            return

        total_frames_to_extract = len(self.target_frame_indices)
        if total_frames_to_extract > 5000:
            confirm = messagebox.askyesno(
                "নিশ্চিতকরণ (Confirmation)",
                f"আপনি মোট {total_frames_to_extract:,} টি ছবি তৈরি করতে যাচ্ছেন!\n"
                f"এতে কিছুটা সময় লাগতে পারে এবং ডিস্ক স্পেস প্রয়োজন হবে। আপনি কি এগিয়ে যেতে চান?"
            )
            if not confirm:
                return

        # Prepare UI for conversion
        self.is_converting = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.status_badge.configure(text="প্রসেসিং হচ্ছে... (Converting...)", text_color=("#0284c7", "#38bdf8"))
        self.progressbar.set(0)
        self.percent_label.configure(text="0%")
        self.saved_count_label.configure(text=f"📁 সেভ হয়েছে: ০ / {total_frames_to_extract:,} টি ছবি")
        self.speed_label.configure(text="⚡ প্রসেসিং স্পিড: গণনাকৃত হচ্ছে...")
        self.time_label.configure(text="⏱️ সময় অতিবাহিত: 00:00 | সময় বাকি: হিসেব হচ্ছে...")

        self.extractor = VideoExtractor()

        # Gather settings
        fmt = self.format_var.get().lower()
        quality = int(self.quality_var.get())
        prefix = self.prefix_var.get().strip() or "frame"
        naming = self.naming_var.get()

        # Run extraction in background thread
        thread = threading.Thread(
            target=self._worker_thread,
            args=(out_dir, fmt, quality, prefix, naming),
            daemon=True
        )
        thread.start()

    def _worker_thread(self, out_dir: str, fmt: str, quality: int, prefix: str, naming: str):
        result = self.extractor.extract(
            video_info=self.video_info,
            output_dir=out_dir,
            frame_indices=self.target_frame_indices,
            image_format=fmt,
            image_quality=quality,
            filename_prefix=prefix,
            naming_style=naming,
            on_progress=self._on_progress_callback,
            on_thumbnail=self._on_thumbnail_callback
        )

        # Notify completion on GUI thread
        self.after(0, lambda: self._on_conversion_finished(result))

    def _on_progress_callback(self, data: dict):
        # Dispatch to main thread
        self.after(0, lambda: self._update_progress_ui(data))

    def _on_thumbnail_callback(self, frame_bgr: np.ndarray):
        # Resize thumbnail to 160x90 for preview
        try:
            h, w = frame_bgr.shape[:2]
            target_w = 160
            target_h = int(h * (target_w / w))
            if target_h > 90:
                target_h = 90
                target_w = int(w * (target_h / h))

            import cv2
            resized = cv2.resize(frame_bgr, (target_w, target_h))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
            self.after(0, lambda: self._update_thumbnail_ui(ctk_img))
        except Exception:
            pass

    def _update_thumbnail_ui(self, ctk_img):
        self.preview_label.configure(image=ctk_img, text="")

    def _update_progress_ui(self, data: dict):
        percent = data["percentage"]
        fraction = percent / 100.0
        self.progressbar.set(fraction)
        self.percent_label.configure(text=f"{percent}%")

        self.saved_count_label.configure(
            text=f"📁 সেভ হয়েছে: {data['saved_count']:,} / {data['total']:,} টি ছবি"
        )
        self.speed_label.configure(
            text=f"⚡ প্রসেসিং স্পিড: {data['speed_fps']:.1f} fps"
        )

        elapsed_sec = int(data["elapsed_seconds"])
        eta_sec = int(data["eta_seconds"])
        elapsed_str = f"{elapsed_sec // 60:02d}:{elapsed_sec % 60:02d}"
        eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"

        self.time_label.configure(
            text=f"⏱️ সময় অতিবাহিত: {elapsed_str} | সময় বাকি: {eta_str}"
        )

    def _cancel_conversion(self):
        if self.extractor and self.is_converting:
            self.status_badge.configure(text="বাতিল করা হচ্ছে... (Cancelling...)", text_color="#ef4444")
            self.extractor.cancel()

    def _on_conversion_finished(self, result: dict):
        self.is_converting = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

        if result.get("cancelled", False):
            self.status_badge.configure(text="কনভার্সন থামানো হয়েছে (Cancelled)", text_color="#f59e0b")
            messagebox.showinfo(
                "বাতিল হয়েছে",
                f"কনভার্সন থামানো হয়েছে!\nমোট {result.get('saved_count', 0):,} টি ছবি সেভ হয়েছিল।"
            )
            return

        if not result.get("success", False):
            err = result.get("error", "অজানা ত্রুটি")
            self.status_badge.configure(text="ব্যর্থ হয়েছে (Failed)", text_color="#ef4444")
            messagebox.showerror("ত্রুটি", f"কনভার্সন সম্পূর্ণ হতে পারেনি:\n{err}")
            return

        # Successful completion
        self.progressbar.set(1.0)
        self.percent_label.configure(text="100%")
        self.status_badge.configure(text="সম্পন্ন হয়েছে! (Completed)", text_color=("#16a34a", "#22c55e"))

        saved = result.get("saved_count", 0)
        elapsed = result.get("elapsed_seconds", 0)
        out_dir = result.get("output_dir", "")

        # Sound beep on Windows
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        # Ask user if they want to open the output folder
        open_now = messagebox.askyesno(
            "সাফল্য! (Success)",
            f"🎉 অভিনন্দন!\n\n"
            f"মোট {saved:,} টি ছবি সফলভাবে তৈরি হয়েছে!\n"
            f"সময় লেগেছে: {elapsed:.1f} সেকেন্ড।\n"
            f"ফোল্ডার: {out_dir}\n\n"
            f"আপনি কি এখনই আউটপুট ফোল্ডারটি ওপেন করতে চান?"
        )
        if open_now:
            self._open_output_folder()


if __name__ == "__main__":
    app = VideoToImageApp()
    app.mainloop()

