from django.conf import settings
from telegram import Bot, Update
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, Dispatcher, Filters, MessageHandler

from .models import TelegramUser
from .payments import process_payment

FULL_NAME, CARD_NUMBER, EXPIRY_DATE = range(3)


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Assalomu alaykum! SMM Pro kursiga obuna bo‘lish uchun ismingiz va familiyangizni yuboring.")
    return FULL_NAME


def ask_card_number(update: Update, context: CallbackContext):
    context.user_data["full_name"] = update.message.text

    update.message.reply_text("💳 Karta raqamingizni kiriting (16 xonali):")
    return CARD_NUMBER


def ask_expiry_date(update: Update, context: CallbackContext):
    card_number = update.message.text.replace(" ", "")

    if not card_number.isdigit() or len(card_number) != 16:
        update.message.reply_text("❌ Karta raqami noto‘g‘ri! 16 ta raqamdan iborat bo‘lishi kerak.")
        return CARD_NUMBER

    context.user_data["card_number"] = card_number

    update.message.reply_text("📅 Karta amal qilish muddatini kiriting (MM/YY):")
    return EXPIRY_DATE


def process_card(update: Update, context: CallbackContext):
    expiry_date = update.message.text.strip()

    if not expiry_date or len(expiry_date) != 5 or expiry_date[2] != "/":
        update.message.reply_text("❌ Amal qilish muddati noto‘g‘ri! MM/YY formatida bo‘lishi kerak.")
        return EXPIRY_DATE

    context.user_data["expiry_date"] = expiry_date
    user_id = update.message.chat_id

    full_name = context.user_data["full_name"]
    card_number = context.user_data["card_number"]

    success = True

    if success:

        TelegramUser.objects.update_or_create(
            user_id=user_id,
            defaults={
                "full_name": full_name,
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


bot = Bot(token=settings.BOT_TOKEN)

dispatcher = Dispatcher(bot, None)

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        FULL_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_card_number)],
        CARD_NUMBER: [MessageHandler(Filters.text & ~Filters.command, ask_expiry_date)],
        EXPIRY_DATE: [MessageHandler(Filters.text & ~Filters.command, process_card)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

dispatcher.add_handler(conv_handler)
