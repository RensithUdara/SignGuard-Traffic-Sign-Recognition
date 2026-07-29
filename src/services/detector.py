import datetime
import time
from dataclasses import dataclass

from ultralytics import YOLO

from src.config.settings import MODEL_PATH
from src.data.road_signs import ROAD_SIGNS


@dataclass
class DetectionEvent:
    class_name: str
    label: str
    display_name: str
    confidence: float
    box: tuple
    box_color: tuple
    threat_level: str
    state: str
    description: str


class TrafficSignDetector:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(str(model_path))

    def detect(
        self,
        frame,
        current_speed,
        minimum_confidence,
        iou_threshold=0.45,
        image_size=640,
        max_detections=20,
        augment=False,
    ):
        events = []
        results = self.model(
            frame,
            conf=minimum_confidence,
            iou=iou_threshold,
            imgsz=image_size,
            max_det=max_detections,
            augment=augment,
            verbose=False,
        )
        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < minimum_confidence:
                    continue

                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                label = ROAD_SIGNS.get(class_name, class_name)
                event = self._build_event(class_name, label, confidence, current_speed, box)
                events.append(event)
        return events

    def _build_event(self, class_name, label, confidence, current_speed, box):
        display_name = label
        box_color = (45, 212, 191)
        threat_level = "HIGH"
        state = "critical"
        description = "Immediate attention required"

        if confidence < 0.60:
            display_name = f"Degraded: {label}"
            box_color = (0, 165, 255)
            threat_level = "MODERATE"
            state = "warning"
            description = "Detected with reduced confidence"

        if class_name == "DWS-33":
            current_hour = datetime.datetime.now().hour
            if 7 <= current_hour <= 16:
                if current_speed > 30:
                    display_name = "School Zone - Reduce Speed!"
                    threat_level = "CRITICAL"
                    state = "critical"
                    description = "Slow down near school zone"
                    box_color = (0, 0, 255) if int(time.time() * 5) % 2 == 0 else (255, 255, 255)
                else:
                    display_name = "School Zone - Speed OK"
                    threat_level = "SAFE"
                    state = "safe"
                    description = "Road condition acknowledged"
                    box_color = (0, 255, 0)
            else:
                display_name = "School Zone Inactive"
                threat_level = "SAFE"
                state = "safe"
                description = "Road condition acknowledged"
                box_color = (148, 163, 184)

        if class_name.startswith("SLS-"):
            try:
                limit = int(class_name.split("-")[1])
                if current_speed > limit:
                    display_name = "Over Speeding!"
                    threat_level = "CRITICAL"
                    state = "critical"
                    description = f"Current speed exceeds {limit} km/h limit"
                    box_color = (0, 0, 255) if int(time.time() * 5) % 2 == 0 else (255, 255, 255)
            except Exception:
                pass

        if class_name == "PRS-01":
            if current_speed > 5:
                display_name = "STOP Sign Ignored!"
                threat_level = "CRITICAL"
                state = "critical"
                description = "Vehicle must stop"
                box_color = (0, 0, 255) if int(time.time() * 5) % 2 == 0 else (255, 255, 255)
            else:
                display_name = "Vehicle Stopped"
                threat_level = "SAFE"
                state = "safe"
                description = "Road condition acknowledged"
                box_color = (0, 255, 0)

        return DetectionEvent(
            class_name=class_name,
            label=label,
            display_name=display_name,
            confidence=confidence,
            box=tuple(map(int, box.xyxy[0])),
            box_color=box_color,
            threat_level=threat_level,
            state=state,
            description=description,
        )
