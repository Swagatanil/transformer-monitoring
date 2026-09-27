# IoT Transformer Monitoring — Software Backend

Fully software-side implementation. Works right now with **no hardware** using a
built-in simulator; swap one function later when ESP32 is ready.

## Files
- `config.py` — thresholds, Telegram/Firebase settings, data source mode
- `data_source.py` — **swap point**: `_simulated_reading()` now, `_firebase_reading()` later
- `health_engine.py` — health score formula + fault classification (same logic as the dashboard)
- `anomaly_model.py` — scikit-learn Isolation Forest, learns normal patterns, flags outliers
- `telegram_alert.py` — free real-time alerts via Telegram Bot API
- `report_generator.py` — auto-generates PDF maintenance reports
- `main.py` — runs the full loop: read → analyze → detect anomaly → alert → log → report

## Run it now (no hardware needed)
```bash
pip install scikit-learn joblib requests fpdf2
python main.py
```
Readings are logged to `readings_log.csv`, PDF reports land in `reports/`.

## Enable Telegram alerts (free, optional)
1. Telegram → search **BotFather** → `/newbot` → copy the token
2. Send your new bot any message
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → copy your `chat_id`
4. Paste both into `config.py`, set `TELEGRAM_ENABLED = True`

## When hardware arrives
1. ESP32 pushes sensor readings to **Firebase Realtime Database** (free tier)
2. In `config.py` set `DATA_SOURCE = "firebase"`
3. In `data_source.py`, fill in `_firebase_reading()` (a few lines using `requests`
   to GET the latest node — example is already commented in the file)

Nothing else changes — `health_engine.py`, `anomaly_model.py`, `telegram_alert.py`,
and `report_generator.py` all work off whatever `get_reading()` returns.

## Connecting to the web dashboard
The dashboard (separate HTML file) currently uses its own JS simulator.
Once Firebase is live, replace its `Math.random()` calls with a Firebase
JS SDK read from the same database path ESP32/this script writes to.
