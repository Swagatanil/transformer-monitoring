"""
Main loop - ties together data source, health engine, anomaly
detection, Telegram alerts, CSV logging, and PDF reports.

Run with:  python main.py
Stop with: Ctrl+C

Right now data comes from the simulator (no hardware needed).
When ESP32 is ready: set config.DATA_SOURCE = "firebase" and fill
in the Firebase section in data_source.py - nothing else changes.
"""

import csv
import os
import time

import config
from data_source import get_reading
from health_engine import compute_health, classify_fault
from anomaly_model import is_anomaly
from telegram_alert import send_alert
from report_generator import generate_pdf_report


def init_csv():
    new_file = not os.path.exists(config.LOG_CSV_PATH)
    f = open(config.LOG_CSV_PATH, "a", newline="")
    writer = csv.writer(f)
    if new_file:
        writer.writerow([
            "timestamp", "temperature", "current", "voltage", "oil_level",
            "health", "fault_level", "fault_label", "anomaly"
        ])
    return f, writer


def main():
    log_file, writer = init_csv()
    stats = {"count": 0, "alerts": 0, "anomalies": 0, "peak_temp": 0,
              "peak_current": 0, "min_health": 100}

    print("Transformer monitoring started (mode: %s). Ctrl+C to stop.\n" % config.DATA_SOURCE)

    try:
        while True:
            r = get_reading()
            temp, curr, volt, oil = r["temperature"], r["current"], r["voltage"], r["oil_level"]

            health = compute_health(temp, curr, volt, oil)
            level, label, reason = classify_fault(temp, curr, volt, oil, health)
            anomaly = is_anomaly(temp, curr, volt, oil)

            stats["count"] += 1
            stats["peak_temp"] = max(stats["peak_temp"], temp)
            stats["peak_current"] = max(stats["peak_current"], curr)
            stats["min_health"] = min(stats["min_health"], health)
            if level != "good":
                stats["alerts"] += 1
            if anomaly:
                stats["anomalies"] += 1

            writer.writerow([r["timestamp"], temp, curr, volt, oil, health, level, label, anomaly])
            log_file.flush()

            tag = "[ANOMALY] " if anomaly else ""
            print(f"{tag}Health:{health}% | T:{temp}C I:{curr}A V:{volt}V Oil:{oil}% -> {label}")

            if level != "good":
                send_alert(
                    f"⚠️ {label}\nHealth: {health}%\n"
                    f"T:{temp}C I:{curr}A V:{volt}V Oil:{oil}%\n{reason}"
                )
            if anomaly:
                send_alert(f"🧠 Anomaly detected in sensor pattern (Health: {health}%)")

            if stats["count"] % config.REPORT_EVERY_N_READINGS == 0:
                path = generate_pdf_report(stats)
                print(f"  -> Report generated: {path}")

            time.sleep(config.READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopped. Generating final report...")
        path = generate_pdf_report(stats)
        print(f"Final report: {path}")
    finally:
        log_file.close()


if __name__ == "__main__":
    main()
