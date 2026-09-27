"""
Local web server — runs the same backend (health score, anomaly
detection, fault classification) as main.py, but shows the output
on a webpage in your browser instead of the terminal.

Run with:  python webapp.py
Then open: http://127.0.0.1:5000  in your browser.

Data source is still the simulator (no hardware needed). Later,
same swap as before: change DATA_SOURCE in config.py to "firebase".
"""

import threading
import time
import os
from collections import deque

from flask import Flask, jsonify, send_from_directory

import config
from data_source import get_reading
from health_engine import compute_health, classify_fault
from anomaly_model import is_anomaly
from telegram_alert import send_alert
from report_generator import generate_pdf_report

app = Flask(__name__)

# Shared state between the background reading loop and the web routes
state_lock = threading.Lock()
history = deque(maxlen=20)          # last 20 readings for the chart
latest = {}                          # most recent full reading
stats = {"count": 0, "alerts": 0, "anomalies": 0, "peak_temp": 0,
          "peak_current": 0, "min_health": 100}
alert_log = deque(maxlen=15)         # recent alert/log messages


def background_loop():
    while True:
        r = get_reading()
        temp, curr, volt, oil = r["temperature"], r["current"], r["voltage"], r["oil_level"]

        health = compute_health(temp, curr, volt, oil)
        level, label, reason = classify_fault(temp, curr, volt, oil, health)
        anomaly = is_anomaly(temp, curr, volt, oil)

        with state_lock:
            stats["count"] += 1
            stats["peak_temp"] = max(stats["peak_temp"], temp)
            stats["peak_current"] = max(stats["peak_current"], curr)
            stats["min_health"] = min(stats["min_health"], health)
            if level != "good":
                stats["alerts"] += 1
                alert_log.appendleft({
                    "time": time.strftime("%H:%M:%S"),
                    "level": level,
                    "text": f"{label} — T:{temp}C I:{curr}A V:{volt}V Oil:{oil}%",
                })
            if anomaly:
                stats["anomalies"] += 1
                alert_log.appendleft({
                    "time": time.strftime("%H:%M:%S"),
                    "level": "bad",
                    "text": "Anomaly pattern detected in sensor data",
                })

            latest.update({
                "temperature": temp, "current": curr, "voltage": volt, "oil_level": oil,
                "health": health, "fault_level": level, "fault_label": label,
                "fault_reason": reason, "anomaly": anomaly,
            })
            history.append({"health": health, "temp": temp, "current": curr, "voltage": volt,
                              "load": round((volt * curr) / 1000, 2)})

        if level != "good":
            send_alert(f"⚠️ {label}\nHealth:{health}% T:{temp}C I:{curr}A V:{volt}V Oil:{oil}%\n{reason}")
        if anomaly:
            send_alert(f"🧠 Anomaly detected (Health:{health}%)")

        if stats["count"] % config.REPORT_EVERY_N_READINGS == 0:
            generate_pdf_report(stats)

        time.sleep(config.READ_INTERVAL_SECONDS)


@app.route("/")
def index():
    return send_from_directory(".", "dashboard_live.html")


@app.route("/api/data")
def api_data():
    with state_lock:
        return jsonify({
            "latest": latest,
            "history": list(history),
            "stats": stats,
            "alerts": list(alert_log),
            "thresholds": config.THRESHOLDS,
        })


@app.route("/api/thresholds", methods=["POST"])
def api_set_thresholds():
    from flask import request
    data = request.get_json(force=True)
    with state_lock:
        if "max_temp" in data:
            config.THRESHOLDS["max_temp"] = float(data["max_temp"])
        if "max_current" in data:
            config.THRESHOLDS["max_current"] = float(data["max_current"])
        if "min_oil" in data:
            config.THRESHOLDS["min_oil"] = float(data["min_oil"])
    return jsonify({"ok": True, "thresholds": config.THRESHOLDS})


# Start the background reading loop once when the module loads.
# This works both with `python webapp.py` (local) and with gunicorn
# (cloud hosting), since gunicorn imports this module rather than
# running the __main__ block.
_bg_thread = threading.Thread(target=background_loop, daemon=True)
_bg_thread.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Dashboard running -> open http://127.0.0.1:{port} in your browser")
    app.run(debug=False, host="0.0.0.0", port=port)
