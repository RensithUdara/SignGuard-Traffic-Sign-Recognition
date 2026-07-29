import tkinter as tk

import cv2
from PIL import Image, ImageTk

from src.config.settings import APP_NAME, LOGO_PATH
from src.services.detector import TrafficSignDetector
from src.services.speech import SpeechService
from src.ui.dashboard import MainDashboard
from src.ui.startup import StartupScreen
from src.ui.theme import COLORS


class TrafficSignApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title(APP_NAME)
        self.window.geometry("1600x950")
        try:
            self.window.state("zoomed")
        except Exception:
            pass
        self.window.configure(bg=COLORS["app_bg"])
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.set_window_icon()

        self.detector = TrafficSignDetector()
        self.speech_service = SpeechService()
        self.current_screen = StartupScreen(self.window, self.start_dashboard)

    def start_dashboard(self, source, source_name):
        self.current_screen.destroy()
        self.current_screen = MainDashboard(
            self.window,
            detector=self.detector,
            speech_service=self.speech_service,
            source=source,
            source_name=source_name,
        )
        self.current_screen.update_frame()

    def run(self):
        self.window.mainloop()
        cv2.destroyAllWindows()

    def set_window_icon(self):
        if not LOGO_PATH.exists():
            return
        try:
            icon = Image.open(LOGO_PATH).resize((64, 64), Image.Resampling.LANCZOS)
            self.window_icon = ImageTk.PhotoImage(icon)
            self.window.iconphoto(True, self.window_icon)
        except Exception as exc:
            print(f"Logo icon error: {exc}")

    def close(self):
        if self.current_screen and hasattr(self.current_screen, "destroy"):
            self.current_screen.destroy()
        self.window.destroy()


def main():
    app = TrafficSignApp()
    app.run()
