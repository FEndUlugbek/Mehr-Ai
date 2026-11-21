# MEHR AI — ovozli yordamchi (demo)

Ovozni tanish -> AI javobi -> ovozli javob, eslatmalar, SOS (Telegram).

## Ishga tushirish
1. `pip install -r requirements.txt`
2. `.env.example` ni `.env` ga nusxalang va kalitlarni yozing
   - AI: `GEMINI_API_KEY` (aistudio.google.com, bepul) YOKI `ANTHROPIC_API_KEY` (console.anthropic.com)
   - Telegram: `TELEGRAM_BOT_TOKEN` (@BotFather), `TELEGRAM_CHAT_IDS` (yaqinning ID'si; u botga avval /start yozgan bo'lsin)
3. `python server.py`
4. Chrome'da http://localhost:8000 oching. Tekshirish: http://localhost:8000/health

## Internetga chiqarish (Render.com)
- Build: `pip install -r requirements.txt`
- Start: `gunicorn server:app`
- Environment bo'limiga `.env` dagi kalitlarni kiriting (`.env` faylini GitHub'ga yuklamang)

## Eslatma
- Faqat Chrome'da (Android/kompyuter) ovozni tanish ishlaydi; mikrofon uchun https yoki localhost kerak.
- Robot shifokor emas: dori dozasi va tashxis bermaydi.
- Manzilni faqat kerakli odamlarga bering (AI balansi sarflanadi).
