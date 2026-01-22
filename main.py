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

def classify(text: str):
    available = ["受付中", "残りわずか", "Available", "In stock", "○"]
    unavailable = ["受付終了", "予定枚数終了", "Sold out", "Unavailable", "×", "Not available"]

    for k in available:
        if k in text:
            return "AVAILABLE", k
    for k in unavailable:
        if k in text:
            return "SOLDOUT", k
    return "UNKNOWN", ""

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
            state, hit = classify(text)
            print("ticket_state:", state, "hit:", hit)

            if state != last_state:
                emoji = "🎉" if state == "AVAILABLE" else ("🚫" if state == "SOLDOUT" else "❓")
                hit_text = f"（偵測到：{hit}）" if hit else ""
                msg = f"{emoji} 票況變更：{state}{hit_text}\n{TARGET_URL}"
                code, resp = line_push(msg)
                print("PUSH:", code, resp)
                last_state = state

        except Exception as e:
            print("monitor error:", e)

        time.sleep(CHECK_INTERVAL)

@app.get("/")
def home():
    return "OK"

# Render 啟動後背景監控（服務活著時會一直跑）
threading.Thread(target=monitor_loop, daemon=True).start()
