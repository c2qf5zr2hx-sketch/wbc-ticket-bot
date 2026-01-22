import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

TARGET_URL = os.environ.get("TARGET_URL", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
TO_USER = os.environ.get("LINE_TO_USER", "")

CHECK_INTERVAL = 180  # 3 minutes

def line_push(text: str):
    if not LINE_TOKEN or not TO_USER:
        print("Missing env: LINE_CHANNEL_ACCESS_TOKEN or LINE_TO_USER")
        return None, "missing env"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"to": TO_USER, "messages": [{"type": "text", "text": text}]}
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=data,
        timeout=20,
    )
    return r.status_code, r.text

def fetch_page_text(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
    }
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    return r.text

def classify(text: str) -> str:
    available = ["受付中", "残りわずか", "Available", "In stock", "○"]
    unavailable = ["受付終了", "予定枚数終了", "Sold out", "Unavailable", "×", "Not available"]

    if any(k in text for k in available):
        return "AVAILABLE"
    if any(k in text for k in unavailable):
        return "SOLDOUT"
    return "UNKNOWN"

def monitor_loop():
    if not TARGET_URL:
        print("TARGET_URL not set")
        return

    last_state = None
    code, resp = line_push(f"🟢 開始監控票況（每3分鐘）\n{TARGET_URL}")
    print("START PUSH:", code, resp)

    while True:
        try:
            text = fetch_page_text(TARGET_URL)
            state = classify(text)
            print("ticket_state:", state)

            if state != last_state:
                msg = f"🎫 票況變更：{state}\n{TARGET_URL}"
                code, resp = line_push(msg)
                print("PUSH:", code, resp)
                last_state = state

        except Exception as e:
            print("monitor error:", e)

        time.sleep(CHECK_INTERVAL)

@app.get("/")
def home():
    return "OK"

threading.Thread(target=monitor_loop, daemon=True).start()
