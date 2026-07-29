from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_NAME = "SignGuard LK"
APP_TAGLINE = "Sri Lankan road-sign intelligence for safer driving"
APP_SUBTITLE = "Real-time sign detection, speed context, and driver alerts"
LOGO_PATH = ROOT_DIR / "logo.png"
MODEL_PATH = ROOT_DIR / "best.pt"
DEFAULT_SPEED = 60
GPS_SERIAL_PORT = None
GPS_SERIAL_BAUDRATE = 9600
LOCATION_REFRESH_SECONDS = 5
SNAPSHOT_PREFIX = "signguard_lk_snapshot"
DEFAULT_CONFIDENCE = 0.50
DEFAULT_IOU = 0.45
DEFAULT_IMAGE_SIZE = 640
DEFAULT_MAX_DETECTIONS = 20
