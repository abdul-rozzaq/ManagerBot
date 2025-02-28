import re
import time
from datetime import datetime

from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, Dispatcher, Filters, MessageHandler, Updater

from .models import TelegramUser
from .payments import process_payment

FULL_NAME, PHONE_NUMBER, CARD_NUMBER, EXPIRY_DATE = range(4)


home_page_buttons = [
    ["💳 Sotib Olish", "📞 Menejer bilan aloqa"],
    ["ℹ️ Kanal haqida", "❓ F.A.Q"],
    ["⚙️ Obunani boshqarish"],
]


def start(update: Update, context: CallbackContext):
    """Botni ishga tushirish"""
    reply_markup = ReplyKeyboardMarkup(home_page_buttons, resize_keyboard=True)
    update.message.reply_text("👋 Assalomu alaykum! SMM kursiga obuna bo‘lish uchun ismingiz va familiyangizni yuboring.", reply_markup=ReplyKeyboardRemove())

    return FULL_NAME


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Jarayon bekor qilindi.")
    return ConversationHandler.END


def validate_full_name(update: Update, context: CallbackContext):
    full_name = update.message.text.strip()
    if not full_name:
        update.message.reply_text("Iltimos, to‘liq ismingizni kiriting.")
        return FULL_NAME

    context.user_data["full_name"] = full_name
    update.message.reply_text("Endi telefon raqamingizni ulashing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📞 Telefonni ulash", request_contact=True)]], resize_keyboard=True))
    return PHONE_NUMBER


def validate_phone_number(update: Update, context: CallbackContext):
    phone_number = update.message.contact.phone_number

    if not update.message.contact or not re.match(r"^\+?\d{9,15}$", phone_number):
        update.message.reply_text("❌ Telefon raqami noto‘g‘ri! Iltimos, to‘g‘ri raqam kiriting.")
        return PHONE_NUMBER

    user_id = update.message.chat_id

    context.user_data["phone_number"] = phone_number

    TelegramUser.objects.update_or_create(
        user_id=user_id,
        defaults={
            "full_name": context.user_data["full_name"],
            "phone_number": context.user_data["phone_number"],
        },
    )

    update.message.reply_text(
        f"{context.user_data['full_name']}, ro'yxatdan o'tganingiz uchun rahmat! \n\n" "Klubga qo‘shilish uchun 'Sotib olish' tugmasi orqali to‘lovni amalga oshiring.",
        reply_markup=ReplyKeyboardMarkup(home_page_buttons, resize_keyboard=True),
    )
    return ConversationHandler.END


def buy(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📌 **To‘lov tafsilotlari**:\n\n"
        "💰 **Xizmat narxi**: 350 000 so‘m\n"
        "⏳ **Obuna muddati**: 1 oy\n\n"
        "✅ To‘lov faqat **UzCard** yoki **Humo** kartalari orqali amalga oshiriladi.\n"
        "💳 Iltimos, karta raqamingizni kiriting (16 ta raqam):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    return CARD_NUMBER


def validate_card_number(update: Update, context: CallbackContext):
    card_number = update.message.text.strip()
    if not re.match(r"^[0-9]{16}$", card_number):
        update.message.reply_text("❌ Karta raqami noto‘g‘ri! 16 xonali raqam kiriting.")
        return CARD_NUMBER

    update.message.delete()

    context.user_data["card_number"] = card_number
    update.message.reply_text("Iltimos, amal qilish muddatini MM/YY formatida kiriting:")
    return EXPIRY_DATE


def validate_expiry_date(update: Update, context: CallbackContext):
    expiry_date = update.message.text.strip()

    if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{2}$", expiry_date):
        update.message.reply_text("❌ Amal qilish muddati noto‘g‘ri! MM/YY formatida kiriting.")
        return EXPIRY_DATE

    update.message.delete()

    month, year = map(int, expiry_date.split("/"))
    current_year = int(str(datetime.now().year)[-2:])
    current_month = datetime.now().month

    if year < current_year or (year == current_year and month < current_month):
        update.message.reply_text("❌ Karta muddati o‘tgan! Iltimos, yaroqli karta kiriting.")
        return EXPIRY_DATE

    context.user_data["expiry_date"] = expiry_date

    user_id = update.message.chat_id
    card_number = context.user_data["card_number"]

    update.message.reply_text("To'lov amalga oshirilmoqda ⏳")

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


updater = Updater(token=settings.BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher


dispatcher.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULL_NAME: [MessageHandler(Filters.text & ~Filters.command, validate_full_name)],
            PHONE_NUMBER: [MessageHandler(Filters.contact | (Filters.text & ~Filters.command), validate_phone_number)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
)

dispatcher.add_handler(
    ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(r"^💳 Sotib Olish$"), buy)],
        states={
            CARD_NUMBER: [MessageHandler(Filters.text & ~Filters.command, validate_card_number)],
            EXPIRY_DATE: [MessageHandler(Filters.text & ~Filters.command, validate_expiry_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
)

dispatcher.add_handler(MessageHandler(Filters.regex(r"^📞 Menejer bilan aloqa$"), contact_manager))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^ℹ️ Kanal haqida$"), channel_info))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❓ F.A.Q$"), faq))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^⚙️ Obunani boshqarish$"), manage_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❌ Obunani bekor qilish$"), cancel_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^🔙 Ortga$"), back_to_main))
