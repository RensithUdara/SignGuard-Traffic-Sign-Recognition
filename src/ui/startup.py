import math
import time
from tkinter import Canvas, Frame, Label, filedialog

from src.config.settings import APP_NAME, APP_SUBTITLE, APP_TAGLINE
from src.ui.components import make_button, make_panel
from src.ui.theme import COLORS, FONT_SMALL


class StartupScreen:
    """Landing screen for choosing live camera or video input."""

    def __init__(self, parent_window, start_callback):
        self.window = parent_window
        self.start_callback = start_callback
        self.frame = Frame(self.window, bg=COLORS["app_bg"])
        self.frame.pack(fill="both", expand=True)
        self.loading_index = 0
        self.loading_chars = ["|", "/", "-", "\\"]
        self.create_ui()
        self.animate_logo()

    def create_ui(self):
        shell = Frame(self.frame, bg=COLORS["app_bg"])
        shell.pack(fill="both", expand=True, padx=44, pady=36)

        topbar = Frame(shell, bg=COLORS["app_bg"])
        topbar.pack(fill="x")
        Label(
            topbar,
            text=APP_NAME.upper(),
            font=("Segoe UI", 11, "bold"),
            fg=COLORS["accent"],
            bg=COLORS["app_bg"],
        ).pack(side="left")
        Label(topbar, text="ROAD SAFETY VISION CONSOLE", font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["app_bg"]).pack(
            side="right"
        )

        body = Frame(shell, bg=COLORS["app_bg"])
        body.pack(fill="both", expand=True, pady=(34, 0))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        hero = make_panel(body, bg="#101719", border="#40555a")
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_rowconfigure(1, weight=1)

        hero_top = Frame(hero, bg="#101719")
        hero_top.grid(row=0, column=0, sticky="ew", padx=34, pady=(30, 0))
        Label(hero_top, text="INTELLIGENT ROAD GUARD", font=FONT_SMALL, fg=COLORS["accent_2"], bg="#101719").pack(anchor="w")
        Label(
            hero_top,
            text=APP_NAME,
            font=("Segoe UI", 36, "bold"),
            fg=COLORS["text"],
            bg="#101719",
        ).pack(anchor="w", pady=(6, 2))
        Label(
            hero_top,
            text=APP_TAGLINE,
            font=("Segoe UI", 13),
            fg=COLORS["muted"],
            bg="#101719",
        ).pack(anchor="w")

        self.logo_canvas = Canvas(hero, bg="#101719", highlightthickness=0)
        self.logo_canvas.grid(row=1, column=0, sticky="nsew", padx=34, pady=28)
        self.logo_canvas.create_line(210, 230, 710, 230, fill="#40555a", width=2)
        self.logo_canvas.create_polygon(460, 106, 590, 160, 560, 318, 460, 370, 360, 318, 330, 160,
                                        fill=COLORS["surface_2"], outline=COLORS["accent"], width=3)
        self.logo_ring = self.logo_canvas.create_oval(372, 146, 548, 322, outline=COLORS["accent_2"], width=3)
        self.logo_canvas.create_text(460, 226, text="SG", fill=COLORS["text"], font=("Segoe UI", 42, "bold"))
        self.logo_canvas.create_text(460, 272, text="LK", fill=COLORS["accent"], font=("Segoe UI", 18, "bold"))

        hero_bottom = Frame(hero, bg="#101719")
        hero_bottom.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 30))
        for label, value in [("Vision", "YOLOv8 model"), ("Guard", "Speed-aware alerts"), ("Input", "Camera or video")]:
            metric = Frame(hero_bottom, bg=COLORS["surface"])
            metric.pack(side="left", fill="x", expand=True, padx=(0, 12))
            Label(metric, text=label.upper(), font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface"]).pack(
                anchor="w", padx=16, pady=(12, 0)
            )
            Label(metric, text=value, font=("Segoe UI", 13, "bold"), fg=COLORS["text"], bg=COLORS["surface"]).pack(
                anchor="w", padx=16, pady=(2, 14)
            )

        side = make_panel(body)
        side.grid(row=0, column=1, sticky="nsew")
        Label(side, text="Launch Guard", font=("Segoe UI", 24, "bold"), fg=COLORS["text"], bg=COLORS["surface"]).pack(
            anchor="w", padx=28, pady=(34, 6)
        )
        Label(side, text=APP_SUBTITLE, font=("Segoe UI", 12), fg=COLORS["muted"], bg=COLORS["surface"]).pack(
            anchor="w", padx=28
        )

        actions = Frame(side, bg=COLORS["surface"])
        actions.pack(fill="x", padx=28, pady=34)
        make_button(actions, "START LIVE GUARD", lambda: self.start_callback(0, "Camera"), "primary").pack(fill="x", pady=(0, 12))
        make_button(actions, "SCAN VIDEO FILE", self.open_video_file, "secondary").pack(fill="x", pady=(0, 12))
        make_button(actions, "CLOSE SIGNGUARD", self.window.quit, "ghost").pack(fill="x")

        status = make_panel(side, bg=COLORS["surface_2"], border=COLORS["surface_3"])
        status.pack(fill="x", padx=28, pady=(8, 0))
        Label(status, text="GUARD STATUS", font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
            anchor="w", padx=16, pady=(14, 0)
        )
        self.loading_label = Label(status, text="", font=("Segoe UI", 12, "bold"), fg=COLORS["accent"], bg=COLORS["surface_2"])
        self.loading_label.pack(anchor="w", padx=16, pady=(4, 14))

    def animate_logo(self):
        if not self.frame.winfo_exists():
            return
        scale = 1.0 + 0.15 * math.sin(time.time() * 3)
        self.logo_canvas.itemconfig(self.logo_ring, width=max(2, int(3 * scale)))
        self.loading_index = (self.loading_index + 1) % len(self.loading_chars)
        self.loading_label.config(text=f"{self.loading_chars[self.loading_index]} SignGuard model ready")
        self.window.after(120, self.animate_logo)

    def open_video_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
        if file_path:
            self.start_callback(file_path, "Video file")

    def destroy(self):
        self.frame.destroy()
