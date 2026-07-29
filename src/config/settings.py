from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_NAME = "SignGuard LK"
APP_TAGLINE = "Sri Lankan road-sign intelligence for safer driving"
APP_SUBTITLE = "Real-time sign detection, speed context, and driver alerts"
MODEL_PATH = ROOT_DIR / "best.pt"
DEFAULT_GPS = "6.9271 N, 79.8612 E"
DEFAULT_SPEED = 60
SNAPSHOT_PREFIX = "signguard_lk_snapshot"
DEFAULT_CONFIDENCE = 0.50
DEFAULT_IOU = 0.45
DEFAULT_IMAGE_SIZE = 640
DEFAULT_MAX_DETECTIONS = 20
