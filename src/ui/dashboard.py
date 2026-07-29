import datetime
import time
import tkinter as tk
from tkinter import Canvas, Frame, Label, Listbox, filedialog

import cv2
from PIL import Image, ImageTk

from src.config.settings import (
    APP_NAME,
    APP_SUBTITLE,
    DEFAULT_CONFIDENCE,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_IOU,
    DEFAULT_MAX_DETECTIONS,
    DEFAULT_SPEED,
    LOGO_PATH,
    SNAPSHOT_PREFIX,
)
from src.services.report_service import ReportService
from src.ui.components import make_button, make_panel, make_switch
from src.ui.theme import COLORS, FONT_BODY, FONT_SECTION, FONT_SMALL, FONT_TITLE


class MainDashboard:
    """Main SignGuard dashboard with real-time detection."""

    def __init__(self, parent_window, detector, speech_service, location_service, source, source_name="Camera"):
        self.window = parent_window
        self.detector = detector
        self.speech_service = speech_service
        self.location_service = location_service
        self.source_name = source_name
        self.cap = None
        self.is_streaming = False
        self.is_paused = False

        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.session_start = time.time()
        self.last_spoken_sign = None
        self.last_spoken_time = 0
        self.last_frame = None
        self.current_alert_text = "No sign detected"

        self.total_detection_count = 0
        self.session_events = []
        self.critical_count = 0
        self.warning_count = 0
        self.safe_count = 0

        self.tts_enabled = tk.BooleanVar(value=True)
        self.show_boxes = tk.BooleanVar(value=True)
        self.augment_enabled = tk.BooleanVar(value=False)
        self.use_live_speed = tk.BooleanVar(value=True)
        self.active_tab = None
        self.tab_buttons = {}

        self.window.title(f"{APP_NAME} - Guard Console")
        self.window.configure(bg=COLORS["app_bg"])
        self.create_main_ui()
        self.switch_source(source, source_name)

    def create_main_ui(self):
        self.root_frame = Frame(self.window, bg=COLORS["app_bg"])
        self.root_frame.pack(fill="both", expand=True)

        self.create_header()

        content = Frame(self.root_frame, bg=COLORS["app_bg"])
        content.pack(fill="both", expand=True, padx=24, pady=(0, 22))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, minsize=430)
        content.grid_rowconfigure(0, weight=1)

        self.create_video_panel(content)
        self.create_side_panel(content)

    def create_header(self):
        header = Frame(self.root_frame, bg=COLORS["app_bg"], height=76)
        header.pack(fill="x", padx=24, pady=(18, 10))
        header.pack_propagate(False)

        brand = Frame(header, bg=COLORS["app_bg"])
        brand.pack(side="left", fill="y")
        self.header_logo = self.load_logo((52, 52))
        if self.header_logo:
            Label(brand, image=self.header_logo, bg=COLORS["app_bg"]).pack(side="left", padx=(0, 12), pady=3)

        title = Frame(brand, bg=COLORS["app_bg"])
        title.pack(side="left", fill="y")
        Label(title, text=APP_NAME.upper(), font=FONT_TITLE, fg=COLORS["text"], bg=COLORS["app_bg"]).pack(anchor="w")
        Label(title, text=APP_SUBTITLE, font=FONT_BODY, fg=COLORS["muted"], bg=COLORS["app_bg"]).pack(anchor="w")

        self.status_pill = make_panel(header, bg=COLORS["surface"], border=COLORS["surface_3"])
        self.status_pill.pack(side="right", pady=8)
        self.status_dot = Canvas(self.status_pill, width=18, height=18, bg=COLORS["surface"], highlightthickness=0)
        self.status_indicator = self.status_dot.create_oval(4, 4, 14, 14, fill=COLORS["success"], outline="")
        self.status_dot.pack(side="left", padx=(14, 6), pady=10)
        self.status_text = Label(
            self.status_pill,
            text="System Active",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["success"],
            bg=COLORS["surface"],
        )
        self.status_text.pack(side="left", padx=(0, 14))

    def create_video_panel(self, parent):
        shell = make_panel(parent, bg=COLORS["surface"], border=COLORS["line"])
        shell.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        top = Frame(shell, bg=COLORS["surface"])
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        Label(top, text="ROAD VISION", font=("Segoe UI", 13, "bold"), fg=COLORS["text"], bg=COLORS["surface"]).pack(
            side="left"
        )
        self.source_label = Label(top, text=self.source_name, font=FONT_SMALL, fg=COLORS["accent"], bg=COLORS["surface"])
        self.source_label.pack(side="right")

        stage = Frame(shell, bg="#020506", highlightbackground="#32474c", highlightthickness=1)
        stage.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        stage.grid_columnconfigure(0, weight=1)
        stage.grid_rowconfigure(0, weight=1)

        self.video_label = Label(stage, bg="#020506")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.set_blank_frame()

        stats = Frame(shell, bg=COLORS["surface"])
        stats.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        for column in range(4):
            stats.grid_columnconfigure(column, weight=1)
        self.session_label = self.create_metric(stats, 0, "SESSION", "00:00", COLORS["text"])
        self.detection_count_label = self.create_metric(stats, 1, "DETECTIONS", "0", COLORS["accent"])
        self.last_conf_label = self.create_metric(stats, 2, "CONFIDENCE", "--", COLORS["accent_2"])
        self.quality_label = self.create_metric(stats, 3, "MODE", "FAST", COLORS["success"])

    def create_metric(self, parent, column, label_text, value_text, color):
        box = Frame(parent, bg=COLORS["surface_2"], highlightbackground=COLORS["surface_3"], highlightthickness=1)
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        Label(box, text=label_text, font=("Segoe UI", 8, "bold"), fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
            anchor="w", padx=12, pady=(9, 0)
        )
        value = Label(box, text=value_text, font=("Segoe UI", 15, "bold"), fg=color, bg=COLORS["surface_2"])
        value.pack(anchor="w", padx=12, pady=(0, 9))
        return value

    def create_side_panel(self, parent):
        side = Frame(parent, bg=COLORS["app_bg"])
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)

        self.create_alert_card(side)
        self.create_tab_bar(side)

        self.tab_host = make_panel(side, bg=COLORS["surface"], border=COLORS["line"])
        self.tab_host.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        self.tab_host.grid_columnconfigure(0, weight=1)
        self.tab_host.grid_rowconfigure(0, weight=1)

        self.tabs = {
            "Drive": self.create_drive_tab(),
            "Tune": self.create_tune_tab(),
            "Log": self.create_log_tab(),
            "Reports": self.create_reports_tab(),
        }
        self.show_tab("Drive")

    def create_alert_card(self, parent):
        card = make_panel(parent, bg=COLORS["surface"], border=COLORS["line"])
        card.grid(row=0, column=0, sticky="ew")
        Label(card, text="CURRENT GUARD ALERT", font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=18, pady=(16, 8)
        )
        self.alert_label = Label(
            card,
            text="No sign detected",
            fg=COLORS["text"],
            bg=COLORS["surface_2"],
            font=("Segoe UI", 21, "bold"),
            height=3,
            wraplength=360,
            justify="center",
        )
        self.alert_label.pack(fill="x", padx=18, pady=(0, 10))
        self.desc_label = Label(
            card,
            text="Waiting for road sign input",
            fg=COLORS["muted"],
            bg=COLORS["surface"],
            font=("Segoe UI", 10, "bold"),
        )
        self.desc_label.pack(anchor="w", padx=18, pady=(0, 16))

    def create_tab_bar(self, parent):
        bar = Frame(parent, bg=COLORS["app_bg"])
        bar.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            bar.grid_columnconfigure(column, weight=1)
        for index, name in enumerate(["Drive", "Tune", "Log", "Reports"]):
            button = tk.Button(
                bar,
                text=name.upper(),
                command=lambda tab=name: self.show_tab(tab),
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=10,
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))
            self.tab_buttons[name] = button

    def create_drive_tab(self):
        frame = Frame(self.tab_host, bg=COLORS["surface"])
        self.create_section_title(frame, "Drive Telemetry")

        speed_box = Frame(frame, bg=COLORS["surface_2"])
        speed_box.pack(fill="x", padx=18, pady=(0, 14))
        Label(speed_box, text="CURRENT SPEED", font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
            anchor="w", padx=16, pady=(14, 0)
        )
        self.speed_value = Label(
            speed_box,
            text=f"{DEFAULT_SPEED} km/h",
            font=("Segoe UI", 30, "bold"),
            fg=COLORS["accent"],
            bg=COLORS["surface_2"],
        )
        self.speed_value.pack(anchor="w", padx=16, pady=(0, 2))
        self.speed_slider = tk.Scale(
            speed_box,
            from_=0,
            to=120,
            orient="horizontal",
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent"],
            sliderrelief="flat",
            showvalue=False,
            command=self.update_speed_label,
        )
        self.speed_slider.set(DEFAULT_SPEED)
        self.speed_slider.pack(fill="x", padx=12, pady=(0, 14))

        grid = Frame(frame, bg=COLORS["surface"])
        grid.pack(fill="x", padx=18, pady=(0, 14))
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        self.time_label = self.create_info_tile(grid, 0, 0, "Time", "--:--:--", COLORS["accent_2"])
        self.gps_label = self.create_info_tile(grid, 0, 1, "GPS", "Acquiring...", COLORS["text"])
        self.fps_label = self.create_info_tile(grid, 1, 0, "Frame Rate", "0 FPS", COLORS["accent"])
        self.source_tile = self.create_info_tile(grid, 1, 1, "Input", self.source_name, COLORS["text"])

        self.pause_button = make_button(frame, "PAUSE STREAM", self.toggle_pause, "primary")
        self.pause_button.pack(fill="x", padx=18, pady=(0, 10))
        make_button(frame, "STOP STREAM", self.stop_stream, "danger").pack(fill="x", padx=18, pady=(0, 18))
        return frame

    def create_tune_tab(self):
        frame = Frame(self.tab_host, bg=COLORS["surface"])
        self.create_section_title(frame, "Vision Tuning")

        self.threshold_label = self.create_slider(
            frame,
            "Minimum confidence",
            25,
            90,
            int(DEFAULT_CONFIDENCE * 100),
            self.update_threshold_label,
        )
        self.iou_label = self.create_slider(frame, "IoU threshold", 30, 80, int(DEFAULT_IOU * 100), self.update_iou_label)
        self.image_size_label = self.create_slider(
            frame,
            "Inference image size",
            320,
            960,
            DEFAULT_IMAGE_SIZE,
            self.update_image_size_label,
            resolution=32,
        )

        switches = Frame(frame, bg=COLORS["surface"])
        switches.pack(fill="x", padx=18, pady=(4, 14))
        make_switch(switches, "Voice alerts", self.tts_enabled, self.update_tts_state).pack(fill="x", pady=3)
        make_switch(switches, "Draw detection boxes", self.show_boxes, lambda: None).pack(fill="x", pady=3)
        make_switch(switches, "Accuracy mode (TTA)", self.augment_enabled, self.update_quality_mode).pack(fill="x", pady=3)
        make_switch(switches, "Use live GPS speed", self.use_live_speed, self.update_speed_source_state).pack(fill="x", pady=3)
        return frame

    def create_log_tab(self):
        frame = Frame(self.tab_host, bg=COLORS["surface"])
        self.create_section_title(frame, "SignGuard Log")

        counts = Frame(frame, bg=COLORS["surface"])
        counts.pack(fill="x", padx=18, pady=(0, 12))
        for column in range(3):
            counts.grid_columnconfigure(column, weight=1)
        self.critical_label = self.create_metric(counts, 0, "CRITICAL", "0", COLORS["danger"])
        self.warning_label = self.create_metric(counts, 1, "WARNING", "0", COLORS["warning"])
        self.safe_label = self.create_metric(counts, 2, "SAFE", "0", COLORS["success"])

        self.history_list = Listbox(
            frame,
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            selectbackground=COLORS["surface_3"],
            selectforeground=COLORS["white"],
            highlightthickness=0,
            bd=0,
            height=12,
            font=("Consolas", 9),
        )
        self.history_list.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        make_button(frame, "CLEAR LOG", self.clear_history, "ghost").pack(fill="x", padx=18, pady=(0, 18))
        return frame

    def create_reports_tab(self):
        frame = Frame(self.tab_host, bg=COLORS["surface"])
        self.create_section_title(frame, "Reports & Evidence")

        actions = [
            ("ROAD SNAPSHOT", self.save_snapshot),
            ("CAPTURE INCIDENT", self.capture_incident),
            ("EXPORT CSV LOG", self.export_history),
            ("DOWNLOAD HTML REPORT", self.export_html_report),
            ("DOWNLOAD TXT REPORT", self.export_text_report),
            ("SWITCH TO CAMERA", self.switch_to_camera),
            ("SCAN VIDEO FILE", self.switch_to_video),
        ]
        for label, command in actions:
            make_button(frame, label, command, "secondary").pack(fill="x", padx=18, pady=(0, 10))
        return frame

    def create_section_title(self, parent, text):
        Label(parent, text=text.upper(), font=FONT_SECTION, fg=COLORS["text"], bg=COLORS["surface"]).pack(
            anchor="w", padx=18, pady=(18, 12)
        )

    def create_info_tile(self, parent, row, column, label_text, value_text, color):
        tile = Frame(parent, bg=COLORS["surface_2"], highlightbackground=COLORS["surface_3"], highlightthickness=1)
        tile.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0), pady=(0, 8))
        Label(tile, text=label_text.upper(), font=("Segoe UI", 8, "bold"), fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
            anchor="w", padx=12, pady=(9, 0)
        )
        value = Label(tile, text=value_text, font=("Segoe UI", 12, "bold"), fg=color, bg=COLORS["surface_2"], wraplength=160)
        value.pack(anchor="w", padx=12, pady=(0, 10))
        return value

    def create_slider(self, parent, label_text, start, end, value, command, resolution=1):
        box = Frame(parent, bg=COLORS["surface"])
        box.pack(fill="x", padx=18, pady=(0, 12))
        label = Label(
            box,
            text=f"{label_text}: {value}",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
        )
        label.pack(anchor="w")
        slider = tk.Scale(
            box,
            from_=start,
            to=end,
            resolution=resolution,
            orient="horizontal",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent_2"],
            sliderrelief="flat",
            showvalue=False,
            command=command,
        )
        slider.set(value)
        slider.pack(fill="x")
        if "confidence" in label_text.lower():
            self.confidence_slider = slider
        elif "iou" in label_text.lower():
            self.iou_slider = slider
        else:
            self.image_size_slider = slider
        return label

    def show_tab(self, name):
        for tab in getattr(self, "tabs", {}).values():
            tab.grid_forget()
        self.tabs[name].grid(row=0, column=0, sticky="nsew")
        self.active_tab = name
        for tab_name, button in self.tab_buttons.items():
            active = tab_name == name
            button.config(
                bg=COLORS["accent"] if active else COLORS["surface_2"],
                activebackground=COLORS["accent"] if active else COLORS["surface_3"],
                fg="#061412" if active else COLORS["muted"],
                activeforeground="#061412" if active else COLORS["text"],
            )

    def set_blank_frame(self):
        black_img = Image.new("RGB", (1024, 576), color=(2, 5, 6))
        img = ImageTk.PhotoImage(black_img)
        self.video_label.imgtk = img
        self.video_label.config(image=img)

    def load_logo(self, size):
        if not LOGO_PATH.exists():
            return None
        try:
            image = Image.open(LOGO_PATH).convert("RGB")
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception as exc:
            print(f"Logo load error: {exc}")
            return None

    def update_speed_label(self, value):
        self.speed_value.config(text=f"{int(float(value))} km/h")

    def update_threshold_label(self, value):
        self.threshold_label.config(text=f"Minimum confidence: {int(float(value))}%")

    def update_iou_label(self, value):
        self.iou_label.config(text=f"IoU threshold: {int(float(value))}%")

    def update_image_size_label(self, value):
        self.image_size_label.config(text=f"Inference image size: {int(float(value))}")

    def update_quality_mode(self):
        if self.augment_enabled.get():
            self.quality_label.config(text="ACCURACY")
            self.desc_label.config(text="Accuracy mode enabled; FPS may be lower", fg=COLORS["accent"])
        else:
            self.quality_label.config(text="FAST")
            self.desc_label.config(text="Fast mode enabled", fg=COLORS["muted"])

    def update_tts_state(self):
        enabled = self.tts_enabled.get()
        self.speech_service.set_enabled(enabled)
        state = "enabled" if enabled else "muted"
        self.desc_label.config(text=f"Voice alerts {state}", fg=COLORS["accent"] if enabled else COLORS["muted"])

    def update_speed_source_state(self):
        if self.use_live_speed.get():
            self.desc_label.config(text="Using live GPS speed when available", fg=COLORS["accent"])
        else:
            self.desc_label.config(text="Using manual speed slider", fg=COLORS["muted"])

    def clear_history(self):
        self.history_list.delete(0, tk.END)
        self.total_detection_count = 0
        self.session_events.clear()
        self.critical_count = 0
        self.warning_count = 0
        self.safe_count = 0
        self.detection_count_label.config(text="0")
        self.critical_label.config(text="0")
        self.warning_label.config(text="0")
        self.safe_label.config(text="0")

    def export_history(self):
        if not self.session_events:
            self.desc_label.config(text="No detection history to export", fg=COLORS["warning"])
            return
        default_name = f"signguard_lk_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV File", "*.csv")],
        )
        if file_path:
            ReportService.export_csv(file_path, self.session_events)
            self.desc_label.config(text="Detection history exported", fg=COLORS["success"])

    def export_html_report(self):
        self.export_session_report("html")

    def export_text_report(self):
        self.export_session_report("txt")

    def export_session_report(self, file_type):
        if not self.session_events:
            self.desc_label.config(text="No detections available for report", fg=COLORS["warning"])
            return
        default_name = f"signguard_lk_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_type}"
        filetypes = [("HTML Report", "*.html")] if file_type == "html" else [("Text Report", "*.txt")]
        file_path = filedialog.asksaveasfilename(defaultextension=f".{file_type}", initialfile=default_name, filetypes=filetypes)
        if not file_path:
            return
        summary = ReportService.build_summary(
            self.session_events,
            self.session_start,
            time.time(),
            self.source_name,
            self.get_runtime_settings(),
        )
        if file_type == "html":
            ReportService.export_html(file_path, summary, self.session_events)
        else:
            ReportService.export_text(file_path, summary, self.session_events)
        self.desc_label.config(text=f"{file_type.upper()} report downloaded", fg=COLORS["success"])

    def capture_incident(self):
        if self.last_frame is None:
            self.desc_label.config(text="No frame available for incident capture", fg=COLORS["warning"])
            return
        default_name = f"signguard_lk_incident_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=default_name,
            filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png")],
        )
        if not file_path:
            return
        incident_frame = self.last_frame.copy()
        cv2.rectangle(incident_frame, (0, 0), (1024, 52), (15, 26, 29), -1)
        cv2.putText(
            incident_frame,
            f"INCIDENT: {self.current_alert_text}",
            (18, 34),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (45, 212, 191),
            1,
        )
        cv2.imwrite(file_path, incident_frame)
        self.desc_label.config(text="Incident snapshot captured", fg=COLORS["success"])

    def save_snapshot(self):
        if self.last_frame is None:
            self.desc_label.config(text="No frame available to save", fg=COLORS["warning"])
            return
        default_name = f"{SNAPSHOT_PREFIX}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=default_name,
            filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png")],
        )
        if file_path:
            cv2.imwrite(file_path, self.last_frame)
            self.desc_label.config(text="Snapshot saved", fg=COLORS["success"])

    def add_history_item(self, event):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        text = f"{stamp}  {event.confidence * 100:>3.0f}%  {event.threat_level[:8]:<8}  {event.display_name}"
        existing_first = self.history_list.get(0) if self.history_list.size() else ""
        if text[:22] == existing_first[:22]:
            return
        self.history_list.insert(0, text)
        while self.history_list.size() > 12:
            self.history_list.delete(tk.END)
        self.total_detection_count += 1
        self.session_events.append(self.build_event_record(event, stamp))
        self.update_threat_counts(event.threat_level)
        self.detection_count_label.config(text=str(self.total_detection_count))

    def build_event_record(self, event, stamp):
        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d") + f" {stamp}",
            "source": self.source_name,
            "speed": int(self.get_current_speed()),
            "class_name": event.class_name,
            "label": event.label,
            "message": event.display_name,
            "threat": event.threat_level,
            "confidence": round(event.confidence * 100, 2),
            "description": event.description,
        }

    def update_threat_counts(self, threat_level):
        if threat_level == "CRITICAL":
            self.critical_count += 1
            self.critical_label.config(text=str(self.critical_count))
        elif threat_level == "MODERATE":
            self.warning_count += 1
            self.warning_label.config(text=str(self.warning_count))
        elif threat_level == "SAFE":
            self.safe_count += 1
            self.safe_label.config(text=str(self.safe_count))

    def get_runtime_settings(self):
        return {
            "confidence_threshold": f"{self.confidence_slider.get()}%",
            "iou_threshold": f"{self.iou_slider.get()}%",
            "image_size": int(self.image_size_slider.get()),
            "accuracy_mode": "on" if self.augment_enabled.get() else "off",
            "speed_source": "live GPS" if self.use_live_speed.get() else "manual slider",
            "voice_alerts": "on" if self.tts_enabled.get() else "off",
            "draw_boxes": "on" if self.show_boxes.get() else "off",
        }

    def update_session_metrics(self):
        elapsed = int(time.time() - self.session_start)
        minutes, seconds = divmod(elapsed, 60)
        self.session_label.config(text=f"{minutes:02d}:{seconds:02d}")

    def switch_source(self, source, source_name):
        self.release_capture()
        self.cap = cv2.VideoCapture(source)
        self.is_streaming = self.cap.isOpened()
        self.is_paused = False
        self.pause_button.config(text="PAUSE STREAM")
        self.source_name = source_name
        self.source_label.config(text=source_name)
        self.source_tile.config(text=source_name)
        self.session_start = time.time()
        if self.is_streaming:
            self.set_status("System Active", "success")
        else:
            self.set_status("Input unavailable", "danger")

    def switch_to_camera(self):
        self.switch_source(0, "Camera")

    def switch_to_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
        if file_path:
            self.switch_source(file_path, "Video file")

    def stop_stream(self):
        self.is_streaming = False
        self.is_paused = False
        self.pause_button.config(text="PAUSE STREAM")
        self.release_capture()
        self.set_alert_state("Stream stopped", "Select a new input source to continue", "idle")
        self.set_status("Stream stopped", "warning")

    def toggle_pause(self):
        if not self.is_streaming:
            return
        self.is_paused = not self.is_paused
        self.pause_button.config(text="RESUME STREAM" if self.is_paused else "PAUSE STREAM")
        self.set_status("Stream Paused" if self.is_paused else "System Active", "warning" if self.is_paused else "success")

    def set_status(self, text, state):
        color = COLORS[state]
        self.status_text.config(text=text, fg=color)
        self.status_dot.itemconfig(self.status_indicator, fill=color)

    def set_alert_state(self, text, description, state):
        palette = {
            "critical": (COLORS["danger"], COLORS["white"]),
            "warning": (COLORS["warning"], COLORS["white"]),
            "safe": (COLORS["success"], COLORS["white"]),
            "idle": (COLORS["surface_2"], COLORS["text"]),
        }
        bg_color, fg_color = palette[state]
        self.current_alert_text = text
        self.alert_label.config(text=text, bg=bg_color, fg=fg_color)
        self.desc_label.config(text=description, fg=bg_color if state != "idle" else COLORS["muted"])

    def update_frame(self):
        if not self.root_frame.winfo_exists():
            return
        if not self.is_streaming:
            self.window.after(50, self.update_frame)
            return

        self.update_session_metrics()
        self.update_location_display()

        if self.is_paused:
            self.window.after(100, self.update_frame)
            return

        ret, frame = self.cap.read()
        if not ret:
            self.window.after(30, self.update_frame)
            return

        self.update_clock_and_fps()
        current_speed = self.get_current_speed()
        minimum_confidence = self.confidence_slider.get() / 100
        iou_threshold = self.iou_slider.get() / 100
        image_size = int(self.image_size_slider.get())
        frame = self.draw_hud(frame, current_speed)
        events = self.detector.detect(
            frame,
            current_speed,
            minimum_confidence,
            iou_threshold=iou_threshold,
            image_size=image_size,
            max_detections=DEFAULT_MAX_DETECTIONS,
            augment=self.augment_enabled.get(),
        )

        for event in events:
            if self.show_boxes.get():
                self.draw_detection_box(frame, event)
            self.set_alert_state(event.display_name, event.description, event.state)
            self.last_conf_label.config(text=f"{event.confidence * 100:.0f}%")
            self.add_history_item(event)
            self.speak_event(event)

        if not events:
            self.set_alert_state("No sign detected", "Waiting for road sign input", "idle")
            self.last_conf_label.config(text="--")

        self.render_frame(frame)
        self.window.after(10, self.update_frame)

    def update_clock_and_fps(self):
        self.time_label.config(text=datetime.datetime.now().strftime("%H:%M:%S"))
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_time >= 1:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            self.fps_label.config(text=f"{self.fps} FPS")

    def draw_hud(self, frame, current_speed):
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (400, 172), (7, 17, 31), -1)
        frame = cv2.addWeighted(overlay, 0.72, frame, 0.28, 0)
        cv2.rectangle(frame, (20, 20), (400, 28), (45, 212, 191), -1)

        current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"TIME   {current_time_str}", (36, 58), cv2.FONT_HERSHEY_DUPLEX, 0.62, (238, 245, 255), 1)
        cv2.putText(frame, f"SPEED  {current_speed} km/h", (36, 94), cv2.FONT_HERSHEY_DUPLEX, 0.62, (45, 212, 191), 1)
        cv2.putText(frame, f"GPS    {self.gps_label.cget('text')}", (36, 130), cv2.FONT_HERSHEY_DUPLEX, 0.62, (238, 245, 255), 1)
        cv2.putText(frame, f"FPS    {self.fps}", (36, 166), cv2.FONT_HERSHEY_DUPLEX, 0.62, (96, 165, 250), 1)
        return frame

    def draw_detection_box(self, frame, event):
        x1, y1, x2, y2 = event.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), event.box_color, 2)
        label_text = f"{event.display_name} {event.confidence * 100:.0f}%"
        (width, _), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)
        cv2.rectangle(frame, (x1, y1 - 35), (x1 + width + 10, y1), event.box_color, -1)
        cv2.putText(frame, label_text, (x1 + 5, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

    def speak_event(self, event):
        current_time = time.time()
        if event.display_name != self.last_spoken_sign or (current_time - self.last_spoken_time) > 4:
            self.last_spoken_sign = event.display_name
            self.last_spoken_time = current_time
            self.speech_service.speak_async(event.display_name)

    def render_frame(self, frame):
        frame = cv2.resize(frame, (1024, 576))
        self.last_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.video_label.imgtk = img
        self.video_label.config(image=img)

    def release_capture(self):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def get_current_speed(self):
        reading = self.location_service.get_reading()
        if self.use_live_speed.get() and reading.speed_kmh is not None:
            speed = int(round(reading.speed_kmh))
            self.speed_value.config(text=f"{speed} km/h")
            return speed
        return self.speed_slider.get()

    def update_location_display(self):
        reading = self.location_service.get_reading()
        if reading.latitude is not None and reading.longitude is not None:
            gps_text = f"{reading.latitude:.5f}, {reading.longitude:.5f}"
            if reading.source != "GPS":
                gps_text += " approx"
            self.gps_label.config(text=gps_text)
        else:
            self.gps_label.config(text=reading.status or "GPS unavailable")

    def destroy(self):
        self.release_capture()
        self.root_frame.destroy()
