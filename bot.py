"""
Jose Alvarez - İlişki Koçu Telegram Botu (Türkçe)
---------------------------------------------------
Bir kullanıcı /start yazdığında karşılama mesajı ve üç konu butonu gösterilir:
Aşk, Aile, Arkadaşlık. Kullanıcı bir konu seçtikten sonra serbest sohbet moduna
geçilir ve mesajlar Gemini API'sine (Google) gönderilerek destekleyici, empatik
yanıtlar üretilir.

Kurulum:
    pip install -r requirements.txt

Ortam değişkenleri (.env dosyasına veya Railway "Variables" bölümüne ekleyin):
    TELEGRAM_BOT_TOKEN=...   (BotFather'dan alınır)
    GEMINI_API_KEY=...       (aistudio.google.com'dan alınır, ücretsiz)

Çalıştırma:
    python bot.py
"""

import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

genai.configure(api_key=GEMINI_API_KEY)

# --- Basit bellek içi durum (kalıcı değil; sunucu yeniden başlarsa sıfırlanır) ---
# Üretimde bunun yerine bir veritabanı (SQLite/Postgres/Redis) kullanmanız önerilir.
user_state: dict[int, dict] = {}

TOPICS = {
    "romance": {"label": "❤️ Aşk", "name": "Aşk"},
    "family": {"label": "👪 Aile", "name": "Aile"},
    "friendship": {"label": "🤝 Arkadaşlık", "name": "Arkadaşlık"},
}

WELCOME_TEXT = (
    "Merhaba, ben Jose Alvarez 💬\n\n"
    "İlişkilerinle ilgili yaşadığın her şeyi -aşk, aile ya da arkadaşlık- "
    "birlikte düşünmene yardımcı olmak için buradayım.\n\n"
    "Aklında ne var?"
)

SYSTEM_PROMPT_TEMPLATE = """Sen Jose Alvarez adında, sıcak ve empatik bir ilişki koçusun. \
Bir Telegram botu üzerinden kullanıcılarla Türkçe olarak sohbet ediyorsun. \
Şu an kullanıcı "{topic}" konusunu seçti.

DİL KURALI (kesinlikle uy): Kullanıcı hangi dilde yazarsa yazsın — Türkçe, \
İngilizce ya da başka bir dil — sen HER ZAMAN sadece Türkçe cevap ver. \
Kullanıcının dilini asla taklit etme, çeviri yapma, başka dilde tek kelime \
bile kullanma. Yanıtların tamamı her zaman doğal, akıcı Türkçe olmalı.

Üslubun:
- Sıcak, samimi, yargılamayan ve destekleyici ol.
- Kullanıcıyı önce dinle, ne yaşadığını anlamaya çalış, sonra somut ve dengeli \
öneriler sun.
- Kısa ve doğal cümleler kullan; bir terapist gibi resmi değil, güvenilir bir \
arkadaş gibi konuş.
- Gerektiğinde açıklayıcı sorular sor ama art arda çok fazla soru sorma.

Sınırların (kesinlikle uy):
- Bir kişiye zarar vermek, intikam almak, birini takip etmek/gözetlemek, \
manipüle etmek veya "ders vermek" için plan, taktik ya da yöntem ASLA önerme. \
Böyle bir istek gelirse nazikçe reddet, kullanıcının öfke/acı gibi duygusunu \
onayla, ve bunun yerine duygularıyla sağlıklı şekilde başa çıkmasına yardımcı ol.
- Kullanıcı kendine zarar vermekten ya da intihardan bahsederse, tavsiye vermeyi \
bırak, ciddiyetle karşıla ve onu güvenilir biriyle (yakını, profesyonel destek \
hattı) konuşmaya yönlendir.
- Tıbbi, hukuki ya da psikiyatrik teşhis koyma; gerektiğinde bir uzmana \
danışmasını öner.
- Kimseyi kötülemeyi teşvik etme; dengeli bir bakış açısı sun.

Bu sınırlar dışında, ilişkiler, iletişim, kırgınlıklar, ayrılıklar, aile içi \
çatışmalar, arkadaşlık sorunları gibi her konuda -ve kullanıcı isterse alakasız \
konularda da- rahatça ve etkili şekilde sohbet edebilirsin."""


def build_topic_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(TOPICS["romance"]["label"], callback_data="topic:romance")],
        [InlineKeyboardButton(TOPICS["family"]["label"], callback_data="topic:family")],
        [InlineKeyboardButton(TOPICS["friendship"]["label"], callback_data="topic:friendship")],
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_state[chat_id] = {"topic": None, "history": []}
    await update.message.reply_text(WELCOME_TEXT, reply_markup=build_topic_keyboard())


async def topic_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    topic_key = query.data.split(":", 1)[1]
    topic_name = TOPICS[topic_key]["name"]

    user_state[chat_id] = {"topic": topic_name, "history": []}

    await query.edit_message_text(
        f"{TOPICS[topic_key]['label']}\n\n— Seni dinliyorum. Neler oluyor, anlat."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text

    state = user_state.get(chat_id)
    if not state or not state.get("topic"):
        # Kullanıcı henüz bir konu seçmediyse, genel bir koç olarak devam et.
        state = user_state.setdefault(chat_id, {"topic": "Genel", "history": []})
        state["topic"] = state.get("topic") or "Genel"

    history = state["history"]
    history.append({"role": "user", "parts": [text]})

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(topic=state["topic"])

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_prompt,
        )
        # Son 20 mesajla sınırla (basit bağlam yönetimi), son mesaj hariç geçmiş olarak gönder
        chat = model.start_chat(history=history[:-1][-20:])
        response = chat.send_message(text)
        reply_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API çağrısı başarısız oldu")
        reply_text = (
            "Şu anda küçük bir bağlantı sorunu yaşıyorum, birazdan tekrar dener misin?"
        )

    history.append({"role": "model", "parts": [reply_text]})
    await update.message.reply_text(reply_text)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/menu ile kullanıcı istediği zaman konu menüsüne dönebilir."""
    await update.message.reply_text(
        "Hangi konuda konuşmak istersin?", reply_markup=build_topic_keyboard()
    )


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(topic_chosen, pattern=r"^topic:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
