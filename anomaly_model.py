"""
AI-based anomaly detection using scikit-learn's Isolation Forest.

Instead of only flagging fixed threshold breaches, this learns what
"normal" sensor behaviour looks like and flags readings that don't
fit the pattern - even if no single value crosses a hard limit.

Trains on synthetic "mostly normal" data on first run and saves the
model to disk so it doesn't retrain every time.
"""

import os
import random
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

MODEL_PATH = "anomaly_model.joblib"


def _generate_training_data(n=500):
    """Synthetic historical data: mostly normal operation, a few outliers."""
    rows = []
    for _ in range(n):
        if random.random() < 0.9:  # 90% normal
            temp = random.uniform(40, 60)
            current = random.uniform(8, 14)
            voltage = random.uniform(220, 240)
            oil = random.uniform(50, 85)
        else:  # 10% outlier-ish
            temp = random.uniform(65, 85)
            current = random.uniform(16, 25)
            voltage = random.uniform(195, 260)
            oil = random.uniform(10, 35)
        rows.append([temp, current, voltage, oil])
    return np.array(rows)


def train_and_save_model():
    data = _generate_training_data()
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    model.fit(data)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_and_save_model()


_model = load_model()


def is_anomaly(temp, current, voltage, oil):
    """Returns True/False. Uses -1 (outlier) / 1 (normal) from Isolation Forest."""
    sample = np.array([[temp, current, voltage, oil]])
    prediction = _model.predict(sample)[0]
    return bool(prediction == -1)