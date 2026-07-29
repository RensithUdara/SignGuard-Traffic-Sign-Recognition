import math
import os
import threading
import time
from dataclasses import dataclass

import requests

from src.config.settings import GPS_SERIAL_BAUDRATE, LOCATION_REFRESH_SECONDS


@dataclass
class LocationReading:
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    source: str = "Unavailable"
    status: str = "Waiting for location"
    timestamp: float = 0


class LocationService:
    """Reads live GPS when available, with approximate IP location as fallback."""

    def __init__(self):
        self.serial_port = os.environ.get("SIGNGUARD_GPS_PORT")
        self.baudrate = int(os.environ.get("SIGNGUARD_GPS_BAUDRATE", GPS_SERIAL_BAUDRATE))
        self.reading = LocationReading()
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def get_reading(self):
        return self.reading

    def _run(self):
        if self.serial_port:
            self._read_serial_gps()
        else:
            self._read_ip_location()

    def _read_serial_gps(self):
        try:
            import serial
        except Exception as exc:
            self.reading = LocationReading(source="GPS", status=f"pyserial missing: {exc}", timestamp=time.time())
            self._read_ip_location()
            return

        try:
            with serial.Serial(self.serial_port, self.baudrate, timeout=2) as gps:
                while self.running:
                    line = gps.readline().decode("ascii", errors="ignore").strip()
                    if line.startswith(("$GPRMC", "$GNRMC")):
                        parsed = self._parse_rmc(line)
                        if parsed:
                            self.reading = parsed
        except Exception as exc:
            self.reading = LocationReading(source="GPS", status=f"GPS unavailable: {exc}", timestamp=time.time())
            self._read_ip_location()

    def _read_ip_location(self):
        while self.running:
            try:
                response = requests.get("http://ip-api.com/json/", timeout=5)
                data = response.json()
                if data.get("status") == "success":
                    self.reading = LocationReading(
                        latitude=float(data.get("lat")),
                        longitude=float(data.get("lon")),
                        speed_kmh=None,
                        source="Approx IP",
                        status="Approximate location only",
                        timestamp=time.time(),
                    )
                else:
                    self.reading = LocationReading(source="Approx IP", status="Location lookup failed", timestamp=time.time())
            except Exception as exc:
                self.reading = LocationReading(source="Approx IP", status=f"Location unavailable: {exc}", timestamp=time.time())
            time.sleep(LOCATION_REFRESH_SECONDS * 12)

    def _parse_rmc(self, sentence):
        parts = sentence.split(",")
        if len(parts) < 8 or parts[2] != "A":
            return None
        latitude = self._nmea_to_decimal(parts[3], parts[4])
        longitude = self._nmea_to_decimal(parts[5], parts[6])
        speed_knots = float(parts[7] or 0)
        return LocationReading(
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_knots * 1.852,
            source="GPS",
            status="Live GPS",
            timestamp=time.time(),
        )

    def _nmea_to_decimal(self, value, direction):
        if not value:
            return None
        raw = float(value)
        degrees = math.floor(raw / 100)
        minutes = raw - degrees * 100
        decimal = degrees + minutes / 60
        if direction in ("S", "W"):
            decimal *= -1
        return decimal
