from django.db import models


class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True)

    full_name = models.CharField(max_length=255, null=True, blank=True)
    card_number = models.CharField(max_length=16, null=True, blank=True)
    expiry_date = models.CharField(max_length=5, null=True, blank=True)
    last_payment = models.DateField(auto_now=True, null=True, blank=True)


    def __str__(self):
        return f"{self.full_name} ({self.user_id})"
