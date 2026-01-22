import os
import json
import hashlib
import requests

TARGET_URL = os.environ["TARGET_URL"]
LINE_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
TO_USER = os.environ["LINE_TO_USER"]

STATE_FILE = "ticket_state.json"

def line_push(text: str):
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"to": TO_USER, "messages": [{"type": "text", "text": text}]}
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=payload,
        timeout=20,
    )
    r.raise_for_status()

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

def load_last_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("state")
    except Exception:
        return None

def save_state(state: str):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"state": state}, f, ensure_ascii=False)

def main():
    html = fetch_page_text(TARGET_URL)
    state, hit = classify(html)

    last_state = load_last_state()

    # 第一次跑：先記錄，不通知（避免一上線就吵你）
    if last_state is None:
        save_state(state)
        print("First run, saved state:", state)
        return

    # 有變化才推播
    if state != last_state:
        emoji = "🎉" if state == "AVAILABLE" else ("🚫" if state == "SOLDOUT" else "❓")
        hit_text = f"（偵測到：{hit}）" if hit else ""
        msg = f"{emoji} 票況變更：{state}{hit_text}\n{TARGET_URL}"
        line_push(msg)
        save_state(state)
        print("Changed:", last_state, "->", state)
    else:
        print("No change:", state)

if __name__ == "__main__":
    main()
