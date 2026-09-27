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


def _simulated_reading():
    """Generates one fake sensor reading, same ranges as the demo dashboard."""
    return {
        "timestamp": time.time(),
        "temperature": round(random.uniform(35, 75), 1),
        "current": round(random.uniform(5, 20), 1),
        "voltage": round(random.uniform(210, 245), 1),
        "oil_level": round(random.uniform(25, 90), 1),
    }


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
    if config.DATA_SOURCE == "firebase":
        return _firebase_reading()
    return _simulated_reading()
