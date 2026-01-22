from flask import Flask, request, abort

app = Flask(__name__)

@app.get("/")
def home():
    return "OK"

@app.post("/callback")
def callback():
    # 先簡單回應，之後再加 LINE Webhook 驗證
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
