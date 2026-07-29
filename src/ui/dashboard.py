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
    DEFAULT_GPS,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_IOU,
    DEFAULT_MAX_DETECTIONS,
    DEFAULT_SPEED,
    LOGO_PATH,
    SNAPSHOT_PREFIX,
)
from src.ui.components import labelled_value, make_button, make_panel, make_stat_chip, make_switch
from src.ui.theme import COLORS, FONT_BODY, FONT_SECTION, FONT_SMALL, FONT_TITLE


class MainDashboard:
    """Main SignGuard dashboard with real-time detection."""

    def __init__(self, parent_window, detector, speech_service, source, source_name="Camera"):
        self.window = parent_window
        self.detector = detector
        self.speech_service = speech_service
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
        self.total_detection_count = 0

        self.tts_enabled = tk.BooleanVar(value=True)
        self.show_boxes = tk.BooleanVar(value=True)
        self.augment_enabled = tk.BooleanVar(value=False)

        self.window.title(f"{APP_NAME} - Guard Console")
        self.window.configure(bg=COLORS["app_bg"])
        self.create_main_ui()
        self.switch_source(source, source_name)

    def create_main_ui(self):
        self.root_frame = Frame(self.window, bg=COLORS["app_bg"])
        self.root_frame.pack(fill="both", expand=True)

        header = Frame(self.root_frame, bg=COLORS["app_bg"], height=84)
        header.pack(fill="x", padx=28, pady=(20, 10))
        header.pack_propagate(False)

        brand_block = Frame(header, bg=COLORS["app_bg"])
        brand_block.pack(side="left", fill="y")

        self.header_logo = self.load_logo((58, 58))
        if self.header_logo:
            Label(brand_block, image=self.header_logo, bg=COLORS["app_bg"]).pack(side="left", padx=(0, 14), pady=4)

        title_block = Frame(brand_block, bg=COLORS["app_bg"])
        title_block.pack(side="left", fill="y")
        Label(title_block, text=APP_NAME.upper(), font=FONT_TITLE, fg=COLORS["text"], bg=COLORS["app_bg"]).pack(anchor="w")
        Label(
            title_block,
            text=APP_SUBTITLE,
            font=FONT_BODY,
            fg=COLORS["muted"],
            bg=COLORS["app_bg"],
        ).pack(anchor="w", pady=(2, 0))

        status_frame = make_panel(header, bg=COLORS["surface"], border=COLORS["surface_3"])
        status_frame.pack(side="right", padx=(12, 0), pady=10)
        self.status_dot = Canvas(status_frame, width=18, height=18, bg=COLORS["surface"], highlightthickness=0)
        self.status_indicator = self.status_dot.create_oval(4, 4, 14, 14, fill=COLORS["success"], outline="")
        self.status_dot.pack(side="left", padx=(14, 6), pady=10)
        self.status_text = Label(
            status_frame, text="System Active", font=("Segoe UI", 10, "bold"), fg=COLORS["success"], bg=COLORS["surface"]
        )
        self.status_text.pack(side="left", padx=(0, 14))

        content = Frame(self.root_frame, bg=COLORS["app_bg"])
        content.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, minsize=470)
        content.grid_rowconfigure(0, weight=1)

        self.create_video_panel(content)
        self.create_control_panels(content)

    def create_video_panel(self, parent):
        video_shell = make_panel(parent, bg=COLORS["surface"])
        video_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        video_shell.grid_rowconfigure(1, weight=1)
        video_shell.grid_columnconfigure(0, weight=1)

        toolbar = Frame(video_shell, bg=COLORS["surface"])
        toolbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 12))
        Label(toolbar, text="ROAD VISION FEED", font=FONT_SECTION, fg=COLORS["text"], bg=COLORS["surface"]).pack(side="left")
        self.source_label = Label(toolbar, text=self.source_name, font=FONT_SMALL, fg=COLORS["accent"], bg=COLORS["surface"])
        self.source_label.pack(side="right")

        video_stage = Frame(video_shell, bg="#020712", highlightbackground="#20344f", highlightthickness=1)
        video_stage.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        video_stage.grid_rowconfigure(0, weight=1)
        video_stage.grid_columnconfigure(0, weight=1)

        self.video_label = Label(video_stage, bg="#020712")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.set_blank_frame()

        quick_stats = Frame(video_shell, bg=COLORS["surface"])
        quick_stats.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.session_label = make_stat_chip(quick_stats, "SESSION", "00:00")
        self.detection_count_label = make_stat_chip(quick_stats, "DETECTIONS", "0")
        self.last_conf_label = make_stat_chip(quick_stats, "CONFIDENCE", "--")
        self.quality_label = make_stat_chip(quick_stats, "GUARD MODE", "FAST")

    def create_control_panels(self, parent):
        control_frame = Frame(parent, bg=COLORS["app_bg"])
        control_frame.grid(row=0, column=1, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)

        self.create_alert_panel(control_frame)
        self.create_telemetry_panel(control_frame)
        self.create_settings_panel(control_frame)
        self.create_history_panel(control_frame)
        self.create_actions_panel(control_frame)

    def create_alert_panel(self, parent):
        card = make_panel(parent, bg=COLORS["surface"])
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        Label(card, text="GUARD ALERT", font=FONT_SECTION, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=20, pady=(18, 10)
        )
        self.alert_label = Label(
            card,
            text="No sign detected",
            fg=COLORS["text"],
            bg=COLORS["surface_2"],
            font=("Segoe UI", 23, "bold"),
            height=3,
            wraplength=350,
            justify="center",
        )
        self.alert_label.pack(fill="x", padx=20, pady=(0, 12))
        self.desc_label = Label(
            card,
            text="Waiting for road sign input",
            fg=COLORS["muted"],
            bg=COLORS["surface"],
            font=("Segoe UI", 11, "bold"),
        )
        self.desc_label.pack(anchor="w", pady=(0, 18), padx=20)

    def create_telemetry_panel(self, parent):
        card = make_panel(parent, bg=COLORS["surface"])
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        Label(card, text="DRIVE TELEMETRY", font=FONT_SECTION, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=20, pady=(18, 12)
        )
        speed_box = Frame(card, bg=COLORS["surface_2"])
        speed_box.pack(fill="x", padx=20, pady=(0, 16))
        Label(speed_box, text="CURRENT SPEED", font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
            anchor="w", padx=16, pady=(14, 0)
        )
        self.speed_value = Label(
            speed_box, text=f"{DEFAULT_SPEED} km/h", font=("Segoe UI", 26, "bold"), fg=COLORS["accent"], bg=COLORS["surface_2"]
        )
        self.speed_value.pack(anchor="w", padx=16, pady=(0, 4))
        self.speed_slider = tk.Scale(
            speed_box,
            from_=0,
            to=120,
            orient="horizontal",
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            length=340,
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent"],
            sliderrelief="flat",
            showvalue=False,
            command=self.update_speed_label,
        )
        self.speed_slider.set(DEFAULT_SPEED)
        self.speed_slider.pack(fill="x", padx=12, pady=(0, 14))

        info = Frame(card, bg=COLORS["surface"])
        info.pack(fill="x", padx=20, pady=(0, 18))
        self.time_label = labelled_value(info, "Time", "--:--:--")
        self.gps_label = labelled_value(info, "GPS", DEFAULT_GPS)
        self.fps_label = labelled_value(info, "Frame rate", "0 FPS", COLORS["accent"])

    def create_settings_panel(self, parent):
        card = make_panel(parent, bg=COLORS["surface"])
        card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        Label(card, text="VISION TUNING", font=FONT_SECTION, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=20, pady=(16, 10)
        )
        threshold_box = Frame(card, bg=COLORS["surface"])
        threshold_box.pack(fill="x", padx=20, pady=(0, 12))
        self.threshold_label = Label(
            threshold_box,
            text=f"Minimum confidence: {int(DEFAULT_CONFIDENCE * 100)}%",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
        )
        self.threshold_label.pack(anchor="w")
        self.confidence_slider = tk.Scale(
            threshold_box,
            from_=25,
            to=90,
            orient="horizontal",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            length=360,
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent_2"],
            sliderrelief="flat",
            showvalue=False,
            command=self.update_threshold_label,
        )
        self.confidence_slider.set(int(DEFAULT_CONFIDENCE * 100))
        self.confidence_slider.pack(fill="x")

        self.iou_label = Label(
            threshold_box,
            text=f"IoU threshold: {int(DEFAULT_IOU * 100)}%",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
        )
        self.iou_label.pack(anchor="w", pady=(8, 0))
        self.iou_slider = tk.Scale(
            threshold_box,
            from_=30,
            to=80,
            orient="horizontal",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            length=360,
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent_2"],
            sliderrelief="flat",
            showvalue=False,
            command=self.update_iou_label,
        )
        self.iou_slider.set(int(DEFAULT_IOU * 100))
        self.iou_slider.pack(fill="x")

        self.image_size_label = Label(
            threshold_box,
            text=f"Inference image size: {DEFAULT_IMAGE_SIZE}",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
        )
        self.image_size_label.pack(anchor="w", pady=(8, 0))
        self.image_size_slider = tk.Scale(
            threshold_box,
            from_=320,
            to=960,
            resolution=32,
            orient="horizontal",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            length=360,
            highlightthickness=0,
            troughcolor=COLORS["line"],
            activebackground=COLORS["accent_2"],
            sliderrelief="flat",
            showvalue=False,
            command=self.update_image_size_label,
        )
        self.image_size_slider.set(DEFAULT_IMAGE_SIZE)
        self.image_size_slider.pack(fill="x")

        make_switch(card, "Voice alerts", self.tts_enabled, self.update_tts_state).pack(fill="x", padx=20, pady=(0, 6))
        make_switch(card, "Draw detection boxes", self.show_boxes, lambda: None).pack(fill="x", padx=20, pady=(0, 6))
        make_switch(card, "Accuracy mode (TTA)", self.augment_enabled, self.update_quality_mode).pack(
            fill="x", padx=20, pady=(0, 14)
        )

    def create_history_panel(self, parent):
        card = make_panel(parent, bg=COLORS["surface"])
        card.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        parent.grid_rowconfigure(3, weight=1)
        Label(card, text="SIGNGUARD LOG", font=FONT_SECTION, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=20, pady=(16, 10)
        )
        self.history_list = Listbox(
            card,
            bg=COLORS["surface_2"],
            fg=COLORS["text"],
            selectbackground=COLORS["surface_3"],
            selectforeground=COLORS["white"],
            highlightthickness=0,
            bd=0,
            height=6,
            font=("Consolas", 9),
        )
        self.history_list.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        make_button(card, "CLEAR LOG", self.clear_history, "ghost").pack(fill="x", padx=20, pady=(0, 16))

    def create_actions_panel(self, parent):
        card = make_panel(parent, bg=COLORS["surface"])
        card.grid(row=4, column=0, sticky="ew")
        Label(card, text="GUARD CONTROLS", font=FONT_SECTION, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=20, pady=(18, 12)
        )
        actions = Frame(card, bg=COLORS["surface"])
        actions.pack(fill="x", padx=20, pady=(0, 20))
        self.pause_button = make_button(actions, "PAUSE STREAM", self.toggle_pause, "primary")
        self.pause_button.pack(fill="x", pady=(0, 10))
        make_button(actions, "SAVE ROAD SNAPSHOT", self.save_snapshot, "secondary").pack(fill="x", pady=(0, 10))
        make_button(actions, "EXPORT GUARD LOG", self.export_history, "secondary").pack(fill="x", pady=(0, 10))
        make_button(actions, "SWITCH TO CAMERA", self.switch_to_camera, "secondary").pack(fill="x", pady=(0, 10))
        make_button(actions, "SCAN ANOTHER VIDEO", self.switch_to_video, "secondary").pack(fill="x", pady=(0, 10))
        make_button(actions, "STOP STREAM", self.stop_stream, "danger").pack(fill="x")

    def set_blank_frame(self):
        black_img = Image.new("RGB", (1024, 576), color=(2, 7, 18))
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

    def clear_history(self):
        self.history_list.delete(0, tk.END)
        self.total_detection_count = 0
        self.detection_count_label.config(text="0")

    def export_history(self):
        if self.history_list.size() == 0:
            self.desc_label.config(text="No detection history to export", fg=COLORS["warning"])
            return
        default_name = f"signguard_lk_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV File", "*.csv")],
        )
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as history_file:
            history_file.write("time,confidence,threat,message\n")
            for item in reversed(self.history_list.get(0, tk.END)):
                parts = item.split(None, 3)
                if len(parts) == 4:
                    history_file.write(f"{parts[0]},{parts[1]},{parts[2]},{parts[3]}\n")
        self.desc_label.config(text="Detection history exported", fg=COLORS["success"])

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
        self.detection_count_label.config(text=str(self.total_detection_count))

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
        self.alert_label.config(text=text, bg=bg_color, fg=fg_color)
        self.desc_label.config(text=description, fg=bg_color if state != "idle" else COLORS["muted"])

    def update_frame(self):
        if not self.root_frame.winfo_exists():
            return
        if not self.is_streaming:
            self.window.after(50, self.update_frame)
            return

        self.update_session_metrics()

        if self.is_paused:
            self.window.after(100, self.update_frame)
            return

        ret, frame = self.cap.read()
        if not ret:
            self.window.after(30, self.update_frame)
            return

        self.update_clock_and_fps()
        current_speed = self.speed_slider.get()
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
        cv2.putText(frame, f"GPS    {DEFAULT_GPS}", (36, 130), cv2.FONT_HERSHEY_DUPLEX, 0.62, (238, 245, 255), 1)
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

    def destroy(self):
        self.release_capture()
        self.root_frame.destroy()
