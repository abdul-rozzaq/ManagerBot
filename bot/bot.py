import re
from datetime import datetime

from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, Dispatcher, Filters, MessageHandler, Updater

from .models import TelegramUser
from .payments import process_payment

FULL_NAME, CARD_NUMBER, EXPIRY_DATE = range(3)

# Asosiy menyu tugmalari
home_page_buttons = [
    ["💳 Sotib Olish", "📞 Menejer bilan aloqa"],
    ["ℹ️ Kanal haqida", "❓ F.A.Q"],
    ["⚙️ Obunani boshqarish"],
]


def start(update: Update, context: CallbackContext):
    """Botni ishga tushirish"""
    reply_markup = ReplyKeyboardMarkup(home_page_buttons, resize_keyboard=True)
    update.message.reply_text("👋 Assalomu alaykum! SMM kursiga obuna bo‘lish uchun ismingiz va familiyangizni yuboring.", reply_markup=reply_markup)


def buy(update: Update, context: CallbackContext):
    """Sotib olish tugmasi bosilganda"""
    keyboard = [
        [
            InlineKeyboardButton("💳 Humo/UzCard", callback_data="humo-uzCard"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    update.message.reply_text(
        "💰 O‘zbekistonda bo‘lsangiz Uzcard yoki Humo orqali to‘lov qilsangiz bo‘ladi.\n\n"
        "🌍 Chet elda bo‘lsangiz Visa, Mastercard, Rus kartalari va boshqa ko'plab kartalar orqali to‘lovni amalga oshirishingiz mumkin.\n\n"
        "💳 To‘lovni amalga oshirish uchun karta turini tanlang:\n\n"
        "<blockquote><a href='https://telegra.ph/Sizdan-karta-malumotlarini-sorayotganimizning-sababi-01-08'>Sizdan karta ma'lumotlarini so'rayotganimizni sababi</a></blockquote>",
        reply_markup=reply_markup,
        parse_mode="html",
        disable_web_page_preview=True,
    )


def manage_subscription(update: Update, context: CallbackContext):
    """Obunani boshqarish menyusi"""
    keyboard = [["❌ Obunani bekor qilish"], ["🔙 Ortga"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("⚙️ Tugmalardan birini tanlang:", reply_markup=reply_markup)


def cancel_subscription(update: Update, context: CallbackContext):
    """Obunani bekor qilish"""
    update.message.reply_text("❌ Sizning obunangiz bekor qilindi.")


def contact_manager(update: Update, context: CallbackContext):
    """Menejer bilan aloqa"""
    update.message.reply_text("📞 Menejer bilan bog‘lanish uchun quyidagi kontaktga yozing:\n" "📩 Telegram: @your_manager_username")


def channel_info(update: Update, context: CallbackContext):
    """Kanal haqida ma'lumot"""
    update.message.reply_text(
        "📢 Bizning kanal haqida ma'lumot:\n\n" "Bu yerda siz eng so‘nggi yangiliklar va kurs bo‘yicha qo‘llanmalarni topishingiz mumkin.\n" "🔗 Kanal havolasi: https://t.me/your_channel"
    )


def faq(update: Update, context: CallbackContext):
    """Tez-tez so‘raladigan savollar (F.A.Q)"""
    update.message.reply_text(
        "❓ Tez-tez so‘raladigan savollar:\n\n"
        "1️⃣ Qanday qilib obuna bo‘lish mumkin?\n"
        "👉 Tugmalar orqali kerakli to‘lov turini tanlab, to‘lovni amalga oshiring.\n\n"
        "2️⃣ Obuna qancha davom etadi?\n"
        "👉 Obuna har oy avtomatik ravishda yangilanadi.\n\n"
        "3️⃣ Menejer bilan qanday bog‘lanish mumkin?\n"
        "👉 '📞 Menejer bilan aloqa' tugmasini bosing."
    )


def back_to_main(update: Update, context: CallbackContext):
    """Asosiy menyuga qaytish"""
    reply_markup = ReplyKeyboardMarkup(home_page_buttons, resize_keyboard=True)
    update.message.reply_text("🏠 Quyidagi tugmalardan birini tanlang:", reply_markup=reply_markup)


def humo_uzcard(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.reply_text("Iltimos, karta raqamingizni kiriting:")
    return CARD_NUMBER


def validate_card_number(update: Update, context: CallbackContext):
    card_number = update.message.text.strip()
    
    if not re.match(r"^[0-9]{16,20}$", card_number):
        update.message.reply_text("❌ Karta raqami noto‘g‘ri! 16 yoki 20 xonali raqam kiriting.")
        return CARD_NUMBER
    
    context.user_data["card_number"] = card_number.replace(" ", "")
    update.message.reply_text("Endi karta amal qilish muddatini MM/YY formatida kiriting:")
    return EXPIRY_DATE


def validate_expiry_date(update: Update, context: CallbackContext):
    expiry_date = update.message.text.strip()

    if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{2}$", expiry_date):
        update.message.reply_text("❌ Amal qilish muddati noto‘g‘ri! MM/YY formatida kiriting.")
        return EXPIRY_DATE

    month, year = map(int, expiry_date.split("/"))
    current_year = int(str(datetime.now().year)[-2:])
    current_month = datetime.now().month

    if year < current_year or (year == current_year and month < current_month):
        update.message.reply_text("❌ Karta muddati o‘tgan! Iltimos, yaroqli karta kiriting.")
        return EXPIRY_DATE

    context.user_data["expiry_date"] = expiry_date

    user_id = update.message.chat_id
    card_number = context.user_data["card_number"]
    success = True

    if success:
        TelegramUser.objects.update_or_create(
            user_id=user_id,
            defaults={
                "card_number": card_number,
                "expiry_date": expiry_date,
            },
        )

        try:
            invite_link = context.bot.create_chat_invite_link(chat_id=settings.CHANNEL_ID, member_limit=1, expire_date=None)

            update.message.reply_text(f"✅ To‘lov muvaffaqiyatli amalga oshirildi!\n🔗 Kanalga qo‘shilish havolangiz: {invite_link.invite_link}")

        except Exception as e:
            update.message.reply_text(f"⚠️ Taklif havolasini yaratishda xatolik yuz berdi: {e}")

    else:
        update.message.reply_text("❌ To‘lov amalga oshmadi. Iltimos, boshqa kartani kiriting.")

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Jarayon bekor qilindi.")
    return ConversationHandler.END


updater = Updater(token=settings.BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher


dispatcher.add_handler(
    ConversationHandler(
        entry_points=[CallbackQueryHandler(humo_uzcard, pattern="^humo-uzCard$")],
        states={
            CARD_NUMBER: [MessageHandler(Filters.text & ~Filters.command, validate_card_number)],
            EXPIRY_DATE: [MessageHandler(Filters.text & ~Filters.command, validate_expiry_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
)


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^💳 Sotib Olish$"), buy))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^📞 Menejer bilan aloqa$"), contact_manager))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^ℹ️ Kanal haqida$"), channel_info))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❓ F.A.Q$"), faq))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^⚙️ Obunani boshqarish$"), manage_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❌ Obunani bekor qilish$"), cancel_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^🔙 Ortga$"), back_to_main))
