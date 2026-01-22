import os
import json
import hashlib
import requests

STATE_FILE = "state.json"

def env_required(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing env var: {key} (check GitHub Secrets/Workflow env mapping)")
    return v

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def push_line(access_token: str, to_user: str, message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": to_user,
        "messages": [{"type": "text", "text": message}],
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    if r.status_code >= 300:
        raise RuntimeError(f"LINE push failed: {r.status_code} {r.text}")

def detect_status(html: str) -> str:
    # 你目前訊息出現「受付中」→ 這樣判斷就會打到 AVAILABLE
    if "受付中" in html or "AVAILABLE" in html or "Available" in html:
        return "AVAILABLE（偵測到：受付中）"
    if "予定枚数終了" in html or "SOLD OUT" in html:
        return "SOLD_OUT（予定枚数終了）"
    if "受付終了" in html or "CLOSED" in html:
        return "CLOSED（受付終了）"
    return "UNKNOWN（未命中關鍵字）"

def main():
    access_token = env_required("LINE_CHANNEL_ACCESS_TOKEN")
    to_user = env_required("LINE_TO_USER")
    target_url = env_required("TARGET_URL")

    # 抓頁面
    r = requests.get(target_url, timeout=20, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ja,en;q=0.8,zh-TW;q=0.7",
    })
    r.raise_for_status()
    html = r.text

    status = detect_status(html)
    fp = sha(status + "|" + target_url)

    state = load_state()
    last_fp = state.get("last_fp")

    # ✅ 只有狀態變了才推播
    if fp != last_fp:
        msg = f"🎉 票況變更：{status}\n{target_url}"
        push_line(access_token, to_user, msg)
        state["last_fp"] = fp
        state["last_status"] = status
        save_state(state)
        print("Changed -> pushed.")
    else:
        print("No change.")

if __name__ == "__main__":
    main()
