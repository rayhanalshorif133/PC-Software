import os
import sys
import time
import threading
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import keyboard
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageGrab

# Set Process DPI Awareness for sharp coordinates and capture accuracy
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Win32 Structures and Constants for High-Speed Mouse Control
user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP   = 0x0040

WM_MOUSEMOVE   = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP   = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP   = 0x0205
WM_RBUTTONDBLCLK = 0x0206
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP   = 0x0208
WM_MBUTTONDBLCLK = 0x0209


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.RealChildWindowFromPoint.argtypes = [wintypes.HWND, POINT]
user32.RealChildWindowFromPoint.restype = wintypes.HWND
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL


def get_mouse_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_mouse_pos(x, y):
    user32.SetCursorPos(int(x), int(y))


def do_click(button='Left', click_type='Single'):
    if button == 'Left':
        down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    elif button == 'Right':
        down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    else:
        down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP

    clicks = 2 if click_type == 'Double' else 1
    for _ in range(clicks):
        user32.mouse_event(down, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(up, 0, 0, 0, 0)
        if clicks > 1:
            time.sleep(0.05)


def do_background_virtual_click(target_x, target_y, button='Left', click_type='Single'):
    """Sends background click messages directly to the window at (target_x, target_y)
       WITHOUT MOVING THE USER'S PHYSICAL MOUSE CURSOR AT ALL.
    """
    pt = POINT(int(target_x), int(target_y))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return False

    try:
        child = user32.RealChildWindowFromPoint(hwnd, pt)
        target = child if child else hwnd
    except Exception:
        target = hwnd

    c_pt = POINT(int(target_x), int(target_y))
    user32.ScreenToClient(target, ctypes.byref(c_pt))
    lparam = (c_pt.y << 16) | (c_pt.x & 0xFFFF)

    if button == 'Right':
        down_msg, up_msg, dbl_msg, mk = WM_RBUTTONDOWN, WM_RBUTTONUP, WM_RBUTTONDBLCLK, 0x0002
    elif button == 'Middle':
        down_msg, up_msg, dbl_msg, mk = WM_MBUTTONDOWN, WM_MBUTTONUP, WM_MBUTTONDBLCLK, 0x0010
    else:
        down_msg, up_msg, dbl_msg, mk = WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK, 0x0001

    clicks = 2 if click_type == 'Double' else 1
    for _ in range(clicks):
        user32.PostMessageW(target, WM_MOUSEMOVE, 0, lparam)
        user32.PostMessageW(target, down_msg, mk, lparam)
        time.sleep(0.012)
        user32.PostMessageW(target, up_msg, 0, lparam)
        if click_type == 'Double':
            user32.PostMessageW(target, dbl_msg, mk, lparam)
        if clicks > 1:
            time.sleep(0.03)
    return True


class VirtualCursorIndicator:
    """A floating, click-through duplicate cursor indicator that shows where the virtual click happened."""
    def __init__(self, master):
        self.master = master
        self.win = None
        self._init_window()

    def _init_window(self):
        try:
            self.win = tk.Toplevel(self.master)
            self.win.overrideredirect(True)
            self.win.attributes('-topmost', True)
            self.win.attributes('-transparentcolor', '#000001')
            self.win.config(bg='#000001')
            self.win.withdraw()

            # Click-through style
            hwnd = user32.GetParent(self.win.winfo_id())
            if not hwnd:
                hwnd = self.win.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_TRANSPARENT | WS_EX_LAYERED
            )

            self.canvas = tk.Canvas(self.win, width=44, height=44, bg='#000001', highlightthickness=0)
            self.canvas.pack()

            # Target ring & duplicate cursor icon
            self.canvas.create_oval(3, 3, 41, 41, outline='#00d26a', width=2)
            self.canvas.create_oval(17, 17, 27, 27, fill='#ff4757', outline='#ffffff', width=1)
            self.canvas.create_text(28, 14, text='🖱️', font=('Segoe UI Emoji', 12))
        except Exception as e:
            print(f"Could not init virtual cursor indicator: {e}")

    def show_at(self, x, y, duration_ms=350):
        if not self.win:
            return
        try:
            self.win.geometry(f'44x44+{int(x)-22}+{int(y)-22}')
            self.win.deiconify()
            self.win.after(duration_ms, self.win.withdraw)
        except Exception:
            pass


class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("⚡ Auto Clicker Pro - Manual & Image Match")
        self.geometry("560x760")
        self.minsize(500, 660)
        self.resizable(True, True)

        # Set Icon if available
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Execution State Variables
        self.is_running = False
        self.running_mode = None  # "manual" or "image"
        self.click_thread = None
        self.stop_event = threading.Event()
        self.total_clicks_done = 0
        self.always_on_top_var = ctk.BooleanVar(value=True)
        self._countdown_active = False

        # Image Detection Template State
        self.template_image_cv = None     # cv2 BGR numpy array
        self.template_image_pil = None    # PIL Image
        self.template_image_name = None   # filename
        self.template_ctk_image = None    # CTkImage for thumbnail
        self.template_display_size = None
        self.is_preview_hidden = False
        self.auto_minimize_var = ctk.BooleanVar(value=False)

        # Advanced Settings for Non-Disruptive Virtual Clicking & Multi-Scale Detection
        self.click_method_var = ctk.StringVar(value="virtual")  # "virtual" or "flick"
        self.multiscale_var = ctk.BooleanVar(value=True)       # Auto-detect resized buttons (small or big)
        self.show_indicator_var = ctk.BooleanVar(value=True)    # Show visual duplicate cursor ring

        # CustomTkinter Appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.attributes('-topmost', True)

        self._create_widgets()
        self._register_hotkeys()
        self._start_mouse_tracker()
        self.virtual_cursor = VirtualCursorIndicator(self)
        self.load_default_template()  # Auto-loads submit.png if present

    def _create_widgets(self):
        # 1. Header Card (Top)
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        self.header_frame.pack(side="top", fill="x", padx=16, pady=(10, 4))

        top_bar = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(8, 2))

        self.app_title = ctk.CTkLabel(
            top_bar,
            text="⚡ Auto Clicker Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#00cec9"
        )
        self.app_title.pack(side="left")

        self.chk_top = ctk.CTkCheckBox(
            top_bar,
            text="Always on Top",
            variable=self.always_on_top_var,
            font=ctk.CTkFont(size=12),
            command=self._toggle_always_on_top
        )
        self.chk_top.pack(side="right")

        # Real-time Mouse Tracker Banner
        self.tracker_frame = ctk.CTkFrame(self.header_frame, fg_color=("#3a3a3a", "#25282a"), corner_radius=8)
        self.tracker_frame.pack(fill="x", padx=12, pady=(4, 10))

        self.lbl_cur_pos = ctk.CTkLabel(
            self.tracker_frame,
            text="📍 Live Mouse Position: X = 0, Y = 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00d26a"
        )
        self.lbl_cur_pos.pack(side="left", padx=12, pady=6)

        self.lbl_hotkey_hint = ctk.CTkLabel(
            self.tracker_frame,
            text="[ Hotkey: Ctrl+Shift+S ]",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#fdcb6e"
        )
        self.lbl_hotkey_hint.pack(side="right", padx=12, pady=6)

        # 2. Bottom Action Card (Always at bottom, fixed height & never shrinks)
        self.action_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        self.action_frame.pack(side="bottom", fill="x", padx=16, pady=(4, 12))

        # Status Row
        self.status_row = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.status_row.pack(fill="x", padx=14, pady=(8, 4))

        self.lbl_status = ctk.CTkLabel(
            self.status_row,
            text="● Status: Stopped",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ff4757"
        )
        self.lbl_status.pack(side="left")

        # Dynamic match / countdown message
        self.lbl_countdown = ctk.CTkLabel(
            self.status_row,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1c40f"
        )
        self.lbl_countdown.pack(side="left", expand=True)

        self.lbl_stats = ctk.CTkLabel(
            self.status_row,
            text="Clicks: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#dcdde1"
        )
        self.lbl_stats.pack(side="right")

        # Main Start / Stop Button
        self.btn_start_stop = ctk.CTkButton(
            self.action_frame,
            text="🚀 START (Ctrl + Shift + S)",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=46,
            fg_color="#00b894",
            hover_color="#00a383",
            corner_radius=10,
            command=self.toggle_clicking
        )
        self.btn_start_stop.pack(fill="x", padx=14, pady=(6, 10))

        # 3. Tabview Container (Center Expands)
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color=("#2b2b2b", "#1a1c1e"),
            segmented_button_selected_color="#0984e3",
            segmented_button_selected_hover_color="#0873c4"
        )
        self.tabview.pack(side="top", fill="both", expand=True, padx=16, pady=4)

        self.tab_manual = self.tabview.add("📌 Manual Click")
        self.tab_image = self.tabview.add("🖼️ Image Detection")
        self.tabview.set("📌 Manual Click")

        self._build_manual_tab()
        self._build_image_tab()

    def _toggle_always_on_top(self):
        self.attributes('-topmost', self.always_on_top_var.get())

    # =========================================================================
    # TAB 1: MANUAL CLICKING CONTROLS
    # =========================================================================
    def _build_manual_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_manual, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. Target Position Box
        pos_card = ctk.CTkFrame(scroll, corner_radius=10)
        pos_card.pack(fill="x", pady=4)

        ctk.CTkLabel(pos_card, text="🎯 Click Target Location", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

        self.coord_frame = ctk.CTkFrame(pos_card, fg_color="transparent")
        self.coord_frame.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(self.coord_frame, text="X:").pack(side="left", padx=(0, 4))
        self.ent_x = ctk.CTkEntry(self.coord_frame, width=70, placeholder_text="0")
        self.ent_x.insert(0, "500")
        self.ent_x.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.coord_frame, text="Y:").pack(side="left", padx=(0, 4))
        self.ent_y = ctk.CTkEntry(self.coord_frame, width=70, placeholder_text="0")
        self.ent_y.insert(0, "500")
        self.ent_y.pack(side="left", padx=(0, 12))

        # 3-Second Countdown Pick Button
        self.btn_pick_countdown = ctk.CTkButton(
            self.coord_frame,
            text="⏱ 3s Delay Pick",
            fg_color="#e67e22",
            hover_color="#d35400",
            height=32,
            font=ctk.CTkFont(weight="bold"),
            command=self.start_3s_pick_countdown
        )
        self.btn_pick_countdown.pack(side="right", fill="x", expand=True)

        # 2. Click Interval Box (Default: 6 sec)
        interval_card = ctk.CTkFrame(scroll, corner_radius=10)
        interval_card.pack(fill="x", pady=4)

        ctk.CTkLabel(interval_card, text="⏱ Click Interval (Default: 6 seconds)", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

        int_row = ctk.CTkFrame(interval_card, fg_color="transparent")
        int_row.pack(fill="x", padx=12, pady=(2, 8))

        self.ent_hours = ctk.CTkEntry(int_row, width=44)
        self.ent_hours.insert(0, "0")
        self.ent_hours.pack(side="left")
        ctk.CTkLabel(int_row, text="h").pack(side="left", padx=(2, 8))

        self.ent_mins = ctk.CTkEntry(int_row, width=44)
        self.ent_mins.insert(0, "0")
        self.ent_mins.pack(side="left")
        ctk.CTkLabel(int_row, text="m").pack(side="left", padx=(2, 8))

        self.ent_secs = ctk.CTkEntry(int_row, width=44)
        self.ent_secs.insert(0, "6")
        self.ent_secs.pack(side="left")
        ctk.CTkLabel(int_row, text="s").pack(side="left", padx=(2, 8))

        self.ent_ms = ctk.CTkEntry(int_row, width=60)
        self.ent_ms.insert(0, "0")
        self.ent_ms.pack(side="left")
        ctk.CTkLabel(int_row, text="ms").pack(side="left", padx=(2, 4))

        # 3. Click Type and Button
        opts_card = ctk.CTkFrame(scroll, corner_radius=10)
        opts_card.pack(fill="x", pady=4)

        ctk.CTkLabel(opts_card, text="⚙️ Click Options", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

        opts_row = ctk.CTkFrame(opts_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=12, pady=(2, 4))

        ctk.CTkLabel(opts_row, text="Button:").pack(side="left", padx=(0, 6))
        self.opt_button = ctk.CTkOptionMenu(opts_row, values=["Left", "Right", "Middle"], width=90)
        self.opt_button.set("Left")
        self.opt_button.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(opts_row, text="Type:").pack(side="left", padx=(0, 6))
        self.opt_type = ctk.CTkOptionMenu(opts_row, values=["Single", "Double"], width=90)
        self.opt_type.set("Single")
        self.opt_type.pack(side="left")

        # 4. Repeat Mode
        repeat_row = ctk.CTkFrame(opts_card, fg_color="transparent")
        repeat_row.pack(fill="x", padx=12, pady=(4, 8))

        self.repeat_mode = ctk.StringVar(value="infinite")
        self.rb_repeat_inf = ctk.CTkRadioButton(
            repeat_row, text="Repeat until stopped", variable=self.repeat_mode, value="infinite",
            command=self._on_repeat_mode_change
        )
        self.rb_repeat_inf.pack(side="left", padx=(0, 14))

        self.rb_repeat_count = ctk.CTkRadioButton(
            repeat_row, text="Repeat", variable=self.repeat_mode, value="count",
            command=self._on_repeat_mode_change
        )
        self.rb_repeat_count.pack(side="left", padx=(0, 6))

        self.ent_repeat_times = ctk.CTkEntry(repeat_row, width=54)
        self.ent_repeat_times.insert(0, "50")
        self.ent_repeat_times.pack(side="left")
        self.ent_repeat_times.configure(state="disabled")
        ctk.CTkLabel(repeat_row, text="times").pack(side="left", padx=(4, 0))

    def _on_repeat_mode_change(self):
        if self.repeat_mode.get() == "infinite":
            self.ent_repeat_times.configure(state="disabled")
        else:
            self.ent_repeat_times.configure(state="normal")

    # =========================================================================
    # TAB 2: IMAGE DETECTION CLICKER CONTROLS
    # =========================================================================
    def _build_image_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_image, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. Image Template Card
        img_card = ctk.CTkFrame(scroll, corner_radius=10)
        img_card.pack(fill="x", pady=4)

        card_title_row = ctk.CTkFrame(img_card, fg_color="transparent")
        card_title_row.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(card_title_row, text="🖼️ Target Template Image", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        # Action Buttons for Image
        btn_row = ctk.CTkFrame(img_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=4)

        self.btn_upload_img = ctk.CTkButton(
            btn_row,
            text="📁 Upload Image",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0984e3",
            hover_color="#0873c4",
            height=32,
            command=self.choose_template_file
        )
        self.btn_upload_img.pack(side="left", padx=(0, 6), expand=True, fill="x")

        self.btn_snip_img = ctk.CTkButton(
            btn_row,
            text="✂️ Snip Screen",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c5ce7",
            hover_color="#5849be",
            height=32,
            command=self.start_screen_snip
        )
        self.btn_snip_img.pack(side="left", padx=(0, 6), expand=True, fill="x")

        self.btn_toggle_preview = ctk.CTkButton(
            btn_row,
            text="👁️ Hide",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#636e72",
            hover_color="#2d3436",
            width=65,
            height=32,
            command=self.toggle_preview_visibility
        )
        self.btn_toggle_preview.pack(side="left", padx=(0, 6))

        self.btn_clear_img = ctk.CTkButton(
            btn_row,
            text="❌ Clear",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d63031",
            hover_color="#b82828",
            width=65,
            height=32,
            command=self.clear_template_image
        )
        self.btn_clear_img.pack(side="right")

        # Thumbnail Preview Container (Height 130 for clear visualization)
        self.preview_box = ctk.CTkFrame(img_card, fg_color=("#22252a", "#15181b"), corner_radius=8, height=130)
        self.preview_box.pack(fill="x", padx=12, pady=(4, 6))
        self.preview_box.pack_propagate(False)

        self.lbl_img_preview = ctk.CTkLabel(
            self.preview_box,
            text="🖼️ No Image Selected\nClick 'Upload Image' or 'Snip Screen' to choose a target",
            font=ctk.CTkFont(size=12),
            text_color="#7f8c8d"
        )
        self.lbl_img_preview.pack(expand=True, fill="both", padx=8, pady=4)

        self.lbl_img_info = ctk.CTkLabel(
            img_card,
            text="Status: No template loaded",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        )
        self.lbl_img_info.pack(anchor="w", padx=14, pady=(0, 6))

        # 2. Detection Settings Card
        detect_card = ctk.CTkFrame(scroll, corner_radius=10)
        detect_card.pack(fill="x", pady=4)

        ctk.CTkLabel(detect_card, text="🎯 Detection & Multi-Scale Scanning", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

        # Confidence Slider Row
        conf_row = ctk.CTkFrame(detect_card, fg_color="transparent")
        conf_row.pack(fill="x", padx=12, pady=2)

        self.lbl_conf_value = ctk.CTkLabel(
            conf_row,
            text="Match Accuracy (Confidence): 80%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00cec9"
        )
        self.lbl_conf_value.pack(side="left")

        self.slider_confidence = ctk.CTkSlider(
            detect_card,
            from_=50,
            to=99,
            number_of_steps=49,
            command=self._on_confidence_change
        )
        self.slider_confidence.set(80)
        self.slider_confidence.pack(fill="x", padx=12, pady=(0, 4))

        # Multi-scale Option (Handles small / big button sizes)
        ms_row = ctk.CTkFrame(detect_card, fg_color="transparent")
        ms_row.pack(fill="x", padx=12, pady=(0, 6))

        self.chk_multiscale = ctk.CTkCheckBox(
            ms_row,
            text="🔍 Auto-detect resized buttons (Support Small & Big image sizes)",
            variable=self.multiscale_var,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.chk_multiscale.pack(side="left")

        # Scan Interval Row (DEFAULT: 3 seconds as requested)
        scan_row = ctk.CTkFrame(detect_card, fg_color="transparent")
        scan_row.pack(fill="x", padx=12, pady=(2, 6))

        ctk.CTkLabel(scan_row, text="Scan Screen Every:").pack(side="left", padx=(0, 8))

        self.ent_img_scan_s = ctk.CTkEntry(scan_row, width=44)
        self.ent_img_scan_s.insert(0, "3")  # Default: 3 seconds
        self.ent_img_scan_s.pack(side="left")
        ctk.CTkLabel(scan_row, text="s").pack(side="left", padx=(2, 10))

        self.ent_img_scan_ms = ctk.CTkEntry(scan_row, width=54)
        self.ent_img_scan_ms.insert(0, "0")
        self.ent_img_scan_ms.pack(side="left")
        ctk.CTkLabel(scan_row, text="ms").pack(side="left", padx=(2, 12))

        ctk.CTkLabel(scan_row, text="Post-Click Delay:").pack(side="left", padx=(0, 6))
        self.ent_img_cooldown = ctk.CTkEntry(scan_row, width=44)
        self.ent_img_cooldown.insert(0, "1.0")
        self.ent_img_cooldown.pack(side="left")
        ctk.CTkLabel(scan_row, text="s").pack(side="left", padx=(2, 0))

        # 3. Independent / Duplicate Cursor Click Options Card
        click_card = ctk.CTkFrame(scroll, corner_radius=10)
        click_card.pack(fill="x", pady=4)

        ctk.CTkLabel(click_card, text="⚙️ Click Method & Duplicate Cursor Mode", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))

        # Mode Selection Row: Background Virtual Click vs Hardware Flick
        method_row = ctk.CTkFrame(click_card, fg_color="transparent")
        method_row.pack(fill="x", padx=12, pady=3)

        ctk.CTkLabel(method_row, text="Click Mode:").pack(side="left", padx=(0, 8))

        self.rb_click_virtual = ctk.CTkRadioButton(
            method_row,
            text="🤖 Background Virtual (User's mouse NEVER moves)",
            variable=self.click_method_var,
            value="virtual"
        )
        self.rb_click_virtual.pack(side="left", padx=(0, 12))

        self.rb_click_flick = ctk.CTkRadioButton(
            method_row,
            text="⚡ Instant Flick & Restore",
            variable=self.click_method_var,
            value="flick"
        )
        self.rb_click_flick.pack(side="left")

        # Visual indicator and auto-minimize row
        ind_row = ctk.CTkFrame(click_card, fg_color="transparent")
        ind_row.pack(fill="x", padx=12, pady=3)

        self.chk_indicator = ctk.CTkCheckBox(
            ind_row,
            text="Show Duplicate Cursor target ring on click",
            variable=self.show_indicator_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_indicator.pack(side="left", padx=(0, 16))

        self.chk_auto_minimize = ctk.CTkCheckBox(
            ind_row,
            text="Auto-minimize window while scanning",
            variable=self.auto_minimize_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_auto_minimize.pack(side="left")

        # Standard click properties row
        c_row1 = ctk.CTkFrame(click_card, fg_color="transparent")
        c_row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(c_row1, text="Button:").pack(side="left", padx=(0, 6))
        self.opt_img_button = ctk.CTkOptionMenu(c_row1, values=["Left", "Right", "Middle"], width=90)
        self.opt_img_button.set("Left")
        self.opt_img_button.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(c_row1, text="Type:").pack(side="left", padx=(0, 6))
        self.opt_img_type = ctk.CTkOptionMenu(c_row1, values=["Single", "Double"], width=90)
        self.opt_img_type.set("Single")
        self.opt_img_type.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(c_row1, text="Position:").pack(side="left", padx=(0, 6))
        self.opt_img_pos = ctk.CTkOptionMenu(c_row1, values=["Center", "Top-Left"], width=95)
        self.opt_img_pos.set("Center")
        self.opt_img_pos.pack(side="left")

        # Repeat Behavior
        c_row2 = ctk.CTkFrame(click_card, fg_color="transparent")
        c_row2.pack(fill="x", padx=12, pady=(4, 8))

        self.img_repeat_mode = ctk.StringVar(value="infinite")

        self.rb_img_inf = ctk.CTkRadioButton(
            c_row2, text="Continuous (every time seen)", variable=self.img_repeat_mode, value="infinite",
            command=self._on_img_repeat_change
        )
        self.rb_img_inf.pack(side="left", padx=(0, 12))

        self.rb_img_once = ctk.CTkRadioButton(
            c_row2, text="Click once & stop", variable=self.img_repeat_mode, value="once",
            command=self._on_img_repeat_change
        )
        self.rb_img_once.pack(side="left", padx=(0, 12))

        self.rb_img_count = ctk.CTkRadioButton(
            c_row2, text="Repeat", variable=self.img_repeat_mode, value="count",
            command=self._on_img_repeat_change
        )
        self.rb_img_count.pack(side="left", padx=(0, 4))

        self.ent_img_repeat_times = ctk.CTkEntry(c_row2, width=48)
        self.ent_img_repeat_times.insert(0, "10")
        self.ent_img_repeat_times.pack(side="left")
        self.ent_img_repeat_times.configure(state="disabled")
        ctk.CTkLabel(c_row2, text="times").pack(side="left", padx=(3, 0))

    def _on_confidence_change(self, value):
        val = int(value)
        self.lbl_conf_value.configure(text=f"Match Accuracy (Confidence): {val}%")

    def _on_img_repeat_change(self):
        if self.img_repeat_mode.get() == "count":
            self.ent_img_repeat_times.configure(state="normal")
        else:
            self.ent_img_repeat_times.configure(state="disabled")

    # =========================================================================
    # TEMPLATE IMAGE MANAGEMENT & AUTO-LOAD
    # =========================================================================
    def load_default_template(self):
        """Automatically loads submit.png if present in root or bundled resources."""
        candidate_names = ["submit.png", "Submit.png"]
        found_path = None
        for name in candidate_names:
            p1 = resource_path(name)
            if os.path.exists(p1):
                found_path = p1
                break
            p2 = os.path.abspath(name)
            if os.path.exists(p2):
                found_path = p2
                break

        if found_path and os.path.exists(found_path):
            try:
                pil_raw = Image.open(found_path)
                pil_raw.load()
                pil_img = pil_raw.convert("RGBA")
                np_arr = np.array(pil_img)
                img_cv = cv2.cvtColor(np_arr, cv2.COLOR_RGBA2BGR)
                self._apply_template_image(img_cv, pil_img, os.path.basename(found_path))
                # Switch to Image Detection tab so user can immediately click Start!
                self.tabview.set("🖼️ Image Detection")
            except Exception as e:
                print(f"Could not auto-load default template: {e}")

    def choose_template_file(self):
        """Open a file dialog to pick an image file and display it cleanly."""
        file_path = filedialog.askopenfilename(
            title="Select Target Image",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"),
                ("All files", "*.*")
            ]
        )
        if not file_path:
            return

        try:
            pil_raw = Image.open(file_path)
            pil_raw.load()
            pil_img = pil_raw.convert("RGBA")
            np_arr = np.array(pil_img)
            img_cv = cv2.cvtColor(np_arr, cv2.COLOR_RGBA2BGR)
            self._apply_template_image(img_cv, pil_img, os.path.basename(file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{e}")

    def _apply_template_image(self, img_cv, pil_img, name="Template"):
        """Stores the image and displays a crystal-clear preview."""
        self.template_image_cv = img_cv
        self.template_image_pil = pil_img
        self.template_image_name = name
        self.is_preview_hidden = False
        self.btn_toggle_preview.configure(text="👁️ Hide")

        w, h = pil_img.size

        # Smart thumbnail size calculation
        max_disp_w = 320
        max_disp_h = 120

        # If image is very small (< 60px in both dims), zoom it up for clear visibility
        if w < 60 and h < 60:
            zoom = min(80 // max(1, w), 80 // max(1, h), 4)
            zoom = max(2, zoom)
            disp_w = w * zoom
            disp_h = h * zoom
            zoom_badge = f" [Zoom: {zoom}x]"
        else:
            scale = min(max_disp_w / max(1, w), max_disp_h / max(1, h), 1.0)
            disp_w = max(1, int(w * scale))
            disp_h = max(1, int(h * scale))
            zoom_badge = ""

        self.template_display_size = (disp_w, disp_h)

        # Composite transparent images over a neutral light-contrast tile
        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            bg_tile = Image.new("RGBA", pil_img.size, (235, 238, 242, 255))
            clean_pil = Image.alpha_composite(bg_tile, pil_img).convert("RGB")
        else:
            clean_pil = pil_img.convert("RGB")

        preview_resized = clean_pil.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.template_ctk_image = ctk.CTkImage(
            light_image=preview_resized,
            dark_image=preview_resized,
            size=(disp_w, disp_h)
        )

        self._show_preview_on_ui()

        self.lbl_img_info.configure(
            text=f"Loaded: {name} ({w}×{h} px){zoom_badge}",
            text_color="#00d26a"
        )

    def _show_preview_on_ui(self):
        """Displays the image thumbnail in the preview box."""
        if self.template_ctk_image is not None:
            self.lbl_img_preview.configure(
                image=self.template_ctk_image,
                text=""
            )
            self.lbl_img_preview._image = self.template_ctk_image
            self.is_preview_hidden = False
            self.btn_toggle_preview.configure(text="👁️ Hide")

    def _hide_preview_on_ui(self, reason_text=None):
        """Hides the thumbnail preview to protect against self-detection during scanning."""
        if reason_text is None:
            reason_text = "🛡️ Image Preview Hidden While Scanning\n(Auto-protected so scanner never detects itself)"

        self.lbl_img_preview.configure(
            image="",
            text=reason_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f1c40f"
        )
        self.is_preview_hidden = True
        self.btn_toggle_preview.configure(text="👁️ Show")

    def toggle_preview_visibility(self):
        """Allows user to manually hide or show the template preview."""
        if self.template_ctk_image is None:
            return

        if self.is_preview_hidden:
            self._show_preview_on_ui()
        else:
            self._hide_preview_on_ui("👁️ Preview Manually Hidden\nClick 'Show' to view again")

    def clear_template_image(self):
        """Resets the template image."""
        self.template_image_cv = None
        self.template_image_pil = None
        self.template_image_name = None
        self.template_ctk_image = None
        self.template_display_size = None
        self.is_preview_hidden = False
        self.btn_toggle_preview.configure(text="👁️ Hide")

        self.lbl_img_preview.configure(
            image="",
            text="🖼️ No Image Selected\nClick 'Upload Image' or 'Snip Screen' to choose a target",
            font=ctk.CTkFont(size=12),
            text_color="#7f8c8d"
        )
        self.lbl_img_info.configure(
            text="Status: No template loaded",
            text_color="#95a5a6"
        )

    # =========================================================================
    # SCREEN SNIPPER TOOL
    # =========================================================================
    def start_screen_snip(self):
        """Hides the app and allows user to drag a rectangle to snip a target image from screen."""
        self.withdraw()
        self.after(260, self._do_screen_snip)

    def _capture_screen_pil(self):
        """Grabs the current desktop screenshot reliably."""
        try:
            hdesk = user32.OpenDesktopA(b'Default', 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass
        try:
            return ImageGrab.grab()
        except Exception as e:
            print(f"ImageGrab error: {e}")
            return None

    def _do_screen_snip(self):
        screen = self._capture_screen_pil()
        if screen is None:
            self.deiconify()
            messagebox.showerror("Error", "Could not capture screen for snipping.")
            return

        snip_win = tk.Toplevel(self)
        snip_win.attributes('-fullscreen', True)
        snip_win.attributes('-topmost', True)
        snip_win.config(cursor="cross")

        canvas = tk.Canvas(snip_win, cursor="cross", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        bg_photo = ImageTk.PhotoImage(screen)
        canvas.create_image(0, 0, image=bg_photo, anchor="nw")
        snip_win.bg_photo = bg_photo  # Maintain reference

        canvas.create_text(
            screen.width // 2, 35,
            text="✂️ Drag a box around the button/icon to capture | ESC or Right-Click to cancel",
            fill="#f1c40f", font=("Helvetica", 14, "bold")
        )

        start_x = [0]
        start_y = [0]
        rect_id = [None]

        def on_press(e):
            start_x[0], start_y[0] = e.x, e.y
            if rect_id[0]:
                canvas.delete(rect_id[0])
            rect_id[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#00d26a", width=2)

        def on_drag(e):
            if rect_id[0]:
                canvas.coords(rect_id[0], start_x[0], start_y[0], e.x, e.y)

        def on_release(e):
            x1 = min(start_x[0], e.x)
            y1 = min(start_y[0], e.y)
            x2 = max(start_x[0], e.x)
            y2 = max(start_y[0], e.y)

            snip_win.destroy()
            self.deiconify()

            if (x2 - x1) >= 6 and (y2 - y1) >= 6:
                cropped = screen.crop((x1, y1, x2, y2))
                cropped_rgba = cropped.convert("RGBA")
                cropped_np = np.array(cropped_rgba)
                cropped_cv = cv2.cvtColor(cropped_np, cv2.COLOR_RGBA2BGR)
                self._apply_template_image(cropped_cv, cropped_rgba, f"Snip_{x2-x1}x{y2-y1}.png")

        def on_cancel(e=None):
            snip_win.destroy()
            self.deiconify()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        snip_win.bind("<Escape>", on_cancel)
        snip_win.bind("<Button-3>", on_cancel)

    # =========================================================================
    # DELAY PICK & MOUSE TRACKER
    # =========================================================================
    def start_3s_pick_countdown(self):
        """Starts a 3-second countdown to pick mouse position wherever it is placed."""
        if self._countdown_active:
            return
        self._countdown_active = True

        def step(remaining):
            if remaining > 0:
                self.btn_pick_countdown.configure(
                    text=f"Move mouse! Picking: {remaining}s...",
                    fg_color="#d35400"
                )
                self.after(1000, lambda: step(remaining - 1))
            else:
                x, y = get_mouse_pos()
                self.ent_x.delete(0, "end")
                self.ent_x.insert(0, str(x))
                self.ent_y.delete(0, "end")
                self.ent_y.insert(0, str(y))

                self.btn_pick_countdown.configure(
                    text=f"🎯 Locked: ({x}, {y})!",
                    fg_color="#00b894"
                )

                def reset():
                    self.btn_pick_countdown.configure(
                        text="⏱ 3s Delay Pick",
                        fg_color="#e67e22"
                    )
                    self._countdown_active = False

                self.after(1500, reset)

        step(3)

    def _start_mouse_tracker(self):
        """Continuously update live mouse coordinate in the UI."""
        def update_cursor_label():
            try:
                x, y = get_mouse_pos()
                self.lbl_cur_pos.configure(text=f"📍 Live Mouse Position: X = {x}, Y = {y}")
            except Exception:
                pass
            self.after(50, update_cursor_label)

        self.after(50, update_cursor_label)

    def _register_hotkeys(self):
        """Registers system-wide hotkeys:
           Ctrl + Shift + S: Toggle Start/Stop
        """
        def on_toggle_hotkey():
            self.after(0, self.toggle_clicking)

        try:
            keyboard.add_hotkey("ctrl+shift+s", on_toggle_hotkey, suppress=False)
        except Exception as e:
            print(f"Warning: Could not register global keyboard hotkey: {e}")

    # =========================================================================
    # EXECUTION CONTROLLER: START / STOP
    # =========================================================================
    def toggle_clicking(self):
        if self.is_running:
            self.stop_clicking()
        else:
            self.start_clicking()

    def get_manual_interval_seconds(self):
        try:
            h = float(self.ent_hours.get() or 0)
            m = float(self.ent_mins.get() or 0)
            s = float(self.ent_secs.get() or 0)
            ms = float(self.ent_ms.get() or 0)
            total = (h * 3600) + (m * 60) + s + (ms / 1000.0)
            return max(0.001, total)
        except ValueError:
            return 6.0

    def get_image_scan_interval(self):
        try:
            s = float(self.ent_img_scan_s.get() or 0)
            ms = float(self.ent_img_scan_ms.get() or 0)
            return max(0.05, s + (ms / 1000.0))
        except ValueError:
            return 3.0  # Default 3 seconds

    def get_image_cooldown(self):
        try:
            return max(0.05, float(self.ent_img_cooldown.get() or 1.0))
        except ValueError:
            return 1.0

    def start_clicking(self):
        if self.is_running:
            return

        active_tab = self.tabview.get()

        if active_tab == "🖼️ Image Detection":
            if self.template_image_cv is None:
                self.lbl_status.configure(text="● No Image Selected!", text_color="#ff4757")
                self.lbl_countdown.configure(text="Upload or snip a template image first!", text_color="#f1c40f")
                return

            self.running_mode = "image"
            self.is_running = True
            self.stop_event.clear()
            self.total_clicks_done = 0

            # 🛡️ HIDE PREVIEW IMAGE ON SCAN START (Prevents self-detection)
            self._hide_preview_on_ui()

            # Optional Auto-minimize
            if self.auto_minimize_var.get():
                self.iconify()

            scan_sec = self.get_image_scan_interval()
            method_desc = "Virtual Click" if self.click_method_var.get() == "virtual" else "Flick Click"
            self.lbl_status.configure(text=f"🔍 SCANNING ({method_desc})", text_color="#00cec9")
            self.lbl_countdown.configure(
                text=f"Scanning screen every {int(scan_sec) if scan_sec.is_integer() else scan_sec}s...",
                text_color="#f1c40f"
            )
            self.btn_start_stop.configure(
                text="🛑 STOP (Ctrl + Shift + S)",
                fg_color="#ff4757",
                hover_color="#e04040"
            )
            self.click_thread = threading.Thread(target=self._run_image_click_loop, daemon=True)
            self.click_thread.start()

        else:  # Manual Click mode
            self.running_mode = "manual"
            self.is_running = True
            self.stop_event.clear()
            self.total_clicks_done = 0

            self.lbl_status.configure(text="● RUNNING (Manual)", text_color="#00d26a")
            self.lbl_countdown.configure(text="Starting...", text_color="#f1c40f")
            self.btn_start_stop.configure(
                text="🛑 STOP (Ctrl + Shift + S)",
                fg_color="#ff4757",
                hover_color="#e04040"
            )
            self.click_thread = threading.Thread(target=self._run_manual_click_loop, daemon=True)
            self.click_thread.start()

    def stop_clicking(self):
        if not self.is_running:
            return

        self.is_running = False
        self.stop_event.set()

        # Restore window if minimized
        if self.auto_minimize_var.get():
            self.deiconify()

        # 🛡️ RESTORE PREVIEW IMAGE ON STOP
        self._show_preview_on_ui()

        self.lbl_status.configure(text="● Stopped", text_color="#ff4757")
        self.lbl_countdown.configure(text="")
        self.btn_start_stop.configure(
            text="🚀 START (Ctrl + Shift + S)",
            fg_color="#00b894",
            hover_color="#00a383"
        )

    # =========================================================================
    # MANUAL CLICK LOOP
    # =========================================================================
    def _run_manual_click_loop(self):
        interval = self.get_manual_interval_seconds()
        button = self.opt_button.get()
        click_type = self.opt_type.get()

        try:
            target_x = int(self.ent_x.get())
            target_y = int(self.ent_y.get())
        except ValueError:
            target_x, target_y = get_mouse_pos()

        is_infinite = (self.repeat_mode.get() == "infinite")
        try:
            max_clicks = int(self.ent_repeat_times.get()) if not is_infinite else -1
        except ValueError:
            max_clicks = 50

        clicks_count = 0

        while not self.stop_event.is_set():
            if not is_infinite and clicks_count >= max_clicks:
                break

            set_mouse_pos(target_x, target_y)
            do_click(button, click_type)
            clicks_count += 1
            self.total_clicks_done = clicks_count

            self.after(0, lambda c=clicks_count: (
                self.lbl_stats.configure(text=f"Clicks: {c}"),
                self.lbl_countdown.configure(text="💥 CLICK!", text_color="#00d26a")
            ))

            if not is_infinite and clicks_count >= max_clicks:
                break

            sleep_end = time.perf_counter() + interval
            last_shown = -1
            while time.perf_counter() < sleep_end:
                if self.stop_event.is_set():
                    break
                rem = sleep_end - time.perf_counter()
                if interval >= 1.0:
                    sec = int(rem) + 1
                    if sec != last_shown and rem > 0:
                        last_shown = sec
                        self.after(0, lambda s=sec: self.lbl_countdown.configure(
                            text=f"⏳ Next: {s}s",
                            text_color="#f1c40f"
                        ))
                else:
                    self.after(0, lambda: self.lbl_countdown.configure(
                        text="⚡ Rapid Clicking",
                        text_color="#00cec9"
                    ))
                time.sleep(0.04)

        self.after(0, self._on_click_finished)

    # =========================================================================
    # MULTI-SCALE MATCHING (SMALL & BIG SUBMIT IMAGE SUPPORT)
    # =========================================================================
    def _find_template_multiscale(self, screen_bgr, template, conf_threshold):
        th, tw = template.shape[:2]
        sh, sw = screen_bgr.shape[:2]

        # 1. Fast match check at 1.0x (exact size)
        res = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)

        if max_v >= conf_threshold or not self.multiscale_var.get():
            return max_l, max_v, 1.0, tw, th

        # 2. Multi-scale search for resized (smaller or larger) buttons
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        scales = [0.9, 1.1, 0.8, 1.2, 0.7, 1.3, 0.6, 1.4, 0.5, 1.5]
        best_v = max_v
        best_l = max_l
        best_s = 1.0
        best_w = tw
        best_h = th

        for s in scales:
            cur_w = int(tw * s)
            cur_h = int(th * s)
            if cur_w > sw or cur_h > sh or cur_w < 10 or cur_h < 10:
                continue

            interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
            scaled_tpl = cv2.resize(template_gray, (cur_w, cur_h), interpolation=interp)
            res_s = cv2.matchTemplate(screen_gray, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            _, s_max_v, _, s_max_l = cv2.minMaxLoc(res_s)

            if s_max_v > best_v:
                best_v = s_max_v
                best_l = s_max_l
                best_s = s
                best_w = cur_w
                best_h = cur_h
                if best_v >= conf_threshold:
                    break

        return best_l, best_v, best_s, best_w, best_h

    # =========================================================================
    # IMAGE MATCH CLICK LOOP (WITH DUPLICATE & VIRTUAL CURSOR)
    # =========================================================================
    def _run_image_click_loop(self):
        template = self.template_image_cv
        if template is None:
            self.after(0, self.stop_clicking)
            return

        conf_threshold = float(self.slider_confidence.get()) / 100.0
        scan_interval = self.get_image_scan_interval()
        cooldown = self.get_image_cooldown()
        button = self.opt_img_button.get()
        click_type = self.opt_img_type.get()
        pos_mode = self.opt_img_pos.get()  # "Center" or "Top-Left"
        click_method = self.click_method_var.get()  # "virtual" or "flick"

        mode = self.img_repeat_mode.get()  # "infinite", "once", "count"
        try:
            max_clicks = int(self.ent_img_repeat_times.get()) if mode == "count" else (1 if mode == "once" else -1)
        except ValueError:
            max_clicks = 1

        clicks_count = 0

        while not self.stop_event.is_set():
            if mode != "infinite" and clicks_count >= max_clicks:
                break

            # 1. Capture screen
            screen_pil = self._capture_screen_pil()
            if screen_pil is None:
                time.sleep(scan_interval)
                continue

            grab_w, grab_h = screen_pil.size
            screen_np = np.array(screen_pil)
            screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

            # 🛡️ EXCLUDE AUTO-CLICKER WINDOW FROM SCREEN BUFFER (Self-Click Immunity)
            try:
                sys_w = user32.GetSystemMetrics(0)
                sys_h = user32.GetSystemMetrics(1)
                wx = self.winfo_rootx()
                wy = self.winfo_rooty()
                ww = self.winfo_width()
                wh = self.winfo_height()

                if ww > 0 and wh > 0 and self.state() != "iconic":
                    x1 = max(0, int(wx * (grab_w / sys_w)))
                    y1 = max(0, int(wy * (grab_h / sys_h)))
                    x2 = min(grab_w, int((wx + ww) * (grab_w / sys_w)))
                    y2 = min(grab_h, int((wy + wh) * (grab_h / sys_h)))
                    if x2 > x1 and y2 > y1:
                        screen_bgr[y1:y2, x1:x2] = 0
            except Exception:
                pass

            # 2. Multi-Scale Template Matching (Supports small or big submit image)
            best_l, best_v, matched_scale, matched_w, matched_h = self._find_template_multiscale(
                screen_bgr, template, conf_threshold
            )

            if best_v >= conf_threshold:
                # MATCH FOUND!
                if pos_mode == "Center":
                    match_x = best_l[0] + matched_w // 2
                    match_y = best_l[1] + matched_h // 2
                else:
                    match_x = best_l[0]
                    match_y = best_l[1]

                # Map screen coordinates accurately
                target_x = int(match_x * (sys_w / grab_w))
                target_y = int(match_y * (sys_h / grab_h))

                # 🎯 Show Duplicate Cursor visual ring at target
                if self.show_indicator_var.get():
                    self.after(0, lambda tx=target_x, ty=target_y: self.virtual_cursor.show_at(tx, ty))

                # 🖱️ EXECUTE CLICK ACCORDING TO SELECTED METHOD
                if click_method == "virtual":
                    # 🤖 METHOD 1: BACKGROUND VIRTUAL CLICK (USER'S MOUSE NEVER MOVES AT ALL!)
                    do_background_virtual_click(target_x, target_y, button, click_type)
                    method_tag = "Virtual Click"
                else:
                    # ⚡ METHOD 2: GHOST FLICK & INSTANT RESTORE
                    orig_x, orig_y = get_mouse_pos()
                    set_mouse_pos(target_x, target_y)
                    do_click(button, click_type)
                    time.sleep(0.012)
                    set_mouse_pos(orig_x, orig_y)
                    method_tag = "Flick & Return"

                clicks_count += 1
                self.total_clicks_done = clicks_count

                conf_pct = int(best_v * 100)
                scale_info = f" (Scale {matched_scale:.1f}x)" if matched_scale != 1.0 else ""
                self.after(0, lambda c=clicks_count, tx=target_x, ty=target_y, cp=conf_pct, si=scale_info, mt=method_tag: (
                    self.lbl_stats.configure(text=f"Clicks: {c}"),
                    self.lbl_countdown.configure(
                        text=f"🎯 MATCH {cp}%{si}! {mt} ({tx}, {ty})",
                        text_color="#00d26a"
                    ),
                    self.lbl_status.configure(text="● MATCH FOUND & CLICKED", text_color="#00d26a")
                ))

                if mode != "infinite" and clicks_count >= max_clicks:
                    break

                # Post-click cooldown before scanning again
                sleep_end = time.perf_counter() + cooldown
                while time.perf_counter() < sleep_end and not self.stop_event.is_set():
                    time.sleep(0.04)

            else:
                # NO MATCH -> DO NOT CLICK!
                conf_pct = int(best_v * 100)
                self.after(0, lambda cp=conf_pct: (
                    self.lbl_status.configure(text="● Scanning (Waiting for match)", text_color="#00cec9")
                ))

                # Countdown sleep for the scan interval (Default 3s)
                sleep_end = time.perf_counter() + scan_interval
                last_shown = -1
                while time.perf_counter() < sleep_end and not self.stop_event.is_set():
                    rem = sleep_end - time.perf_counter()
                    sec = int(rem) + 1
                    if scan_interval >= 1.0 and sec != last_shown and rem > 0:
                        last_shown = sec
                        self.after(0, lambda s=sec: self.lbl_countdown.configure(
                            text=f"🔍 Scan in {s}s... (No match yet)",
                            text_color="#f1c40f"
                        ))
                    time.sleep(0.04)

        self.after(0, self._on_click_finished)

    def _on_click_finished(self):
        self.stop_clicking()
        self.lbl_stats.configure(text=f"Clicks: {self.total_clicks_done}")
        self.lbl_countdown.configure(text="Finished", text_color="#00cec9")

    def on_closing(self):
        self.stop_clicking()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = AutoClickerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
