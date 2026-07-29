import csv
import html
from collections import Counter
from datetime import datetime

from src.config.settings import APP_NAME


class ReportService:
    @staticmethod
    def build_summary(events, session_start, session_end, source_name, settings):
        duration_seconds = max(0, int(session_end - session_start))
        threat_counts = Counter(event["threat"] for event in events)
        sign_counts = Counter(event["message"] for event in events)
        avg_confidence = 0
        if events:
            avg_confidence = sum(event["confidence"] for event in events) / len(events)

        return {
            "app_name": APP_NAME,
            "source_name": source_name,
            "started_at": datetime.fromtimestamp(session_start).strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": datetime.fromtimestamp(session_end).strftime("%Y-%m-%d %H:%M:%S"),
            "duration": ReportService.format_duration(duration_seconds),
            "total_events": len(events),
            "critical_events": threat_counts.get("CRITICAL", 0),
            "warning_events": threat_counts.get("MODERATE", 0),
            "safe_events": threat_counts.get("SAFE", 0),
            "avg_confidence": avg_confidence,
            "top_signs": sign_counts.most_common(5),
            "settings": settings,
        }

    @staticmethod
    def export_csv(path, events):
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "timestamp",
                    "source",
                    "speed",
                    "class_name",
                    "label",
                    "message",
                    "threat",
                    "confidence",
                    "description",
                ],
            )
            writer.writeheader()
            writer.writerows(events)

    @staticmethod
    def export_text(path, summary, events):
        lines = [
            f"{summary['app_name']} Session Report",
            "=" * 42,
            f"Source: {summary['source_name']}",
            f"Started: {summary['started_at']}",
            f"Ended: {summary['ended_at']}",
            f"Duration: {summary['duration']}",
            f"Total detections: {summary['total_events']}",
            f"Critical: {summary['critical_events']}",
            f"Warnings: {summary['warning_events']}",
            f"Safe: {summary['safe_events']}",
            f"Average confidence: {summary['avg_confidence']:.1f}%",
            "",
            "Runtime Settings",
            "-" * 16,
        ]
        for key, value in summary["settings"].items():
            lines.append(f"{key}: {value}")

        lines.extend(["", "Top Signs", "-" * 9])
        if summary["top_signs"]:
            for sign, count in summary["top_signs"]:
                lines.append(f"{sign}: {count}")
        else:
            lines.append("No signs recorded.")

        lines.extend(["", "Detection Events", "-" * 16])
        for event in events:
            lines.append(
                f"{event['timestamp']} | {event['confidence']:.0f}% | {event['threat']} | "
                f"{event['speed']} km/h | {event['message']}"
            )

        with open(path, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(lines) + "\n")

    @staticmethod
    def export_html(path, summary, events):
        rows = "\n".join(
            "<tr>"
            f"<td>{html.escape(event['timestamp'])}</td>"
            f"<td>{event['confidence']:.0f}%</td>"
            f"<td>{html.escape(event['threat'])}</td>"
            f"<td>{event['speed']} km/h</td>"
            f"<td>{html.escape(event['class_name'])}</td>"
            f"<td>{html.escape(event['message'])}</td>"
            "</tr>"
            for event in events
        )
        top_signs = "".join(
            f"<li><strong>{html.escape(sign)}</strong>: {count}</li>" for sign, count in summary["top_signs"]
        ) or "<li>No signs recorded.</li>"
        settings = "".join(
            f"<li><strong>{html.escape(str(key))}</strong>: {html.escape(str(value))}</li>"
            for key, value in summary["settings"].items()
        )
        document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(summary['app_name'])} Session Report</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #152025; }}
    h1 {{ color: #0f766e; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
    .card {{ border: 1px solid #d6e2e5; padding: 14px; border-radius: 8px; background: #f7fbfb; }}
    .label {{ color: #60717a; font-size: 12px; text-transform: uppercase; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ border-bottom: 1px solid #e1e8ea; padding: 9px; text-align: left; }}
    th {{ background: #102023; color: white; }}
  </style>
</head>
<body>
  <h1>{html.escape(summary['app_name'])} Session Report</h1>
  <p><strong>Source:</strong> {html.escape(summary['source_name'])}</p>
  <p><strong>Started:</strong> {summary['started_at']} &nbsp; <strong>Ended:</strong> {summary['ended_at']}</p>
  <div class="cards">
    <div class="card"><div class="label">Duration</div><div class="value">{summary['duration']}</div></div>
    <div class="card"><div class="label">Detections</div><div class="value">{summary['total_events']}</div></div>
    <div class="card"><div class="label">Critical</div><div class="value">{summary['critical_events']}</div></div>
    <div class="card"><div class="label">Avg Confidence</div><div class="value">{summary['avg_confidence']:.1f}%</div></div>
  </div>
  <h2>Top Signs</h2>
  <ul>{top_signs}</ul>
  <h2>Runtime Settings</h2>
  <ul>{settings}</ul>
  <h2>Detection Events</h2>
  <table>
    <thead>
      <tr><th>Time</th><th>Confidence</th><th>Threat</th><th>Speed</th><th>Class</th><th>Message</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as report_file:
            report_file.write(document)

    @staticmethod
    def format_duration(seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
