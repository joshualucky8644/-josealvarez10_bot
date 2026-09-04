"""
Jose Alvarez - İlişki Koçu Telegram Botu (Türkçe)
---------------------------------------------------
Bir kullanıcı /start yazdığında karşılama mesajı ve üç konu butonu gösterilir:
Aşk, Aile, Arkadaşlık. Kullanıcı bir konu seçtikten sonra serbest sohbet moduna
geçilir ve mesajlar Gemini API'sine (Google) gönderilerek destekleyici, empatik
yanıtlar üretilir.

REDIRECT MODE: Admin gizli komutlarla botu casino/promosyon moduna alabilir.
- "REDIRECT" yazınca bot promosyon moduna geçer
- "REVERSE" yazınca normal moda döner
- 2 saatte bir tüm aktif kullanıcılara hatırlatma mesajı gönderir

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
import asyncio
from datetime import datetime
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

# ===== ENV VARIABLES =====
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

genai.configure(api_key=GEMINI_API_KEY)

# ===== GLOBAL BOT MODES =====
GLOBAL_BOT_MODE = "NORMAL"  # "NORMAL" or "REDIRECT"

# ===== ADMIN SECRET COMMANDS =====
ADMIN_REDIRECT_CMD = "REDIRECT"  # Change this to your secret word
ADMIN_REVERSE_CMD = "REVERSE"    # Change this to your secret word

# ===== REDIRECT MODE CONFIGURATION =====
# Local image file (place promo_image.jpg in the same directory as bot.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REDIRECT_IMAGE_PATH = os.path.join(BASE_DIR, "promo_image.jpg")

REDIRECT_MESSAGE = (
    "🎁 *Bonus fırsatlarını keşfet!*\n\n"
    "🔥 *750 TL Deneme Bonusu*\n"
    "💰 *%400 Yatırım Bonusu*\n"
    "🛡 *%35 Kayıp Bonusu*\n\n"
    "Avantajları incelemek ve detayları görmek için aşağıdaki butona tıkla. 👇"
)

REDIRECT_BUTTON_TEXT = "🎁 Bonusları İncele"
REDIRECT_WEBSITE_URL = "https://strz.cc/Pu0_"

# ===== REMINDER SETTINGS =====
REMINDER_INTERVAL_HOURS = 2  # Send reminder every 2 hours

# ===== ADMIN LIST (Optional security) =====
ADMIN_USER_IDS = []  # Add your Telegram user IDs here for extra security
# Get your ID from @userinfobot

# ===== USER TRACKING =====
active_users = set()  # Track users who have started the bot

# ===== TOPICS CONFIGURATION =====
TOPICS = {
    "romance": {"label": "❤️ Aşk", "name": "Aşk"},
    "family": {"label": "👪 Aile", "name": "Aile"},
    "friendship": {"label": "🤝 Arkadaşlık", "name": "Arkadaşlık"},
}

# ===== WELCOME MESSAGES =====
NORMAL_WELCOME_TEXT = (
    "Merhaba, ben Jose Alvarez 💬\n\n"
    "İlişkilerinle ilgili yaşadığın her şeyi -aşk, aile ya da arkadaşlık- "
    "birlikte düşünmene yardımcı olmak için buradayım.\n\n"
    "Aklında ne var?"
)

# ===== SYSTEM PROMPT =====
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

# ===== USER STATE =====
user_state: dict[int, dict] = {}

# ===== BUILD KEYBOARD =====
def build_topic_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(TOPICS["romance"]["label"], callback_data="topic:romance")],
        [InlineKeyboardButton(TOPICS["family"]["label"], callback_data="topic:family")],
        [InlineKeyboardButton(TOPICS["friendship"]["label"], callback_data="topic:friendship")],
    ]
    return InlineKeyboardMarkup(buttons)

# ===== REDIRECT PROMO FUNCTION =====
async def send_redirect_promo(update: Update, context: ContextTypes.DEFAULT_TYPE, is_reminder=False):
    """Send the redirect promotional content with image"""
    chat_id = update.effective_chat.id if update else None
    message = update.message if update else None
    
    try:
        # Create the inline keyboard
        keyboard = [
            [InlineKeyboardButton(REDIRECT_BUTTON_TEXT, url=REDIRECT_WEBSITE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Reminder message suffix
        reminder_suffix = "\n\n⏰ *Bu fırsatı kaçırma!*" if is_reminder else ""
        
        # 1. Send the image from local file
        if os.path.exists(REDIRECT_IMAGE_PATH):
            with open(REDIRECT_IMAGE_PATH, 'rb') as photo:
                if message:
                    await message.reply_photo(
                        photo=photo,
                        caption="🎰 *KAZANMAYA HAZIR MISIN?*",
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption="🎰 *KAZANMAYA HAZIR MISIN?*",
                        parse_mode='Markdown'
                    )
        else:
            logger.error(f"Image not found: {REDIRECT_IMAGE_PATH}")
            # Fallback: Send text only
            if message:
                await message.reply_text("⚠️ Görsel yüklenemedi, ancak fırsatlar devam ediyor!")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Görsel yüklenemedi, ancak fırsatlar devam ediyor!"
                )
        
        # 2. Small delay between messages
        await asyncio.sleep(1)
        
        # 3. Send the bonus message with button
        promo_text = REDIRECT_MESSAGE + reminder_suffix
        
        if message:
            await message.reply_text(
                promo_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=promo_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error sending promo: {e}")
        # Emergency fallback
        fallback_text = (
            "🎁 *Bonus fırsatlarını kaçırma!*\n\n"
            "Detaylar için butona tıkla 👇"
        )
        if message:
            await message.reply_text(
                fallback_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Bonusları İncele", url=REDIRECT_WEBSITE_URL)]
                ]),
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=fallback_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Bonusları İncele", url=REDIRECT_WEBSITE_URL)]
                ]),
                parse_mode='Markdown'
            )

# ===== REMINDER FUNCTION =====
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder messages to all active users every 2 hours"""
    global GLOBAL_BOT_MODE
    
    # Only send reminders if in REDIRECT mode
    if GLOBAL_BOT_MODE != "REDIRECT":
        return
    
    logger.info(f"[{datetime.now()}] Sending reminders to {len(active_users)} users...")
    
    # Create the inline keyboard
    keyboard = [
        [InlineKeyboardButton(REDIRECT_BUTTON_TEXT, url=REDIRECT_WEBSITE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    reminder_suffix = "\n\n⏰ *Bu fırsatı kaçırma!*"
    promo_text = REDIRECT_MESSAGE + reminder_suffix
    
    # Send to each active user
    for user_id in list(active_users):
        try:
            # Send image with caption
            if os.path.exists(REDIRECT_IMAGE_PATH):
                with open(REDIRECT_IMAGE_PATH, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption="🎰 *KAZANMAYA HAZIR MISIN?*\n\n⏰ *2 Saatlik Hatırlatma!*",
                        parse_mode='Markdown'
                    )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎰 *KAZANMAYA HAZIR MISIN?*\n\n⏰ *2 Saatlik Hatırlatma!*",
                    parse_mode='Markdown'
                )
            
            await asyncio.sleep(0.5)  # Small delay to avoid rate limiting
            
            # Send bonus message with button
            await context.bot.send_message(
                chat_id=user_id,
                text=promo_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"Reminder sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send reminder to {user_id}: {e}")
            # Remove inactive users
            if "chat not found" in str(e) or "user not found" in str(e):
                active_users.discard(user_id)

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with mode-based responses"""
    global GLOBAL_BOT_MODE
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Track user for reminders
    active_users.add(user_id)
    
    # Check if in REDIRECT mode
    if GLOBAL_BOT_MODE == "REDIRECT":
        # Send redirect promotional message with image
        await send_redirect_promo(update, context)
        return
    
    # NORMAL MODE - Standard welcome with topic selection
    user_state[chat_id] = {"topic": None, "history": []}
    await update.message.reply_text(NORMAL_WELCOME_TEXT, reply_markup=build_topic_keyboard())

# ===== TOPIC CHOSEN =====
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

# ===== HANDLE MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages with admin command interception"""
    global GLOBAL_BOT_MODE
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text
    
    # Track user for reminders
    active_users.add(user_id)
    
    # ===== ADMIN COMMAND INTERCEPTION =====
    if text == ADMIN_REDIRECT_CMD:
        # Check if user is admin (optional)
        if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("⛔ Yetkisiz komut.")
            return
            
        GLOBAL_BOT_MODE = "REDIRECT"
        await update.message.reply_text(
            "✅ *Yönlendirme modu aktifleştirildi!*\n"
            "Bot artık casino bonuslarını tanıtacak.\n\n"
            f"⏰ Hatırlatmalar her {REMINDER_INTERVAL_HOURS} saatte bir gönderilecek.\n\n"
            "Normal moda dönmek için `REVERSE` yazın.",
            parse_mode='Markdown'
        )
        return
    
    elif text == ADMIN_REVERSE_CMD:
        # Check if user is admin (optional)
        if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("⛔ Yetkisiz komut.")
            return
            
        GLOBAL_BOT_MODE = "NORMAL"
        await update.message.reply_text(
            "✅ *Normal mod aktifleştirildi!*\n"
            "Bot artık ilişki koçu olarak çalışıyor.",
            parse_mode='Markdown'
        )
        return
    
    # ===== REDIRECT MODE =====
    if GLOBAL_BOT_MODE == "REDIRECT":
        # Send the promo again when user messages in redirect mode
        await send_redirect_promo(update, context)
        return
    
    # ===== NORMAL MODE - Gemini AI Response =====
    state = user_state.get(chat_id)
    if not state or not state.get("topic"):
        # User hasn't selected a topic yet
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

# ===== MENU COMMAND =====
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/menu ile kullanıcı istediği zaman konu menüsüne dönebilir."""
    # Check if in redirect mode
    if GLOBAL_BOT_MODE == "REDIRECT":
        await update.message.reply_text(
            "⚠️ *Bot şu anda promosyon modunda.*\n"
            "Konu menüsü için lütfen normal moda geçin.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "Hangi konuda konuşmak istersin?", reply_markup=build_topic_keyboard()
    )

# ===== STATUS COMMAND =====
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status - Show current bot status (admin only)"""
    user_id = update.effective_user.id
    
    if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ Yetkisiz komut.")
        return
    
    status = "🔴 YÖNLENDİRME" if GLOBAL_BOT_MODE == "REDIRECT" else "🟢 NORMAL"
    active_count = len(active_users)
    
    # Check if image exists
    image_status = "✅ Var" if os.path.exists(REDIRECT_IMAGE_PATH) else "❌ Yok"
    
    await update.message.reply_text(
        f"*Bot Durumu:* {status}\n"
        f"*Mod:* {GLOBAL_BOT_MODE}\n"
        f"*Aktif Kullanıcı:* {active_count}\n"
        f"*Hatırlatma Aralığı:* Her {REMINDER_INTERVAL_HOURS} saat\n"
        f"*Görsel Durumu:* {image_status}",
        parse_mode='Markdown'
    )

# ===== STARTUP REMINDER SETUP =====
async def post_init(application):
    """Set up the reminder job when bot starts"""
    job_queue = application.job_queue
    
    if job_queue:
        # Schedule the reminder job every 2 hours
        job_queue.run_repeating(
            send_reminder,
            interval=REMINDER_INTERVAL_HOURS * 3600,  # 2 hours in seconds
            first=60  # Start after 60 seconds
        )
        logger.info(f"⏰ Hatırlatma işi her {REMINDER_INTERVAL_HOURS} saatte bir planlandı")
        
        # Check if image exists on startup
        if os.path.exists(REDIRECT_IMAGE_PATH):
            logger.info(f"✅ Görsel bulundu: {REDIRECT_IMAGE_PATH}")
        else:
            logger.warning(f"❌ Görsel bulunamadı: {REDIRECT_IMAGE_PATH}")
    else:
        logger.warning("Job queue not available!")

# ===== MAIN =====
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(topic_chosen, pattern=r"^topic:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set up reminder on startup
    application.post_init = post_init

    logger.info("Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
