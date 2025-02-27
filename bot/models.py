from datetime import date, timedelta

from django.db import models


class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True)
    card_number = models.CharField(max_length=16, null=True, blank=True)
    expiry_date = models.CharField(max_length=5, null=True, blank=True)
    last_payment = models.DateField(auto_now=True, null=True, blank=True)
    is_subscribed = models.BooleanField(default=True)

    def is_available(self):
        """Foydalanuvchi obunasi hali amal qiladimi?"""
        if not self.last_payment:
            return False

        one_month_ago = date.today() - timedelta(days=30)
        return self.last_payment >= one_month_ago

    def __str__(self):
        return f"TelegramUser(id={self.user_id}, available={self.is_available()}, last_payment={self.last_payment})"
