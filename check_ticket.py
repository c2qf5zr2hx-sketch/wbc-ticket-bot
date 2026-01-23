import os
import time
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def line_push(token: str, to_user: str, text: str) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": to_user,
        "messages": [{"type": "text", "text": text}],
    }
    r = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=20)
    if r.status_code >= 400:
        print("LINE push failed:", r.status_code, r.text)

def fetch_page(url: str, timeout: int = 25) -> requests.Response:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

def parse_status(html: str) -> str:
    if "受付中" in html or "AVAILABLE" in html or "Available" in html:
        return "AVAILABLE（偵測到：受付中）"
    if "予定枚数終了" in html or "SOLD OUT" in html:
        return "SOLD_OUT（予定枚数終了）"
    if "受付終了" in html or "CLOSED" in html:
        return "CLOSED（受付終了）"
    return "UNKNOWN（未命中關鍵字）"

def main():
    token = must_env("LINE_CHANNEL_ACCESS_TOKEN")
    to_user = must_env("LINE_TO_USER")
    target_url = must_env("TARGET_URL")

    tries = 3
    for i in range(tries):
        try:
            resp = fetch_page(target_url, timeout=25)

            if resp.status_code == 403:
                line_push(
                    token, to_user,
                    "⚠️ 票況檢查被網站擋下（HTTP 403）。\n"
                    "這通常是網站防爬/封鎖雲端 IP（GitHub Actions 很常遇到）。\n"
                    f"{target_url}"
                )
                print("403 Forbidden - handled.")
                return  # ✅ 讓 workflow 成功結束（不紅叉）

            if resp.status_code != 200:
                line_push(token, to_user, f"⚠️ 票況頁回傳 HTTP {resp.status_code}\n{target_url}")
                print(f"HTTP {resp.status_code} - handled.")
                return

            status = parse_status(resp.text)
            line_push(token, to_user, f"🎫 票況檢查結果：{status}\n{target_url}")
            print("OK - pushed.")
            return

        except Exception as e:
            # 最後一次才通知錯誤
            if i == tries - 1:
                line_push(token, to_user, f"⚠️ 票況檢查發生錯誤：{e}\n{target_url}")
                print("Error:", e)
                return
            time.sleep(2)

if __name__ == "__main__":
    main()
