"""
Data source abstraction.

Right now this returns SIMULATED sensor readings so the whole
software pipeline (health score, anomaly detection, alerts, reports)
can be built and tested without any hardware.

When the ESP32 + sensors are ready, only get_reading() needs to
change (or set config.DATA_SOURCE = "firebase") - nothing else in
the project needs to be touched.
"""

import random
import time
import config
from health_engine import compute_health


def _simulated_reading():
    """Generates one fake sensor reading, same ranges as the demo dashboard."""
    return {
        "timestamp": time.time(),
        "temperature": round(random.uniform(35, 75), 1),
        "current": round(random.uniform(5, 20), 1),
        "voltage": round(random.uniform(210, 245), 1),
        "oil_level": round(random.uniform(25, 90), 1),
    }


import os
import csv

_ETT_ROWS = None
_ETT_INDEX = 0
_ETT_PATH = os.path.join(os.path.dirname(__file__), "data", "ETTh1.csv")

# Scaling: the raw ETT columns are normalized/de-meaned values from the
# original research paper (they can go negative), not physical units.
# We linearly remap them into realistic transformer ranges so the
# dashboard shows sensible numbers while still being driven by real
# recorded temperature/load *patterns* (highs stay high, lows stay low).
_OT_MIN, _OT_MAX = -4.08, 46.01          # observed range of the OT column
_TEMP_LO, _TEMP_HI = 32, 78               # target temperature range (°C)

_LOAD_MIN, _LOAD_MAX = -45.66, 46.77      # observed range of HUFL+MUFL+LUFL
_CURR_LO, _CURR_HI = 4, 22                # target current range (A)


def _load_ett_rows():
    global _ETT_ROWS
    if _ETT_ROWS is None:
        with open(_ETT_PATH, newline="") as f:
            _ETT_ROWS = list(csv.DictReader(f))
    return _ETT_ROWS


def _rescale(value, src_lo, src_hi, dst_lo, dst_hi):
    ratio = (value - src_lo) / (src_hi - src_lo)
    ratio = max(0.0, min(1.0, ratio))
    return dst_lo + ratio * (dst_hi - dst_lo)


def _dataset_reading():
    """
    Replays the real ETT (Electricity Transformer Temperature) dataset,
    one row per call, looping back to the start when it runs out.

    Source: ETTh1.csv (hourly), zhouhaoyi/ETDataset (GitHub).
    OT column -> temperature. HUFL+MUFL+LUFL -> load -> current
    (Current = Load*1000 / Voltage, single-phase approximation).
    Both are linearly rescaled from the dataset's own value range into
    realistic transformer ranges - see constants above.
    """
    global _ETT_INDEX
    rows = _load_ett_rows()
    row = rows[_ETT_INDEX % len(rows)]
    _ETT_INDEX += 1

    ot = float(row["OT"])
    raw_load = float(row["HUFL"]) + float(row["MUFL"]) + float(row["LUFL"])

    temp = round(_rescale(ot, _OT_MIN, _OT_MAX, _TEMP_LO, _TEMP_HI), 1)
    # Small realistic voltage wobble so the "Voltage Fluctuation" fault
    # can still trigger occasionally, instead of a perfectly fixed value.
    voltage = round(random.uniform(215, 245), 1)
    current = round(_rescale(raw_load, _LOAD_MIN, _LOAD_MAX, _CURR_LO, _CURR_HI), 1)
    # Oil level has no equivalent column in this dataset - keep it simulated.
    oil = round(random.uniform(30, 90), 1)

    return {
        "timestamp": time.time(),
        "temperature": temp,
        "current": current,
        "voltage": voltage,
        "oil_level": oil,
    }


def get_dataset_window(hours):
    """
    Returns a chart-ready slice of the REAL dataset spanning `hours` of
    its own recorded history (ETTh1 is hourly, so 1 day = 24 rows,
    1 week = 168 rows, etc). Independent of the live replay pointer and
    of how long the dashboard has been open - this reads straight from
    the dataset's own dates, so long ranges (day/week/month) work
    immediately instead of waiting for that much real time to pass.
    Returns [] if the dataset file isn't available.
    """
    try:
        rows = _load_ett_rows()
    except Exception:
        return []
    n = max(2, min(int(hours), len(rows)))
    slice_rows = rows[:n]
    out = []
    for row in slice_rows:
        ot = float(row["OT"])
        raw_load = float(row["HUFL"]) + float(row["MUFL"]) + float(row["LUFL"])
        temp = round(_rescale(ot, _OT_MIN, _OT_MAX, _TEMP_LO, _TEMP_HI), 1)
        current = round(_rescale(raw_load, _LOAD_MIN, _LOAD_MAX, _CURR_LO, _CURR_HI), 1)
        voltage = 230.0
        oil = 60.0  # placeholder - not present in this dataset
        health = compute_health(temp, current, voltage, oil)
        out.append({
            "time": row["date"],
            "health": health,
            "temp": temp,
            "current": current,
            "voltage": voltage,
            "load": round(current * voltage / 1000, 2),
        })
    return out


def _firebase_reading():
    """
    Placeholder for real hardware mode.
    Once ESP32 pushes data to Firebase Realtime DB, pull the latest
    node here using the `requests` library (Firebase REST API) or
    the `firebase-admin` SDK. Example (REST, no SDK needed):

        import requests
        url = config.FIREBASE_DB_URL + "latest_reading.json"
        data = requests.get(url).json()
        return data
    """
    raise NotImplementedError(
        "Firebase mode not wired up yet - set config.DATA_SOURCE='simulator' "
        "until the ESP32 hardware side is ready."
    )


def get_reading():
    """Single entry point the rest of the project calls. Swap-safe."""
    try:
        if config.DATA_SOURCE == "firebase":
            return _firebase_reading()
        if config.DATA_SOURCE == "dataset":
            return _dataset_reading()
    except Exception as e:
        # Mode selected on the website failed (missing file, bad format,
        # network issue, etc) - fall back to the simulator instead of
        # crashing the whole background reading loop.
        print(f"[get_reading fallback] {config.DATA_SOURCE} failed: {e}", flush=True)
    return _simulated_reading()
