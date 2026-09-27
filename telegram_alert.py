"""
Sends free real-time alerts via Telegram Bot API.

Setup (one-time, free):
1. Open Telegram, search "BotFather", send /newbot, follow steps -> get a token.
2. Send any message to your new bot.
3. Visit https://api.telegram.org/bot<TOKEN>/getUpdates in a browser
   to find your numeric chat_id.
4. Paste both into config.py and set TELEGRAM_ENABLED = True.

Until then, alerts just print to the console so you can test logic
without a real bot.
"""

import requests
import config


def send_alert(message: str):
    if not config.TELEGRAM_ENABLED:
        print(f"[Telegram-disabled] Would send: {message}")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": message}
    try:
        resp = requests.post(url, data=payload, timeout=5)
        if resp.status_code != 200:
            print(f"[Telegram error] {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"[Telegram error] Could not send alert: {e}")
