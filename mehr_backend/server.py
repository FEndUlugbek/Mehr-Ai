import os
import time
from collections import defaultdict, deque

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Bir nechta yaqin bo'lsa vergul bilan: 12345,67890
TELEGRAM_CHAT_IDS = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL", "claude-haiku-5-5")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# Gemini kaliti bo'lsa o'sha ishlatiladi (bepul tarif), bo'lmasa Claude
PROVIDER = "gemini" if GEMINI_API_KEY else "anthropic"

SYSTEM = (
    "Sen Mehr — nogironligi bor insonlar va keksalarga yordam beradigan mehribon o‘zbek tilidagi ovozli yordamchisan. "
    "Faqat o‘zbek tilida, lotin yozuvida javob ber. Javobing 1–3 qisqa, sodda gap bo‘lsin, ro‘yxat va belgilarsiz. "
    "Sen shifokor emassan: dori dozasini aytma, kasallik tashxisini qo‘yma, jiddiy holatda yaqinlariga yoki shifokorga murojaat qilishni ayt."
)

app = Flask(__name__, static_folder="static")

# --- Oddiy cheklov: kalitingiz va yaqinlaringiz bezovta bo'lmasligi uchun ---
_hits = defaultdict(deque)


def limited(bucket, limit, per_seconds):
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
    q = _hits[(bucket, ip)]
    now = time.time()
    while q and now - q[0] > per_seconds:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/health")
def health():
    return jsonify(ok=True, ai=bool(ANTHROPIC_API_KEY or GEMINI_API_KEY), provider=PROVIDER, telegram=bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS))


def call_ai(msgs):
    if PROVIDER == "gemini":
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY, "content-type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [
                    {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
                    for m in msgs
                ],
                "generationConfig": {"maxOutputTokens": 300},
            },
            timeout=30,
        )
        if not r.ok:
            raise RuntimeError(f"Gemini {r.status_code}: {r.text[:300]}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        return " ".join(p.get("text", "") for p in parts).strip()

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 300, "system": SYSTEM, "messages": msgs},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Anthropic {r.status_code}: {r.text[:300]}")
    return " ".join(b["text"] for b in r.json()["content"] if b.get("type") == "text").strip()


@app.post("/api/chat")
def chat():
    if not (ANTHROPIC_API_KEY or GEMINI_API_KEY):
        return jsonify(error="Serverda AI kaliti yo'q"), 500
    if limited("chat", 20, 60):
        return jsonify(error="Juda ko'p so'rov, bir oz kuting"), 429

    data = request.get_json(silent=True) or {}
    msgs = []
    for m in (data.get("messages") or [])[-8:]:
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) and m["content"].strip():
            msgs.append({"role": m["role"], "content": m["content"][:500]})
    while msgs and msgs[0]["role"] != "user":  # birinchi xabar user bo'lishi kerak
        msgs.pop(0)
    if not msgs:
        return jsonify(error="Xabar bo'sh"), 400

    try:
        return jsonify(reply=call_ai(msgs))
    except Exception as e:
        app.logger.error("AI xatosi: %s", e)  # sababi terminalda ko'rinadi
        return jsonify(error="AI bilan bog'lanib bo'lmadi"), 502


@app.post("/api/sos")
def sos():
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS):
        return jsonify(error="Telegram sozlanmagan"), 500
    if limited("sos", 2, 60):
        return jsonify(error="SOS yaqinda yuborilgan"), 429

    text = "🆘 MEHR AI: yordam kerak! (" + time.strftime("%H:%M") + ")"
    ok = 0
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            ok += 1 if r.ok else 0
        except Exception as e:
            app.logger.error("Telegram xatosi: %s", e)
    if not ok:
        return jsonify(error="Xabar yuborilmadi"), 502
    return jsonify(sent=ok)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
