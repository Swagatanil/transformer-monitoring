"""
Central configuration for the Transformer Monitoring System.
Fill in TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID and FIREBASE_* values
when you're ready to go live. Everything works in simulation mode
without touching these.
"""

# ---- Alert thresholds (same logic as the dashboard) ----
THRESHOLDS = {
    "max_temp": 65,      # deg C
    "max_current": 16,   # Amps
    "min_oil": 30,        # percent
    "nominal_voltage": 230,
    "max_voltage_dev": 15,
}

# ---- Telegram Bot (free) ----
# 1. Message @BotFather on Telegram -> /newbot -> get token
# 2. Message your bot once, then visit:
#    https://api.telegram.org/bot<TOKEN>/getUpdates  to find chat_id
TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "PASTE_YOUR_CHAT_ID_HERE"
TELEGRAM_ENABLED = False   # set True once token/chat_id are filled in

# ---- Firebase Realtime Database (free) ----
# Used later when ESP32 hardware is ready. Leave as-is for now;
# the simulator does not need this.
FIREBASE_DB_URL = "https://YOUR-PROJECT.firebaseio.com/"
FIREBASE_ENABLED = False

# ---- Data source mode ----
# "simulator" -> uses fake random sensor data (works right now, no hardware)
# "firebase"  -> reads live readings pushed by ESP32 into Firebase (switch later)
DATA_SOURCE = "simulator"

# ---- Logging ----
LOG_CSV_PATH = "readings_log.csv"
REPORT_OUTPUT_DIR = "reports"

# ---- Loop timing ----
READ_INTERVAL_SECONDS = 3
REPORT_EVERY_N_READINGS = 50
