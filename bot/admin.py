from django.contrib import admin

from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["user_id", "full_name", "phone_number", "card_number", "expiry_date", "last_payment", "is_subscribed", "is_available"]
