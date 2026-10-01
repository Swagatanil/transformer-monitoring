"""
Local/cloud web server for the transformer dashboard.

Run locally:  python webapp.py   -> http://127.0.0.1:5000
Cloud (Render): gunicorn webapp:app

IMPORTANT DESIGN NOTE
Readings are generated ON DEMAND (each time the dashboard asks for data,
if READ_INTERVAL_SECONDS have passed). There is no background thread, so
nothing can silently die on free hosting. When real hardware is added,
the ESP32 data will simply be read inside get_reading() in data_source.py.
"""

import os
import time
import threading
import traceback
from collections import deque

from flask import Flask, jsonify, request, send_from_directory

import config
from data_source import get_reading, get_dataset_window
from health_engine import compute_health, classify_fault
from anomaly_model import is_anomaly
from telegram_alert import send_alert
from report_generator import generate_pdf_report

app = Flask(__name__)
BUILD = "v6-persist-mode"

_MODE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_mode.txt")


def _load_saved_mode():
    try:
        with open(_MODE_FILE) as f:
            mode = f.read().strip()
            if mode in ("simulator", "dataset", "firebase"):
                return mode
    except FileNotFoundError:
        pass
    return config.DATA_SOURCE


config.DATA_SOURCE = _load_saved_mode()

state_lock = threading.Lock()
history = deque(maxlen=1200)    # up to ~1 hour at 3s/tick, for the time-range selector
latest = {}                      # most recent full reading
stats = {"count": 0, "alerts": 0, "anomalies": 0, "peak_temp": 0,
         "peak_current": 0, "min_health": 100}
alert_log = deque(maxlen=15)
diag = {"last_error": None, "error_count": 0, "boot_time": time.time(), "pid": os.getpid()}
_last_tick = 0.0


def do_tick():
    """Take one reading, analyse it, update shared state."""
    r = get_reading()
    temp, curr = r["temperature"], r["current"]
    volt, oil = r.get("voltage"), r.get("oil_level")
    load_kw = r.get("load_kw")
    if load_kw is None and volt is not None:
        load_kw = round((volt * curr) / 1000, 2)
    source_label = r.get("source_label", config.DATA_SOURCE)

    health = compute_health(temp, curr, volt, oil)
    level, label, reason = classify_fault(temp, curr, volt, oil, health)
    # Anomaly detection needs all 4 features - skip it honestly when some
    # readings (e.g. voltage/oil) aren't available from this data source,
    # rather than guessing values to feed the model.
    if volt is not None and oil is not None:
        anomaly = is_anomaly(temp, curr, volt, oil)
    else:
        anomaly = False

    stats["count"] += 1
    stats["peak_temp"] = max(stats["peak_temp"], temp)
    stats["peak_current"] = max(stats["peak_current"], curr)
    stats["min_health"] = min(stats["min_health"], health)
    now = time.strftime("%H:%M:%S")
    volt_txt = f"{volt}V" if volt is not None else "N/A"
    oil_txt = f"{oil}%" if oil is not None else "N/A"
    if level != "good":
        stats["alerts"] += 1
        alert_log.appendleft({"time": now, "level": level,
                              "text": f"{label} — T:{temp}C I:{curr}A V:{volt_txt} Oil:{oil_txt}"})
    if anomaly:
        stats["anomalies"] += 1
        alert_log.appendleft({"time": now, "level": "bad",
                              "text": "Anomaly pattern detected in sensor data"})

    latest.update({
        "temperature": temp, "current": curr, "voltage": volt, "oil_level": oil,
        "load_kw": load_kw, "source_label": source_label,
        "health": health, "fault_level": level, "fault_label": label,
        "fault_reason": reason, "anomaly": anomaly,
    })
    history.append({"health": health, "temp": temp, "current": curr, "voltage": volt,
                    "load": load_kw, "time": time.strftime("%H:%M:%S"),
                    "ts": time.time()})

    # Side effects must never break the dashboard.
    try:
        if level != "good":
            send_alert(f"⚠️ {label}\nHealth:{health}% T:{temp}C I:{curr}A V:{volt_txt} Oil:{oil_txt}\n{reason}")
        if anomaly:
            send_alert(f"🧠 Anomaly detected (Health:{health}%)")
        if stats["count"] % config.REPORT_EVERY_N_READINGS == 0:
            generate_pdf_report(stats)
    except Exception:
        diag["last_error"] = "side-effect: " + traceback.format_exc()[-400:]
        diag["error_count"] += 1


def maybe_tick():
    """Generate a new reading if enough time has passed since the last one."""
    global _last_tick
    with state_lock:
        if time.time() - _last_tick < config.READ_INTERVAL_SECONDS - 0.2:
            return
        _last_tick = time.time()
        try:
            do_tick()
        except Exception:
            diag["last_error"] = traceback.format_exc()[-600:]
            diag["error_count"] += 1
            print("[tick error]", diag["last_error"], flush=True)


@app.route("/")
def index():
    return send_from_directory(".", "dashboard_live.html")


@app.route("/api/data")
def api_data():
    maybe_tick()
    with state_lock:
        resp = jsonify({
            "latest": latest,
            "history": list(history),
            "stats": stats,
            "alerts": list(alert_log),
            "thresholds": config.THRESHOLDS,
            "diag": diag,
            "build": BUILD,
            "uptime_sec": round(time.time() - diag["boot_time"]),
            "data_source": config.DATA_SOURCE,
        })
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/thresholds", methods=["POST"])
def api_set_thresholds():
    data = request.get_json(force=True)
    with state_lock:
        if "max_temp" in data:
            config.THRESHOLDS["max_temp"] = float(data["max_temp"])
        if "max_current" in data:
            config.THRESHOLDS["max_current"] = float(data["max_current"])
        if "min_oil" in data:
            config.THRESHOLDS["min_oil"] = float(data["min_oil"])
    return jsonify({"ok": True, "thresholds": config.THRESHOLDS})


@app.route("/api/dataset_window")
def api_dataset_window():
    hours = request.args.get("hours", "24")
    try:
        hours = int(hours)
    except ValueError:
        hours = 24
    points = get_dataset_window(hours)
    return jsonify({"ok": bool(points), "points": points, "source": "ETTh1.csv (real dataset)"})


@app.route("/api/datasource", methods=["POST"])
def api_set_datasource():
    data = request.get_json(force=True)
    mode = data.get("mode", "")
    if mode not in ("simulator", "dataset", "firebase"):
        return jsonify({"ok": False, "error": "invalid mode"}), 400
    config.DATA_SOURCE = mode
    try:
        with open(_MODE_FILE, "w") as f:
            f.write(mode)
    except Exception:
        pass
    return jsonify({"ok": True, "data_source": config.DATA_SOURCE})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Dashboard running -> open http://127.0.0.1:{port} in your browser", flush=True)
    app.run(debug=False, host="0.0.0.0", port=port)
