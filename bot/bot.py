import re
import time
from datetime import datetime
from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, LabeledPrice
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, Dispatcher, Filters, MessageHandler, Updater, PreCheckoutQueryHandler
from .models import TelegramUser


FULL_NAME, PHONE_NUMBER = range(2)


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


def validate_full_name(update: Update, context: CallbackContext):
    """Toʻliq ismni tekshirish"""
    full_name = update.message.text.strip()
    if not full_name:
        update.message.reply_text("Iltimos, to‘liq ismingizni kiriting.")
        return FULL_NAME

    context.user_data["full_name"] = full_name
    update.message.reply_text("Endi telefon raqamingizni ulashing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📞 Telefonni ulash", request_contact=True)]], resize_keyboard=True))
    return PHONE_NUMBER


def validate_phone_number(update: Update, context: CallbackContext):
    """Telefon raqamini tekshirish"""
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
    """Sotib olish bosilganda to'lov haqida ma'lumot va invoice yuborish"""
    update.message.reply_text(
        "📌 **To‘lov tafsilotlari**:\n\n"
        "💰 **Xizmat narxi**: 350 000 so‘m\n"
        "⏳ **Obuna muddati**: 1 oy\n\n"
        "✅ To‘lov faqat **UzCard** yoki **Humo** kartalari orqali amalga oshiriladi.\n\n"
        "To'lovni amalga oshirish uchun quyidagi tugmani bosing:",
        parse_mode="Markdown",
    )

    title = "SMM Kursga Obuna bo'lish"
    description = "1 oylik obuna uchun to'lov"
    payload = "custom_payload"
    currency = "UZS"
    prices = [LabeledPrice("Obuna narxi", 350000 * 100)]

    update.message.reply_invoice(
        title,
        description,
        payload,
        settings.PAYMENT_PROVIDER_TOKEN,
        currency,
        prices,
    )


def successful_payment_handler(update: Update, context: CallbackContext):
    """To'lov muvaffaqiyatli amalga oshirilganda kanalga qo'shilish havolasini yuborish"""

    try:

        invite_link = context.bot.create_chat_invite_link(chat_id=settings.CHANNEL_ID, member_limit=1, expire_date=int(time.time()) + 3600)

        update.message.reply_text(
            f"✅ To‘lov muvaffaqiyatli amalga oshirildi!\n\n" f"🔗 Quyidagi havola orqali kanalga qo‘shiling (havola 1 soat davomida amal qiladi):\n" f"{invite_link.invite_link}"
        )

    except Exception as e:
        update.message.reply_text(f"⚠️ Kanalga qo'shilish havolasini yaratishda xatolik yuz berdi. Iltimos, menejer bilan bog'laning: @your_manager_username")


def precheckout_callback(update: Update, context: CallbackContext):
    """To'lovni oldindan tekshirish"""
    query = update.pre_checkout_query
    query.answer(ok=True)


def cancel(update: Update, context: CallbackContext):
    """Jarayonni bekor qilish"""
    update.message.reply_text("❌ Jarayon bekor qilindi.")
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


dispatcher.add_handler(MessageHandler(Filters.regex(r"^💳 Sotib Olish$"), buy))


dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_handler))


dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))


dispatcher.add_handler(MessageHandler(Filters.regex(r"^📞 Menejer bilan aloqa$"), contact_manager))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^ℹ️ Kanal haqida$"), channel_info))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❓ F.A.Q$"), faq))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^⚙️ Obunani boshqarish$"), manage_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^❌ Obunani bekor qilish$"), cancel_subscription))
dispatcher.add_handler(MessageHandler(Filters.regex(r"^🔙 Ortga$"), back_to_main))
